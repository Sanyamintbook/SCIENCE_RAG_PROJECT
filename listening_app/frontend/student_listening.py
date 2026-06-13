import streamlit as st
import requests

API_URL = "http://localhost:8002"

st.set_page_config(page_title="Listening Assessment - Student", layout="centered", page_icon="🎧")

st.title("🎧 Listening Assessment")

# Initialize session state for audio transcription
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "sub_id" not in st.session_state:
    st.session_state.sub_id = None
if "last_audio_bytes" not in st.session_state:
    st.session_state.last_audio_bytes = None

# Fetch current assignment
try:
    response = requests.get(f"{API_URL}/get_assignment")
    if response.status_code == 200:
        assignment = response.json()
        
        st.write("### 1. Listen to the Audio")
        # Stream audio directly from backend
        st.audio(f"{API_URL}/audio/{assignment['id']}")
        
        st.write("---")
        st.write("### 2. Dictation")
        st.info("Type out EXACTLY what you hear in the audio.")
        dictation_text = st.text_area("Your Dictation:", height=100)
        
        questions = assignment.get("questions", [])
        if questions:
            st.write("---")
            st.write("### 3. Comprehension Questions")
            for i, q in enumerate(questions):
                st.markdown(f"**Q{i+1}:** {q['question']}")
            
        student_name = st.text_input("Your Name:")
        
        if not questions:
            if st.button("Submit Dictation", type="primary"):
                if not student_name.strip() or not dictation_text.strip():
                    st.warning("⚠️ Please enter your name and complete the dictation.")
                else:
                    with st.spinner("AI is evaluating your dictation..."):
                        import json
                        data = {
                            "student_name": student_name,
                            "dictation_text": dictation_text,
                            "response_type": "text",
                            "answers_json": json.dumps([])
                        }
                        try:
                            res = requests.post(f"{API_URL}/submit_answer", data=data)
                            if res.status_code == 200:
                                st.success("✅ Dictation submitted successfully! Your teacher will review your results.")
                            else:
                                st.error(f"Error submitting answer: {res.text}")
                        except Exception as e:
                            st.error(f"Connection error: Make sure the Listening API is running. Error: {e}")
        else:
            response_type = st.radio("How would you like to answer the questions?", ["⌨️ Type my answers", "🎙️ Speak my answers (Question by question)"])
            
            if response_type == "⌨️ Type my answers":
                text_answers = []
                for i, q in enumerate(questions):
                    ans = st.text_input(f"Your Answer for Q{i+1}:", key=f"ans_{i}")
                    text_answers.append(ans)
                    
                if st.button("Submit Assignment", type="primary"):
                    if not student_name.strip() or not dictation_text.strip():
                        st.warning("⚠️ Please enter your name and complete the dictation.")
                    else:
                        with st.spinner("AI is evaluating your dictation and answers..."):
                            import json
                            data = {
                                "student_name": student_name,
                                "dictation_text": dictation_text,
                                "response_type": "text",
                                "answers_json": json.dumps(text_answers)
                            }
                            try:
                                res = requests.post(f"{API_URL}/submit_answer", data=data)
                                if res.status_code == 200:
                                    st.success("✅ Assignment submitted successfully! Your teacher will review your results.")
                                else:
                                    st.error(f"Error submitting answer: {res.text}")
                            except Exception as e:
                                st.error(f"Connection error: Make sure the Listening API is running. Error: {e}")
                            
            else:
                # Voice Input Option
                st.write("Record your answer for each question using the microphone buttons below:")
                voice_answers = []
                all_recorded = True
                for i, q in enumerate(questions):
                    ab = st.audio_input(f"Record Answer for Q{i+1}", key=f"audio_q_{i}")
                    if ab is None:
                        all_recorded = False
                    voice_answers.append(ab)
                
                if all_recorded:
                    if st.button("Submit Voice Assignment", type="primary"):
                        if not student_name.strip() or not dictation_text.strip():
                            st.warning("⚠️ Please enter your name and complete the dictation before submitting.")
                        else:
                            with st.spinner("Submitting your dictation and voice answers for grading..."):
                                files = []
                                for i, ab in enumerate(voice_answers):
                                    files.append(("voice_audio", (f"answer_{i}.wav", ab.getvalue(), "audio/wav")))
                                
                                data = {
                                    "student_name": student_name, 
                                    "dictation_text": dictation_text,
                                    "response_type": "voice"
                                }
                                
                                try:
                                    res = requests.post(f"{API_URL}/submit_answer", data=data, files=files)
                                    if res.status_code == 200:
                                        st.success("✅ Assignment submitted successfully! Your teacher will review your results.")
                                    else:
                                        st.error(f"Failed to submit: {res.text}")
                                except Exception as e:
                                    st.error(f"Connection error: Make sure the Listening API is running. Error: {e}")
                            
    else:
        st.warning("No active assignment found. Please ask your teacher to upload one.")

except Exception as e:
    st.error(f"Could not connect to the Assessment Server. Is it running? ({e})")
