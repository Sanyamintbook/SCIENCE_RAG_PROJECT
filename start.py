"""
start.py — Single launcher for ALL services
=============================================
Run this instead of run_all.bat.

    python start.py

All 6 services start silently in the BACKGROUND (no separate windows).
Press Ctrl+C once to stop EVERYTHING cleanly.
"""

import subprocess   # lets Python start other programs as background processes
import sys          # lets us read the Python executable path
import os           # lets us build file paths
import time         # lets us pause (sleep) between steps
import signal       # lets us catch Ctrl+C

# ── Where is this file? Build all paths from here. ──────────────────────────
ROOT   = os.path.dirname(os.path.abspath(__file__))   # project root folder
PYTHON = sys.executable                                # the python.exe inside .venv
STREAM = os.path.join(os.path.dirname(PYTHON), "streamlit.exe")   # streamlit.exe
UVICORN = os.path.join(os.path.dirname(PYTHON), "uvicorn.exe")    # uvicorn.exe

# ── Define all 6 services ───────────────────────────────────────────────────
# Each entry: (display name, command list, working directory)
SERVICES = [
    (
        "RAG Backend       (http://localhost:8000)",
        [UVICORN, "api:app", "--port", "8000", "--log-level", "warning"],
        os.path.join(ROOT, "rag_app"),
    ),
    (
        "RAG Chat UI       (http://localhost:8501)",
        [STREAM, "run", os.path.join(ROOT, "rag_app", "rag_ui.py"),
         "--server.port", "8501", "--server.headless", "true", "--logger.level", "error"],
        ROOT,
    ),
    (
        "Plagiarism Backend(http://localhost:8001)",
        [UVICORN, "plagiarism_api:app", "--port", "8001", "--log-level", "warning"],
        os.path.join(ROOT, "plagiarism_app"),
    ),
    (
        "Student UI        (http://localhost:8502)",
        [STREAM, "run", os.path.join(ROOT, "plagiarism_app", "student_ui.py"),
         "--server.port", "8502", "--server.headless", "true", "--logger.level", "error"],
        ROOT,
    ),
    (
        "Teacher UI        (http://localhost:8503)",
        [STREAM, "run", os.path.join(ROOT, "plagiarism_app", "teacher_ui.py"),
         "--server.port", "8503", "--server.headless", "true", "--logger.level", "error"],
        ROOT,
    ),
    (
        "Dashboard         (http://localhost:8500)",
        [STREAM, "run", os.path.join(ROOT, "dashboard", "main_dashboard.py"),
         "--server.port", "8500", "--server.headless", "true", "--logger.level", "error"],
        ROOT,
    ),
    (
        "Listening Backend (http://localhost:8002)",
        [UVICORN, "listening_api:app", "--port", "8002", "--log-level", "warning"],
        os.path.join(ROOT, "listening_app"),
    ),
    (
        "Listen Teacher UI (http://localhost:8504)",
        [STREAM, "run", os.path.join(ROOT, "listening_app", "frontend", "teacher_listening.py"),
         "--server.port", "8504", "--server.headless", "true", "--logger.level", "error"],
        ROOT,
    ),
    (
        "Listen Student UI (http://localhost:8505)",
        [STREAM, "run", os.path.join(ROOT, "listening_app", "frontend", "student_listening.py"),
         "--server.port", "8505", "--server.headless", "true", "--logger.level", "error"],
        ROOT,
    ),
]

# ── Start all services ───────────────────────────────────────────────────────
processes = []   # we collect all running processes here so we can stop them later

print("\n" + "="*55)
print("   [START]  Starting AI Tools - Science RAG + Plagiarism")
print("="*55)

for name, cmd, cwd in SERVICES:
    try:
        # Open a log file to catch background crashes
        log_file = open(os.path.join(ROOT, "backend_crash.log"), "a")
        
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=log_file, # Log the actual Python crash reasons!
        )
        processes.append((proc, log_file))
        print(f"  [SUCCESS]  Started  {name}")
        time.sleep(0.5)   # small pause so services don't all fight for resources at once
    except FileNotFoundError:
        print(f"  [ERROR]  Could not find command to start {name}.")
    except Exception as e:
        print(f"  [ERROR]  Failed to start {name}: {e}")
        print("      Make sure your .venv is activated and requirements are installed.")

print()
print("="*55)
print("  Open your browser and go to:")
print("      http://localhost:8500")
print()
print("  Press  Ctrl + C  to stop everything.")
print("="*55 + "\n")

# ── Wait and handle Ctrl+C ──────────────────────────────────────────────────
try:
    # Keep this script alive forever (the background processes run independently).
    # Without this loop the script would exit immediately and the services would
    # keep running orphaned — Ctrl+C would have nothing to catch.
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    # Ctrl+C was pressed — shut down ALL services cleanly.
    print("\n\n  Stopping all services...")
    for proc, log_file in processes:
        try:
            proc.terminate()   # sends a polite stop signal to each process
        except Exception:
            pass
        try:
            log_file.close()
        except Exception:
            pass
    time.sleep(2)
    print("  All services stopped. Goodbye!")
    sys.exit(0)
