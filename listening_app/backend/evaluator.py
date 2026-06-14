"""
evaluator.py
============
Scores how much of the audio a student actually understood — the way a teacher
who holds the transcript would: by COVERAGE of the content.

How it works (all local, all in RAM):
  1. The transcript is split into its individual sentences (key ideas). Each is
     embedded into a vector once, when the assignment is created.
  2. When a student submits, their answer is split into sentences and embedded.
  3. For every transcript sentence we find the student's best-matching sentence
     and award partial credit for how closely it matches (meaning, not wording).
  4. The score is the AVERAGE credit across all transcript sentences — i.e. the
     proportion of the audio's ideas the student captured. Skipping lines lowers
     the score; an answer about a different topic scores near zero.

Spelling and wording are forgiven (embeddings match meaning). A spelling-tolerant
lexical floor still guarantees an essentially complete copy scores ~100.
Nothing is written to disk; every embedding request stays on localhost.
"""

import os
import re
from difflib import SequenceMatcher

import numpy as np
import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
_EMBED_DIM = 768   # dimension of nomic-embed-text vectors

# --- Per-sentence coverage calibration ---------------------------------------
# A transcript sentence counts as fully "captured" once the best-matching
# student sentence reaches HIGH_SIM; below LOW_SIM it counts as missed. In
# between, partial credit is given. Tuned for nomic-embed-text sentence pairs:
# a correct paraphrase scores ~0.75-0.9, an unrelated/missing line ~0.4-0.6.
LOW_SIM = 0.70
HIGH_SIM = 0.85

# Auto-award full marks only for an essentially COMPLETE copy of the transcript.
LEX_FULL_COPY = 0.95


def get_embedding(text: str) -> np.ndarray:
    """Convert text into a normalized vector via local Ollama (held only in RAM)."""
    text = (text or "").strip()
    if not text:
        return np.zeros(_EMBED_DIM, dtype=np.float32)

    response = requests.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    response.raise_for_status()
    embedding = response.json().get("embedding", [])
    if not embedding:
        raise ValueError("Ollama returned an empty embedding.")

    vec = np.array(embedding, dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, in the range -1.0 .. 1.0."""
    if a.size == 0 or b.size == 0:
        return 0.0
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def split_sentences(text: str) -> list:
    """Split text into sentences on ., ?, ! — dropping trivially short fragments."""
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) >= 3]


def embed_sentences(text: str) -> list:
    """Embed each sentence of a text into a vector (computed once per assignment)."""
    return [get_embedding(s) for s in split_sentences(text)]


def _normalize(text: str) -> str:
    """Lowercase, drop punctuation and collapse whitespace (for fuzzy matching)."""
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _lexical_ratio(a: str, b: str) -> float:
    """Spelling-tolerant character similarity on normalized text (0.0 .. 1.0)."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _sentence_credit(best_sim: float) -> float:
    """Map a sentence's best match similarity to 0.0 .. 1.0 partial credit."""
    norm = (best_sim - LOW_SIM) / (HIGH_SIM - LOW_SIM)
    return max(0.0, min(1.0, norm))


def _feedback_for(score: int) -> str:
    if score >= 85:
        return "Excellent! You captured almost all of the audio."
    if score >= 70:
        return "Good job — you captured most of the audio, but missed a few parts."
    if score >= 50:
        return "Fair — you captured about half of the audio; several ideas were missed."
    if score >= 25:
        return "Needs work — most of the audio's content was missed."
    return "Very little of the audio was captured. Try listening again carefully."


def score_dictation(
    transcript_text: str,
    transcript_sentence_vectors: list,
    student_text: str,
) -> dict:
    """
    Score how much of the audio the student captured (0-100), by averaging
    per-sentence coverage of the transcript. Wording and spelling are forgiven;
    missing or wrong content lowers the score proportionally.

    Nothing is stored — every value is computed in memory and discarded.
    """
    if not transcript_sentence_vectors:
        return {"score": 0, "coverage": 0.0,
                "feedback": "No transcript available to grade against."}

    student_vectors = embed_sentences(student_text)

    # For each transcript sentence, find the student's best-matching sentence
    # and award partial credit; the score is the average across all sentences.
    credits = []
    for tvec in transcript_sentence_vectors:
        best = max((cosine_similarity(tvec, svec) for svec in student_vectors),
                   default=0.0)
        credits.append(_sentence_credit(best))
    coverage = sum(credits) / len(credits)
    base = coverage * 100.0

    # Guarantee full marks for an essentially complete copy of the transcript.
    if _lexical_ratio(transcript_text, student_text) >= LEX_FULL_COPY:
        base = max(base, 100.0)

    score = int(round(min(max(base, 0.0), 100.0)))
    return {
        "score": score,
        "coverage": round(coverage, 4),
        "feedback": _feedback_for(score),
    }
