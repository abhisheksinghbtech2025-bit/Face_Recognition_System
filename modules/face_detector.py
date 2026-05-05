# ============================================================
#   FaceSecuritySystem — modules/face_detector.py
#   Module 4: Face Detection using OpenCV
# ============================================================

import cv2
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import CAMERA_WIDTH, CAMERA_HEIGHT


class FaceDetector:
    """
    Detects faces in a frame using OpenCV's Haar Cascade classifier.
    Fast and lightweight — runs on any machine without GPU.
    """

    def __init__(self):
        # Load OpenCV's built-in face detector
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(cascade_path)

        if self.detector.empty():
            raise RuntimeError(
                "[DETECTOR] Failed to load Haar cascade. "
                "Check your OpenCV installation."
            )
        print("[DETECTOR] Face detector loaded successfully.")

    def detect_faces(self, frame: np.ndarray):
        """
        Detect all faces in a frame.

        Args:
            frame: BGR image from OpenCV camera

        Returns:
            List of (x, y, w, h) tuples — one per detected face
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor = 1.1,
            minNeighbors= 5,
            minSize     = (60, 60),
            flags       = cv2.CASCADE_SCALE_IMAGE
        )

        if len(faces) == 0:
            return []

        return [(x, y, w, h) for (x, y, w, h) in faces]

    def draw_boxes(self, frame: np.ndarray,
                   faces: list,
                   labels: list = None,
                   colors: list = None) -> np.ndarray:
        """
        Draw bounding boxes and labels on the frame.

        Args:
            frame:  BGR image
            faces:  list of (x, y, w, h)
            labels: list of name strings (one per face)
            colors: list of BGR color tuples (one per face)

        Returns:
            Annotated frame
        """
        output = frame.copy()

        for i, (x, y, w, h) in enumerate(faces):
            color = colors[i] if colors else (0, 255, 0)
            label = labels[i] if labels else ""

            # Draw rectangle
            cv2.rectangle(output, (x, y), (x + w, y + h), color, 2)

            # Draw label background
            if label:
                label_size, _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                lw, lh = label_size
                cv2.rectangle(
                    output,
                    (x, y - lh - 12),
                    (x + lw + 10, y),
                    color, -1
                )
                cv2.putText(
                    output, label,
                    (x + 5, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2
                )

        return output

    def crop_face(self, frame: np.ndarray,
                  face: tuple,
                  padding: int = 20) -> np.ndarray:
        """
        Crop a single face region from the frame with padding.

        Args:
            frame:   BGR image
            face:    (x, y, w, h)
            padding: pixels of padding around the face

        Returns:
            Cropped face image
        """
        x, y, w, h = face
        h_img, w_img = frame.shape[:2]

        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(w_img, x + w + padding)
        y2 = min(h_img, y + h + padding)

        return frame[y1:y2, x1:x2]