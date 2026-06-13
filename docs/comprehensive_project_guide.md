# Comprehensive Project Guide: Science RAG & Plagiarism Detector

This document is a technical reference guide for the **Science RAG + Plagiarism Detector** project. It is structured to help you understand every aspect of the project—from high-level architecture to line-by-line code logic, library choices, and technical terms—so you can confidently explain it to your mentor.

---

## Table of Contents
1. Folder & Directory Structure
2. Library Dependency Mapping (with Alternatives)
3. Architecture, Ports, & Communication Flow
4. Exhaustive File-by-File & Function-by-Function Walkthrough
   - Dashboard Component
   - Science Tutor (RAG) Component
   - Plagiarism Detector Component
5. How Ollama Runs & Communicates

---

## 1. Folder & Directory Structure

Here is the structural blueprint of the project and the technical reason why each file and folder exists.

```
science_rag_project/
|-- .gitignore                   # Git configuration: lists untracked files to exclude from version control.
|-- requirements.txt             # Dependency manifest: list of all external Python libraries required.
|-- run_all.bat                  # Bootstrap script (Windows): starts all backends and frontends concurrently.
|-- run_all.sh                   # Bootstrap script (Bash): Linux/macOS equivalent of run_all.bat.
|-- stop_all.bat                 # Cleanup script (Windows): kills running processes bound to app ports.
|-- stop_all.sh                  # Cleanup script (Bash): Linux/macOS equivalent of stop_all.bat.
|
|-- submissions/                 # Data directory: stores raw binary documents uploaded by students.
|-- reports/                     # Data directory: stores generated JSON report outputs.
|
|-- dashboard/
|   |-- main_dashboard.py        # Entry point web interface (Port 8500): redirects users to sub-applications.
|
|-- rag_app/                     # Retrieval-Augmented Generation (RAG) subsystem
|   |-- 10th_science_book.pdf    # Source knowledge base: the raw PDF textbook.
|   |-- app.py                   # One-time builder: extracts, embeds, and indexes the PDF to disk.
|   |-- api.py                   # RAG API backend (Port 8000): FastAPI endpoint that runs the query chain.
|   |-- rag_ui.py                # RAG Client UI (Port 8501): Streamlit chat interface.
|   |-- faiss_science_index/     # Database folder: serialized FAISS files (index.faiss, index.pkl).
|
|-- plagiarism_app/              # Plagiarism detector subsystem
    |-- plagiarism_api.py        # Plagiarism API backend (Port 8001): routes analysis requests.
    |-- student_ui.py            # Student Client UI (Port 8502): uploads student files to backend.
    |-- teacher_ui.py            # Teacher Client UI (Port 8503): displays reports and drill-downs.
    |-- report_builder.py        # Business logic: merges detector metrics into a single score.
    |-- detectors/               # Modular checking library (Python package)
        |-- __init__.py          # Package initializer: makes the folder importable as a Python package.
        |-- ollama_client.py     # HTTP Client wrapper: connects the app to the local Ollama service.
        |-- text_extractor.py    # ETL utility: converts PDF/DOCX/PPTX into normalized text strings.
        |-- ai_detector.py       # Judge: instructs Qwen2.5 to evaluate writing style via JSON prompt.
        |-- copy_checker.py      # Math analyzer: compares words using TF-IDF and Cosine Similarity.
        |-- paraphrase.py        # Math analyzer: compares sentence meaning-vectors via cosine distance.
        |-- originality.py       # Stats analyzer: evaluates text metrics (TTR, burstiness, markers).
```

---

## 2. Library Dependency Mapping (with Alternatives)

Each library in requirements.txt is listed below with its purpose, key functions, alternatives, and the reason it was chosen.

### fastapi
- Technical Purpose: Web API Framework — used to build the backend engines (ports 8000 and 8001).
- Key Functions: FastAPI(), @app.post(), @app.get(), UploadFile, HTTPException, Form, File
- Alternatives: Flask, Django, Sanic, Bottle
- Why Chosen: Modern, extremely fast (built on Starlette + Pydantic), auto-generates Swagger UI API documentation at /docs, and supports type validation out of the box.

### uvicorn
- Technical Purpose: ASGI (Asynchronous Server Gateway Interface) Web Server — the actual engine that runs a FastAPI app and listens for network requests.
- Key Functions: Used via command line — `uvicorn api:app --port 8000`
- Alternatives: Hypercorn, Daphne, Gunicorn (WSGI, not ASGI)
- Why Chosen: It is the recommended standard server for FastAPI. Lightweight, extremely fast, and supports async programming natively.

### streamlit
- Technical Purpose: Frontend Web UI Framework — used to build all visual browser interfaces (dashboard, chat, upload, reports) in pure Python.
- Key Functions: st.title(), st.write(), st.columns(), st.chat_input(), st.dataframe(), st.session_state, st.progress(), st.spinner(), st.link_button()
- Alternatives: Gradio, Dash (by Plotly), Panel, Reflex, Flask + HTML templates
- Why Chosen: No HTML, CSS, or JavaScript knowledge required. Every Python variable and function call becomes an interactive UI component automatically.

### requests
- Technical Purpose: HTTP Client Library — allows Python programs to send HTTP requests to other services (like calling the FastAPI backend from within a Streamlit UI file).
- Key Functions: requests.post(), requests.get(), response.json(), response.ok
- Alternatives: httpx (async-capable), urllib3, aiohttp, http.client (built-in)
- Why Chosen: The industry-standard, simplest, most readable library for HTTP operations in Python.

