import os
import time
import cv2
import requests
import pandas as pd
import streamlit as st
from PIL import Image

from lamp_steps import STEPS as LAMP_STEPS
from keychain_steps import STEPS as KEYCHAIN_STEPS

from openai_verifier import verify_step
from motion_detector import calculate_motion_score, classify_motion


PRODUCTS = {
    "Lamp Assembly": LAMP_STEPS,
    "Keychain Assembly": KEYCHAIN_STEPS,
}

ZONE = {
    "x1_ratio": 0.02,
    "y1_ratio": 0.05,
    "x2_ratio": 0.63,
    "y2_ratio": 0.57
}

CAMERA_INDEX = 1

MOTION_THRESHOLD = 800
MIN_ACTION_DURATION = 2.0
IDLE_GRACE_SECONDS = 3.0

NEMOTRON_URL = "http://192.168.8.238:8000/analyze"
NEMOTRON_FPS = 8
FRAME_SAMPLE_INTERVAL = 3
MAX_NEMOTRON_FRAMES = 900
NEMOTRON_CLIP_DIR = "captured/nemotron_clips"


st.set_page_config(
    page_title="Lean AI Assembly Guide",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 2.2rem !important;
    padding-bottom: 0rem !important;
    max-width: 96% !important;
}
h1 {
    font-size: 24px !important;
    margin-bottom: 0.15rem !important;
}
h2, h3 {
    font-size: 20px !important;
    margin-top: 0.1rem !important;
    margin-bottom: 0.25rem !important;
}
.stAlert {
    padding: 0.5rem !important;
    margin-bottom: 0.3rem !important;
}
div[data-testid="stImage"] img {
    max-height: 430px;
    object-fit: contain;
}
button {
    height: 38px !important;
}
.motion-card {
    padding: 12px;
    border-radius: 10px;
    background: #132f4c;
    border: 1px solid #1f6feb;
    margin-bottom: 10px;
    color: #ffffff;
}
.motion-card div {
    color: #ffffff;
}
.motion-action {
    font-size: 22px;
    font-weight: 700;
    color: #4ade80 !important;
}
</style>
""", unsafe_allow_html=True)


def reset_run_state():
    st.session_state.current_step = 0
    st.session_state.last_result = None
    st.session_state.action_logs = []
    st.session_state.previous_zone_frame = None
    st.session_state.detected_action = "IDLE"
    st.session_state.motion_score = 0
    st.session_state.current_motion_action = "IDLE"
    st.session_state.motion_action_start_time = time.time()
    st.session_state.last_motion_time = time.time()
    st.session_state.active_step_id = None

    st.session_state.step_frame_buffer = []
    st.session_state.buffer_frame_counter = 0
    st.session_state.saved_nemotron_clips = []
    st.session_state.nemotron_step_results = []
    st.session_state.last_nemotron_result = None
    st.session_state.nemotron_processed = False


def log_action(action_name, action_type, description, start_time, end_time, step):
    duration = end_time - start_time

    if duration < MIN_ACTION_DURATION:
        return

    st.session_state.action_logs.append({
        "step_id": step["id"],
        "action_name": action_name,
        "description": description,
        "action_type": action_type,
        "start_time": round(start_time, 2),
        "end_time": round(end_time, 2),
        "duration_seconds": round(duration, 2),
    })


def log_motion_action(end_time, step):
    action_name = st.session_state.current_motion_action
    start_time = st.session_state.motion_action_start_time

    if action_name == "ASSEMBLE":
        action_type = "VA"
        description = f"Operator performed assembly activity during {step['title']}."
    else:
        action_type = "NVA"
        description = f"Operator was idle during {step['title']}."

    log_action(
        action_name=action_name,
        action_type=action_type,
        description=description,
        start_time=start_time,
        end_time=end_time,
        step=step
    )


def save_frames_to_video(frames, output_path, fps=8):
    if not frames:
        return False

    height, width = frames[0].shape[:2]

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        if frame.shape[:2] != (height, width):
            frame = cv2.resize(frame, (width, height))

        writer.write(frame)

    writer.release()
    return True


def analyze_step_with_nemotron(video_path, step):
    try:
        with open(video_path, "rb") as video_file:
            response = requests.post(
                NEMOTRON_URL,
                files={"file": ("step_video.mp4", video_file, "video/mp4")},
                data={
                    "step_id": str(step["id"]),
                    "step_title": step["title"],
                },
                timeout=1800
            )

        if response.status_code != 200:
            return {
                "error": True,
                "message": response.text,
                "actions": []
            }

        return response.json()

    except requests.exceptions.ConnectionError:
        return {
            "error": True,
            "message": "Cannot connect to Nemotron AI PC server.",
            "actions": []
        }

    except requests.exceptions.Timeout:
        return {
            "error": True,
            "message": "Nemotron analysis timed out.",
            "actions": []
        }

    except Exception as e:
        return {
            "error": True,
            "message": str(e),
            "actions": []
        }


def convert_nemotron_result_to_rows(result, step):
    rows = []

    for action in result.get("actions", []):
        rows.append({
            "step_id": step["id"],
            "step_title": step["title"],
            "start_time": action.get("start_time"),
            "end_time": action.get("end_time"),
            "duration_seconds": action.get("duration_seconds", 0),
            "action_name": action.get("action_name", "Unknown"),
            "action_type": action.get("action_type", "VA"),
        })

    return rows


def save_current_step_clip(step):
    if not st.session_state.step_frame_buffer:
        return None

    os.makedirs(NEMOTRON_CLIP_DIR, exist_ok=True)

    safe_product_name = st.session_state.selected_product.lower().replace(" ", "_")
    clip_path = (
        f"{NEMOTRON_CLIP_DIR}/"
        f"{safe_product_name}_step_{step['id']}_nemotron.mp4"
    )

    saved = save_frames_to_video(
        frames=st.session_state.step_frame_buffer,
        output_path=clip_path,
        fps=NEMOTRON_FPS
    )

    if not saved:
        return None

    clip_info = {
        "step_id": step["id"],
        "step_title": step["title"],
        "clip_path": clip_path,
    }

    # Replace old clip for the same step if user retries
    st.session_state.saved_nemotron_clips = [
        clip for clip in st.session_state.saved_nemotron_clips
        if clip["step_id"] != step["id"]
    ]

    st.session_state.saved_nemotron_clips.append(clip_info)

    return clip_path


def run_nemotron_for_saved_clips():
    results = []

    for clip in st.session_state.saved_nemotron_clips:
        step = {
            "id": clip["step_id"],
            "title": clip["step_title"],
        }

        result = analyze_step_with_nemotron(
            video_path=clip["clip_path"],
            step=step
        )

        st.session_state.last_nemotron_result = result

        rows = convert_nemotron_result_to_rows(
            result=result,
            step=step
        )

        results.extend(rows)

    st.session_state.nemotron_step_results = results
    st.session_state.nemotron_processed = True


# =========================
# SESSION STATE
# =========================
if "selected_product" not in st.session_state:
    st.session_state.selected_product = "Lamp Assembly"

if "current_step" not in st.session_state:
    st.session_state.current_step = 0

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "action_logs" not in st.session_state:
    st.session_state.action_logs = []

if "previous_zone_frame" not in st.session_state:
    st.session_state.previous_zone_frame = None

if "detected_action" not in st.session_state:
    st.session_state.detected_action = "IDLE"

if "motion_score" not in st.session_state:
    st.session_state.motion_score = 0

if "current_motion_action" not in st.session_state:
    st.session_state.current_motion_action = "IDLE"

if "motion_action_start_time" not in st.session_state:
    st.session_state.motion_action_start_time = time.time()

if "last_motion_time" not in st.session_state:
    st.session_state.last_motion_time = time.time()

if "active_step_id" not in st.session_state:
    st.session_state.active_step_id = None

if "step_frame_buffer" not in st.session_state:
    st.session_state.step_frame_buffer = []

if "buffer_frame_counter" not in st.session_state:
    st.session_state.buffer_frame_counter = 0

if "saved_nemotron_clips" not in st.session_state:
    st.session_state.saved_nemotron_clips = []

if "nemotron_step_results" not in st.session_state:
    st.session_state.nemotron_step_results = []

if "last_nemotron_result" not in st.session_state:
    st.session_state.last_nemotron_result = None

if "nemotron_processed" not in st.session_state:
    st.session_state.nemotron_processed = False


# =========================
# PRODUCT SELECTOR
# =========================
selected_product = st.sidebar.radio(
    "Select Product",
    list(PRODUCTS.keys()),
    index=list(PRODUCTS.keys()).index(st.session_state.selected_product)
)

if selected_product != st.session_state.selected_product:
    st.session_state.selected_product = selected_product
    reset_run_state()
    st.rerun()

STEPS = PRODUCTS[st.session_state.selected_product]

if st.session_state.current_step >= len(STEPS):
    st.session_state.current_step = 0

current_step = STEPS[st.session_state.current_step]
is_completion_step = st.session_state.current_step == len(STEPS) - 1


# Reset motion/Nemotron buffer when step changes
if not is_completion_step and st.session_state.active_step_id != current_step["id"]:
    st.session_state.active_step_id = current_step["id"]
    st.session_state.previous_zone_frame = None
    st.session_state.detected_action = "IDLE"
    st.session_state.motion_score = 0
    st.session_state.current_motion_action = "IDLE"
    st.session_state.motion_action_start_time = time.time()
    st.session_state.last_motion_time = time.time()

    st.session_state.step_frame_buffer = []
    st.session_state.buffer_frame_counter = 0


# =========================
# COMPLETION SCREEN
# =========================
if is_completion_step:
    st.markdown(f"""
    <div style="
        text-align: center;
        padding: 35px 20px;
        border-radius: 20px;
        background: linear-gradient(135deg, #0f5132, #198754);
        color: white;
        margin-top: 20px;
    ">
        <h1 style="font-size: 44px;">Assembly Completed</h1>
        <h2>{st.session_state.selected_product} has been verified successfully.</h2>
        <p style="font-size: 18px;">All required steps are completed.</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Lean Analytics Summary")

    if st.session_state.action_logs:
        logs = st.session_state.action_logs

        total_va = sum(
            log["duration_seconds"]
            for log in logs
            if log["action_type"] == "VA"
        )

        total_nva = sum(
            log["duration_seconds"]
            for log in logs
            if log["action_type"] == "NVA"
        )

        total_nnva = sum(
            log["duration_seconds"]
            for log in logs
            if log["action_type"] == "NNVA"
        )

        total_time = total_va + total_nva + total_nnva
        efficiency = (total_va / total_time) * 100 if total_time > 0 else 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)

        with kpi1:
            st.metric("Total VA Time", f"{total_va:.2f}s")

        with kpi2:
            st.metric("Total NVA Time", f"{total_nva:.2f}s")

        with kpi3:
            st.metric("Total Time", f"{total_time:.2f}s")

        with kpi4:
            st.metric("Efficiency", f"{efficiency:.1f}%")

        st.subheader("Lean Time Distribution")

        chart_data = {
            "VA": total_va,
            "NVA": total_nva,
            "NNVA": total_nnva
        }

        st.bar_chart(chart_data)

        st.subheader("Action Duration by Type")

        summary_by_action = {}

        for log in logs:
            action_name = log["action_name"]

            if action_name not in summary_by_action:
                summary_by_action[action_name] = 0

            summary_by_action[action_name] += log["duration_seconds"]

        st.bar_chart(summary_by_action)

        st.subheader("Lean Action Log")

        st.dataframe(
            logs,
            use_container_width=True
        )

        csv_rows = [
            "step_id,action_name,description,action_type,start_time,end_time,duration_seconds"
        ]

        for log in logs:
            row = [
                str(log["step_id"]),
                log["action_name"],
                log["description"].replace(",", " "),
                log["action_type"],
                str(log["start_time"]),
                str(log["end_time"]),
                str(log["duration_seconds"])
            ]

            csv_rows.append(",".join(row))

        csv_data = "\n".join(csv_rows)

        st.download_button(
            label="Download Lean Report CSV",
            data=csv_data,
            file_name=f"{st.session_state.selected_product.lower().replace(' ', '_')}_lean_report.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.subheader("Nemotron AI Timeline")

        st.caption(
            "Nemotron analysis runs after assembly completion so it does not slow down step verification."
        )

        st.write(f"Saved step clips: {len(st.session_state.saved_nemotron_clips)}")

        if st.button("Run Nemotron AI Timeline", use_container_width=True, type="primary"):
            with st.spinner("Nemotron is analyzing all saved step clips..."):
                run_nemotron_for_saved_clips()

            st.success("Nemotron analysis completed.")
            st.rerun()

        if st.session_state.nemotron_processed:
            if st.session_state.nemotron_step_results:
                nemotron_df = pd.DataFrame(st.session_state.nemotron_step_results)

                st.dataframe(
                    nemotron_df,
                    use_container_width=True
                )

                nemotron_csv = nemotron_df.to_csv(index=False).encode("utf-8")

                st.download_button(
                    label="Download Nemotron AI Timeline CSV",
                    data=nemotron_csv,
                    file_name="nemotron_ai_timeline.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("Nemotron analysis completed, but no actions were returned.")

        if st.session_state.last_nemotron_result:
            with st.expander("Last Nemotron Raw Result"):
                st.json(st.session_state.last_nemotron_result)

    else:
        st.info("No action logs recorded yet.")

    if st.button("Restart Assembly", use_container_width=True):
        reset_run_state()
        st.rerun()

    st.stop()


# =========================
# HEADER
# =========================
top_left, top_right = st.columns([3, 1])

with top_left:
    st.title("Lean AI Assembly Guide")
    st.caption(f"Selected Product: {st.session_state.selected_product}")
    st.subheader(f"Step {current_step['id']}: {current_step['title']}")
    st.info(current_step["instruction"])

with top_right:
    progress = (st.session_state.current_step + 1) / len(STEPS)
    st.metric("Progress", f"{st.session_state.current_step + 1}/{len(STEPS)}")
    st.progress(progress)

    col_prev, col_next = st.columns(2)

    with col_prev:
        if st.button("Previous", use_container_width=True):
            if st.session_state.current_step > 0:
                st.session_state.current_step -= 1
                st.session_state.last_result = None
                st.rerun()

    with col_next:
        if st.button("Next", use_container_width=True):
            if st.session_state.current_step < len(STEPS) - 1:
                st.session_state.current_step += 1
                st.session_state.last_result = None
                st.rerun()


# =========================
# MAIN LAYOUT
# =========================
live_col, ref_col, status_col = st.columns([2.4, 1.4, 1.2])

with live_col:
    st.markdown("### Live Camera")
    frame_placeholder = st.empty()

with ref_col:
    st.markdown("### Expected Result")

    reference_images = current_step.get("reference_images", [])

    if reference_images and os.path.exists(reference_images[0]):
        ref_img = Image.open(reference_images[0])
        st.image(ref_img, use_container_width=True)
    else:
        st.warning("No reference image found.")

with status_col:
    st.markdown("### AI Verification")

    verify_clicked = st.button(
        "Verify Step",
        use_container_width=True,
        type="primary"
    )

    st.markdown(
        f"""
        <div class="motion-card">
            <div>Detected Action</div>
            <div class="motion-action">{st.session_state.detected_action}</div>
            <div>Motion Score: {st.session_state.motion_score}</div>
            <div>Buffered Frames: {len(st.session_state.step_frame_buffer)}</div>
            <div>Saved Clips: {len(st.session_state.saved_nemotron_clips)}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.last_result:
        result = st.session_state.last_result

        if result["status"] == "correct":
            st.success(result["message"])
        elif result["status"] == "wrong":
            st.error(result["message"])
        else:
            st.warning(result["message"])
    else:
        st.info("Complete the step, then click Verify Step.")


# =========================
# CAMERA
# =========================
camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

if not camera.isOpened():
    st.error("Failed to open camera. Try changing CAMERA_INDEX to 0 or 2.")
    st.stop()

verification_done = False

while True:
    success, frame = camera.read()

    if not success:
        st.error("Failed to read camera frame.")
        break

    height, width, _ = frame.shape

    zx1 = int(width * ZONE["x1_ratio"])
    zy1 = int(height * ZONE["y1_ratio"])
    zx2 = int(width * ZONE["x2_ratio"])
    zy2 = int(height * ZONE["y2_ratio"])

    original_frame = frame.copy()
    current_zone_frame = original_frame[zy1:zy2, zx1:zx2]

    # Buffer zone frames for Nemotron step clip
    st.session_state.buffer_frame_counter += 1

    if st.session_state.buffer_frame_counter % FRAME_SAMPLE_INTERVAL == 0:
        st.session_state.step_frame_buffer.append(current_zone_frame.copy())

        if len(st.session_state.step_frame_buffer) > MAX_NEMOTRON_FRAMES:
            st.session_state.step_frame_buffer.pop(0)

    motion_score = calculate_motion_score(
        st.session_state.previous_zone_frame,
        current_zone_frame
    )

    raw_action = classify_motion(
        motion_score,
        motion_threshold=MOTION_THRESHOLD
    )

    now = time.time()

    if raw_action == "ASSEMBLE":
        st.session_state.last_motion_time = now
        detected_action = "ASSEMBLE"
    else:
        if now - st.session_state.last_motion_time >= IDLE_GRACE_SECONDS:
            detected_action = "IDLE"
        else:
            detected_action = "ASSEMBLE"

    if detected_action != st.session_state.current_motion_action:
        log_motion_action(now, current_step)
        st.session_state.current_motion_action = detected_action
        st.session_state.motion_action_start_time = now

    st.session_state.motion_score = motion_score
    st.session_state.detected_action = detected_action
    st.session_state.previous_zone_frame = current_zone_frame.copy()

    display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    zone_color = (0, 255, 0)
    if detected_action == "ASSEMBLE":
        zone_color = (255, 165, 0)

    cv2.rectangle(
        display_frame,
        (zx1, zy1),
        (zx2, zy2),
        zone_color,
        3
    )

    cv2.putText(
        display_frame,
        f"Assembly Zone - {detected_action}",
        (zx1, max(zy1 - 8, 22)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        zone_color,
        2
    )

    frame_placeholder.image(
        display_frame,
        channels="RGB",
        use_container_width=True
    )

    if verify_clicked and not verification_done:
        verification_done = True

        now = time.time()

        # Log current motion state before verification
        log_motion_action(now, current_step)
        st.session_state.motion_action_start_time = now

        # Save Nemotron clip only. Do not analyze yet.
        save_current_step_clip(current_step)

        # Log VERIFY action as NNVA
        verify_start = time.time()

        os.makedirs("captured", exist_ok=True)

        current_crop = original_frame[zy1:zy2, zx1:zx2]
        safe_product_name = st.session_state.selected_product.lower().replace(" ", "_")
        current_image_path = f"captured/{safe_product_name}_current_step_{current_step['id']}.jpg"
        reference_image_paths = current_step["reference_images"]

        cv2.imwrite(current_image_path, current_crop)

        missing_refs = [
            ref for ref in reference_image_paths
            if not os.path.exists(ref)
        ]

        if missing_refs:
            camera.release()
            st.session_state.last_result = {
                "status": "waiting",
                "message": f"Reference image not found: {missing_refs[0]}"
            }
            st.rerun()

        with st.spinner("AI is verifying the assembly..."):
            result = verify_step(
                reference_image_paths=reference_image_paths,
                current_image_path=current_image_path,
                step=current_step
            )

        verify_end = time.time()

        log_action(
            action_name="VERIFY",
            action_type="NNVA",
            description=f"AI verification performed for {current_step['title']}.",
            start_time=verify_start,
            end_time=verify_end,
            step=current_step
        )

        st.session_state.last_result = result

        camera.release()

        if result["status"] == "wrong":
            log_action(
                action_name="REWORK",
                action_type="NVA",
                description=f"Assembly was incorrect during {current_step['title']} and requires rework.",
                start_time=verify_end,
                end_time=verify_end + 1.0,
                step=current_step
            )

        if result["status"] == "correct":
            time.sleep(0.7)

            st.session_state.step_frame_buffer = []
            st.session_state.buffer_frame_counter = 0

            if st.session_state.current_step < len(STEPS) - 1:
                st.session_state.current_step += 1
                st.session_state.current_motion_action = "IDLE"
                st.session_state.motion_action_start_time = time.time()
                st.session_state.previous_zone_frame = None
                st.session_state.last_motion_time = time.time()

        st.rerun()

    time.sleep(0.03)

camera.release()