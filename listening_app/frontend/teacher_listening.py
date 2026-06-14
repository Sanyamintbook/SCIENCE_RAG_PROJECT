import streamlit as st
import requests

API_URL = "http://localhost:8002"

st.set_page_config(page_title="Listening Assessment - Teacher Portal", page_icon="👩‍🏫", layout="wide")

st.title("🎙️ Listening Assessment — Teacher Portal")
st.caption(
    "⚠️ Everything runs in memory only. The audio, transcript and scores are "
    "NOT saved anywhere and disappear when the server restarts."
)

tab1, tab2 = st.tabs(["Upload Audio", "Student Results"])

# ── Tab 1: upload audio ──────────────────────────────────────────────────────
with tab1:
    st.header("Create Listening Assignment")
    st.info(
        "Upload an audio clip. It is transcribed locally with Whisper and turned "
        "into a vector — all in RAM. Students then type what they hear and get "
        "scored on how much they understood."
    )

    audio_file = st.file_uploader("Upload Audio File", type=["mp3", "wav", "m4a"])

    if st.button("Create Assignment", type="primary"):
        if not audio_file:
            st.error("❌ Please upload an audio file.")
        else:
            with st.spinner("Transcribing audio locally (this can take a moment)…"):
                try:
                    files = {"audio_file": (audio_file.name, audio_file.getvalue(), audio_file.type)}
                    res = requests.post(f"{API_URL}/create_assignment", files=files)
                except Exception as e:
                    st.error(f"Connection error: Is the Listening API running? {e}")
                else:
                    if res.status_code == 200:
                        transcript = res.json().get("transcript", "")
                        st.success("✅ Assignment ready! Students can now take the test.")
                        st.markdown("**Reference transcript (kept in RAM only):**")
                        st.write(f"> {transcript}")
                    else:
                        st.error(f"Failed to create assignment: {res.text}")

# ── Tab 2: student results ───────────────────────────────────────────────────
with tab2:
    st.header("Student Results")
    if st.button("🔄 Refresh"):
        st.rerun()

    try:
        res = requests.get(f"{API_URL}/get_results")
    except Exception as e:
        st.error(f"Connection error: Is the Listening API running? {e}")
    else:
        if res.status_code != 200:
            st.error("Failed to fetch results.")
        else:
            payload = res.json()
            transcript = payload.get("transcript")
            results = payload.get("results", {})

            if transcript:
                with st.expander("Reference transcript"):
                    st.write(transcript)

            if not results:
                st.info("No submissions yet.")
            else:
                search = st.text_input("Search by student name:", "")
                rows = [r for name, r in results.items() if search.lower() in name.lower()]
                rows.sort(key=lambda r: r["score"], reverse=True)

                for r in rows:
                    score = r["score"]
                    light = "🟢" if score >= 70 else ("🟡" if score >= 50 else "🔴")
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 4])
                        with c1:
                            st.metric("Score", f"{score}/100")
                        with c2:
                            st.markdown(f"**{light} {r['student_name']}**")
                            st.caption(f"Audio captured: {round(r['coverage'] * 100)}%")
                            st.markdown(f"**What they typed:** {r['dictation_text']}")
                            st.info(r["feedback"])
