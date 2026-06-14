# Project Structure & Flow — Science RAG Project

This document explains **every folder and file**, what it does, why it exists,
what is inside it, and how the pieces connect (which function calls which, and
where each imported function comes from).

The project is **three independent AI tools** for a 10th‑grade science class,
tied together by one dashboard. Everything runs **locally** — the AI models run
in **Ollama** on your own machine (no paid cloud APIs).

---

## 1. Top‑level map

```
SCIENCE_RAG_PROJECT-main/
│
├── start.py              # ⭐ ONE launcher — starts all 9 services in the background
├── run_all.bat / .sh     # Alternative launcher (opens a separate window per service)
├── stop_all.bat / .sh    # Stops the services started by run_all
├── requirements.txt      # All Python packages the project needs (pip install -r)
├── README.md             # Human setup guide
├── PROJECT_STRUCTURE.md  # (this file) granular structure + flow
├── .gitignore            # Tells git which files NOT to upload (venv, audio, PDFs…)
│
├── dashboard/            # The master menu page (port 8500)
│   └── main_dashboard.py
│
├── rag_app/              # TOOL 1 — Science textbook question‑answering (RAG)
│   ├── app.py            # One‑time: build the searchable index from the PDF + CLI test
│   ├── api.py            # The web backend that answers questions (port 8000)
│   ├── rag_ui.py         # The chat web page students use (port 8501)
│   ├── 10th_science_book.pdf      # source textbook (git‑ignored, large)
│   └── faiss_science_index/       # the built search index (git‑ignored, regenerable)
│
├── plagiarism_app/       # TOOL 2 — Assignment integrity checker
│   ├── plagiarism_api.py # Backend: receives uploads, runs detectors (port 8001)
│   ├── student_ui.py     # Students upload assignments (port 8502)
│   ├── teacher_ui.py     # Teacher dashboard of results (port 8503)
│   ├── report_builder.py # Combines detector outputs into one integrity score
│   └── detectors/        # The individual checks
│       ├── ollama_client.py   # the ONE place that talks to Ollama
│       ├── text_extractor.py  # PDF / Word / PPT  ->  plain text
│       ├── ai_detector.py     # "was this written by AI?"  (asks Qwen)
│       ├── copy_checker.py    # student‑vs‑student copy‑paste (TF‑IDF math)
│       ├── paraphrase.py      # reworded copying (embedding meaning match)
│       └── originality.py     # positive proof the student wrote it (pure math)
│
├── listening_app/        # TOOL 3 — Listening comprehension test (we rebuilt this)
│   ├── listening_api.py  # Backend (port 8002), RAM‑only, no disk writes
│   ├── backend/
│   │   ├── __init__.py        # marks this folder as an importable package
│   │   ├── whisper_service.py # audio bytes -> text (local Whisper, in RAM)
│   │   └── evaluator.py       # text -> vectors -> coverage score
│   └── frontend/
│       ├── teacher_listening.py  # teacher uploads audio (port 8504)
│       └── student_listening.py  # student listens + types answer (port 8505)
│
├── submissions/          # plagiarism uploads land here (mostly git‑ignored)
├── reports/              # plagiarism JSON reports land here (git‑ignored)
├── data/                 # OLD listening files (no longer used — app is RAM‑only now)
├── docs/                 # extra written guides (markdown/html)
├── dummy reports/        # sample student essays + scripts that generate them (for testing)
└── generate_*.py         # one‑off scripts that build Excel/feature‑matrix reports
```

---

## 2. Which port is what

`start.py` launches all of these at once. Open the dashboard and click through.

| Service | Port | File | Type |
|---|---|---|---|
| Dashboard (menu) | 8500 | `dashboard/main_dashboard.py` | Streamlit page |
| RAG backend | 8000 | `rag_app/api.py` | FastAPI (uvicorn) |
| RAG chat UI | 8501 | `rag_app/rag_ui.py` | Streamlit page |
| Plagiarism backend | 8001 | `plagiarism_app/plagiarism_api.py` | FastAPI (uvicorn) |
| Plagiarism student UI | 8502 | `plagiarism_app/student_ui.py` | Streamlit page |
| Plagiarism teacher UI | 8503 | `plagiarism_app/teacher_ui.py` | Streamlit page |
| Listening backend | 8002 | `listening_app/listening_api.py` | FastAPI (uvicorn) |
| Listening teacher UI | 8504 | `listening_app/frontend/teacher_listening.py` | Streamlit page |
| Listening student UI | 8505 | `listening_app/frontend/student_listening.py` | Streamlit page |

**Pattern used everywhere:** a *backend* (FastAPI) does the AI work and exposes
URLs; a *frontend* (Streamlit) is just a web page that calls those URLs with
`requests`. Frontends hold no AI logic — they send text/files to the backend and
display whatever comes back.

