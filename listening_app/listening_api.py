"""
listening_api.py — Listening Assessment backend (RAM-only)
==========================================================
Flow:
  1. Teacher uploads an audio clip.
  2. Whisper transcribes it locally (in RAM) and the transcript is embedded
     into a vector (in RAM).
  3. A student listens to the audio and types what they heard.
  4. Their text is embedded (in RAM) and compared to the transcript vector,
     producing a 0-100 "understanding" score shown to student and teacher.

NOTHING is written to disk. The audio, transcript, vectors and results all
live only in this process's memory and disappear when it stops or restarts.
"""

import os

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from backend.whisper_service import transcribe_audio_bytes
from backend.evaluator import embed_sentences, score_dictation

# Map common audio extensions to MIME types so the browser can play the stream
# even when the upload arrives with a generic content type.
_AUDIO_MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4"}


def _resolve_mime(filename: str, content_type: str) -> str:
    if content_type and content_type != "application/octet-stream":
        return content_type
    return _AUDIO_MIME.get(os.path.splitext(filename or "")[1].lower(), "audio/mpeg")

app = FastAPI(title="Listening Assessment API (RAM-only)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory state (RAM only — never persisted) ─────────────────────────────
ASSIGNMENT = {
    "ready": False,
    "audio_bytes": None,        # raw audio, streamed to the student on demand
    "audio_mime": None,
    "transcript": None,                  # reference transcript (teacher-only)
    "transcript_sentence_vectors": None, # per-sentence vectors used for coverage scoring
}
RESULTS = {}   # student_name -> result dict, kept in RAM for the teacher view


@app.post("/create_assignment")
async def create_assignment(audio_file: UploadFile = File(...)):
    """Teacher uploads audio. We transcribe + embed it, all in RAM."""
    audio_bytes = await audio_file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Uploaded audio is empty.")

    try:
        transcript = transcribe_audio_bytes(audio_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    if not transcript:
        raise HTTPException(
            status_code=422, detail="Could not transcribe any speech from the audio."
        )

    ASSIGNMENT.update({
        "ready": True,
        "audio_bytes": audio_bytes,
        "audio_mime": _resolve_mime(audio_file.filename, audio_file.content_type),
        "transcript": transcript,
        "transcript_sentence_vectors": embed_sentences(transcript),
    })
    RESULTS.clear()   # a new assignment clears any old (in-RAM) results

    return {"message": "Assignment created.", "transcript": transcript}


@app.get("/get_assignment")
async def get_assignment():
    """Student-facing: reveals only whether an assignment is ready (not the answer)."""
    if not ASSIGNMENT["ready"]:
        raise HTTPException(status_code=404, detail="No active assignment.")
    return {"ready": True}


@app.get("/audio")
async def get_audio():
    """Stream the teacher's audio straight from RAM (no file on disk)."""
    if not ASSIGNMENT["ready"] or ASSIGNMENT["audio_bytes"] is None:
        raise HTTPException(status_code=404, detail="No audio available.")
    return Response(content=ASSIGNMENT["audio_bytes"], media_type=ASSIGNMENT["audio_mime"])


@app.post("/submit_answer")
async def submit_answer(
    student_name: str = Form(...),
    dictation_text: str = Form(...),
):
    """Student submits typed dictation; we score how much of the audio they captured."""
    if not ASSIGNMENT["ready"]:
        raise HTTPException(status_code=400, detail="No active assignment.")
    if not student_name.strip() or not dictation_text.strip():
        raise HTTPException(status_code=400, detail="Name and dictation are required.")

    result = score_dictation(
        ASSIGNMENT["transcript"],
        ASSIGNMENT["transcript_sentence_vectors"],
        dictation_text,
    )

    RESULTS[student_name] = {
        "student_name": student_name,
        "dictation_text": dictation_text,
        "score": result["score"],
        "coverage": result["coverage"],
        "feedback": result["feedback"],
    }

    return {"status": "success", **result}


@app.get("/get_results")
async def get_results():
    """Teacher-facing: the reference transcript + all scores collected this session."""
    return {"transcript": ASSIGNMENT["transcript"], "results": RESULTS}


@app.post("/reset")
async def reset():
    """Wipe everything from memory (audio, transcript, vectors and results)."""
    ASSIGNMENT.update({
        "ready": False, "audio_bytes": None, "audio_mime": None,
        "transcript": None, "transcript_sentence_vectors": None,
    })
    RESULTS.clear()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("listening_api:app", host="127.0.0.1", port=8002, reload=True)
