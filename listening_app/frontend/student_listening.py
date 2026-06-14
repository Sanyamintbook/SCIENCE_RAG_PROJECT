import streamlit as st
import requests

API_URL = "http://localhost:8002"

st.set_page_config(page_title="Listening Assessment - Student", page_icon="🎧", layout="centered")
st.title("🎧 Listening Assessment")

# Fetch the current assignment (only tells us whether one is ready).
try:
    resp = requests.get(f"{API_URL}/get_assignment")
except Exception as e:
    st.error(f"Could not connect to the Assessment Server. Is it running? ({e})")
    st.stop()

if resp.status_code != 200:
    st.warning("No active assignment found. Please ask your teacher to upload one.")
    st.stop()

st.write("### 1. Listen to the Audio")
st.audio(f"{API_URL}/audio")   # streamed from the backend's memory

st.write("---")
st.write("### 2. Type What You Heard")
st.info("Listen carefully, then type out what you understood from the audio.")

student_name = st.text_input("Your Name:")
dictation_text = st.text_area("Your Dictation:", height=160)

if st.button("Submit", type="primary"):
    if not student_name.strip() or not dictation_text.strip():
        st.warning("⚠️ Please enter your name and type what you heard.")
    else:
        with st.spinner("Scoring your understanding…"):
            try:
                res = requests.post(f"{API_URL}/submit_answer", data={
                    "student_name": student_name,
                    "dictation_text": dictation_text,
                })
            except Exception as e:
                st.error(f"Connection error: Is the Listening API running? {e}")
            else:
                if res.status_code == 200:
                    data = res.json()
                    score = data["score"]
                    st.success(f"✅ Submitted! Your understanding score: **{score} / 100**")
                    st.progress(score / 100)
                    st.info(f"**Feedback:** {data['feedback']}")
                    st.caption(f"Audio captured: {round(data['coverage'] * 100)}%")
                else:
                    st.error(f"Error submitting answer: {res.text}")
