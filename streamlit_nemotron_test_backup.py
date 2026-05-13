import cv2
import time
import streamlit as st
import requests
import tempfile
import os
import pandas as pd

CAMERA_INDEX = 1
AI_PC_URL = "http://192.168.8.238:8000/analyze"
RECORD_SECONDS = 40
FPS = 10

st.set_page_config(
    page_title="Nemotron",
    layout="wide"
)

st.title("Nemotron Lean AI")

frame_placeholder = st.empty()

record_button = st.button("Record 40 Seconds & Analyze")

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
    st.video(video_path)

    st.info("Sending video to Nemotron AI PC...")

    try:
        with open(video_path, "rb") as f:
            response = requests.post(
                AI_PC_URL,
                files={"file": ("video.mp4", f, "video/mp4")},
                timeout=900
            )

        if response.status_code != 200:
            st.error("Nemotron server error.")
            st.text(response.text)
            st.stop()

        result = response.json()

        st.success("Analysis completed.")

        actions = result.get("actions", [])

        if actions:
            st.subheader("Detected Actions")

            df = pd.DataFrame(actions)
            st.dataframe(df, use_container_width=True)

            col1, col2, col3 = st.columns(3)

            va_count = len([
                action for action in actions
                if action.get("lean_category") == "VA"
            ])

            nva_count = len([
                action for action in actions
                if action.get("lean_category") == "NVA"
            ])

            col1.metric("Total Actions", len(actions))
            col2.metric("VA Actions", va_count)
            col3.metric("NVA Actions", nva_count)

        st.subheader("Raw Result")
        st.json(result)

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to AI PC. Make sure Nemotron server is running.")
        st.code("uvicorn nemotron_server:app --host 0.0.0.0 --port 8000")

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