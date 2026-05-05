# ============================================================
#   FaceSecuritySystem — modules/camera_manager.py
#   Module 7: Multi-Camera Manager
#   Handles opening, reading, and managing multiple cameras
# ============================================================

import cv2
import threading
import numpy as np
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import (
    CAMERA_WIDTH, CAMERA_HEIGHT, MAX_CAMERAS
)
from database.db_manager import db


class SingleCamera:
    """
    Represents one physical camera.
    Runs its own capture thread and stores the latest frame.
    """

    def __init__(self, index: int, label: str = None,
                 location: str = None):
        self.index    = index
        self.label    = label    or f"Camera {index}"
        self.location = location or "Unknown"

        self.cap      = None
        self.running  = False
        self._thread  = None
        self._lock    = threading.Lock()

        self.latest_frame  = None   # most recent BGR frame
        self.frame_count   = 0
        self.fps           = 0.0
        self.error         = None
        self.connected     = False

        self._fps_counter  = 0
        self._fps_start    = datetime.now()

    # ── Start / Stop ──────────────────────────────────────────

    def start(self) -> bool:
        """Open the camera and start the capture thread."""
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            self.error     = f"Could not open camera {self.index}"
            self.connected = False
            print(f"[CAM {self.index}] {self.error}")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

        self.running   = True
        self.connected = True
        self.error     = None
        self._thread   = threading.Thread(
            target=self._capture_loop, daemon=True
        )
        self._thread.start()
        print(f"[CAM {self.index}] Started — {self.label}")
        return True

    def stop(self):
        """Stop the capture thread and release the camera."""
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.connected    = False
        self.latest_frame = None
        print(f"[CAM {self.index}] Stopped.")

    # ── Capture loop ──────────────────────────────────────────

    def _capture_loop(self):
        while self.running:
            if not self.cap or not self.cap.isOpened():
                self.error     = "Camera disconnected"
                self.connected = False
                break

            ret, frame = self.cap.read()
            if not ret:
                continue

            with self._lock:
                self.latest_frame = frame
                self.frame_count += 1

            # FPS calculation
            self._fps_counter += 1
            diff = (datetime.now() - self._fps_start).total_seconds()
            if diff >= 1.0:
                self.fps          = self._fps_counter / diff
                self._fps_counter = 0
                self._fps_start   = datetime.now()

    # ── Read ──────────────────────────────────────────────────

    def read(self):
        """
        Get the latest frame safely.
        Returns (True, frame) or (False, None).
        """
        with self._lock:
            if self.latest_frame is not None:
                return True, self.latest_frame.copy()
        return False, None

    @property
    def info(self) -> dict:
        return {
            "index"    : self.index,
            "label"    : self.label,
            "location" : self.location,
            "connected": self.connected,
            "fps"      : round(self.fps, 1),
            "frames"   : self.frame_count,
            "error"    : self.error,
        }


class CameraManager:
    """
    Manages multiple SingleCamera instances.

    Usage:
        manager = CameraManager()
        manager.add_camera(0, "Front Gate")
        manager.add_camera(1, "Back Door")
        manager.start_all()

        frame0 = manager.get_frame(0)
        frame1 = manager.get_frame(1)

        manager.stop_all()
    """

    def __init__(self):
        self.cameras: dict[int, SingleCamera] = {}
        self._load_from_db()

    # ── DB Integration ────────────────────────────────────────

    def _load_from_db(self):
        """Load registered cameras from the database."""
        rows = db.get_active_cameras()
        for row in rows:
            idx      = row["camera_index"]
            label    = row.get("label",    f"Camera {idx}")
            location = row.get("location", "Unknown")
            if idx not in self.cameras:
                self.cameras[idx] = SingleCamera(idx, label, location)
        print(f"[CAM_MGR] Loaded {len(self.cameras)} camera(s) from DB.")

    def refresh_from_db(self):
        """Reload camera list from DB (call after admin changes cameras)."""
        self.stop_all()
        self.cameras.clear()
        self._load_from_db()

    # ── Add / Remove ──────────────────────────────────────────

    def add_camera(self, index: int,
                   label: str    = None,
                   location: str = None,
                   save_to_db: bool = True) -> bool:
        """
        Add a new camera to the manager.
        Optionally saves it to the database.
        """
        if index in self.cameras:
            print(f"[CAM_MGR] Camera {index} already registered.")
            return False

        if len(self.cameras) >= MAX_CAMERAS:
            print(f"[CAM_MGR] Max cameras ({MAX_CAMERAS}) reached.")
            return False

        cam = SingleCamera(index, label, location)
        self.cameras[index] = cam

        if save_to_db:
            db.execute(
                "INSERT IGNORE INTO cameras "
                "(camera_index, label, location) VALUES (%s,%s,%s)",
                (index, label or f"Camera {index}",
                 location or "Unknown")
            )

        print(f"[CAM_MGR] Added camera {index} — {label}")
        return True

    def remove_camera(self, index: int):
        """Stop and remove a camera."""
        if index in self.cameras:
            self.cameras[index].stop()
            del self.cameras[index]
            db.execute(
                "UPDATE cameras SET is_active=0 WHERE camera_index=%s",
                (index,)
            )
            print(f"[CAM_MGR] Removed camera {index}.")

    # ── Start / Stop ──────────────────────────────────────────

    def start_all(self):
        """Start all registered cameras."""
        for cam in self.cameras.values():
            if not cam.running:
                cam.start()

    def stop_all(self):
        """Stop all cameras."""
        for cam in self.cameras.values():
            cam.stop()

    def start_camera(self, index: int) -> bool:
        if index in self.cameras:
            return self.cameras[index].start()
        return False

    def stop_camera(self, index: int):
        if index in self.cameras:
            self.cameras[index].stop()

    # ── Read ──────────────────────────────────────────────────

    def get_frame(self, index: int):
        """
        Get latest frame from a specific camera.
        Returns (True, frame) or (False, None).
        """
        if index in self.cameras:
            return self.cameras[index].read()
        return False, None

    def get_all_frames(self) -> dict:
        """
        Get latest frame from every camera.
        Returns {index: frame} for connected cameras.
        """
        frames = {}
        for idx, cam in self.cameras.items():
            ok, frame = cam.read()
            if ok:
                frames[idx] = frame
        return frames

    # ── Info ──────────────────────────────────────────────────

    def get_info(self) -> list:
        """Return info dict for every camera."""
        return [cam.info for cam in self.cameras.values()]

    def get_connected_count(self) -> int:
        return sum(1 for c in self.cameras.values() if c.connected)

    def is_any_running(self) -> bool:
        return any(c.running for c in self.cameras.values())

    @property
    def indices(self) -> list:
        return list(self.cameras.keys())


# Module-level singleton
camera_manager = CameraManager()