### python-multipart
- Technical Purpose: HTTP Form Data Parser — required by FastAPI to accept multipart/form-data requests (the standard format for file uploads with accompanying text fields).
- Key Functions: No direct function calls — FastAPI auto-uses it when `UploadFile` or `Form(...)` appears in an endpoint.
- Alternatives: Built-in email.parser, cgi module (deprecated)
- Why Chosen: FastAPI's official dependency for handling file uploads alongside form fields.

### pymupdf (imported as fitz)
- Technical Purpose: PDF Parser — reads PDF binary files and extracts raw text content per page.
- Key Functions: fitz.open(filepath), doc[page_index], page.get_text()
- Alternatives: PyPDF2, pdfplumber, pypdf, pdfminer
- Why Chosen: Extremely fast (C-based implementation), more accurate text layout extraction, and handles a wider range of PDF encodings than alternatives.

### python-docx (imported as docx)
- Technical Purpose: Microsoft Word File Parser — reads .docx files and extracts text from paragraphs.
- Key Functions: docx.Document(filepath), document.paragraphs, paragraph.text
- Alternatives: docx2txt, Mammoth, textract
- Why Chosen: The official and most comprehensive library for reading and writing .docx file format natively.

### python-pptx (imported as pptx)
- Technical Purpose: Microsoft PowerPoint Parser — reads .pptx files and extracts text from slides.
- Key Functions: Presentation(filepath), prs.slides, slide.shapes, shape.has_text_frame, shape.text_frame.text
- Alternatives: Custom ZIP extraction (PPTX is a zip archive of XML files), LibreOffice SDK
- Why Chosen: The standard library for structured access to PowerPoint slide content.

### scikit-learn
- Technical Purpose: Machine Learning and Statistics Toolkit — used for TF-IDF vectorization and cosine similarity calculation in the copy checker.
- Key Functions: TfidfVectorizer(), vectorizer.fit_transform(docs), cosine_similarity(matrix)
- Alternatives: TensorFlow, PyTorch (overkill for this task), SciPy, raw math with numpy
- Why Chosen: Provides highly optimized, production-grade implementations of standard ML algorithms. No model training needed — these are mathematical transformations.

### numpy
- Technical Purpose: Numerical Array and Linear Algebra Library — used for vector math in the paraphrase detector.
- Key Functions: np.array(), np.dot(a, b), np.linalg.norm(v)
- Alternatives: Pure Python lists with math module (much slower)
- Why Chosen: Performs vector operations (dot product, norm calculation) at C-compiled speeds. Essential for working with embedding vectors efficiently.

### pandas
- Technical Purpose: Tabular Data Manipulation Library — used to load report data into a table and apply conditional cell formatting in the teacher UI.
- Key Functions: pd.DataFrame(rows), df.rename(columns={...}), df.style, df.style.map(), df.style.format()
- Alternatives: Polars (faster but less mature), native Python lists
- Why Chosen: Industry-standard for tabular data manipulation. Streamlit natively renders pandas DataFrames with formatting support.

### langchain-community, langchain-core, langchain-classic, langchain-text-splitters, langchain-ollama
- Technical Purpose: LLM Application Orchestration Framework — provides pre-built components for loading documents, splitting text, connecting to Ollama, building prompt templates, and chaining them into a RAG pipeline.
- Key Functions: PyMuPDFLoader, RecursiveCharacterTextSplitter, OllamaEmbeddings, OllamaLLM, ChatPromptTemplate, create_retrieval_chain, create_stuff_documents_chain
- Alternatives: LlamaIndex (formerly GPT Index), Haystack, raw Python code writing all components manually
- Why Chosen: The most popular LLM framework. Provides well-tested abstractions for RAG pipelines, dramatically reducing the amount of code needed.

### faiss-cpu
- Technical Purpose: Vector Similarity Search Database — stores document embedding vectors on disk and performs fast nearest-neighbor searches during query time.
- Key Functions: FAISS.from_documents(chunks, embeddings), db.add_documents(batch), db.save_local(path), FAISS.load_local(path, embeddings), db.as_retriever(search_kwargs={"k": 3})
- Alternatives: ChromaDB, Pinecone (cloud), Qdrant, Weaviate, Milvus
- Why Chosen: Developed by Meta AI Research. Fastest local vector search available. Saves as simple binary files — no separate database server required.

### tqdm
- Technical Purpose: Progress Bar Visualization — wraps any iterable and renders an animated progress bar in the terminal showing completion percentage and estimated time.
- Key Functions: tqdm(iterable, desc="label")
- Alternatives: Custom print() counter, rich library progress bars
- Why Chosen: Zero-configuration, one-line integration with any Python loop. Universal standard for CLI progress reporting.

---

## 3. Architecture, Ports, & Communication Flow

The system runs as a Local Microservices Architecture on the loopback network interface (127.0.0.1 / localhost).

### Port Directory
| Port | Service | File |
|------|---------|------|
| 8500 | Master Dashboard UI | dashboard/main_dashboard.py |
| 8000 | RAG Backend API | rag_app/api.py |
| 8501 | RAG Chat UI | rag_app/rag_ui.py |
| 8001 | Plagiarism Backend API | plagiarism_app/plagiarism_api.py |
| 8502 | Student Upload UI | plagiarism_app/student_ui.py |
| 8503 | Teacher Report UI | plagiarism_app/teacher_ui.py |
| 11434 | Ollama AI Engine | (separate installation) |

