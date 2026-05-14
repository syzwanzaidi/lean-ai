import cv2
import time
import streamlit as st
import requests
import tempfile
import os
import pandas as pd
import shutil

CAMERA_INDEX = 1
AI_PC_URL = "http://192.168.8.238:8000/analyze"
RECORD_SECONDS = 40
FPS = 10

SAMPLE_VIDEO_DIR = r"C:\Users\User\lean_ai\sample_video"

st.set_page_config(
    page_title="Nemotron",
    layout="wide"
)

st.title("Nemotron Lean AI Time Study")

mode = st.radio(
    "Choose input mode",
    ["Use sample video", "Record from camera"],
    horizontal=True
)

frame_placeholder = st.empty()


def get_sample_videos():
    if not os.path.exists(SAMPLE_VIDEO_DIR):
        return []

    supported_ext = [".mp4", ".avi", ".mov", ".mkv"]

    videos = []

    for file_name in os.listdir(SAMPLE_VIDEO_DIR):
        if any(file_name.lower().endswith(ext) for ext in supported_ext):
            videos.append(file_name)

    return videos


def analyze_video(video_path):
    st.video(video_path)

    st.info("Sending video to Nemotron AI PC...")

    with open(video_path, "rb") as f:
        response = requests.post(
            AI_PC_URL,
            files={"file": ("video.mp4", f, "video/mp4")},
            timeout=1800
        )

    if response.status_code != 200:
        st.error("Nemotron server error.")
        st.text(response.text)
        st.stop()

    return response.json()


def show_results(result):
    actions = result.get("actions", [])

    if actions:
        st.subheader("Time Study Table")

        df = pd.DataFrame(actions)

        desired_columns = [
            "start_time",
            "end_time",
            "duration_seconds",
            "action_name",
            "action_type"
        ]

        existing_columns = [
            col for col in desired_columns
            if col in df.columns
        ]

        df = df[existing_columns]

        st.dataframe(
            df,
            use_container_width=True
        )

        va_count = len([
            action for action in actions
            if action.get("action_type") == "VA"
        ])

        nva_count = len([
            action for action in actions
            if action.get("action_type") == "NVA"
        ])

        nnva_count = len([
            action for action in actions
            if action.get("action_type") == "NNVA"
        ])

        total_duration = sum([
            action.get("duration_seconds", 0)
            for action in actions
        ])

        va_duration = sum([
            action.get("duration_seconds", 0)
            for action in actions
            if action.get("action_type") == "VA"
        ])

        nva_duration = sum([
            action.get("duration_seconds", 0)
            for action in actions
            if action.get("action_type") == "NVA"
        ])

        nnva_duration = sum([
            action.get("duration_seconds", 0)
            for action in actions
            if action.get("action_type") == "NNVA"
        ])

        efficiency = 0

        if total_duration > 0:
            efficiency = (va_duration / total_duration) * 100

        st.subheader("Lean Summary")

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Total Actions", len(actions))
        col2.metric("VA Actions", va_count)
        col3.metric("NVA Actions", nva_count)
        col4.metric("NNVA Actions", nnva_count)
        col5.metric("Efficiency", f"{efficiency:.1f}%")

        col6, col7, col8, col9 = st.columns(4)

        col6.metric("VA Time", f"{va_duration}s")
        col7.metric("NVA Time", f"{nva_duration}s")
        col8.metric("NNVA Time", f"{nnva_duration}s")
        col9.metric("Total Time", f"{total_duration}s")

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Time Study CSV",
            data=csv,
            file_name="nemotron_time_study.csv",
            mime="text/csv",
            use_container_width=True
        )

    else:
        st.warning("No parsed actions found.")
        st.info("Check clean timeline and raw timeline below.")

    st.subheader("Clean Timeline")
    st.text(result.get("clean_timeline", ""))

    st.subheader("Raw Nemotron Timeline")
    st.text(result.get("raw_timeline", ""))

    with st.expander("Raw Result JSON"):
        st.json(result)


if mode == "Use sample video":
    sample_videos = get_sample_videos()

    if not sample_videos:
        st.warning(f"No video found in: {SAMPLE_VIDEO_DIR}")
        st.stop()

    selected_video = st.selectbox(
        "Select sample video",
        sample_videos
    )

    selected_path = os.path.join(SAMPLE_VIDEO_DIR, selected_video)

    st.video(selected_path)

    if st.button("Analyze Sample Video", type="primary"):
        try:
            result = analyze_video(selected_path)
            st.success("Analysis completed.")
            show_results(result)

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to AI PC. Make sure Nemotron server is running.")
            st.code("source nemotron-env/bin/activate")
            st.code("CUDA_LAUNCH_BLOCKING=1 uvicorn nemotron_server:app --host 0.0.0.0 --port 8000")

        except requests.exceptions.Timeout:
            st.error("Nemotron request timed out. The video may be too long.")

        except Exception as e:
            st.error("Unexpected error.")
            st.exception(e)


else:
    record_button = st.button("Record 40 Seconds & Analyze", type="primary")

    if record_button:
        camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

        if not camera.isOpened():
            st.error("Failed to open camera.")
            st.stop()

        temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        video_path = temp_video.name
        temp_video.close()

        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_path, fourcc, FPS, (width, height))

        st.info("Recording started...")

        start_time = time.time()
        progress_bar = st.progress(0)

        while time.time() - start_time < RECORD_SECONDS:
            success, frame = camera.read()

            if not success:
                st.error("Failed to read frame.")
                break

            writer.write(frame)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            frame_placeholder.image(
                rgb,
                channels="RGB",
                use_container_width=True
            )

            elapsed = time.time() - start_time
            progress_bar.progress(min(elapsed / RECORD_SECONDS, 1.0))

            time.sleep(1 / FPS)

        writer.release()
        camera.release()

        st.success("Recording completed.")

        try:
            result = analyze_video(video_path)
            st.success("Analysis completed.")
            show_results(result)

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to AI PC. Make sure Nemotron server is running.")
            st.code("source nemotron-env/bin/activate")
            st.code("CUDA_LAUNCH_BLOCKING=1 uvicorn nemotron_server:app --host 0.0.0.0 --port 8000")

        except requests.exceptions.Timeout:
            st.error("Nemotron request timed out. Try shorter recording duration.")

        except Exception as e:
            st.error("Unexpected error.")
            st.exception(e)

        finally:
            try:
                os.remove(video_path)
            except PermissionError:
                pass
            except FileNotFoundError:
                pass
    else:
        st.info("Click the button to record from the top-view camera.")