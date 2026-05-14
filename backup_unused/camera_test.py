import cv2

for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)

    if cap.isOpened():
        print(f"Camera found at index {i}")

        ret, frame = cap.read()

        if ret:
            print(f"Camera {i} can read frame: {frame.shape}")
        else:
            print(f"Camera {i} opened but cannot read frame")

    cap.release()