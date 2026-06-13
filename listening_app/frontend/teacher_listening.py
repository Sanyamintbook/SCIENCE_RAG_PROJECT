import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8002"

st.set_page_config(page_title="Listening Assessment - Teacher Portal", layout="wide", page_icon="👩‍🏫")

# Force smaller scale and 100% screen width
st.markdown("""
    <style>
    /* Shrink the entire UI to mimic 80% browser zoom */
    html, body, [class*="st-"] {
        font-size: 14px;
    }
    .block-container {
        zoom: 0.8; /* Scales down the entire Streamlit container */
        max-width: 95% !important;
        padding-top: 2rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 2rem;
    }
    
    /* Ensure the table is incredibly compact */
    .results-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 12px; border: 1px solid #eee; table-layout: fixed; }
    .results-table th { background-color: #f8f9fa; color: #333; padding: 8px; text-align: left; border-bottom: 2px solid #ddd; font-weight: 600; }
    .results-table td { padding: 8px; border-bottom: 1px solid #eee; vertical-align: top; word-wrap: break-word; }
    .col-score { width: 7%; }
    .col-name { width: 10%; }
    .col-dict { width: 41.5%; }
    .col-comp { width: 41.5%; }
    .audio-player { height: 32px; width: 100%; }
    .score-badge { font-weight: 600; padding: 3px 6px; border-radius: 4px; white-space: nowrap; font-size: 11px; }
    .feedback-box { background-color: #f8f9fa; border-left: 3px solid #0056b3; padding: 6px 10px; margin-top: 4px; margin-bottom: 8px; font-size: 11px; color: #444; }
    </style>
""", unsafe_allow_html=True)

st.title("🎙️ Listening Assessment - Teacher Portal")

tab1, tab2 = st.tabs(["Upload New Assignment", "Student Results"])

with tab1:
    st.header("Create Listening Assignment")
    st.info("Upload an audio recording of a story or passage. Then set a question to test student comprehension.")
    
    if "question_ids" not in st.session_state:
        st.session_state.question_ids = [0]
        st.session_state.next_q_id = 1
        
    audio_file = st.file_uploader("Upload Audio File (.mp3 or .wav)", type=["mp3", "wav"])
    
    st.write("### Comprehension Questions")
    
    questions_data = []
    for idx, q_id in enumerate(list(st.session_state.question_ids)):
        with st.container(border=True):
            col1, col2 = st.columns([11, 1])
            with col1:
                st.markdown(f"**Question {idx+1}**")
            with col2:
                if st.button("✖", key=f"del_{q_id}", help="Remove this question"):
                    st.session_state.question_ids.remove(q_id)
                    st.rerun()
                    
            if q_id in st.session_state.question_ids:
                q = st.text_input("Question Text", key=f"q_{q_id}", label_visibility="visible")
                a = st.text_area("Expected Answer", key=f"a_{q_id}")
                questions_data.append({"question": q, "expected_answer": a})
        
    if st.button("➕ Add Question"):
        st.session_state.question_ids.append(st.session_state.next_q_id)
        st.session_state.next_q_id += 1
        st.rerun()
        
    if st.button("Create Assignment", type="primary"):
        # Filter out empty questions
        valid_questions = [qd for qd in questions_data if qd["question"].strip() and qd["expected_answer"].strip()]
        
        if not audio_file:
            st.error("❌ Please upload an Audio file.")
        else:
            with st.spinner("Uploading and auto-transcribing audio using AI..."):
                import json
                files = {"audio_file": (audio_file.name, audio_file, audio_file.type)}
                data = {"questions_json": json.dumps(valid_questions)}
                
                try:
                    response = requests.post(f"{API_URL}/create_assignment", files=files, data=data)
                    if response.status_code == 200:
                        auto_transcript = response.json().get("auto_transcript", "")
                        st.success("✅ Assignment created successfully! Students can now take the test.")
                        st.info(f"**Auto-Transcribed Dictation Text:**\n\n> {auto_transcript}")
                        st.session_state.q_count = 1 # reset
                    else:
                        st.error(f"Failed to create assignment: {response.text}")
                except Exception as e:
                    st.error(f"Connection error: Make sure the Listening API is running. Error: {e}")

with tab2:
    st.header("Student Results")
    st.markdown("Review AI-graded submissions. You can listen to the actual student voice recordings to verify the transcripts.")
    
    col1, col2 = st.columns([8, 2])
    with col1:
        search_query = st.text_input("Search by Student Name:", "")
    with col2:
        st.write("")
        st.write("")
        if st.button("Refresh Results"):
            st.rerun()
            
    try:
        response = requests.get(f"{API_URL}/get_results")
        if response.status_code == 200:
            results_data = response.json()
            
            # Filter by search
            if search_query:
                results_data = {k: v for k, v in results_data.items() if search_query.lower() in k.lower()}
            
            if not results_data:
                st.info("No student submissions match your criteria.")
            else:
                html_table = f"""
<table class="results-table">
    <tr>
        <th class="col-score">Score</th>
        <th class="col-name">Student Name</th>
        <th class="col-dict">Dictation Details</th>
        <th class="col-comp">Comprehension Details</th>
    </tr>
"""
                for student_name, data in results_data.items():
                    score = data.get("overall_score", 0)
                    method = data.get("method", "text")
                    sub_id = data.get("sub_id")
                    
                    if score >= 80: badge_class = "score-high"
                    elif score >= 50: badge_class = "score-med"
                    else: badge_class = "score-low"
                    
                    score_html = f"<span class='score-badge {badge_class}'>{score}/100</span>"
                    
                    dict_eval = data.get("dictation_eval", {})
                    dict_html = f"""
                    <b>Score:</b> {dict_eval.get('score', 0)}/100<br>
                    <b>Text:</b> {data.get('dictation_text', '')}<br>
                    <div class='feedback-box'><b>Feedback:</b> {dict_eval.get('feedback', '')}</div>
                    """
                    
                    comp_html = f"<b>Average Score:</b> {data.get('comp_score', 0)}/100<br>"
                    
                    # Support for legacy monolithic audio submissions
                    legacy_sub_id = data.get("sub_id")
                    if method == "voice" and legacy_sub_id:
                        comp_html += f"<br><b>Audio:</b><br>"
                        comp_html += f"<audio class='audio-player' controls src='{API_URL}/student_audio/{legacy_sub_id}'></audio><br>"
                        
                    for i, q in enumerate(data.get("question_results", [])):
                        comp_html += f"<b>Q{i+1}:</b> {q['question']}<br>"
                        if method == "voice":
                            comp_html += f"<i>Transcribed Speech: {q.get('student_answer', '')}</i><br>"
                            sub_id_q = q.get("sub_id")
                            if sub_id_q:
                                comp_html += f"<b>Audio:</b><br><audio class='audio-player' controls src='{API_URL}/student_audio/{sub_id_q}'></audio><br>"
                        else:
                            comp_html += f"<b>Ans:</b> {q['student_answer']}<br>"
                        comp_html += f"<div class='feedback-box'><b>Score {q['score']}/100:</b> {q['feedback']}</div>"
                        
                    html_table += f"""<tr>
<td>{score_html}</td>
<td><b>{student_name}</b></td>
<td>{dict_html}</td>
<td>{comp_html}</td>
</tr>"""
                html_table += "</table>"
                st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.error("Failed to fetch results.")
    except Exception as e:
        st.error(f"Connection error: Make sure the Listening API is running. Error: {e}")
