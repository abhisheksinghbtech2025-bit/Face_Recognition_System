# ============================================================
#   FaceSecuritySystem — modules/camera_coordinator.py
#   Cross-Camera Alert Coordination
#
#   PROBLEM SOLVED:
#   When a known person is at a bad angle, Camera 0 may see
#   "Unknown" while Camera 1 correctly sees "John Doe".
#   Without coordination each camera fires independently,
#   causing false alerts.
#
#   SOLUTION:
#   A shared registry tracks every camera's latest recognition
#   results. Before firing any alert the system checks ALL
#   cameras. If ANY camera recognizes the person as known,
#   the Unknown alert is suppressed.
# ============================================================

import threading
import time
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FaceObservation:
    """
    Stores one camera's latest observation of a face region.

    Fields:
        camera_id   : which camera saw this
        name        : recognized name or "Unknown"
        confidence  : recognition confidence 0.0 - 1.0
        is_known    : True if recognized as a registered person
        timestamp   : when this observation was recorded
        face_quality: estimated quality score 0.0 - 1.0
    """

    def __init__(self, camera_id: int, name: str,
                 confidence: float, is_known: bool,
                 face_quality: float = 1.0):
        self.camera_id    = camera_id
        self.name         = name
        self.confidence   = confidence
        self.is_known     = is_known
        self.face_quality = face_quality
        self.timestamp    = time.time()

    @property
    def age_seconds(self) -> float:
        """How old this observation is in seconds."""
        return time.time() - self.timestamp

    def __repr__(self):
        return (f"FaceObservation(cam={self.camera_id}, "
                f"name={self.name}, known={self.is_known}, "
                f"conf={self.confidence:.2f}, "
                f"age={self.age_seconds:.1f}s)")


