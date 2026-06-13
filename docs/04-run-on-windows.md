# 4. Running on Windows

A complete, beginner-friendly guide to run this project on a **Windows 10 / 11**
PC. Everything stays local (no paid APIs).

---

## 4.1 Requirements

| Need | Details |
|------|---------|
| OS | Windows 10 or 11 (64-bit) |
| RAM | **8 GB minimum** (use `qwen2.5:3b`). 16 GB+ can use `qwen2.5:7b`. |
| Disk | ~6 GB free (models + libraries) |
| Python | **3.12** (NOT 3.13/3.14 — some AI libraries lack wheels for those) |
| Ollama | Ollama for Windows (runs the AI models locally) |
| The PDF | `10th_science_book.pdf` inside the `rag_app/` folder (needed once to build the search index) |

---

## 4.2 Step 1 — Install Python 3.12

1. Download **Python 3.12** from <https://www.python.org/downloads/windows/>.
2. Run the installer and **tick "Add python.exe to PATH"** on the first screen.
3. Verify in a new **PowerShell** (search "PowerShell" in Start menu):
   ```powershell
   py -3.12 --version
   ```
   It should print `Python 3.12.x`.

---

## 4.3 Step 2 — Install Ollama and the models

1. Download **Ollama for Windows** from <https://ollama.com/download/windows>.
2. Run `OllamaSetup.exe`. It installs and starts automatically (you'll see a small
   llama icon in the system tray / bottom-right). It listens on
   `http://localhost:11434`.
3. Pull the two models — in PowerShell:
   ```powershell
   ollama pull qwen2.5:3b
   ollama pull nomic-embed-text
   ```
4. Verify:
   ```powershell
   ollama list
   ```
   You should see both models. Quick test:
   ```powershell
   ollama run qwen2.5:3b "say hello"
   ```
   (Press `Ctrl + D` to exit.)

---

## 4.4 Step 3 — Set up the project

Open **PowerShell** and go to the project folder (adjust the path to where you
put it):

```powershell
cd C:\Users\YOUR_NAME\Documents\SCIENCE_RAG_PROJECT-main
```

Create and activate a **virtual environment** (an isolated package folder so
this project's libraries don't interfere with anything else on your PC):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
```

Your prompt now starts with `(.venv)`. Install the libraries:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Remember:** every new PowerShell window for this project must run
> `.venv\Scripts\activate` first before any other command.

---

## 4.5 Step 4 — Build the science search index (once only)

This reads the textbook PDF and builds the FAISS vector index on disk.
You only need to do this **one time** (or if the PDF changes):

```powershell
cd rag_app
python app.py
```

Wait until you see **"Your AI Tutor is Ready!"**, then type `exit` and press Enter.
Go back to the project root:

```powershell
cd ..
```

---

## 4.6 Step 5 — Start everything (the easy way)

> ✅ **This is the recommended way.** One command, one terminal, no clutter.

Make sure your virtual environment is activated (you see `(.venv)` in your prompt),
then run:

```powershell
python start.py
```

You will see a clean status output like this:

```
=======================================================
   🚀  Starting AI Tools — Science RAG + Plagiarism
=======================================================
  ✅  Started  RAG Backend       (http://localhost:8000)
  ✅  Started  RAG Chat UI       (http://localhost:8501)
  ✅  Started  Plagiarism Backend(http://localhost:8001)
  ✅  Started  Student UI        (http://localhost:8502)
  ✅  Started  Teacher UI        (http://localhost:8503)
  ✅  Started  Dashboard         (http://localhost:8500)

=======================================================
  🌐  Open your browser and go to:
      http://localhost:8500

  ⏹️   Press  Ctrl + C  to stop everything.
=======================================================
```

All 6 services run silently in the background — **no separate windows**.

Wait ~10 seconds, then open your browser to:

### 👉 http://localhost:8500   (the master dashboard)

From there:
- **Science Tutor** — ask questions from the textbook.
- **Student Portal** — upload an assignment.
- **Teacher Reports** — click *Run analysis* to score all submissions.

> The Ollama tray app (llama icon in the bottom-right system tray) must be
> running. The first AI answer is slow (~10–20s) while the model loads into
> memory, then it speeds up.

---

## 4.7 Stopping

Press **`Ctrl + C`** once in the PowerShell window where `start.py` is running.

This stops **all 6 services at once** cleanly:

```
  🛑  Stopping all services...
  ✅  All services stopped. Goodbye!
```

That's it — one keypress and everything shuts down.

---

## 4.8 Your daily workflow (after first-time setup)

Every time you want to use the project:

```powershell
# 1. Open PowerShell

# 2. Go to the project folder
cd C:\Users\YOUR_NAME\Documents\SCIENCE_RAG_PROJECT-main

# 3. Activate the virtual environment
.venv\Scripts\activate

# 4. Start everything
python start.py

# 5. Open browser → http://localhost:8500

# 6. When done, press Ctrl+C to stop all services
```

---

## 4.9 The ports

| Service | URL | File |
|---------|-----|------|
| Master dashboard | http://localhost:8500 | `dashboard/main_dashboard.py` |
| Science Tutor chat | http://localhost:8501 | `rag_app/rag_ui.py` |
| Student upload | http://localhost:8502 | `plagiarism_app/student_ui.py` |
| Teacher reports | http://localhost:8503 | `plagiarism_app/teacher_ui.py` |
| RAG backend | http://localhost:8000 | `rag_app/api.py` |
| Plagiarism backend | http://localhost:8001 | `plagiarism_app/plagiarism_api.py` |
| Ollama AI engine | http://localhost:11434 | (separate installation) |

---

## 4.10 Common problems

| Problem | Fix |
|---------|-----|
| `'python' is not recognized` | Use `py -3.12` instead, or reinstall Python with "Add to PATH" ticked. |
| `pip install` errors about Python version | You are on 3.13/3.14. Install **3.12** and recreate the venv with `py -3.12 -m venv .venv`. |
| `start.py` shows ❌ FAILED for a service | Make sure `.venv` is activated and `pip install -r requirements.txt` completed successfully. |
| Pages show "Could not reach backend" | Wait 15 seconds after running `start.py` — services need a moment to fully start. |
| AI features return "unavailable" | The Ollama tray icon is not running, or models are not pulled. Re-check Step 2. |
| `streamlit` asks for an email | Press Enter to skip. |
| PowerShell says `run_all.bat` not recognized | Use `python start.py` instead (the recommended method), or prefix with `.\` → `.\run_all.bat`. |

---

## 4.11 Alternative: run_all.bat (old method — not recommended)

If for any reason `start.py` does not work, you can fall back to the original
batch script. In PowerShell you must prefix it with `.\`:

```powershell
.\run_all.bat
```

This opens **6 separate black terminal windows** (one per service). To stop,
either close each window manually or run:

```powershell
.\stop_all.bat
```

---

[← Back to docs index](README.md)
