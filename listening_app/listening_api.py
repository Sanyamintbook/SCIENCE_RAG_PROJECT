"""
listening_api.py — Listening Assessment backend (RAM-only)
==========================================================
Flow:
  1. Teacher uploads an audio clip.
  2. Whisper transcribes it locally (in RAM) and the transcript is split into
     sentences, each embedded into a vector (in RAM).
  3. A student listens to the audio and types what they understood.
  4. Their text is scored against the transcript sentence-vectors, producing a
     0-100 "coverage" score shown to student and teacher.

NOTHING is written to disk. The audio, transcript, vectors and results all
live only in this process's memory and disappear when it stops or restarts.

This file is the BACKEND. The Streamlit pages in frontend/ talk to it over HTTP.
"""

import os                                              # standard library: split file extensions for MIME lookup

from fastapi import FastAPI, UploadFile, File, Form, HTTPException  # third-party: the web framework + helpers
from fastapi.middleware.cors import CORSMiddleware     # third-party: lets the Streamlit pages call this API
from fastapi.responses import Response                 # third-party: send raw bytes back (the audio stream)

# Our own modules (see backend/). transcribe_audio_bytes comes FROM whisper_service.py;
# embed_sentences and score_dictation come FROM evaluator.py.
from backend.whisper_service import transcribe_audio_bytes
from backend.evaluator import embed_sentences, score_dictation

# Map common audio extensions to MIME types so the browser can play the stream
# even when the upload arrives with a generic content type.
_AUDIO_MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4"}


def _resolve_mime(filename: str, content_type: str) -> str:
    """Pick a browser-playable MIME type for the uploaded audio."""
    if content_type and content_type != "application/octet-stream":
        return content_type                            # trust a real content type if we got one
    # otherwise guess from the file extension (os.path.splitext -> ".mp3"), default to mpeg
    return _AUDIO_MIME.get(os.path.splitext(filename or "")[1].lower(), "audio/mpeg")

app = FastAPI(title="Listening Assessment API (RAM-only)")   # create the web application object

app.add_middleware(                                    # allow cross-origin calls (Streamlit runs on other ports)
    CORSMiddleware,
    allow_origins=["*"],                               # any origin may call us (fine for a local tool)
    allow_credentials=True,
    allow_methods=["*"],                               # allow GET, POST, etc.
    allow_headers=["*"],                               # allow any request headers
)

# ── In-memory state (RAM only — never persisted) ─────────────────────────────
# A single current assignment. Replaced each time a teacher uploads new audio.
ASSIGNMENT = {
    "ready": False,                                    # has a teacher uploaded an assignment yet?
    "audio_bytes": None,                               # the raw audio, streamed to the student on demand
    "audio_mime": None,                                # how to label that audio to the browser
    "transcript": None,                                # reference transcript (teacher-only, the answer key)
    "transcript_sentence_vectors": None,               # per-sentence vectors used for coverage scoring
}
RESULTS = {}                                           # student_name -> result dict, kept in RAM for the teacher view


@app.post("/create_assignment")                        # TEACHER endpoint: POST audio here
async def create_assignment(audio_file: UploadFile = File(...)):
    """Teacher uploads audio. We transcribe + embed it, all in RAM."""
    audio_bytes = await audio_file.read()              # read the whole uploaded file into memory (bytes)
    if not audio_bytes:                                # guard: empty upload
        raise HTTPException(status_code=400, detail="Uploaded audio is empty.")

    try:
        transcript = transcribe_audio_bytes(audio_bytes)   # bytes -> text (from whisper_service.py)
    except Exception as e:                             # if Whisper/ffmpeg fail, report a clean 500 error
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    if not transcript:                                 # Whisper ran but found no speech
        raise HTTPException(
            status_code=422, detail="Could not transcribe any speech from the audio."
        )

    ASSIGNMENT.update({                                # store everything for this assignment in RAM
        "ready": True,
        "audio_bytes": audio_bytes,
        "audio_mime": _resolve_mime(audio_file.filename, audio_file.content_type),
        "transcript": transcript,
        "transcript_sentence_vectors": embed_sentences(transcript),  # precompute vectors (from evaluator.py)
    })
    RESULTS.clear()                                    # a new assignment clears any old (in-RAM) results

    return {"message": "Assignment created.", "transcript": transcript}   # teacher sees the transcript


@app.get("/get_assignment")                            # STUDENT endpoint: "is there a test?"
async def get_assignment():
    """Student-facing: reveals only whether an assignment is ready (not the answer)."""
    if not ASSIGNMENT["ready"]:                        # no assignment uploaded yet
        raise HTTPException(status_code=404, detail="No active assignment.")
    return {"ready": True}                             # deliberately does NOT return the transcript


@app.get("/audio")                                     # STUDENT endpoint: the playable audio
async def get_audio():
    """Stream the teacher's audio straight from RAM (no file on disk)."""
    if not ASSIGNMENT["ready"] or ASSIGNMENT["audio_bytes"] is None:
        raise HTTPException(status_code=404, detail="No audio available.")
    # Response sends the raw bytes back with the right content type so the browser plays it.
    return Response(content=ASSIGNMENT["audio_bytes"], media_type=ASSIGNMENT["audio_mime"])


@app.post("/submit_answer")                            # STUDENT endpoint: submit the typed dictation
async def submit_answer(
    student_name: str = Form(...),                     # form field: the student's name
    dictation_text: str = Form(...),                   # form field: what they typed
):
    """Student submits typed dictation; we score how much of the audio they captured."""
    if not ASSIGNMENT["ready"]:                        # nothing to grade against
        raise HTTPException(status_code=400, detail="No active assignment.")
    if not student_name.strip() or not dictation_text.strip():   # both fields required
        raise HTTPException(status_code=400, detail="Name and dictation are required.")

    result = score_dictation(                          # do the scoring (from evaluator.py)
        ASSIGNMENT["transcript"],
        ASSIGNMENT["transcript_sentence_vectors"],
        dictation_text,
    )

    RESULTS[student_name] = {                          # remember this student's result in RAM (for the teacher)
        "student_name": student_name,
        "dictation_text": dictation_text,
        "score": result["score"],
        "coverage": result["coverage"],
        "feedback": result["feedback"],
    }

    return {"status": "success", **result}             # return score + coverage + feedback to the student


@app.get("/get_results")                               # TEACHER endpoint: everyone's scores
async def get_results():
    """Teacher-facing: the reference transcript + all scores collected this session."""
    return {"transcript": ASSIGNMENT["transcript"], "results": RESULTS}


@app.post("/reset")                                    # wipe everything from memory
async def reset():
    """Wipe everything from memory (audio, transcript, vectors and results)."""
    ASSIGNMENT.update({
        "ready": False, "audio_bytes": None, "audio_mime": None,
        "transcript": None, "transcript_sentence_vectors": None,
    })
    RESULTS.clear()
    return {"status": "cleared"}


if __name__ == "__main__":                             # only runs if you start this file directly
    import uvicorn                                      # third-party: the ASGI server that runs FastAPI
    uvicorn.run("listening_api:app", host="127.0.0.1", port=8002, reload=True)
