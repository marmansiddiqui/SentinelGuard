
import cv2
import time
import platform
import json

from datetime import datetime

from engine.recognizer import FaceRecognizer
from engine.identity import IdentityManager
from engine.tracker import FaceTracker

from database.db import (
    initialize_database,
    create_event
)

from config import (
    CAMERA_INDEX,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    AUTHORIZED_DIR,
    FACE_MATCH_THRESHOLD,
    UNKNOWN_EVIDENCE_DIR,
    UNKNOWN_CAPTURE_SECONDS,
    UNKNOWN_ALERT_SECONDS,
    TRACK_IOU_THRESHOLD,
    TRACK_MAX_MISSING_SECONDS
)


def play_alarm():

    print("\n!!! SENTINELGUARD SECURITY ALERT !!!")

    if platform.system() == "Windows":

        try:
            import winsound
            winsound.Beep(1000, 900)

        except Exception as error:
            print("Alarm unavailable:", error)


def save_evidence(frame, track):

    timestamp = datetime.now().astimezone()

    filename = (
        f"unknown_track_{track['id']}_"
        f"{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
    )

    image_path = UNKNOWN_EVIDENCE_DIR / filename

    saved = cv2.imwrite(str(image_path), frame)

    if not saved:
        raise RuntimeError("Could not save evidence image.")

    metadata = {
        "track_id": track["id"],
        "classification": "UNKNOWN",
        "timestamp": timestamp.isoformat(timespec="seconds"),
        "similarity": round(track["score"], 4),
        "image": filename
    }

    metadata_path = image_path.with_suffix(".json")

    with open(metadata_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)

    print("\nUNKNOWN PERSON EVIDENCE SAVED")
    print("Image:", image_path)
    print("Metadata:", metadata_path)

    return image_path


def main():

    print("\n================================")
    print("       SENTINELGUARD")
    print("   SECURITY MONITORING SYSTEM")
    print("================================\n")

    # Initialize the local database
    initialize_database()

    # Load face detection and recognition models
    face_system = FaceRecognizer()

    # Load authorized identities
    identity_system = IdentityManager(
        threshold=FACE_MATCH_THRESHOLD
    )

    identity_system.load_people(AUTHORIZED_DIR)

    # Initialize face tracker
    tracker = FaceTracker(
        iou_threshold=TRACK_IOU_THRESHOLD,
        max_missing_seconds=TRACK_MAX_MISSING_SECONDS
    )

    # Open webcam
    camera = cv2.VideoCapture(CAMERA_INDEX)

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not camera.isOpened():
        print("ERROR: Could not open webcam.")
        return

    print("\nMonitoring started.")
    print("Unknown evidence threshold:", UNKNOWN_CAPTURE_SECONDS)
    print("Unknown alert threshold:", UNKNOWN_ALERT_SECONDS)
    print("Press Q to exit.\n")

    try:

        while True:

            success, frame = camera.read()

            if not success:
                print("Camera frame error.")
                break

            original_frame = frame.copy()
            current_time = time.monotonic()

            faces = face_system.detect_faces(frame)
            detections = []

            if faces is not None:

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

                        detections.append((
                            (x, y, w, h),
                            name,
                            score
                        ))

                    except Exception as error:
                        print("Face processing error:", error)

            active_tracks = tracker.update(
                detections,
                current_time
            )

            unknown_count = 0
            authorized_count = 0

            for track in active_tracks:

                x, y, w, h = track["box"]

                name = track["name"]
                score = track["score"]

                if name == "UNKNOWN":

                    unknown_count += 1

                    elapsed = (
                        current_time - track["unknown_since"]
                    )

                    color = (0, 0, 255)

                    label = (
                        f"UNKNOWN | ID {track['id']} | "
                        f"{elapsed:.1f}s"
                    )

                    # Save evidence and create database event at 10 seconds
                    if (
                        elapsed >= UNKNOWN_CAPTURE_SECONDS
                        and not track["evidence_saved"]
                    ):

                        try:

                            image_path = save_evidence(
                                original_frame,
                                track
                            )

                            create_event(
                                event_type="UNKNOWN_DETECTED",
                                track_id=track["id"],
                                person_name="UNKNOWN",
                                similarity=float(score),
                                evidence_path=image_path,
                                description=(
                                    "Unknown face persisted for "
                                    f"{UNKNOWN_CAPTURE_SECONDS} seconds."
                                )
                            )

                            track["evidence_saved"] = True

                            print("Database event saved: UNKNOWN_DETECTED")

                        except Exception as error:
                            print("Evidence/database error:", error)

                    # Trigger alarm and database event at 30 seconds
                    if (
                        elapsed >= UNKNOWN_ALERT_SECONDS
                        and not track["alerted"]
                    ):

                        play_alarm()

                        try:

                            create_event(
                                event_type="UNKNOWN_ALERT",
                                track_id=track["id"],
                                person_name="UNKNOWN",
                                similarity=float(score),
                                description=(
                                    "Unknown face persisted for "
                                    f"{UNKNOWN_ALERT_SECONDS} seconds."
                                )
                            )

                            print("Database event saved: UNKNOWN_ALERT")

                        except Exception as error:
                            print("Alert database error:", error)

                        track["alerted"] = True

                    if track["alerted"]:
                        label = "ALERT | " + label

                else:

                    authorized_count += 1

                    color = (0, 255, 0)
                    label = f"AUTHORIZED: {name}"

                    # Save one authorized event per tracking session
                    if not track["authorized_logged"]:

                        try:

                            create_event(
                                event_type="AUTHORIZED_DETECTED",
                                track_id=track["id"],
                                person_name=name,
                                similarity=float(score),
                                description="Authorized face detected."
                            )

                            track["authorized_logged"] = True

                            print(
                                "Database event saved: "
                                "AUTHORIZED_DETECTED"
                            )

                        except Exception as error:
                            print("Authorized event error:", error)

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
                    0.55,
                    color,
                    2
                )

                cv2.putText(
                    frame,
                    f"Similarity: {score:.2f}",
                    (x, y + h + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    color,
                    1
                )

            cv2.putText(
                frame,
                f"Unknown: {unknown_count}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

            cv2.putText(
                frame,
                f"Authorized: {authorized_count}",
                (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.imshow(
                "SentinelGuard - Security Monitoring",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:

        camera.release()
        cv2.destroyAllWindows()

        print("\nSentinelGuard stopped.")


if __name__ == "__main__":
    main()
