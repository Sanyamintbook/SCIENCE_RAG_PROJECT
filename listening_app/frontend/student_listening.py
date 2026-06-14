"""
student_listening.py — Listening Assessment STUDENT page (Streamlit, port 8505)
==============================================================================
A simple web page where a student listens to the teacher's audio, types what
they understood, and instantly sees their score. It holds NO AI logic — it only
calls the backend (listening_api.py on port 8002) over HTTP and shows the reply.
"""

import streamlit as st        # third-party: builds the web page (widgets, layout)
import requests               # third-party: sends HTTP calls to the backend

API_URL = "http://localhost:8002"   # where the listening backend (listening_api.py) is listening

# set_page_config sets the browser tab title/icon and page width. Must run first.
st.set_page_config(page_title="Listening Assessment - Student", page_icon="🎧", layout="centered")
st.title("🎧 Listening Assessment")   # big heading on the page

# Ask the backend whether a test exists. get_assignment() returns only {"ready": true}.
try:
    resp = requests.get(f"{API_URL}/get_assignment")   # GET /get_assignment on the backend
except Exception as e:                                  # backend not running / unreachable
    st.error(f"Could not connect to the Assessment Server. Is it running? ({e})")
    st.stop()                                           # stop rendering the rest of the page

if resp.status_code != 200:                             # 404 = no assignment uploaded yet
    st.warning("No active assignment found. Please ask your teacher to upload one.")
    st.stop()

st.write("### 1. Listen to the Audio")                  # section heading
st.audio(f"{API_URL}/audio")                            # audio player; the browser fetches GET /audio (streamed from RAM)

st.write("---")                                         # horizontal divider
st.write("### 2. Type What You Heard")
st.info("Listen carefully, then type out what you understood from the audio.")

student_name = st.text_input("Your Name:")              # text box for the student's name
dictation_text = st.text_area("Your Dictation:", height=160)   # bigger box for what they heard

if st.button("Submit", type="primary"):                 # runs the block below when the button is clicked
    if not student_name.strip() or not dictation_text.strip():   # both fields required
        st.warning("⚠️ Please enter your name and type what you heard.")
    else:
        with st.spinner("Scoring your understanding…"):  # show a spinner while the backend works
            try:
                res = requests.post(f"{API_URL}/submit_answer", data={   # POST the answer to the backend
                    "student_name": student_name,
                    "dictation_text": dictation_text,
                })
            except Exception as e:                       # backend unreachable mid-submit
                st.error(f"Connection error: Is the Listening API running? {e}")
            else:
                if res.status_code == 200:               # success: the backend returned a score
                    data = res.json()                    # parse the JSON {score, coverage, feedback}
                    score = data["score"]
                    st.success(f"✅ Submitted! Your understanding score: **{score} / 100**")
                    st.progress(score / 100)             # visual progress bar (0.0 .. 1.0)
                    st.info(f"**Feedback:** {data['feedback']}")
                    st.caption(f"Audio captured: {round(data['coverage'] * 100)}%")   # coverage as a %
                else:
                    st.error(f"Error submitting answer: {res.text}")
