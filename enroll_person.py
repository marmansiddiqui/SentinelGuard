
import cv2
import numpy as np
import re

from pathlib import Path

from engine.recognizer import FaceRecognizer

from config import (
    CAMERA_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    AUTHORIZED_DIR
)


SAMPLES_REQUIRED = 5


def main():

    name = input("Enter the authorized person's name: ").strip()

    if not name:
        print("ERROR: Name cannot be empty.")
        return

    # Make a safe filename
    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        name
    ).strip("_")

    if not safe_name:
        print("ERROR: Please enter a name containing letters or numbers.")
        return

    output_file = AUTHORIZED_DIR / f"{safe_name}.npz"

    print("\nLoading face recognition system...")

    face_system = FaceRecognizer()

    camera = cv2.VideoCapture(CAMERA_INDEX)

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        return

    embeddings = []

    print("\nENROLLMENT STARTED")
    print("Keep only ONE person's face in the camera.")
    print("Press C to capture a face sample.")
    print("Press Q to cancel.")

    while len(embeddings) < SAMPLES_REQUIRED:

        success, frame = camera.read()

        if not success:
            print("Camera frame could not be read.")
            break

        faces = face_system.detect_faces(frame)

        face_count = 0

        if faces is not None:
            face_count = len(faces)

        # Draw face detection boxes
        if faces is not None:

            for face in faces:

                x, y, w, h = face[:4].astype(int)

                cv2.rectangle(
                    frame,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    2
                )

        cv2.putText(
            frame,
            f"Samples: {len(embeddings)}/{SAMPLES_REQUIRED}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        if face_count == 1:

            message = "One face detected - Press C"

        elif face_count == 0:

            message = "No face detected"

        else:

            message = "Multiple faces - Keep only one person"

        cv2.putText(
            frame,
            message,
            (20, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.imshow(
            "SentinelGuard - Person Enrollment",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            print("\nEnrollment cancelled.")
            break

        if key == ord("c"):

            if face_count != 1:
                print("Please keep exactly one face in the camera.")
                continue

            try:

                embedding = face_system.get_embedding(
                    frame,
                    faces[0]
                )

                embeddings.append(embedding)

                print(
                    f"Captured sample {len(embeddings)}/{SAMPLES_REQUIRED}"
                )

            except Exception as error:

                print("Could not process face:", error)

    camera.release()
    cv2.destroyAllWindows()

    if len(embeddings) != SAMPLES_REQUIRED:
        print("Enrollment incomplete. No new person was saved.")
        return

    # Add samples to an existing person's record, if present.
    if output_file.exists():

        with np.load(output_file, allow_pickle=False) as existing:

            existing_name = str(existing["name"].item())

            if existing_name != name:
                print("ERROR: This filename belongs to a different name.")
                return

            old_embeddings = existing["embeddings"]

        all_embeddings = np.vstack([
            old_embeddings,
            np.asarray(embeddings, dtype=np.float32)
        ])

    else:

        all_embeddings = np.asarray(
            embeddings,
            dtype=np.float32
        )

    np.savez_compressed(
        output_file,
        name=np.asarray(name),
        embeddings=all_embeddings
    )

    print("\n================================")
    print("PERSON ENROLLED SUCCESSFULLY")
    print("Name:", name)
    print("Samples stored:", len(all_embeddings))
    print("Saved at:", output_file)
    print("================================")


if __name__ == "__main__":
    main()
