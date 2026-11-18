
import cv2

from engine.recognizer import FaceRecognizer
from engine.identity import IdentityManager

from config import (
    CAMERA_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    AUTHORIZED_DIR,
    FACE_MATCH_THRESHOLD
)


def main():

    print("\nStarting SentinelGuard Recognition System...")

    # Load AI models
    face_system = FaceRecognizer()

    # Load authorized people
    identity_system = IdentityManager(
        threshold=FACE_MATCH_THRESHOLD
    )

    identity_system.load_people(AUTHORIZED_DIR)

    camera = cv2.VideoCapture(CAMERA_INDEX)

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        FRAME_WIDTH
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        FRAME_HEIGHT
    )

    if not camera.isOpened():

        print("ERROR: Could not open webcam.")
        return

    print("\nRecognition system is running!")
    print("Press Q to exit.")

    while True:

        success, frame = camera.read()

        if not success:
            print("Camera frame error.")
            break

        faces = face_system.detect_faces(frame)

        face_count = 0

        if faces is not None:

            face_count = len(faces)

            for face in faces:

                x, y, w, h = face[:4].astype(int)

                try:

                    embedding = face_system.get_embedding(
                        frame,
                        face
                    )

                    name, score = identity_system.identify(
                        embedding
                    )

                    if name == "UNKNOWN":

                        color = (0, 0, 255)
                        label = "UNKNOWN"

                    else:

                        color = (0, 255, 0)
                        label = f"AUTHORIZED: {name}"

                    cv2.rectangle(
                        frame,
                        (x, y),
                        (x + w, y + h),
                        color,
                        2
                    )

                    cv2.putText(
                        frame,
                        label,
                        (x, max(y - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        color,
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Similarity: {score:.2f}",
                        (x, y + h + 22),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        1
                    )

                except Exception as error:

                    print("Face processing error:", error)

        cv2.putText(
            frame,
            f"Faces detected: {face_count}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2
        )

        cv2.imshow(
            "SentinelGuard - Face Recognition",
            frame
        )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()

    print("SentinelGuard stopped.")


if __name__ == "__main__":
    main()
