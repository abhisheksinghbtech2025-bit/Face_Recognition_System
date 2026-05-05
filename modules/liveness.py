# ============================================================
#   FaceSecuritySystem — modules/liveness.py
#   Module 5: Liveness Detection
#   Uses Eye Aspect Ratio (EAR) for blink detection
#   and head movement for anti-spoofing
# ============================================================

import cv2
import numpy as np
import dlib
from scipy.spatial import distance as dist
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import (
    EAR_THRESHOLD, EAR_CONSEC_FRAMES,
    BLINKS_REQUIRED, LIVENESS_TIMEOUT_SEC
)


class LivenessDetector:
    """
    Detects whether a face belongs to a live person.

    Method 1 — Blink Detection (EAR):
        Measures Eye Aspect Ratio. A real person blinks.
        A printed photo or screen does not.

    Method 2 — Head Movement:
        Tracks nose tip position across frames.
        A real person moves slightly. A static image does not.

    Usage:
        detector = LivenessDetector()
        result   = detector.check(frame, face_location)
        if result["is_live"]:
            # proceed with recognition
    """

    # dlib landmark indices for left and right eyes
    LEFT_EYE  = list(range(42, 48))
    RIGHT_EYE = list(range(36, 42))
    NOSE_TIP  = 30   # landmark index for nose tip

    def __init__(self):
        self._load_dlib()
        self.reset()

    def _load_dlib(self):
        """Load dlib face detector and 68-point landmark predictor."""
        try:
            self.dlib_detector  = dlib.get_frontal_face_detector()
            # Look for the shape predictor file in common locations
            predictor_paths = [
                "shape_predictor_68_face_landmarks.dat",
                os.path.join(os.path.dirname(__file__),
                             "shape_predictor_68_face_landmarks.dat"),
                os.path.join(os.path.expanduser("~"),
                             "shape_predictor_68_face_landmarks.dat"),
            ]
            self.predictor = None
            for p in predictor_paths:
                if os.path.exists(p):
                    self.predictor = dlib.shape_predictor(p)
                    print(f"[LIVENESS] Loaded landmark predictor: {p}")
                    break

            if self.predictor is None:
                print("[LIVENESS] ⚠  shape_predictor_68_face_landmarks.dat not found.")
                print("[LIVENESS]    Download from: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2")
                print("[LIVENESS]    Liveness will use fallback motion-only mode.")

        except Exception as e:
            print(f"[LIVENESS] dlib load error: {e}")
            self.dlib_detector = None
            self.predictor     = None

    # =========================================================
    #  STATE MANAGEMENT
    # =========================================================

    def reset(self):
        """Reset all liveness state for a new check session."""
        self.blink_count        = 0
        self.ear_consec_counter = 0
        self.is_blinking        = False

        # Head movement tracking
        self.nose_positions     = []
        self.movement_detected  = False

        # Session timing
        self.session_start      = time.time()
        self.last_result        = None

    @property
    def timed_out(self) -> bool:
        """True if liveness check has been running too long."""
        return (time.time() - self.session_start) > LIVENESS_TIMEOUT_SEC

    @property
    def elapsed(self) -> float:
        """Seconds elapsed since liveness check started."""
        return time.time() - self.session_start

    # =========================================================
    #  MAIN CHECK
    # =========================================================

    def check(self, frame: np.ndarray,
              face_rect=None) -> dict:
        """
        Run liveness check on the given frame.

        Args:
            frame:      BGR image from OpenCV
            face_rect:  Optional dlib rect or (x,y,w,h) tuple.
                        If None, detector finds faces automatically.

        Returns dict:
            {
              "is_live"          : bool,
              "blinks"           : int,
              "blinks_required"  : int,
              "movement"         : bool,
              "ear"              : float,
              "progress"         : float  (0.0–1.0),
              "message"          : str,
              "timed_out"        : bool
            }
        """
        # Timeout check
        if self.timed_out:
            return self._result(False, "Liveness check timed out.", timed_out=True)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # ── Get dlib face rect ────────────────────────────────
        dlib_rect = self._get_dlib_rect(gray, face_rect)

        if dlib_rect is None:
            return self._result(False, "No face detected.")

        # ── Landmark prediction ───────────────────────────────
        if self.predictor is None:
            # Fallback: motion-only liveness
            return self._motion_only_check(frame)

        try:
            shape = self.predictor(gray, dlib_rect)
        except Exception:
            return self._result(False, "Landmark detection failed.")

        landmarks = self._shape_to_array(shape)

        # ── EAR blink detection ───────────────────────────────
        ear = self._compute_ear(landmarks)
        self._update_blink_state(ear)

        # ── Head movement detection ───────────────────────────
        nose_x = landmarks[self.NOSE_TIP][0]
        nose_y = landmarks[self.NOSE_TIP][1]
        self._update_movement(nose_x, nose_y)

        # ── Liveness decision ─────────────────────────────────
        progress = min(1.0, self.blink_count / BLINKS_REQUIRED)

        if self.blink_count >= BLINKS_REQUIRED:
            return self._result(
                True,
                f"✅  Liveness confirmed! ({self.blink_count} blinks)",
                ear=ear, progress=1.0
            )

        remaining = BLINKS_REQUIRED - self.blink_count
        message   = (
            f"👁  Please blink {remaining} more time(s)  "
            f"[{self.blink_count}/{BLINKS_REQUIRED}]"
        )
        return self._result(False, message, ear=ear, progress=progress)

    # =========================================================
    #  EAR BLINK LOGIC
    # =========================================================

    def _compute_ear(self, landmarks: np.ndarray) -> float:
        """
        Eye Aspect Ratio = distance between vertical eye landmarks
                         / distance between horizontal eye landmarks.
        When eye is closed, EAR drops below threshold.
        """
        left_ear  = self._eye_aspect_ratio(
            landmarks[self.LEFT_EYE[0]:self.LEFT_EYE[-1]+1]
        )
        right_ear = self._eye_aspect_ratio(
            landmarks[self.RIGHT_EYE[0]:self.RIGHT_EYE[-1]+1]
        )
        return (left_ear + right_ear) / 2.0

    @staticmethod
    def _eye_aspect_ratio(eye: np.ndarray) -> float:
        """Compute EAR for one eye given 6 landmark points."""
        # Vertical distances
        A = dist.euclidean(eye[1], eye[5])
        B = dist.euclidean(eye[2], eye[4])
        # Horizontal distance
        C = dist.euclidean(eye[0], eye[3])
        if C == 0:
            return 0.0
        return (A + B) / (2.0 * C)

    def _update_blink_state(self, ear: float):
        """Update blink counter based on EAR value."""
        if ear < EAR_THRESHOLD:
            self.ear_consec_counter += 1
        else:
            if self.ear_consec_counter >= EAR_CONSEC_FRAMES:
                self.blink_count += 1
                print(f"[LIVENESS] Blink detected! Total: {self.blink_count}")
            self.ear_consec_counter = 0

    # =========================================================
    #  HEAD MOVEMENT LOGIC
    # =========================================================

    def _update_movement(self, nose_x: int, nose_y: int):
        """Track nose tip position to detect head movement."""
        self.nose_positions.append((nose_x, nose_y))
        if len(self.nose_positions) > 30:   # keep last 30 frames
            self.nose_positions.pop(0)

        if len(self.nose_positions) >= 10:
            xs = [p[0] for p in self.nose_positions]
            ys = [p[1] for p in self.nose_positions]
            x_range = max(xs) - min(xs)
            y_range = max(ys) - min(ys)
            if x_range > 8 or y_range > 8:
                self.movement_detected = True

    # =========================================================
    #  FALLBACK: MOTION ONLY (no dlib predictor)
    # =========================================================

    def _motion_only_check(self, frame: np.ndarray) -> dict:
        """
        Simplified liveness using frame difference motion.
        Used when shape predictor is not available.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.nose_positions.append(gray.mean())

        if len(self.nose_positions) > 20:
            self.nose_positions.pop(0)

        if len(self.nose_positions) >= 10:
            variance = np.var(self.nose_positions)
            if variance > 5.0:
                return self._result(
                    True,
                    "✅  Motion detected — liveness confirmed (basic mode)"
                )

        return self._result(
            False,
            "👁  Please move slightly in front of the camera..."
        )

    # =========================================================
    #  HELPERS
    # =========================================================

    def _get_dlib_rect(self, gray: np.ndarray, face_rect=None):
        """Convert or detect a dlib rect from given face."""
        if face_rect is not None:
            # face_rect might be (x, y, w, h) from OpenCV
            if isinstance(face_rect, (tuple, list)) and len(face_rect) == 4:
                x, y, w, h = face_rect
                return dlib.rectangle(int(x), int(y),
                                      int(x + w), int(y + h))
            # Already a dlib rect
            return face_rect

        if self.dlib_detector is None:
            return None

        rects = self.dlib_detector(gray, 0)
        if len(rects) == 0:
            return None
        return rects[0]   # use the first detected face

    @staticmethod
    def _shape_to_array(shape) -> np.ndarray:
        """Convert dlib shape object to numpy array of (x, y) coords."""
        coords = np.zeros((68, 2), dtype=int)
        for i in range(68):
            coords[i] = (shape.part(i).x, shape.part(i).y)
        return coords

    def _result(self, is_live: bool, message: str,
                ear: float = 0.0, progress: float = 0.0,
                timed_out: bool = False) -> dict:
        result = {
            "is_live"        : is_live,
            "blinks"         : self.blink_count,
            "blinks_required": BLINKS_REQUIRED,
            "movement"       : self.movement_detected,
            "ear"            : round(ear, 3),
            "progress"       : round(progress, 2),
            "message"        : message,
            "timed_out"      : timed_out or self.timed_out,
            "elapsed"        : round(self.elapsed, 1),
        }
        self.last_result = result
        return result

    # =========================================================
    #  DRAW OVERLAY
    # =========================================================

    def draw_overlay(self, frame: np.ndarray,
                     result: dict,
                     landmarks: np.ndarray = None) -> np.ndarray:
        """
        Draw liveness status overlay on the frame.

        Args:
            frame:     BGR image
            result:    dict from check()
            landmarks: optional 68-point array to draw eye outlines

        Returns:
            Annotated frame
        """
        output = frame.copy()
        h, w   = output.shape[:2]

        # ── Status bar at top ─────────────────────────────────
        color = (0, 200, 80) if result["is_live"] else (60, 80, 245)
        cv2.rectangle(output, (0, 0), (w, 40), (20, 20, 20), -1)

        cv2.putText(
            output,
            result["message"],
            (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6, color, 2
        )

        # ── Progress bar ──────────────────────────────────────
        bar_w = int(w * result["progress"])
        cv2.rectangle(output, (0, 40), (w, 46), (40, 40, 40), -1)
        cv2.rectangle(output, (0, 40), (bar_w, 46), color, -1)

        # ── EAR value ─────────────────────────────────────────
        ear_text = f"EAR: {result['ear']:.2f}"
        cv2.putText(
            output, ear_text,
            (w - 110, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (150, 150, 150), 1
        )

        # ── Draw eye outlines if landmarks available ──────────
        if landmarks is not None:
            for idx_list in [self.LEFT_EYE, self.RIGHT_EYE]:
                pts = landmarks[idx_list[0]:idx_list[-1]+1]
                hull = cv2.convexHull(pts.reshape(-1, 1, 2))
                cv2.drawContours(output, [hull], -1, color, 1)

        return output