class CameraCoordinator:
    """
    Coordinates recognition results across ALL cameras.

    How it works:
    ─────────────
    1. Each camera reports its recognition result by calling
       coordinator.report(camera_id, name, confidence, is_known)

    2. Before firing an Unknown alert, camera calls:
       coordinator.should_alert(camera_id, face_region)

    3. The coordinator checks the registry:
       - If another camera has seen this face as KNOWN
         recently → return False (suppress alert)
       - If this face has been Unknown on ALL cameras for
         longer than the grace period → return True (fire alert)
       - Otherwise → return False (still waiting)

    Configuration:
    ──────────────
    OBSERVATION_TTL_SEC  : How long to keep observations (default 5s)
    GRACE_PERIOD_SEC     : Wait before alerting (default 8s)
    MIN_CONFIDENCE       : Minimum confidence to trust a recognition
    POSITION_TOLERANCE   : How close face positions must be to match
                           across cameras (pixels, default 999 = any)
    """

    OBSERVATION_TTL_SEC  = 5.0    # discard observations older than this
    GRACE_PERIOD_SEC     = 8.0    # wait this long before firing alert
    MIN_CONFIDENCE       = 0.45   # minimum confidence to count as "known"
    POSITION_TOLERANCE   = 9999   # pixel tolerance for same-person matching

    def __init__(self):
        # Registry: {camera_id: [FaceObservation, ...]}
        self._registry  : dict[int, list[FaceObservation]] = {}

        # Unknown timer: {"unknown_cam0": first_seen_timestamp}
        self._unknown_since: dict[str, float] = {}

        # Known cache: {name: last_seen_timestamp}
        # If a person was known on any camera recently, cache it
        self._known_cache: dict[str, float] = {}

        self._lock = threading.Lock()
        print("[COORDINATOR] Cross-camera coordinator ready.")

    # =========================================================
    #  REPORT  — called by each camera every frame
    # =========================================================

    def report(self, camera_id: int, name: str,
               confidence: float, is_known: bool,
               face_quality: float = 1.0):
        """
        Camera reports its latest recognition result.

        Args:
            camera_id   : camera index (0, 1, 2 ...)
            name        : recognized name or "Unknown"
            confidence  : confidence score 0.0 - 1.0
            is_known    : True if matched a registered person
            face_quality: optional quality score (used for weighting)

        Call this EVERY frame for every detected face.
        """
        obs = FaceObservation(
            camera_id    = camera_id,
            name         = name,
            confidence   = confidence,
            is_known     = is_known,
            face_quality = face_quality
        )

        with self._lock:
            # Store observation
            if camera_id not in self._registry:
                self._registry[camera_id] = []
            self._registry[camera_id].append(obs)

            # Purge old observations for this camera
            self._registry[camera_id] = [
                o for o in self._registry[camera_id]
                if o.age_seconds < self.OBSERVATION_TTL_SEC
            ]

            # Update known cache if this is a good recognition
            if is_known and confidence >= self.MIN_CONFIDENCE:
                self._known_cache[name] = time.time()
                # Clear unknown timer for this name if it was pending
                key = f"unknown_{name}_cam{camera_id}"
                self._unknown_since.pop(key, None)

    # =========================================================
    #  SHOULD ALERT  — called before firing an unknown alert
    # =========================================================

    def should_alert(self, camera_id: int,
                     face_id: str = "unknown") -> dict:
        """
        Decide whether to fire an Unknown alert from this camera.

        Args:
            camera_id : camera that wants to fire the alert
            face_id   : unique face identifier string
                        (e.g. position hash or "unknown_0")

        Returns dict:
            {
              "alert"          : bool,   True = fire the alert
              "reason"         : str,    explanation
              "known_on_cam"   : int,    camera ID that knows this person
              "waiting_seconds": float,  how long we've been waiting
              "suppress"       : bool,   True = another cam knows them
            }
        """
        with self._lock:
            # 1. Check known cache — was this person recently
            #    recognized as KNOWN on any camera?
            for name, last_seen in list(self._known_cache.items()):
                age = time.time() - last_seen
                if age < self.OBSERVATION_TTL_SEC * 2:
                    # A known person was seen recently — suppress
                    return {
                        "alert"          : False,
                        "reason"         : f"'{name}' recognized on another camera {age:.1f}s ago",
                        "known_on_cam"   : -1,
                        "waiting_seconds": 0.0,
                        "suppress"       : True,
                    }

            # 2. Check if any OTHER camera currently sees a known face
            for cam_id, observations in self._registry.items():
                if cam_id == camera_id:
                    continue   # skip the reporting camera itself
                for obs in observations:
                    if (obs.is_known
                            and obs.confidence >= self.MIN_CONFIDENCE
                            and obs.age_seconds < self.OBSERVATION_TTL_SEC):
                        return {
                            "alert"          : False,
                            "reason"         : (
                                f"Camera {cam_id} recognizes "
                                f"'{obs.name}' (conf {obs.confidence:.0%})"
                            ),
                            "known_on_cam"   : cam_id,
                            "waiting_seconds": 0.0,
                            "suppress"       : True,
                        }

            # 3. Check grace period — has unknown been unknown long enough?
            timer_key = f"unknown_{face_id}_cam{camera_id}"
            if timer_key not in self._unknown_since:
                self._unknown_since[timer_key] = time.time()

            waiting = time.time() - self._unknown_since[timer_key]

            if waiting < self.GRACE_PERIOD_SEC:
                return {
                    "alert"          : False,
                    "reason"         : (
                        f"Grace period — waiting {self.GRACE_PERIOD_SEC - waiting:.1f}s more"
                    ),
                    "known_on_cam"   : -1,
                    "waiting_seconds": waiting,
                    "suppress"       : False,
                }

            # 4. Unknown on all cameras for long enough → ALERT
            return {
                "alert"          : True,
                "reason"         : (
                    f"Unknown for {waiting:.1f}s across all cameras"
                ),
                "known_on_cam"   : -1,
                "waiting_seconds": waiting,
                "suppress"       : False,
            }

    # =========================================================
    #  CONVENIENCE METHODS
    # =========================================================

    def reset_unknown_timer(self, face_id: str, camera_id: int):
        """Call this when an unknown face leaves the frame."""
        key = f"unknown_{face_id}_cam{camera_id}"
        with self._lock:
            self._unknown_since.pop(key, None)

    def clear_known_cache(self, name: str = None):
        """Clear known cache for a name (or all if name is None)."""
        with self._lock:
            if name:
                self._known_cache.pop(name, None)
            else:
                self._known_cache.clear()

    def get_status(self) -> dict:
        """
        Return current coordinator status for debugging/display.
        """
        with self._lock:
            cameras = {}
            for cam_id, obs_list in self._registry.items():
                fresh = [o for o in obs_list
                         if o.age_seconds < self.OBSERVATION_TTL_SEC]
                cameras[cam_id] = [
                    {
                        "name"      : o.name,
                        "is_known"  : o.is_known,
                        "confidence": round(o.confidence, 2),
                        "age"       : round(o.age_seconds, 1),
                    }
                    for o in fresh
                ]

            known_cache = {
                name: round(time.time() - ts, 1)
                for name, ts in self._known_cache.items()
                if time.time() - ts < self.OBSERVATION_TTL_SEC * 2
            }

            return {
                "cameras"     : cameras,
                "known_cache" : known_cache,
                "pending_unknowns": len(self._unknown_since),
            }

    def set_grace_period(self, seconds: float):
        """Update grace period at runtime."""
        self.GRACE_PERIOD_SEC = max(1.0, seconds)
        print(f"[COORDINATOR] Grace period set to {self.GRACE_PERIOD_SEC}s")

    def set_observation_ttl(self, seconds: float):
        """Update how long observations are kept."""
        self.OBSERVATION_TTL_SEC = max(1.0, seconds)
        print(f"[COORDINATOR] Observation TTL set to {self.OBSERVATION_TTL_SEC}s")


# ── Module-level singleton shared across all cameras ──────────
coordinator = CameraCoordinator()