### Communication Chain
1. Browser visits http://localhost:8500 (Dashboard)
2. User clicks "Science Tutor" → Browser goes to port 8501 (RAG Chat UI)
3. RAG Chat UI sends question via HTTP POST to port 8000 (RAG API Backend)
4. RAG API Backend sends text to port 11434 (Ollama) and gets back answer
5. Answer flows back: Ollama → RAG API → RAG Chat UI → Browser

---

## 4. Exhaustive File-by-File & Function-by-Function Walkthrough

---

### A. Dashboard Component

#### FILE: dashboard/main_dashboard.py
**Purpose:** The entry point landing page (Port 8500). It does NOT run any AI or analysis — it simply provides navigation buttons to the other running applications.

**The Docstring (Lines 1-7):**
The triple-quoted text at the top is called a docstring — it is developer documentation embedded in the code. It explains what the file does, which port it uses, and how to run it manually.

**Line 9: `import streamlit as st`**
- "import" = load an external library into memory
- "streamlit" = the name of the library being loaded
- "as st" = creates an alias, a shorter name. Instead of writing `streamlit.title(...)` everywhere, we write `st.title(...)`. This is purely for convenience.
- WHERE IS THIS FROM: installed via `pip install streamlit`

**Line 11: `st.set_page_config(page_title="My AI Tools", page_icon="🧰", layout="centered")`**
- `st.set_page_config()` = a Streamlit function that configures the browser window settings. MUST be the very first Streamlit command in any script.
- `page_title="My AI Tools"` = sets the text shown on the browser tab
- `page_icon="🧰"` = sets the favicon (the small icon next to the tab title)
- `layout="centered"` = constrains the page content to the center of the screen (alternative is "wide" which uses full browser width)

**Line 12: `st.title("🧰 My AI Tools Dashboard")`**
- `st.title()` = renders a large heading (equivalent to an HTML H1 tag)
- Argument = the text string to display

**Line 13: `st.markdown("Pick a tool to open it in a new tab.")`**
- `st.markdown()` = renders text with Markdown formatting support (bold, italic, links, etc.)
- Used here simply to display a subtitle instruction sentence

**Line 14: `st.markdown("---")`**
- Rendering "---" in Markdown creates a horizontal dividing line on the page

**Line 16: `col1, col2 = st.columns(2)`**
- `st.columns(2)` = divides the page layout into 2 equal vertical side-by-side columns
- Returns a list of column objects. We unpack them directly into two variables: `col1` and `col2`
- This is called "tuple unpacking" — instead of `cols = st.columns(2); col1 = cols[0]; col2 = cols[1]`, Python lets you do it in one line.

**Lines 19-23: `with col1:` block**
- `with col1:` = a context manager that directs all following content to render inside the first column
- `st.subheader("🔬 R&D — Science Tutor")` = renders a smaller heading (H2/H3 equivalent)
- `st.write(...)` = the most flexible display function — renders text, numbers, dataframes, etc.
- `st.link_button("Open Science Tutor →", "http://localhost:8501", use_container_width=True)` = renders a clickable button that opens the given URL
  - First argument = button label text
  - Second argument = the destination URL
  - `use_container_width=True` = stretches the button to fill the full column width

**Lines 26-32: `with col2:` block**
- Same structure as `col1` but for the Plagiarism Detector side
- Two separate `st.link_button()` calls create two buttons stacked vertically:
  - Student Portal → http://localhost:8502
  - Teacher Reports → http://localhost:8503

---

### B. Science Tutor (RAG) Component

#### FILE: rag_app/app.py
**Purpose:** One-time ETL script. Reads the textbook PDF, converts it into mathematical vectors (embeddings), and saves them to a local FAISS database folder. Also contains a terminal-based test chat.

**Lines 1-14: Imports**
- `import os` — Built-in Python library. Used to interact with the operating system (check if files/folders exist via `os.path.exists()`)
- `from langchain_community.document_loaders import PyMuPDFLoader` — From LangChain's community package, import the PDF reader class that uses PyMuPDF internally
- `from langchain_text_splitters import RecursiveCharacterTextSplitter` — From LangChain, import the text chunker class
- `from langchain_community.vectorstores import FAISS` — From LangChain, import the FAISS wrapper class
- `from langchain_ollama import OllamaEmbeddings, OllamaLLM` — From the Ollama-specific LangChain package, import the embedding and LLM connector classes
- `from langchain_classic.chains import create_retrieval_chain` — Function that wires the retriever and the LLM together into a single chain
- `from langchain_classic.chains.combine_documents import create_stuff_documents_chain` — Function that builds the sub-chain for inserting retrieved docs into the prompt
- `from langchain_core.prompts import ChatPromptTemplate` — Class for building structured prompt templates
- `from tqdm import tqdm` — Import the progress bar wrapper function

**Line 16: `INDEX_DIR = "faiss_science_index"`**
- Creates a constant string variable holding the folder name where FAISS data will be saved/loaded
- Writing it as a variable (not a raw string) means if you rename the folder, you only change it in ONE place

**Line 22: `if not os.path.exists(INDEX_DIR):`**
- `os.path.exists(path)` = checks if the folder/file exists on disk, returns True or False
- `not` = inverts the result. So this whole condition means: "if the folder does NOT exist"
- This is a one-time guard: the first run builds the index, every subsequent run skips straight to loading it

