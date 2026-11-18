
import cv2
import time
import json
import platform
import threading

from datetime import datetime

from engine.recognizer import FaceRecognizer
from engine.identity import IdentityManager
from engine.tracker import FaceTracker

from database.db import initialize_database, create_event

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


class SecurityEngine:

    def __init__(self):

        self.running = threading.Event()
        self.thread = None

        self.frame_lock = threading.Lock()
        self.status_lock = threading.Lock()

        self.latest_frame = None

        self.status = {
            "running": False,
            "camera": "starting",
            "message": "Initializing security engine",
            "unknown_count": 0,
            "authorized_count": 0
        }

    # --------------------------------------------------
    # STATUS MANAGEMENT
    # --------------------------------------------------

    def update_status(self, **values):

        with self.status_lock:
            self.status.update(values)

    def get_status(self):

        with self.status_lock:
            return self.status.copy()

    def get_frame(self):

        with self.frame_lock:
            return self.latest_frame

    # --------------------------------------------------
    # ENGINE START / STOP
    # --------------------------------------------------

    def start(self):

        if self.thread and self.thread.is_alive():
            return

        self.running.set()

        self.thread = threading.Thread(
            target=self._run,
            daemon=True
        )

        self.thread.start()

    def stop(self):

        self.running.clear()

        if self.thread:
            self.thread.join(timeout=5)

        with self.status_lock:
            self.status.update({
                "running": False,
                "camera": "stopped",
                "message": "Security engine stopped"
            })

        print("Security engine shutdown requested.")

    # --------------------------------------------------
    # ALARM
    # --------------------------------------------------

    @staticmethod
    def play_alarm():

        print("\n!!! SENTINELGUARD SECURITY ALERT !!!")

        if platform.system() == "Windows":

            try:
                import winsound
                winsound.Beep(1000, 900)

            except Exception as error:
                print("Alarm unavailable:", error)

    # --------------------------------------------------
    # SAVE EVIDENCE
    # --------------------------------------------------

    @staticmethod
    def save_evidence(frame, track):

        timestamp = datetime.now().astimezone()

        filename = (
            f"unknown_track_{track['id']}_"
            f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        )

        image_path = UNKNOWN_EVIDENCE_DIR / filename

        UNKNOWN_EVIDENCE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        success = cv2.imwrite(
            str(image_path),
            frame
        )

        if not success:
            raise RuntimeError(
                "Could not save evidence image."
            )

        metadata = {
            "track_id": track["id"],
            "classification": "UNKNOWN",
            "timestamp": timestamp.isoformat(timespec="seconds"),
            "similarity": round(float(track["score"]), 4),
            "image": filename,
            "image_path": str(image_path)
        }

        metadata_path = image_path.with_suffix(".json")

        with open(
            metadata_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                metadata,
                file,
                indent=4
            )

        print("\nUNKNOWN PERSON EVIDENCE SAVED")
        print("Image:", image_path)
        print("Metadata:", metadata_path)

        return image_path

    # --------------------------------------------------
    # UNKNOWN PERSON EVENT
    # --------------------------------------------------

    @staticmethod
    def record_unknown_event(track):

        event_id = create_event(
            event_type="UNKNOWN_DETECTED",
            track_id=track["id"],
            person_name="UNKNOWN",
            similarity=float(track["score"]),
            evidence_path=track["evidence_path"],
            description=(
                "Unknown face persisted for "
                f"{UNKNOWN_CAPTURE_SECONDS} seconds."
            )
        )

        print(
            "\nUNKNOWN DETECTION EVENT SAVED"
            f"\nDatabase Event ID: {event_id}"
            f"\nFace Track ID: {track['id']}"
            f"\nEvidence: {track['evidence_path']}"
        )

        return event_id

    # --------------------------------------------------
    # UNKNOWN PERSON ALERT
    # --------------------------------------------------

    @staticmethod
    def record_unknown_alert(track):

        event_id = create_event(
            event_type="UNKNOWN_ALERT",
            track_id=track["id"],
            person_name="UNKNOWN",
            similarity=float(track["score"]),
            evidence_path=track.get("evidence_path"),
            description=(
                "Unknown face persisted for "
                f"{UNKNOWN_ALERT_SECONDS} seconds."
            )
        )

        print(
            "\nUNKNOWN SECURITY ALERT SAVED"
            f"\nDatabase Event ID: {event_id}"
            f"\nFace Track ID: {track['id']}"
        )

        return event_id

    # --------------------------------------------------
    # AUTHORIZED PERSON EVENT
    # --------------------------------------------------

    @staticmethod
    def record_authorized_event(track):

        event_id = create_event(
            event_type="AUTHORIZED_DETECTED",
            track_id=track["id"],
            person_name=track["name"],
            similarity=float(track["score"]),
            description="Authorized face detected."
        )

        print(
            "\nAUTHORIZED PERSON EVENT SAVED"
            f"\nDatabase Event ID: {event_id}"
            f"\nFace Track ID: {track['id']}"
            f"\nPerson: {track['name']}"
        )

        return event_id

    # --------------------------------------------------
    # CAMERA ENGINE
    # --------------------------------------------------

    def _run(self):

        camera = None
        engine_error = None

        try:

            initialize_database()

            self.update_status(
                running=False,
                camera="starting",
                message="Loading AI models"
            )

            print("\nLoading SentinelGuard AI models...")

            face_system = FaceRecognizer()

            identity_system = IdentityManager(
                threshold=FACE_MATCH_THRESHOLD
            )

            identity_system.load_people(
                AUTHORIZED_DIR
            )

            tracker = FaceTracker(
                iou_threshold=TRACK_IOU_THRESHOLD,
                max_missing_seconds=TRACK_MAX_MISSING_SECONDS
            )

            # Open webcam
            camera = cv2.VideoCapture(
                CAMERA_INDEX
            )

            camera.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                FRAME_WIDTH
            )

            camera.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                FRAME_HEIGHT
            )

            if not camera.isOpened():
                raise RuntimeError(
                    "Could not open webcam."
                )

            self.update_status(
                running=True,
                camera="connected",
                message="Security monitoring active"
            )

            print("\nSentinelGuard camera engine started.")
            print("Camera connected.")
            print(
                f"Evidence threshold: {UNKNOWN_CAPTURE_SECONDS} seconds"
            )
            print(
                f"Alert threshold: {UNKNOWN_ALERT_SECONDS} seconds"
            )

            # ------------------------------------------
            # MAIN MONITORING LOOP
            # ------------------------------------------

            while self.running.is_set():

                success, frame = camera.read()

                if not success:
                    raise RuntimeError(
                        "Could not read camera frame."
                    )

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

                            print(
                                "Face processing error:",
                                error
                            )

                # --------------------------------------
                # TRACK DETECTED FACES
                # --------------------------------------

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

                    # ----------------------------------
                    # UNKNOWN PERSON
                    # ----------------------------------

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

                        # SAVE IMAGE AFTER 10 SECONDS
                        if (
                            elapsed >= UNKNOWN_CAPTURE_SECONDS
                            and not track["evidence_saved"]
                        ):

                            try:

                                path = self.save_evidence(
                                    original_frame,
                                    track
                                )

                                track["evidence_path"] = str(path)
                                track["evidence_saved"] = True

                            except Exception as error:

                                print(
                                    "Evidence saving error:",
                                    error
                                )

                        # RECORD DATABASE EVENT
                        if (
                            track["evidence_saved"]
                            and not track["event_recorded"]
                        ):

                            try:

                                self.record_unknown_event(
                                    track
                                )

                                track["event_recorded"] = True

                            except Exception as error:

                                print(
                                    "Unknown event database error:",
                                    error
                                )

                        # ALERT AFTER 30 SECONDS
                        if (
                            elapsed >= UNKNOWN_ALERT_SECONDS
                            and not track["alerted"]
                        ):

                            try:

                                self.play_alarm()

                                self.record_unknown_alert(
                                    track
                                )

                                track["alerted"] = True

                            except Exception as error:

                                print(
                                    "Unknown alert error:",
                                    error
                                )

                        if track["alerted"]:

                            label = "ALERT | " + label

                    # ----------------------------------
                    # AUTHORIZED PERSON
                    # ----------------------------------

                    else:

                        authorized_count += 1

                        color = (0, 255, 0)

                        label = (
                            f"AUTHORIZED: {name}"
                        )

                        if not track["authorized_logged"]:

                            try:

                                self.record_authorized_event(
                                    track
                                )

                                track["authorized_logged"] = True

                            except Exception as error:

                                print(
                                    "Authorized event error:",
                                    error
                                )

                    # ----------------------------------
                    # DRAW FACE RECTANGLE
                    # ----------------------------------

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

                # --------------------------------------
                # DISPLAY SYSTEM COUNTS
                # --------------------------------------

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

                # --------------------------------------
                # ENCODE LIVE DASHBOARD FRAME
                # --------------------------------------

                success, buffer = cv2.imencode(
                    ".jpg",
                    frame
                )

                if success:

                    with self.frame_lock:

                        self.latest_frame = buffer.tobytes()

                # --------------------------------------
                # UPDATE CAMERA STATUS
                # --------------------------------------

                self.update_status(
                    running=True,
                    camera="connected",
                    message="Security monitoring active",
                    unknown_count=unknown_count,
                    authorized_count=authorized_count
                )

        except Exception as error:

            engine_error = str(error)

            print(
                "\nSECURITY ENGINE ERROR:",
                engine_error
            )

            self.update_status(
                running=False,
                camera="error",
                message=engine_error
            )

        finally:

            if camera is not None:
                camera.release()

            self.running.clear()

            with self.frame_lock:
                self.latest_frame = None

            if engine_error is None:

                self.update_status(
                    running=False,
                    camera="stopped",
                    message="Security engine stopped",
                    unknown_count=0,
                    authorized_count=0
                )

            print("\nSecurity camera engine stopped.")


security_engine = SecurityEngine()
