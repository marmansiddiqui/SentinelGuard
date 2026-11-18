
import cv2
import numpy as np

from config import (
    FACE_DETECTION_MODEL,
    FACE_RECOGNITION_MODEL,
    DETECTION_SCORE_THRESHOLD,
    NMS_THRESHOLD,
    TOP_K
)


class FaceRecognizer:

    def __init__(self):

        if not FACE_DETECTION_MODEL.exists():
            raise FileNotFoundError(
                f"YuNet model not found: {FACE_DETECTION_MODEL}"
            )

        if not FACE_RECOGNITION_MODEL.exists():
            raise FileNotFoundError(
                f"SFace model not found: {FACE_RECOGNITION_MODEL}"
            )

        print("Loading YuNet face detection model...")

        self.detector = cv2.FaceDetectorYN.create(
            str(FACE_DETECTION_MODEL),
            "",
            (320, 320),
            DETECTION_SCORE_THRESHOLD,
            NMS_THRESHOLD,
            TOP_K
        )

        print("Loading SFace face recognition model...")

        self.recognizer = cv2.FaceRecognizerSF.create(
            str(FACE_RECOGNITION_MODEL),
            ""
        )

        print("Both AI models loaded successfully!")

    def detect_faces(self, frame):

        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))

        _, faces = self.detector.detect(frame)

        return faces

    def get_embedding(self, frame, face):

        aligned_face = self.recognizer.alignCrop(
            frame,
            face
        )

        embedding = self.recognizer.feature(
            aligned_face
        )

        embedding = np.asarray(
            embedding,
            dtype=np.float32
        ).flatten()

        norm = np.linalg.norm(embedding)

        if norm == 0:
            raise ValueError("Invalid face embedding.")

        return embedding / norm