**Lines 25-30: PDF Loading**
- `loader = PyMuPDFLoader("10th_science_book.pdf")` = creates a loader object pointing at the PDF file
- `docs = []` = initializes an empty list to collect page objects
- `loader.lazy_load()` = reads pages one at a time from disk rather than loading the whole PDF into RAM at once (memory-efficient approach)
- `tqdm(loader.lazy_load(), desc="Reading Pages")` = wraps the lazy loader in a progress bar labeled "Reading Pages"
- `docs.append(page)` = adds each page object to the list as it is read

**Lines 34-36: Text Splitting**
- `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)` = creates a splitter with two rules:
  - `chunk_size=1000`: each chunk will have at most 1000 characters
  - `chunk_overlap=200`: consecutive chunks share 200 characters of content at their boundary (prevents losing context at split points)
- `text_splitter.split_documents(docs)` = applies the splitting rules to all loaded pages and returns a flat list of chunk objects

**Lines 39-49: Embedding and Indexing**
- `OllamaEmbeddings(model="nomic-embed-text")` = creates a connector object that will send text to Ollama's nomic-embed-text model and receive floating-point vectors in return
- `batch_size = 25` = process 25 chunks per API call to avoid overloading Ollama
- `FAISS.from_documents(chunks[:batch_size], embeddings)` = initializes the FAISS index with the first 25 chunks; sends each chunk to Ollama, gets back a vector, stores it
- `range(batch_size, len(chunks), batch_size)` = generates indices [25, 50, 75, 100, ...] up to the total chunk count
- `db.add_documents(batch)` = sends the next batch of chunks to Ollama for embedding, then appends the vectors to the existing database
- `db.save_local(INDEX_DIR)` = serializes (saves) the FAISS index to the `faiss_science_index/` folder on disk

**Line 55: `db = FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)`**
- Loads the pre-built FAISS index from disk
- `allow_dangerous_deserialization=True` = FAISS uses Python's `pickle` module to save data. Pickle can theoretically execute code when loading, so LangChain requires this flag to explicitly acknowledge the security trade-off.

**Lines 63-81: RAG Chain Setup**
- `OllamaLLM(model="qwen2.5:3b")` = creates a connector to the Qwen2.5 language model for text generation
- `system_prompt` = a multi-line string defining the rules for the AI: answer only from context, do not invent facts
- `ChatPromptTemplate.from_messages([...])` = compiles the system rules and a `{input}` placeholder into a reusable prompt template object
- `db.as_retriever(search_kwargs={"k": 3})` = converts the FAISS database into a search interface; `k: 3` means "return the 3 most similar chunks for any query"
- `create_stuff_documents_chain(llm, prompt)` = creates a chain that "stuffs" (inserts) the retrieved chunks into the `{context}` slot of the prompt template
- `create_retrieval_chain(retriever, combine_docs_chain)` = links the retriever and the stuffing chain: given a question, retrieve chunks, insert into prompt, send to LLM

**Lines 92-112: Terminal Chat Loop**
- `while True:` = infinite loop that keeps running until explicitly broken
- `input("\nYour Question: ")` = pauses execution and waits for user to type in the terminal
- `if user_question.lower() in ['exit', 'quit']:` = checks for exit commands (`.lower()` normalizes case so "EXIT" also matches)
- `break` = exits the while loop
- `if not user_question.strip(): continue` = `strip()` removes whitespace. If the result is empty, skip this iteration and loop again
- `rag_chain.invoke({"input": user_question})` = runs the full RAG pipeline: embed question → search FAISS → insert chunks → generate answer
- `response["answer"]` = extracts just the answer string from the returned dictionary

#### FILE: rag_app/api.py
**Purpose:** The same RAG logic as app.py but exposed as a web service on Port 8000 using FastAPI. Instead of a terminal loop, it listens for HTTP requests.

**Lines 1-7: Imports**
- `from fastapi import FastAPI, HTTPException` = FastAPI application class and HTTP error class
- `from pydantic import BaseModel` = Pydantic is FastAPI's data validation library. BaseModel is its base class for defining data schemas.
- All other imports same as app.py

**Lines 12: `app = FastAPI(title="10th Grade Science AI Tutor")`**
- Creates the FastAPI application instance. This is the central object that all routes (endpoints) attach to.
- `title` appears in the auto-generated Swagger documentation page at /docs

**Lines 14-15: `class UserRequest(BaseModel): question: str`**
- Defines a data model (schema) for incoming request bodies
- Any HTTP POST request to this API MUST provide a JSON body like: `{"question": "What is photosynthesis?"}`
- If the request is missing the `question` field or it is not a string, FastAPI automatically returns a 422 error before the function even runs.

**Lines 20-42: Startup code (runs once when the server starts)**
- Loads the FAISS index, connects to Ollama, builds the retrieval chain — all identical to app.py

**Line 49: `@app.post("/ask")`**
- This is a Python "decorator" — a special annotation starting with `@`
- It registers the function below it as the handler for HTTP POST requests to the path `/ask`
- The full URL becomes: http://localhost:8000/ask

**Lines 50-59: `def ask_tutor(request: UserRequest):`**
- Defines the endpoint function. FastAPI automatically deserializes the incoming JSON into a `UserRequest` object
- `request.question` = accesses the question string from the validated request body
- `try/except` block = error handling: if anything inside `try` throws an exception, execution jumps to `except`
- `rag_chain.invoke({"input": request.question})` = runs the RAG pipeline
- `return {"answer": response["answer"]}` = FastAPI automatically converts this Python dictionary to a JSON HTTP response
- `raise HTTPException(status_code=500, detail=...)` = sends a proper HTTP 500 Internal Server Error response with error details

