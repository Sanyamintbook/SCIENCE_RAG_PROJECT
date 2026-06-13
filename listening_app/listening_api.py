import os
import json
import shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid

# Import our custom modules
from backend.whisper_service import transcribe_audio
from backend.evaluator import evaluate_answer

app = FastAPI(title="Listening Assessment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSIGNMENTS_DIR = os.path.join(BASE_DIR, "data", "assignments")
SUBMISSIONS_DIR = os.path.join(BASE_DIR, "data", "submissions")
RESULTS_FILE = os.path.join(BASE_DIR, "data", "results.json")

os.makedirs(ASSIGNMENTS_DIR, exist_ok=True)
os.makedirs(SUBMISSIONS_DIR, exist_ok=True)

# Helper to load/save JSON
def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --- Endpoints ---

@app.post("/create_assignment")
async def create_assignment(
    questions_json: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """Teacher uploads audio and questions. Backend auto-transcribes expected transcript."""
    assignment_id = "assignment_1"
    
    file_ext = os.path.splitext(audio_file.filename)[1]
    if not file_ext:
        file_ext = ".wav"
        
    audio_path = os.path.join(ASSIGNMENTS_DIR, f"{assignment_id}{file_ext}")
    
    # Save the file
    with open(audio_path, "wb") as f:
        f.write(await audio_file.read())
        
    # Auto-transcribe the teacher's audio
    from backend.whisper_service import transcribe_audio
    expected_transcript = transcribe_audio(audio_path)
    
    if expected_transcript.startswith("Error"):
        expected_transcript = f"(Auto-transcription failed. Reason: {expected_transcript})"
        
    try:
        questions_list = json.loads(questions_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid questions JSON format.")
        
    metadata = {
        "id": assignment_id,
        "expected_transcript": expected_transcript,
        "questions": questions_list,
        "audio_path": audio_path,
        "filename": audio_file.filename
    }
    
    meta_path = os.path.join(ASSIGNMENTS_DIR, f"{assignment_id}.json")
    save_json(meta_path, metadata)
    
    save_json(RESULTS_FILE, {})
    
    return {"message": "Assignment created successfully", "auto_transcript": expected_transcript}

@app.get("/get_assignment")
async def get_assignment():
    """Student fetches the current assignment details."""
    meta_path = os.path.join(ASSIGNMENTS_DIR, "assignment_1.json")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="No active assignment found.")
    return load_json(meta_path)

@app.get("/audio/{assignment_id}")
async def get_audio(assignment_id: str):
    """Serves the audio file to the browser HTML5 player."""
    meta_path = os.path.join(ASSIGNMENTS_DIR, f"{assignment_id}.json")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=404, detail="Assignment not found.")
        
    metadata = load_json(meta_path)
    audio_path = metadata.get("audio_path")
    
    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found.")
        
    return FileResponse(audio_path)

@app.get("/student_audio/{sub_id}")
async def get_student_audio(sub_id: str):
    """Serves the student's recorded audio to the teacher."""
    audio_path = os.path.join(SUBMISSIONS_DIR, f"{sub_id}.wav")
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Student audio not found.")
    return FileResponse(audio_path)

@app.post("/submit_answer")
async def submit_answer(
    student_name: str = Form(...),
    dictation_text: str = Form(...),
    response_type: str = Form(...), # "text" or "voice"
    answers_json: str = Form(None),
    voice_audio: List[UploadFile] = File(None)
):
    """Student submits dictation and comprehension answers."""
    # 1. Get the current assignment
    meta_path = os.path.join(ASSIGNMENTS_DIR, "assignment_1.json")
    if not os.path.exists(meta_path):
        raise HTTPException(status_code=400, detail="No active assignment.")
    assignment = load_json(meta_path)
    expected_transcript = assignment.get("expected_transcript", "")
    questions = assignment.get("questions", [])
    
    # 2. Evaluate Dictation
    from backend.evaluator import evaluate_dictation
    dictation_eval = evaluate_dictation(expected_transcript, dictation_text)
    
    # 3. Process comprehension answers
    student_answers_list = []
    sub_ids = []
    
    if response_type == "text":
        if not answers_json:
            raise HTTPException(status_code=400, detail="Answers JSON is missing.")
        try:
            student_answers_list = json.loads(answers_json)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid answers JSON.")
            
    elif response_type == "voice":
        if not voice_audio or len(voice_audio) == 0:
            raise HTTPException(status_code=400, detail="Voice audio file missing.")
        
        for va in voice_audio:
            sub_id_idx = str(uuid.uuid4())
            sub_ids.append(sub_id_idx)
            audio_path = os.path.join(SUBMISSIONS_DIR, f"{sub_id_idx}.wav")
            with open(audio_path, "wb") as buffer:
                shutil.copyfileobj(va.file, buffer)
            
            try:
                comp_text = transcribe_audio(audio_path)
            except Exception as e:
                comp_text = f"Error: {str(e)}"
            
            student_answers_list.append(comp_text)
    else:
        raise HTTPException(status_code=400, detail="Invalid response type.")
        
    # 4. Evaluate Comprehension Questions
    question_results = []
    total_comp_score = 0
    for i, q in enumerate(questions):
        expected_ans = q["expected_answer"]
        student_ans = student_answers_list[i] if i < len(student_answers_list) else ""
        eval_result = evaluate_answer(expected_ans, student_ans)
        total_comp_score += eval_result["score"]
        
        q_res = {
            "question": q["question"],
            "student_answer": student_ans,
            "score": eval_result["score"],
            "feedback": eval_result["feedback"]
        }
        if response_type == "voice" and i < len(sub_ids):
            q_res["sub_id"] = sub_ids[i]
            
        question_results.append(q_res)
        
    avg_comp_score = int(total_comp_score / len(questions)) if questions else 0
    if questions:
        final_overall_score = int((dictation_eval["score"] + avg_comp_score) / 2)
    else:
        final_overall_score = dictation_eval["score"]
    
    # 5. Save to results
    results = load_json(RESULTS_FILE)
    results[student_name] = {
        "student_name": student_name,
        "method": response_type,
        "dictation_text": dictation_text,
        "dictation_eval": dictation_eval,
        "question_results": question_results,
        "overall_score": final_overall_score,
        "comp_score": avg_comp_score
    }
    save_json(RESULTS_FILE, results)
    
    return {
        "status": "success", 
        "overall_score": final_overall_score,
        "dictation_eval": dictation_eval,
        "question_results": question_results
    }

@app.get("/get_results")
async def get_results():
    """Teacher fetches all student results."""
    return load_json(RESULTS_FILE)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("listening_api:app", host="127.0.0.1", port=8002, reload=True)