---

## 3. The shared engine: Ollama

All three tools use **Ollama** (a local model server at `http://localhost:11434`)
with two models:

- **`qwen2.5:3b`** — a chat LLM. Used to *judge* things in words (e.g. "is this AI
  written?").
- **`nomic-embed-text`** — an *embedding* model. Turns a piece of text into a
  list of 768 numbers (a "vector"). Texts with similar meaning produce vectors
  that point in a similar direction, so we can measure meaning with math
  (cosine similarity).

If Ollama is not running, the apps still open but AI features return a clear
"unavailable" message instead of crashing.

---

## 4. TOOL 1 — RAG Science Tutor (`rag_app/`)

**Goal:** answer student questions using *only* the textbook, never made‑up facts.
RAG = "Retrieval‑Augmented Generation": first *retrieve* the most relevant
textbook paragraphs, then ask the LLM to *generate* an answer from just those.

### Files and flow

**`app.py`** — run once from a terminal. It:
1. Reads `10th_science_book.pdf` (`PyMuPDFLoader` ← `langchain_community`).
2. Splits it into ~1000‑character chunks (`RecursiveCharacterTextSplitter` ←
   `langchain_text_splitters`).
3. Turns each chunk into a vector (`OllamaEmbeddings` ← `langchain_ollama`).
4. Stores all vectors in a **FAISS** index on disk (`FAISS` ←
   `langchain_community`) under `faiss_science_index/`.
5. Then drops into a terminal loop where you can type test questions.

**`api.py`** — the always‑on web backend (port 8000). On startup it loads the
saved FAISS index and builds a "chain":
- `retriever` = FAISS configured to return the top‑3 matching chunks.
- `create_stuff_documents_chain` (← `langchain_classic`) stuffs those chunks into
  a strict prompt (`ChatPromptTemplate` ← `langchain_core`).
- `create_retrieval_chain` (← `langchain_classic`) wires retriever + prompt + LLM.
- The `POST /ask` endpoint runs `rag_chain.invoke({"input": question})` and
  returns `{"answer": ...}`.

**`rag_ui.py`** — the chat page (port 8501). It keeps the conversation in
`st.session_state` and, for each question, calls `POST http://localhost:8000/ask`
(via `requests`) and shows the answer. No AI logic here.

```
Student types in rag_ui.py (8501)
        │  requests.post(/ask)
        ▼
api.py (8000)  ──>  FAISS finds 3 chunks  ──>  Qwen writes answer from them
        │
        ▼  {"answer": ...}
Shown back in rag_ui.py
```

---

## 5. TOOL 2 — Plagiarism Detector (`plagiarism_app/`)

**Goal:** give each submitted assignment an **integrity score (0–100)** and a
verdict (clean / review / flagged), based on several independent checks.

### The detectors (`plagiarism_app/detectors/`)

| File | What it answers | How | Needs Ollama? |
|---|---|---|---|
| `text_extractor.py` | "what words are in this file?" | PyMuPDF / python‑docx / python‑pptx | no |
| `ai_detector.py` | "was this written by AI?" | asks Qwen for a JSON verdict | yes (chat) |
| `copy_checker.py` | "did two students copy each other?" | TF‑IDF + cosine (scikit‑learn) | no |
| `paraphrase.py` | "is it reworded copying?" | embeds each sentence, compares meaning | yes (embed) |
| `originality.py` | "signs the student wrote it themselves" | vocabulary/sentence‑length math | no |

**`ollama_client.py`** is the single gateway to Ollama. It exposes:
- `generate(prompt)` → Qwen chat reply (used by `ai_detector.py`),
- `embed(text)` → a vector (used by `paraphrase.py`),
- `extract_json(raw)` → safely parse the JSON Qwen returns.

So `ai_detector.py` imports `generate`/`extract_json` **from**
`detectors.ollama_client`; `paraphrase.py` imports `embed` **from** the same file.

**`report_builder.py`** — `build_report(...)` takes the outputs of all detectors
for one student and combines them: a weighted "negative" score (AI 50% + copy 30%
+ paraphrase 20%), minus that from 100, nudged up by originality → integrity
score + verdict.

**`plagiarism_api.py`** — the backend (port 8001). Key functions and where their
imported helpers come from:
- `extract_text` ← `detectors.text_extractor`
- `detect_ai_content` ← `detectors.ai_detector`
- `check_all_submissions` ← `detectors.copy_checker`
- `detect_paraphrase` ← `detectors.paraphrase`
- `score_originality` ← `detectors.originality`
- `build_report` ← `report_builder`

Endpoints: `POST /submit` (save a file), `POST /prepare` (read all files + run the
cross‑student copy check), `POST /analyze_one/{student}` (slow per‑student AI step),
`GET /all_reports` (table), `GET /report/{student}` (one detailed report).

**`student_ui.py`** (8502) uploads files to `/submit`. **`teacher_ui.py`** (8503)
calls `/prepare` then `/analyze_one` per student (so it can show a progress bar),
and renders the table from `/all_reports`.

```
student_ui (8502) ──/submit──> submissions/ folder
teacher_ui (8503) ──/prepare──> read texts + copy_checker
                  ──/analyze_one each student──> ai_detector + originality + paraphrase
                                              └─> report_builder ─> reports/<name>.json
                  ──/all_reports──> table on screen
```

---

## 6. TOOL 3 — Listening Assessment (`listening_app/`) — rebuilt

**Goal:** the teacher uploads an audio clip; a student listens and types what they
understood; the system scores **how much of the audio they captured**.

**Key design rule: RAM‑only.** Nothing is written to disk — not the audio, not the
transcript, not the vectors, not the scores. Everything lives in the backend's
memory and disappears when the server restarts. Audio is streamed to the student
straight from memory.

### Files and flow

**`backend/whisper_service.py`** — turns audio into text, locally and in RAM:
- `_decode_to_waveform(bytes)` pipes the audio through **ffmpeg** (stdin→stdout,
  no temp file) to get a 16 kHz mono waveform as a NumPy array.
- `transcribe_audio_bytes(bytes)` feeds that array to a **faster‑whisper** model
  and returns the text. The model is loaded once and cached in memory.

**`backend/evaluator.py`** — turns text into vectors and scores coverage:
- `get_embedding(text)` → a vector, via Ollama `nomic-embed-text` (same idea as
  `paraphrase.py` in the plagiarism app, but called directly here).
- `split_sentences(text)` / `embed_sentences(text)` → break a text into sentences
  and embed each. The transcript's sentence‑vectors are computed **once** when the
  assignment is created.
- `score_dictation(transcript_text, transcript_sentence_vectors, student_text)`:
  for every transcript sentence, find the student's best‑matching sentence and
  award partial credit; the score is the **average** = the proportion of the
  audio captured. Missing lines lower the score; wording/spelling are forgiven.

**`listening_api.py`** — the backend (port 8002). It imports `transcribe_audio_bytes`
**from** `backend.whisper_service` and `embed_sentences`/`score_dictation` **from**
`backend.evaluator`. It holds two in‑memory objects: `ASSIGNMENT` (current audio +
transcript + sentence vectors) and `RESULTS` (each student's score). Endpoints:
- `POST /create_assignment` (teacher): transcribe → split → embed sentences → store
  in RAM; returns the transcript.
- `GET /get_assignment` (student): only says whether one is ready — does **not**
  reveal the transcript (that would be the answer key).
- `GET /audio` (student): streams the audio bytes from RAM.
- `POST /submit_answer` (student): scores the typed dictation, stores the result in
  RAM, returns the score.
- `GET /get_results` (teacher): the transcript + every student's score.
- `POST /reset`: wipe memory.

**`frontend/teacher_listening.py`** (8504): upload audio → `POST /create_assignment`;
"Results" tab reads `GET /get_results`.
**`frontend/student_listening.py`** (8505): `GET /get_assignment` → play `GET /audio`
→ type answer → `POST /submit_answer` → show score.

```
Teacher (8504) ──/create_assignment(audio)──┐
                                            ▼
            listening_api (8002):  whisper_service ─> transcript
                                   evaluator ─> per‑sentence vectors  (all in RAM)
Student (8505) ──/audio──> hears it
               ──/submit_answer(text)──> evaluator.score_dictation ─> coverage %
                                       └─> shown to student + stored in RAM
Teacher (8504) ──/get_results──> sees every student's score
```

---

## 7. Why the listening app uses two different models

- **faster‑whisper** (speech‑to‑text) runs on `ctranslate2`, *not* PyTorch — it was
  chosen because the PyTorch install on this machine is broken, and ctranslate2 is
  pinned to `4.4.0` (newer builds crash on this CPU). See the notes in
  `requirements.txt`.
- **nomic‑embed‑text via Ollama** (text→vectors) is reused from the rest of the
  project, so the listening app needs no extra embedding download and stays
  consistent with the plagiarism app.

---

## 8. How to run

```powershell
.venv\Scripts\activate     # use the project's virtual environment
python start.py            # launches all 9 services in the background
# open http://localhost:8500  (the dashboard)
# Ctrl+C once in that terminal stops everything
```

Ollama must be running with `qwen2.5:3b` and `nomic-embed-text` pulled.