#### FILE: rag_app/rag_ui.py
**Purpose:** The browser-based chat interface (Port 8501). Does NO AI processing itself — it is purely a UI that communicates with api.py.

**Line 10-11: `import streamlit as st` and `import requests`**
- `requests` library is needed to call the FastAPI backend from within the Streamlit script

**Line 13: `API = "http://localhost:8000"`**
- Stores the backend base URL as a constant. Every API call in this file builds on this string.

**Lines 15-17: Page configuration**
- Same pattern as dashboard: set tab title, render page title and caption

**Lines 20-21: Session State Initialization**
- `st.session_state` = a special Streamlit dictionary that persists across script re-runs (Streamlit re-executes the entire script from top to bottom every time any interaction occurs)
- `if "messages" not in st.session_state:` = checks if we already initialized the history. Only sets it to `[]` on the very first run.
- `st.session_state.messages = []` = the message history is a list of dictionaries: `[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`

**Lines 24-26: Replay Conversation**
- `for msg in st.session_state.messages:` = loops through the stored history
- `with st.chat_message(msg["role"]):` = renders a chat bubble styled for either "user" (right-aligned) or "assistant" (left-aligned)
- `st.markdown(msg["content"])` = displays the message text

**Line 29: `question = st.chat_input("Your question...")`**
- Renders the text input box pinned to the bottom of the page
- Returns the typed text when submitted, or `None` if not yet submitted

**Lines 30-45: Question Submission Handler**
- `if question:` = only runs if the user actually submitted something
- Appends user message to session state history, renders it immediately
- `requests.post(f"{API}/ask", json={"question": question}, timeout=300)` = sends HTTP POST request to the backend. `f"{API}/ask"` = f-string formatting builds the full URL. `json={"question": question}` = sends the data as JSON. `timeout=300` = waits up to 5 minutes for a response.
- `res.json().get("answer", res.text)` = parses the JSON response and retrieves the "answer" key; falls back to raw text if "answer" is missing
- `if res.ok` = checks if the HTTP status code was successful (200-299)

---

### C. Plagiarism Detector Component

#### FILE: plagiarism_app/detectors/__init__.py
**Purpose:** Makes the `detectors/` folder into a Python package. Without this file, `from detectors.copy_checker import check_all_submissions` would fail because Python would not recognize `detectors` as an importable package.
- Contents: just a comment and an `__all__` list declaring which modules are part of the public API.

#### FILE: plagiarism_app/detectors/ollama_client.py
**Purpose:** Centralizes all HTTP communication with the Ollama service. All other files that need AI go through this single file.

**Line 15-17: Imports**
- `import os` = to read environment variables
- `import json` = to parse JSON strings into Python dictionaries
- `import requests` = to make HTTP calls to Ollama

**Line 21: `OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")`**
- `os.environ.get(key, default)` = reads an environment variable by name. If not set, returns the default value.
- This makes the Ollama address configurable: set `OLLAMA_HOST=http://192.168.1.10:11434` in your environment and the whole app switches to a remote Ollama without changing any code.

**Lines 28-44: `def generate(prompt: str, temperature: float = 0.1) -> str:`**
- Function signature:
  - `prompt: str` = type hint saying the argument must be a string
  - `temperature: float = 0.1` = optional parameter with a default value
  - `-> str` = return type hint indicating this function returns a string
- Temperature in LLMs: controls randomness. 0.0 = completely deterministic (same answer every time). 1.0 = highly creative/random. 0.1 = nearly deterministic, appropriate for consistent scoring.
- `requests.post(f"{OLLAMA_HOST}/api/generate", json={...}, timeout=300)` = sends a POST request to Ollama's generate endpoint
- `"stream": False` = tells Ollama to wait until generation is complete before returning the full response (as opposed to streaming tokens one by one)
- `response.raise_for_status()` = checks if the HTTP response code is an error (4xx or 5xx) and raises a Python exception if so

**Lines 47-58: `def embed(text: str) -> list:`**
- Sends text to the `/api/embeddings` endpoint
- Ollama passes the text through the `nomic-embed-text` model and returns a list of 768 floating-point numbers representing the semantic meaning of the text

**Lines 61-72: `def extract_json(raw: str) -> dict:`**
- LLMs sometimes return JSON wrapped in Markdown code fences like:
  ```
  ```json
  {"verdict": "high"}
  ```
  ```
- This function strips those fences using `.split("```")` and then parses the clean JSON string with `json.loads()`

#### FILE: plagiarism_app/detectors/text_extractor.py
**Purpose:** Converts any uploaded document file into a single clean text string.

**Lines 18-24: `def _extract_pdf(filepath: str) -> str:`**
- The underscore prefix `_` is a Python convention meaning "private function" — intended to be used only within this file
- `fitz.open(filepath)` = opens the PDF. `fitz` is the import alias for the `pymupdf` library
- `[page.get_text() for page in doc]` = a list comprehension that loops through every page object and calls `get_text()` on each, collecting the strings into a list
- `" ".join(pages)` = joins all page strings into one large string separated by spaces
- `doc.close()` = releases the file handle so the OS can access the file again

**Lines 27-32: `def _extract_docx(filepath: str) -> str:`**
- `docx.Document(filepath)` = opens the Word document and parses its XML structure
- `.paragraphs` = property returning a list of all paragraph objects in the document
- `[p.text for p in document.paragraphs]` = list comprehension extracting just the text from each paragraph

