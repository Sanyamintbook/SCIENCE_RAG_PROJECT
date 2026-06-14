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

WHO CALLS THIS: listening_api.py imports embed_sentences() (at assignment time)
and score_dictation() (when a student submits).
"""

import os                              # standard library: read environment variables (OLLAMA_HOST etc.)
import re                              # standard library: regular expressions, used to split/normalize text
from difflib import SequenceMatcher    # standard library: measures how similar two strings are (for spelling)

import numpy as np                     # third-party: vector math (dot product, norms)
import requests                        # third-party: send HTTP requests to the Ollama server

# Where Ollama lives and which model to use. os.environ.get(name, default) reads
# an environment variable, falling back to the default if it isn't set.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
_EMBED_DIM = 768                       # nomic-embed-text returns vectors with 768 numbers

# --- Per-sentence coverage calibration ---------------------------------------
# A transcript sentence counts as fully "captured" once the best-matching
# student sentence reaches HIGH_SIM; below LOW_SIM it counts as missed. In
# between, partial credit is given. Tuned for nomic-embed-text sentence pairs:
# a correct paraphrase scores ~0.75-0.9, an unrelated/missing line ~0.4-0.6.
LOW_SIM = 0.70                         # at/below this similarity -> 0 credit for that sentence
HIGH_SIM = 0.85                        # at/above this similarity -> full credit for that sentence

# Auto-award full marks only for an essentially COMPLETE copy of the transcript.
LEX_FULL_COPY = 0.95                   # if the typed text is 95%+ identical to the transcript -> 100


def get_embedding(text: str) -> np.ndarray:
    """Convert text into a normalized vector via local Ollama (held only in RAM)."""
    text = (text or "").strip()                    # treat None as "", and trim whitespace
    if not text:                                   # empty text -> return a zero vector (no meaning)
        return np.zeros(_EMBED_DIM, dtype=np.float32)

    response = requests.post(                       # call Ollama's embeddings endpoint over HTTP
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": text},  # ask EMBED_MODEL to embed this text
        timeout=120,                                # give up after 120 seconds
    )
    response.raise_for_status()                     # turn any HTTP error into a Python exception
    embedding = response.json().get("embedding", [])   # pull the list of numbers out of the JSON reply
    if not embedding:                              # safety: Ollama returned nothing usable
        raise ValueError("Ollama returned an empty embedding.")

    vec = np.array(embedding, dtype=np.float32)    # turn the Python list into a numpy array
    norm = np.linalg.norm(vec)                     # length (magnitude) of the vector
    return vec / norm if norm else vec             # normalize to length 1 (so cosine = dot product)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, in the range -1.0 .. 1.0."""
    if a.size == 0 or b.size == 0:                 # if either vector is empty, no similarity
        return 0.0
    na, nb = np.linalg.norm(a), np.linalg.norm(b)  # lengths of both vectors
    if na == 0 or nb == 0:                          # avoid dividing by zero
        return 0.0
    return float(np.dot(a, b) / (na * nb))         # dot product divided by the two lengths = cosine


def split_sentences(text: str) -> list:
    """Split text into sentences on ., ?, ! — dropping trivially short fragments."""
    # re.split with a "lookbehind" keeps the split AFTER each . ! ? followed by space.
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) >= 3]   # keep only pieces of length >= 3


def embed_sentences(text: str) -> list:
    """Embed each sentence of a text into a vector (computed once per assignment)."""
    # For every sentence from split_sentences(), call get_embedding() (both above).
    return [get_embedding(s) for s in split_sentences(text)]


def _normalize(text: str) -> str:
    """Lowercase, drop punctuation and collapse whitespace (for fuzzy matching)."""
    text = (text or "").lower().strip()            # lowercase + trim
    text = re.sub(r"[^\w\s]", " ", text)           # replace every non-word/space char with a space
    return re.sub(r"\s+", " ", text).strip()       # collapse runs of spaces into one


def _lexical_ratio(a: str, b: str) -> float:
    """Spelling-tolerant character similarity on normalized text (0.0 .. 1.0)."""
    na, nb = _normalize(a), _normalize(b)          # normalize both strings first
    if not na or not nb:                           # if either is empty after normalizing
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()   # difflib's 0..1 similarity ratio


def _sentence_credit(best_sim: float) -> float:
    """Map a sentence's best match similarity to 0.0 .. 1.0 partial credit."""
    norm = (best_sim - LOW_SIM) / (HIGH_SIM - LOW_SIM)   # rescale the [LOW..HIGH] band onto [0..1]
    return max(0.0, min(1.0, norm))                # clamp so it never goes below 0 or above 1


def _feedback_for(score: int) -> str:
    """Turn a numeric score into a short human sentence shown to the student."""
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
    transcript_text: str,              # the full correct transcript (used for the exact-copy floor)
    transcript_sentence_vectors: list, # the transcript's per-sentence vectors (precomputed at assignment time)
    student_text: str,                 # what the student typed
) -> dict:
    """
    Score how much of the audio the student captured (0-100), by averaging
    per-sentence coverage of the transcript. Wording and spelling are forgiven;
    missing or wrong content lowers the score proportionally.

    Nothing is stored — every value is computed in memory and discarded.
    """
    if not transcript_sentence_vectors:            # no transcript to grade against
        return {"score": 0, "coverage": 0.0,
                "feedback": "No transcript available to grade against."}

    student_vectors = embed_sentences(student_text)   # embed each student sentence (function above)

    # For each transcript sentence, find the student's best-matching sentence
    # and award partial credit; the score is the average across all sentences.
    credits = []                                   # will hold one credit (0..1) per transcript sentence
    for tvec in transcript_sentence_vectors:       # loop over each transcript sentence vector
        best = max(                                # best similarity to ANY student sentence
            (cosine_similarity(tvec, svec) for svec in student_vectors),
            default=0.0,                           # if the student wrote nothing, best = 0
        )
        credits.append(_sentence_credit(best))     # convert that best similarity into partial credit
    coverage = sum(credits) / len(credits)         # average credit = fraction of audio captured
    base = coverage * 100.0                         # turn the 0..1 fraction into a 0..100 score

    # Guarantee full marks for an essentially complete copy of the transcript.
    if _lexical_ratio(transcript_text, student_text) >= LEX_FULL_COPY:
        base = max(base, 100.0)

    score = int(round(min(max(base, 0.0), 100.0)))  # clamp to 0..100 and round to a whole number
    return {                                        # the result handed back to listening_api.py
        "score": score,
        "coverage": round(coverage, 4),             # the raw fraction, shown as "Audio captured: X%"
        "feedback": _feedback_for(score),           # the human sentence (function above)
    }
