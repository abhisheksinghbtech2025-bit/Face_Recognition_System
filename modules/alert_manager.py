# ============================================================
#   FaceSecuritySystem — modules/alert_manager.py
#   Module 10: Alerts System
# ============================================================

import cv2
import os
import sys
import threading
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import (
    ALERT_SOUND_ENABLED, ALERT_SNAPSHOT_ENABLED,
    ALERT_SOUND_FILE, SNAPSHOTS_DIR
)
from database.db_manager import db


class AlertManager:
    """
    Manages all security alerts.

    Alert Types:
        - unknown_face     : Unrecognized person detected
        - spoofing_attempt : Photo/screen used instead of live face
        - multiple_faces   : Too many faces detected at once
        - low_confidence   : Face matched but confidence too low
        - system_error     : Camera or system failure
    """

    THROTTLE_SECONDS = 30   # same alert won't fire again for 30s

    def __init__(self):
        self._throttle  = {}
        self._callbacks = []
        self._lock      = threading.Lock()
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
        print("[ALERT] AlertManager ready.")

    # =========================================================
    #  MAIN TRIGGER
    # =========================================================

    def trigger(self, alert_type: str, camera_id: int,
                camera_label: str, frame: np.ndarray = None,
                notes: str = None) -> dict:
        """
        Fire a security alert.
        Returns dict with fired, alert_id, snapshot_path, reason.
        """
        now          = datetime.now()
        throttle_key = f"{alert_type}_{camera_id}"

        # Throttle — avoid duplicate alerts
        with self._lock:
            last = self._throttle.get(throttle_key)
            if last and (now - last).total_seconds() < self.THROTTLE_SECONDS:
                return {"fired": False, "alert_id": None,
                        "snapshot_path": None, "reason": "Throttled"}
            self._throttle[throttle_key] = now

        # Save snapshot image
        snapshot_path = None
        if ALERT_SNAPSHOT_ENABLED and frame is not None:
            snapshot_path = self._save_snapshot(
                frame, alert_type, camera_id, now)

        # Save to database
        alert_id = db.add_alert(
            alert_type    = alert_type,
            camera_id     = camera_id,
            camera_label  = camera_label,
            snapshot_path = snapshot_path,
            alert_date    = now.strftime("%Y-%m-%d"),
            alert_time    = now.strftime("%H:%M:%S")
        )

        # Play sound in background
        if ALERT_SOUND_ENABLED:
            threading.Thread(
                target=self._play_sound, daemon=True).start()

        # Build alert data dict
        alert_data = {
            "alert_id"     : alert_id,
            "alert_type"   : alert_type,
            "camera_id"    : camera_id,
            "camera_label" : camera_label,
            "snapshot_path": snapshot_path,
            "timestamp"    : now.strftime("%H:%M:%S"),
            "date"         : now.strftime("%Y-%m-%d"),
            "notes"        : notes,
        }

        # Notify UI callbacks
        self._fire_callbacks(alert_data)

        print(f"[ALERT] ⚠  {alert_type.upper()} | "
              f"Camera {camera_id} | {now.strftime('%H:%M:%S')}")

        return {"fired": True, "alert_id": alert_id,
                "snapshot_path": snapshot_path, "reason": "OK"}

    # =========================================================
    #  SNAPSHOT HELPERS
    # =========================================================

    def _save_snapshot(self, frame: np.ndarray, alert_type: str,
                        camera_id: int, timestamp: datetime):
        """Save annotated alert frame as JPEG."""
        try:
            ts       = timestamp.strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{alert_type}_cam{camera_id}_{ts}.jpg"
            path     = os.path.join(SNAPSHOTS_DIR, filename)
            annotated = self._annotate_snapshot(
                frame.copy(), alert_type, camera_id, timestamp)
            cv2.imwrite(path, annotated)
            return path
        except Exception as e:
            print(f"[ALERT] Snapshot save failed: {e}")
            return None

    @staticmethod
    def _annotate_snapshot(frame: np.ndarray, alert_type: str,
                            camera_id: int, timestamp: datetime):
        """Draw text overlay on snapshot frame."""
        h, w = frame.shape[:2]
        cv2.rectangle(frame, (0, 0), (w, 50), (20, 20, 20), -1)
        cv2.putText(frame,
                    f"ALERT: {alert_type.replace('_',' ').upper()}",
                    (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 60, 245), 2)
        cv2.putText(frame,
                    timestamp.strftime("%Y-%m-%d  %H:%M:%S"),
                    (w - 260, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (150, 150, 150), 1)
        cv2.putText(frame, f"Camera {camera_id}",
                    (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (150, 150, 150), 1)
        return frame

    # =========================================================
    #  SOUND
    # =========================================================

    def _play_sound(self):
        """Play alert beep — tries WAV file then system beep."""
        try:
            if os.path.exists(ALERT_SOUND_FILE):
                try:
                    from playsound import playsound
                    playsound(ALERT_SOUND_FILE, block=False)
                    return
                except Exception:
                    pass
            try:
                import winsound
                winsound.Beep(1000, 400)
                return
            except Exception:
                pass
            print("\a")   # terminal bell fallback
        except Exception as e:
            print(f"[ALERT] Sound error: {e}")

    # =========================================================
    #  CALLBACKS (for real-time UI updates)
    # =========================================================

    def add_callback(self, fn):
        """Register a function to call whenever an alert fires."""
        self._callbacks.append(fn)

    def remove_callback(self, fn):
        if fn in self._callbacks:
            self._callbacks.remove(fn)

    def _fire_callbacks(self, alert_data: dict):
        for fn in self._callbacks:
            try:
                fn(alert_data)
            except Exception as e:
                print(f"[ALERT] Callback error: {e}")

    # =========================================================
    #  QUERY METHODS
    # =========================================================

    def get_unreviewed(self) -> list:
        """Return all unreviewed alerts newest first."""
        return db.get_unreviewed_alerts()

    def get_all_alerts(self, date_from: str = None,
                        date_to: str = None,
                        alert_type: str = None,
                        limit: int = None) -> list:
        """Flexible alert query with filters."""
        query  = "SELECT * FROM alerts WHERE 1=1"
        params = []
        if date_from:
            query += " AND alert_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND alert_date <= %s"
            params.append(date_to)
        if alert_type:
            query += " AND alert_type = %s"
            params.append(alert_type)
        query += " ORDER BY created_at DESC"
        if limit:
            query += f" LIMIT {int(limit)}"
        return db.fetch_all(query, tuple(params))

    def mark_reviewed(self, alert_id: int,
                       reviewed_by: int = None) -> bool:
        return db.execute(
            "UPDATE alerts SET is_reviewed=1, reviewed_by=%s "
            "WHERE alert_id=%s",
            (reviewed_by, alert_id)
        )

    def mark_all_reviewed(self) -> bool:
        return db.execute(
            "UPDATE alerts SET is_reviewed=1 WHERE is_reviewed=0"
        )

    def get_stats(self) -> dict:
        """Return summary statistics for all alerts."""
        all_alerts   = self.get_all_alerts()
        unreviewed   = [a for a in all_alerts if not a.get("is_reviewed")]
        today        = datetime.now().strftime("%Y-%m-%d")
        today_alerts = [a for a in all_alerts
                        if str(a.get("alert_date","")) == today]
        by_type = {}
        for a in all_alerts:
            t = a.get("alert_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total"     : len(all_alerts),
            "unreviewed": len(unreviewed),
            "today"     : len(today_alerts),
            "by_type"   : by_type,
        }


# Module-level singleton
alert_manager = AlertManager()