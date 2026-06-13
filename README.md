# My AI Tools — Science RAG + Plagiarism Detector

Two tools under one dashboard, running **100% locally on Ollama**
(`qwen2.5:7b` + `nomic-embed-text`). No paid APIs, no HuggingFace downloads.

## What's inside

```
science_rag_project/
├── dashboard/
│   └── main_dashboard.py     # master launcher              (port 8500)
│
├── rag_app/                  # your existing science tutor
│   ├── app.py                # one-time: build FAISS index from the PDF
│   ├── api.py                # RAG backend, /ask endpoint    (port 8000)
│   ├── rag_ui.py             # NEW chat interface            (port 8501)
│   ├── 10th_science_book.pdf
│   └── faiss_science_index/
│
├── plagiarism_app/
│   ├── plagiarism_api.py     # backend: /submit /run_analysis /report (port 8001)
│   ├── student_ui.py         # students upload assignments   (port 8502)
│   ├── teacher_ui.py         # teacher report dashboard      (port 8503)
│   ├── report_builder.py     # combines scores into one report
│   └── detectors/
│       ├── ollama_client.py  # one place that talks to Ollama
│       ├── text_extractor.py # PDF / DOCX / PPTX -> text
│       ├── ai_detector.py    # Qwen2.5 judges AI vs human
│       ├── copy_checker.py   # TF-IDF cosine (student vs student)
│       ├── paraphrase.py     # nomic-embed meaning match (humanized AI)
│       └── originality.py    # positive "own work" score
│
├── submissions/              # uploaded files land here
├── reports/                  # generated JSON reports land here
├── submissions/              # uploaded files land here
├── reports/                  # generated JSON reports land here
├── start.py                  # ✅ recommended launcher — one command, no clutter
├── requirements.txt
├── run_all.sh / stop_all.sh  # alternative launcher (opens separate windows)
```

## How the plagiarism flow works

1. Student uploads a file → saved in `submissions/`.
2. Teacher clicks **Run analysis**. For every file:
   - extract text,
   - **AI check** (Qwen): is it AI-written?
   - **copy check** (TF-IDF): too similar to another student?
   - **paraphrase check** (embeddings): same meaning as a peer, reworded?
   - **originality** (math): signs the student wrote it themselves.
3. Each student gets an **integrity score (0–100)** + a report saved in `reports/`.
4. Teacher views a colour-coded table and drills into any student.

## Setup (do once)

```powershell
# 1. Install Ollama from https://ollama.com, then pull both models:
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

# 2. Create and activate a virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate

# 3. Install Python dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Build the science index (first time only — type 'exit' when ready)
cd rag_app
python app.py
cd ..
```

## Run everything

### ✅ Recommended — single command, no clutter (Windows PowerShell)

```powershell
.venv\Scripts\activate    # activate virtual environment first
python start.py           # starts all 6 services silently in the background
```

Then open your browser to **http://localhost:8500**

To stop everything: press **`Ctrl + C`** once in that terminal.

### Alternative — separate windows (original method)

```powershell
.\run_all.bat        # opens 6 separate windows (one per service)
.\stop_all.bat       # stops them all
```

Or start any single service manually:
```powershell
streamlit run plagiarism_app/teacher_ui.py --server.port 8503
```

## Notes

- Ollama must be installed and **both models pulled** before the AI features work.
  Until then the apps still launch; AI calls just return an "unavailable" message.
- The Ollama address defaults to `http://localhost:11434`. Override with
  `OLLAMA_HOST=http://...` environment variable if Ollama runs on another machine.
- Every new PowerShell window must run `.venv\Scripts\activate` before any command.
- Full Windows setup guide: see `docs/04-run-on-windows.md`
