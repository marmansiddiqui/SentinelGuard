
import cv2

from engine.recognizer import FaceRecognizer
from config import CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT


def main():

    print("Starting SentinelGuard...")

    # Load AI models
    face_system = FaceRecognizer()

    # Open webcam
    camera = cv2.VideoCapture(CAMERA_INDEX)

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        print("Try changing CAMERA_INDEX in config.py to 1.")
        return

    print("Webcam connected!")
    print("Press Q to close SentinelGuard.")

    while True:

        success, frame = camera.read()

        if not success:
            print("Could not read webcam frame.")
            break

        # Detect faces
        faces = face_system.detect_faces(frame)

        face_count = 0

        if faces is not None:

            face_count = len(faces)

            for face in faces:

                x, y, w, h = face[:4].astype(int)

                # Draw rectangle around face
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    "FACE DETECTED",
                    (x, max(y - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

        # Display face count
        cv2.putText(
            frame,
            f"Faces: {face_count}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.imshow("SentinelGuard - Face Detection", frame)

        # Press Q to exit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()

    print("SentinelGuard stopped.")


if __name__ == "__main__":
    main()
