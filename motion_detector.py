import cv2


def calculate_motion_score(previous_frame, current_frame):
    """
    Calculate movement difference between two frames.
    Higher score = more movement.
    """

    if previous_frame is None or current_frame is None:
        return 0

    previous_gray = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(previous_gray, current_gray)

    _, threshold = cv2.threshold(
        diff,
        25,
        255,
        cv2.THRESH_BINARY
    )

    motion_score = cv2.countNonZero(threshold)

    return motion_score


def classify_motion(motion_score, motion_threshold=1500):
    """
    Classify action based on movement score.
    """

    if motion_score >= motion_threshold:
        return "ASSEMBLE"

    return "IDLE"