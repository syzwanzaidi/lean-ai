import os
import time
import cv2
import streamlit as st
from PIL import Image

from steps import STEPS
from openai_verifier import verify_step

ZONE = {
    "x1_ratio": 0.02,
    "y1_ratio": 0.05,
    "x2_ratio": 0.63,
    "y2_ratio": 0.57
}

CAMERA_INDEX = 1

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
hr {
    margin-top: 0.3rem !important;
    margin-bottom: 0.3rem !important;
}
</style>
""", unsafe_allow_html=True)

if "current_step" not in st.session_state:
    st.session_state.current_step = 0

if "last_result" not in st.session_state:
    st.session_state.last_result = None

current_step = STEPS[st.session_state.current_step]

if current_step["id"] == 5:
    st.markdown("""
    <div style="
        text-align: center;
        padding: 45px 20px;
        border-radius: 20px;
        background: linear-gradient(135deg, #0f5132, #198754);
        color: white;
        margin-top: 20px;
    ">
        <h1 style="font-size: 48px;">✅ Assembly Completed</h1>
        <h2>Lamp assembly has been verified successfully.</h2>
        <p style="font-size: 20px;">All required steps are completed.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Restart Assembly", use_container_width=True):
        st.session_state.current_step = 0
        st.session_state.last_result = None
        st.rerun()

    st.stop()

top_left, top_right = st.columns([3, 1])

with top_left:
    st.title("Lean AI Assembly Guide")
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
    display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    cv2.rectangle(
        display_frame,
        (zx1, zy1),
        (zx2, zy2),
        (0, 255, 0),
        3
    )

    cv2.putText(
        display_frame,
        "Assembly Zone",
        (zx1, max(zy1 - 8, 22)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 255, 0),
        2
    )

    frame_placeholder.image(
        display_frame,
        channels="RGB",
        use_container_width=True
    )

    if verify_clicked and not verification_done:
        verification_done = True

        os.makedirs("captured", exist_ok=True)

        current_crop = original_frame[zy1:zy2, zx1:zx2]
        current_image_path = f"captured/current_step_{current_step['id']}.jpg"
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

        st.session_state.last_result = result

        camera.release()

        if result["status"] == "correct":
            time.sleep(0.7)

            if st.session_state.current_step < len(STEPS) - 1:
                st.session_state.current_step += 1

        st.rerun()

    time.sleep(0.03)

camera.release()