**Lines 35-44: `def _extract_pptx(filepath: str) -> str:`**
- `Presentation(filepath)` = opens the PowerPoint file
- `prs.slides` = collection of all slides
- `slide.shapes` = collection of all visual elements (text boxes, images, charts) on the slide
- `shape.has_text_frame` = boolean property — True only if the shape contains text (as opposed to images or charts)
- `shape.text_frame.text` = the full text content of a text box

**Lines 47-68: `def extract_text(filepath: str) -> str:`**
- Main public function (no underscore = intended to be called from outside this file)
- `filepath.lower()` = converts path to lowercase so `.PDF` and `.pdf` are both matched
- `elif lower.endswith(".pdf"):` = checks file extension and routes to the correct private reader
- `raise ValueError(...)` = if no matching extension is found, raises an error with a clear message
- `" ".join(text.split())` = normalizes whitespace: `text.split()` splits on any whitespace (spaces, tabs, newlines) producing a clean word list, then `" ".join()` reassembles with single spaces

#### FILE: plagiarism_app/detectors/copy_checker.py
**Purpose:** Detects direct copy-paste between students using TF-IDF vectorization and cosine similarity.

**What is TF-IDF?**
- TF = Term Frequency: how often a word appears in one document
- IDF = Inverse Document Frequency: penalizes words that appear in many documents (common words like "the", "is")
- TF-IDF score = TF × IDF. Rare meaningful words get high scores; common filler words get near-zero scores.

**What is Cosine Similarity?**
- Measures the angle between two vectors. If two students used the same important words in the same proportions, their vectors point in the same direction → angle is 0° → cosine is 1.0 (100% similar). If they wrote completely differently → angle is 90° → cosine is 0.0.

**Lines 13-23: Function definition and validation**
- `texts: dict` = expects a dictionary like `{"Ravi": "full text...", "Priya": "full text..."}`
- `names = list(texts.keys())` = extract student names into an ordered list
- `docs = list(texts.values())` = extract text strings in the same order
- `if len(docs) < 2: return {...}` = early return with zero scores if there are fewer than 2 students (nothing to compare)

**Line 25: `tfidf = TfidfVectorizer().fit_transform(docs)`**
- `TfidfVectorizer()` = instantiates the vectorizer with default settings
- `.fit_transform(docs)` = two steps combined:
  - "fit" = learns the vocabulary and IDF weights from the entire set of documents
  - "transform" = converts each document into its TF-IDF vector
- Returns a sparse matrix: rows = students, columns = every unique word across all documents

**Line 26: `sim = cosine_similarity(tfidf)`**
- Computes the cosine similarity between every pair of row vectors in the TF-IDF matrix
- Returns a square matrix. `sim[i][j]` = similarity score between student `i` and student `j`
- `sim[i][i]` is always 1.0 (a document is 100% similar to itself)

