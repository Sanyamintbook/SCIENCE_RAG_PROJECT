"""
teacher_listening.py — Listening Assessment TEACHER page (Streamlit, port 8504)
==============================================================================
Two tabs: (1) upload an audio clip to create the test, (2) view every student's
score. Like the student page, it holds NO AI logic — it only calls the backend
(listening_api.py on port 8002) over HTTP and shows the reply.
"""

import streamlit as st        # third-party: builds the web page
import requests               # third-party: sends HTTP calls to the backend

API_URL = "http://localhost:8002"   # where the listening backend is listening

# Page tab title/icon and a wide layout (the results table is wide).
st.set_page_config(page_title="Listening Assessment - Teacher Portal", page_icon="👩‍🏫", layout="wide")

st.title("🎙️ Listening Assessment — Teacher Portal")   # page heading
st.caption(                                             # reminder that nothing is saved
    "⚠️ Everything runs in memory only. The audio, transcript and scores are "
    "NOT saved anywhere and disappear when the server restarts."
)

tab1, tab2 = st.tabs(["Upload Audio", "Student Results"])   # two tabs on the page

# ── Tab 1: upload audio ──────────────────────────────────────────────────────
with tab1:                                              # everything indented here renders inside tab 1
    st.header("Create Listening Assignment")
    st.info(
        "Upload an audio clip. It is transcribed locally with Whisper and turned "
        "into a vector — all in RAM. Students then type what they hear and get "
        "scored on how much they understood."
    )

    audio_file = st.file_uploader("Upload Audio File", type=["mp3", "wav", "m4a"])   # file picker widget

    if st.button("Create Assignment", type="primary"):  # when the teacher clicks the button
        if not audio_file:                              # nothing chosen
            st.error("❌ Please upload an audio file.")
        else:
            with st.spinner("Transcribing audio locally (this can take a moment)…"):  # spinner during work
                try:
                    # Build the multipart upload: (filename, raw bytes, content type).
                    files = {"audio_file": (audio_file.name, audio_file.getvalue(), audio_file.type)}
                    res = requests.post(f"{API_URL}/create_assignment", files=files)  # POST to the backend
                except Exception as e:                  # backend unreachable
                    st.error(f"Connection error: Is the Listening API running? {e}")
                else:
                    if res.status_code == 200:          # success
                        transcript = res.json().get("transcript", "")   # the backend returns the transcript
                        st.success("✅ Assignment ready! Students can now take the test.")
                        st.markdown("**Reference transcript (kept in RAM only):**")
                        st.write(f"> {transcript}")     # show the teacher what Whisper heard
                    else:
                        st.error(f"Failed to create assignment: {res.text}")

# ── Tab 2: student results ───────────────────────────────────────────────────
with tab2:                                              # everything here renders inside tab 2
    st.header("Student Results")
    if st.button("🔄 Refresh"):                          # manual refresh button
        st.rerun()                                      # re-run the script to fetch fresh results

    try:
        res = requests.get(f"{API_URL}/get_results")    # GET everyone's scores from the backend
    except Exception as e:
        st.error(f"Connection error: Is the Listening API running? {e}")
    else:
        if res.status_code != 200:
            st.error("Failed to fetch results.")
        else:
            payload = res.json()                        # {"transcript": ..., "results": {name: {...}}}
            transcript = payload.get("transcript")
            results = payload.get("results", {})

            if transcript:                              # show the answer key in a collapsible box
                with st.expander("Reference transcript"):
                    st.write(transcript)

            if not results:                             # no one has submitted yet
                st.info("No submissions yet.")
            else:
                search = st.text_input("Search by student name:", "")   # optional name filter
                # Keep only rows whose name contains the search text (case-insensitive).
                rows = [r for name, r in results.items() if search.lower() in name.lower()]
                rows.sort(key=lambda r: r["score"], reverse=True)       # highest score first

                for r in rows:                          # draw one card per student
                    score = r["score"]
                    # traffic-light emoji: green >=70, yellow >=50, else red
                    light = "🟢" if score >= 70 else ("🟡" if score >= 50 else "🔴")
                    with st.container(border=True):      # a bordered card
                        c1, c2 = st.columns([1, 4])      # two columns: score | details
                        with c1:
                            st.metric("Score", f"{score}/100")          # big number
                        with c2:
                            st.markdown(f"**{light} {r['student_name']}**")
                            st.caption(f"Audio captured: {round(r['coverage'] * 100)}%")
                            st.markdown(f"**What they typed:** {r['dictation_text']}")
                            st.info(r["feedback"])       # the human feedback sentence