**Lines 32-43: Pair comparison loop**
- `for i in range(len(names)):` = outer loop over all students
- `for j in range(i + 1, len(names)):` = inner loop starting from `i+1` to avoid duplicate pairs (we don't need both Ravi-Priya AND Priya-Ravi)
- `sim[i][j] * 100` = converts the 0.0-1.0 similarity to a 0-100 percentage
- `worst[names[i]] = max(worst[names[i]], score)` = tracks each student's highest match against any peer
- `"severity": "high" if score > 70 else "medium"` = inline conditional expression (ternary operator)

#### FILE: plagiarism_app/detectors/paraphrase.py
**Purpose:** Detects paraphrasing (same meaning, different words) by comparing sentence-level embedding vectors.

**Lines 14-17: `def _cosine(a, b) -> float:`**
- Manual cosine similarity implementation using NumPy
- `np.array(a)` = converts the Python list to a NumPy array for efficient math
- `np.dot(a, b)` = dot product: multiplies corresponding elements and sums them
- `np.linalg.norm(v)` = calculates the Euclidean length (magnitude) of a vector
- Formula: cosine = dot_product / (length_of_a × length_of_b)

**Lines 20-22: `def _sentences(text: str) -> list:`**
- `text.split(".")` = splits the text at every period character
- `s.strip()` = removes leading and trailing whitespace from each segment
- `len(s.strip()) > 20` = filter: only keep segments longer than 20 characters (eliminates trivial fragments)

**Lines 25-53: `def detect_paraphrase(text_a, text_b) -> dict:`**
- `sents_a, sents_b` = lists of sentences from each document
- `emb_a = [embed(s) for s in sents_a]` = sends each sentence to Ollama and gets back a vector; creates a list of vectors
- Nested loops compare every sentence from A against every sentence from B
- `score > 0.82` = threshold: sentences scoring above 82% are considered paraphrases
- `len(pairs) / len(sents_a) * 100` = percentage of A's sentences that are paraphrased from B

#### FILE: plagiarism_app/detectors/originality.py
**Purpose:** Computes three mathematical signals that indicate the text was written by a human.

**What is Type-Token Ratio (TTR)?**
- Count how many unique words (types) exist versus total word count (tokens)
- Humans naturally use varied vocabulary → high TTR
- AI tends to reuse the same words → lower TTR

**What is Burstiness?**
- Variance of sentence length divided by average sentence length
- Humans write some very short sentences and some very long ones (high variance = high burstiness)
- AI generates uniformly structured sentences of similar length (low variance = low burstiness)

**Lines 15-16: Setup**
- `text.split(".")` = splits into sentences
- `text.lower().split()` = converts to lowercase and splits into individual words

**Lines 18-20: TTR Calculation**
- `len(words)` = total word count
- `len(set(words))` = unique word count (Python `set` removes duplicates)
- `ttr = len(set(words)) / total` = ratio of unique to total

**Lines 22-29: Burstiness Calculation**
- `[len(s.split()) for s in sentences]` = word count per sentence
- `avg = sum(lengths) / len(lengths)` = mean sentence length
- `sum((l - avg) ** 2 for l in lengths) / len(lengths)` = statistical variance formula
- `variance / max(avg, 1)` = burstiness (avoid division by zero with max(..., 1))

**Lines 31-34: Personal Markers**
- `re.findall(pattern, text, re.IGNORECASE)` = finds all matches of the regex pattern in the text, case-insensitively
- `\b` = word boundary anchor in regex (ensures we match whole words, not "myself" matching inside "yourselves")
- Returns a list of all matches; `len(...)` gives the count

**Line 37: Combined Score**
- `min(100, (ttr * 40) + (min(burstiness, 5) * 8) + (personal * 3))`
- TTR contributes up to 40 points
- Burstiness capped at 5 contributes up to 40 points
- Each personal marker contributes 3 points
- `min(100, ...)` = prevents the score from exceeding 100

#### FILE: plagiarism_app/detectors/ai_detector.py
**Purpose:** Asks Qwen2.5 to read the student's text and judge whether it was AI-generated. Returns a structured JSON verdict.

**Lines 16-46: `_PROMPT_TEMPLATE`**
- A multi-line string (triple quotes) containing the complete instruction to the LLM
- Describes exactly what signals to look for in AI-written vs human-written text
- Specifies the EXACT JSON structure the model must return
- `{text}` = a placeholder that will be filled with the actual student text using `.format()`
- `{{` and `}}` = escaped curly braces in a format string (literal `{` and `}` characters)

**Lines 49-87: `def detect_ai_content(text: str) -> dict:`**
- `text[:6000]` = Python slicing: takes only the first 6000 characters. LLMs have a maximum context window; truncating prevents errors.
- `_PROMPT_TEMPLATE.format(text=snippet)` = replaces the `{text}` placeholder with the actual student text
- `generate(prompt, temperature=0.1)` = sends to Ollama and gets raw text back
- `extract_json(raw)` = parses the raw text response into a Python dictionary
- `float(data.get("ai_probability", 0.0))` = safely extracts the probability, defaulting to 0.0 if missing
- `round(prob * 100, 1)` = converts 0.85 → 85.0 percent, rounded to 1 decimal place

#### FILE: plagiarism_app/report_builder.py
**Purpose:** Takes all four detector outputs and combines them into one final structured report with an integrity score.

**Lines 12-16: Weighted Penalty Calculation**
- Three negative signals are weighted and combined:
  - AI-generated percentage × 0.50 (contributes 50% of the penalty)
  - Peer similarity percentage × 0.30 (contributes 30% of the penalty)
  - Paraphrase percentage × 0.20 (contributes 20% of the penalty)

**Lines 19-20: Integrity Score Formula**
- `100 - (negative * 0.6) + (orig_result["originality_score"] * 0.2)`
- Start at 100, subtract 60% of the weighted penalty, add 20% of the originality bonus
- `max(0, min(100, integrity))` = clamps the result between 0 and 100
- `round(...)` = rounds to nearest integer

**Lines 23-28: Traffic Light Verdict**
- Simple threshold classification:
  - >= 70 → "clean"
  - 40-69 → "review"
  - < 40 → "flagged"

**Lines 30-44: Return Structure**
- Returns a Python dictionary that will be serialized to JSON and saved to disk
- `"student"` = name
- `"integrity_score"` = the 0-100 number
- `"verdict"` = clean/review/flagged
- `"positive"` = the full originality result dictionary
- `"negative"` = all plagiarism signal details

#### FILE: plagiarism_app/plagiarism_api.py
**Purpose:** FastAPI backend (Port 8001) managing file uploads, running the analysis pipeline, and serving reports.

**Lines 31-35: Path Setup**
- `os.path.abspath(__file__)` = absolute path to this Python file
- `os.path.dirname(...)` = gets the containing folder
- Calling `dirname` twice navigates up two levels to the project root
- `os.path.join(ROOT, "submissions")` = builds the full path platform-independently (works on Windows and Linux)
- `os.makedirs(path, exist_ok=True)` = creates the folder if it does not exist; `exist_ok=True` prevents an error if it already does

**Line 40-47: `/submit` endpoint**
- `student_name: str = Form(...)` = reads a text field from a multipart form request
- `file: UploadFile = File(...)` = receives a binary file upload
- `student_name.strip().replace(" ", "_")` = sanitizes the name (removes whitespace, replaces spaces with underscores for a valid filename)
- `f"{safe}__{file.filename}"` = filename format like `Ravi__essay.pdf` (double underscore is a delimiter for later parsing)
- `shutil.copyfileobj(file.file, f)` = streams the uploaded binary data to disk without loading it all into RAM

**Line 69: `_PREP = {}`**
- Module-level global variable (lives for the entire lifetime of the server process)
- Used to share analysis preparation results between the `/prepare` and `/analyze_one` endpoints without re-computing everything

**Lines 72-113: `_prepare()` function**
- Scans the `submissions/` folder for uploaded files
- Deletes all old `.json` files in `reports/` so results are always fresh
- Reads and extracts text from every submission file
- Runs `check_all_submissions()` once for the entire class (cross-comparison)
- Identifies each student's closest peer (highest similarity match)
- Stores all results in the `_PREP` global dictionary and returns them

**Lines 116-141: `_analyze_student()` function**
- Runs the three slow per-student checks: AI detection, originality score, paraphrase check
- Calls `build_report()` to combine the scores
- Writes the report dictionary as a JSON file to the `reports/` folder
- Returns a summary dictionary for the API response

**Lines 151-156: `/analyze_one/{student}` endpoint**
- `{student}` in the URL path is a path parameter — its value is passed as the `student` argument to the function
- This allows the Teacher UI to call this endpoint once per student in a loop, enabling a live progress bar

#### FILE: plagiarism_app/student_ui.py
**Purpose:** Simple single-screen upload interface for students (Port 8502).

**Line 17: `name = st.text_input("Your name")`**
- Renders a text input field. Returns whatever the user has typed (or empty string if not typed yet).

**Line 20: `file = st.file_uploader("Upload your assignment (any file)")`**
- Renders a drag-and-drop file upload area. Returns a Streamlit UploadedFile object or None.

**Line 23: `if st.button("Submit", type="primary"):`**
- Renders a button. Returns True only in the script execution triggered by clicking it.
- `type="primary"` = applies primary color styling

**Lines 28-31: Form submission**
- `requests.post(f"{API}/submit", data={"student_name": name}, files={"file": (file.name, file.getvalue())})`
- `data={"student_name": name}` = form field
- `files={"file": (filename, bytes)}` = binary file data
- Together these form a multipart/form-data request (required because we are sending both text and binary in one request)

#### FILE: plagiarism_app/teacher_ui.py
**Purpose:** Teacher dashboard (Port 8503) with analysis trigger, summary table, and per-student drill-down view.

**Lines 20-39: Analysis trigger**
- `requests.post(f"{API}/prepare")` = first call: clears old data, reads files, runs copy check, returns student list
- `students = prep.json()["students"]` = extracts list of student names from JSON response
- `bar = st.progress(0.0, text="Starting...")` = creates a progress bar at 0%
- `bar.progress((i-1)/total, text=f"...")` = updates the bar and label after each student is analyzed
- `bar.empty()` = removes the progress bar when done

**Lines 49-56: DataFrame construction**
- `pd.DataFrame(rows)` = converts list of dictionaries to a table
- `.rename(columns={...})` = renames keys to human-readable column headers
- `[[...]]` = reorders and selects which columns to display

**Lines 61-86: Styling**
- `score_colour(val)` = returns CSS style strings based on thresholds
  - Returns `"background-color: #fecaca; color: #111"` for values >= 50 (red/high risk)
  - Returns `"background-color: #fde68a; color: #111"` for values >= 20 (yellow/medium)
  - Returns `"background-color: #bbf7d0; color: #111"` for values < 20 (green/safe)
- `verdict_colour(v)` = returns CSS color for the verdict text
- `df.style.map(score_colour, subset=SCORE_COLS)` = applies the coloring function cell-by-cell only to the score columns

**Lines 122-132: AI Flagged Sentences**
- `for item in neg["flagged_sentences"]:` = loops through each flagged sentence
- `st.markdown(f"<div style='...'>...</div>", unsafe_allow_html=True)` = renders raw HTML with inline CSS styling
- `unsafe_allow_html=True` = Streamlit security flag required when injecting HTML directly

**Lines 135-143: Paraphrase Side-by-Side Display**
- `a, b = st.columns(2)` = splits the layout into two columns for each matched sentence pair
- `a.markdown(...)` and `b.markdown(...)` = renders Student A's sentence on the left and Student B's matching sentence on the right

---

## 5. How Ollama Runs & Communicates

### System Architecture
Ollama is not a Python library — it is an independent system process installed separately from Python.

### Startup
When you launch Ollama (or it auto-starts with Windows), it:
1. Starts a local HTTP server listening on `0.0.0.0:11434`
2. Loads model configuration metadata (not the full weights — those load on first request)
3. Shows a tray icon in the Windows taskbar

### Model Loading
When Python first calls `generate()` or `embed()`:
1. Ollama reads the model weights file from disk (typically from `C:\Users\Username\.ollama\models\`)
2. Loads the weights into system RAM (for CPU inference) or VRAM (for GPU inference)
3. Processes the prompt through the neural network layers
4. Returns the output text as JSON

### API Protocol
Ollama uses standard REST API HTTP communication:

**For text generation:**
- Endpoint: POST http://localhost:11434/api/generate
- Request body: {"model": "qwen2.5:3b", "prompt": "...", "stream": false, "options": {"temperature": 0.1}}
- Response body: {"response": "...", "done": true}

**For embeddings:**
- Endpoint: POST http://localhost:11434/api/embeddings
- Request body: {"model": "nomic-embed-text", "prompt": "..."}
- Response body: {"embedding": [0.023, -0.154, 0.891, ...]} (list of 768 numbers)

### Memory Management
After approximately 5 minutes of inactivity, Ollama automatically unloads the model from RAM to free up system memory. The next request will reload it (causing a brief delay).

### Why This Design?
By running as a separate process with an HTTP API, Ollama can be:
- Shared by multiple Python processes simultaneously (both api.py and plagiarism_api.py can call it)
- Updated independently without changing Python code
- Replaced with a remote server (just change OLLAMA_HOST)
- Used from any programming language that can make HTTP requests
