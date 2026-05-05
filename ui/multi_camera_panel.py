# ============================================================
#   FaceSecuritySystem — ui/multi_camera_panel.py
#   Module 7: Multi-Camera Grid View
#   Shows all camera feeds simultaneously in a responsive grid
# ============================================================

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image
import threading
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import CAMERA_WIDTH, CAMERA_HEIGHT, MAX_CAMERAS
from modules.camera_manager  import CameraManager, SingleCamera
from modules.face_detector   import FaceDetector
from modules.face_recognizer import FaceRecognizer
from modules.low_light       import LowLightEnhancer
from modules.camera_coordinator import coordinator
from modules.alert_manager      import alert_manager
from database.db_manager     import db


class MultiCameraPanel(ctk.CTkFrame):
    """
    Displays multiple camera feeds in a responsive grid.
    Each feed runs face detection independently.

    Layout:
        1 camera  → full width
        2 cameras → side by side
        3–4       → 2x2 grid
    """

    TILE_W = 480
    TILE_H = 320

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.manager    = CameraManager()
        self.detector   = FaceDetector()
        self.recognizer = FaceRecognizer()
        self.enhancer   = LowLightEnhancer()

        self.running            = False
        self._update_thread     = None
        self.detection_enabled  = True

        # Per-camera last log throttle
        self.last_logged = {}

        self._build_ui()

    # =========================================================
    #  UI BUILD
    # =========================================================

    def _build_ui(self):
        # ── Top controls ──────────────────────────────────────
        ctrl = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10,
                             border_width=1, border_color="#21262d")
        ctrl.pack(fill="x", pady=(0, 10))

        row = ctk.CTkFrame(ctrl, fg_color="transparent")
        row.pack(padx=16, pady=10, fill="x")

        # Start All
        self.start_btn = ctk.CTkButton(
            row, text="▶  Start All Cameras",
            height=36, width=160,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3fb950", hover_color="#2ea043",
            corner_radius=8, command=self._start_all
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        # Stop All
        self.stop_btn = ctk.CTkButton(
            row, text="⏹  Stop All",
            height=36, width=120,
            font=ctk.CTkFont(size=13),
            fg_color="#f85149", hover_color="#da3633",
            corner_radius=8, command=self._stop_all,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(0, 14))

        # Add Camera
        ctk.CTkButton(
            row, text="➕  Add Camera",
            height=36, width=130,
            font=ctk.CTkFont(size=13),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8, command=self._open_add_camera_dialog
        ).pack(side="left", padx=(0, 10))

        # Detection toggle
        self.detect_switch = ctk.CTkSwitch(
            row, text="Detection",
            font=ctk.CTkFont(size=12), text_color="#8b949e",
            fg_color="#30363d", progress_color="#1f6feb",
            command=lambda: setattr(
                self, "detection_enabled",
                bool(self.detect_switch.get()))
        )
        self.detect_switch.select()
        self.detect_switch.pack(side="left", padx=(10, 0))

        # Status
        self.status_label = ctk.CTkLabel(
            row, text="● All cameras off",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f85149"
        )
        self.status_label.pack(side="right")

        # ── Camera tiles grid ─────────────────────────────────
        self.grid_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0
        )
        self.grid_frame.pack(fill="both", expand=True)

        # Camera tiles dict: {index: tile_widgets}
        self.tiles = {}
        self._rebuild_grid()

        # ── Log strip ─────────────────────────────────────────
        log_strip = ctk.CTkFrame(
            self, fg_color="#161b22", height=44, corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        log_strip.pack(fill="x", pady=(10, 0))
        log_strip.pack_propagate(False)
        self.log_label = ctk.CTkLabel(
            log_strip, text="No entries logged yet.",
            font=ctk.CTkFont(size=12), text_color="#484f58"
        )
        self.log_label.place(relx=0.5, rely=0.5, anchor="center")

    # =========================================================
    #  GRID BUILDER
    # =========================================================

    def _rebuild_grid(self):
        """Destroy and rebuild all camera tiles."""
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.tiles.clear()

        cameras = self.manager.cameras
        if not cameras:
            ctk.CTkLabel(
                self.grid_frame,
                text="📷\n\nNo cameras registered.\nClick '➕ Add Camera' to add one.",
                font=ctk.CTkFont(size=14),
                text_color="#484f58",
                justify="center"
            ).pack(expand=True, pady=80)
            return

        count = len(cameras)
        cols  = 1 if count == 1 else 2

        for i, (idx, cam) in enumerate(cameras.items()):
            row_i = i // cols
            col_i = i  % cols
            tile  = self._make_tile(idx, cam)
            tile.grid(row=row_i, column=col_i,
                      padx=8, pady=8, sticky="nsew")
            self.grid_frame.columnconfigure(col_i, weight=1)
            self.tiles[idx] = tile

    def _make_tile(self, cam_idx: int,
                   cam: SingleCamera) -> ctk.CTkFrame:
        """Create one camera tile widget."""
        tile = ctk.CTkFrame(
            self.grid_frame, fg_color="#161b22",
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )

        # Tile header
        header = ctk.CTkFrame(tile, fg_color="#21262d",
                               corner_radius=0, height=36)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text=f"📷  {cam.label}  —  {cam.location}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e6edf3"
        ).pack(side="left", padx=12)

        # Per-tile start/stop button
        tile_btn = ctk.CTkButton(
            header, text="▶",
            width=36, height=26,
            font=ctk.CTkFont(size=12),
            fg_color="#3fb950", hover_color="#2ea043",
            corner_radius=6,
            command=lambda i=cam_idx, b=None: self._toggle_tile(i)
        )
        tile_btn.pack(side="right", padx=8)

        # Remove button
        ctk.CTkButton(
            header, text="✕",
            width=30, height=26,
            font=ctk.CTkFont(size=12),
            fg_color="#21262d", hover_color="#f85149",
            corner_radius=6,
            command=lambda i=cam_idx: self._remove_camera(i)
        ).pack(side="right", padx=(0, 4))

        # Video canvas
        canvas = ctk.CTkLabel(
            tile,
            text=f"Camera {cam_idx}\nNot started",
            font=ctk.CTkFont(size=13),
            text_color="#484f58",
            fg_color="#0d1117",
            width=self.TILE_W,
            height=self.TILE_H
        )
        canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Tile footer stats
        footer = ctk.CTkFrame(tile, fg_color="#1a1f27",
                               corner_radius=0, height=28)
        footer.pack(fill="x")
        footer.pack_propagate(False)

        fps_lbl = ctk.CTkLabel(
            footer, text="FPS: —",
            font=ctk.CTkFont(size=11), text_color="#484f58"
        )
        fps_lbl.pack(side="left", padx=12)

        status_lbl = ctk.CTkLabel(
            footer, text="● Off",
            font=ctk.CTkFont(size=11), text_color="#f85149"
        )
        status_lbl.pack(side="right", padx=12)

        # Store widget references for updates
        tile._canvas     = canvas
        tile._fps_lbl    = fps_lbl
        tile._status_lbl = status_lbl
        tile._btn        = tile_btn
        tile._cam_idx    = cam_idx

        return tile

    # =========================================================
    #  CAMERA CONTROL
    # =========================================================

    def _start_all(self):
        self.manager.start_all()
        self.running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(
            text=f"● {self.manager.get_connected_count()} camera(s) on",
            text_color="#3fb950"
        )
        self._update_tiles()

        # Update per-tile status
        for idx, tile in self.tiles.items():
            cam = self.manager.cameras.get(idx)
            if cam and cam.connected:
                tile._status_lbl.configure(
                    text="● On", text_color="#3fb950")
                tile._btn.configure(text="⏹",
                                     fg_color="#f85149",
                                     hover_color="#da3633")

    def _stop_all(self):
        self.running = False
        self.manager.stop_all()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(
            text="● All cameras off", text_color="#f85149"
        )
        # Clear all canvases
        for idx, tile in self.tiles.items():
            tile._canvas.configure(
                image=None,
                text=f"Camera {idx}\nStopped",
                text_color="#484f58"
            )
            tile._status_lbl.configure(
                text="● Off", text_color="#f85149")
            tile._fps_lbl.configure(text="FPS: —")
            tile._btn.configure(text="▶",
                                  fg_color="#3fb950",
                                  hover_color="#2ea043")

    def _toggle_tile(self, cam_idx: int):
        """Start or stop a single camera tile."""
        cam  = self.manager.cameras.get(cam_idx)
        tile = self.tiles.get(cam_idx)
        if not cam or not tile:
            return

        if cam.running:
            cam.stop()
            tile._status_lbl.configure(
                text="● Off", text_color="#f85149")
            tile._btn.configure(text="▶",
                                  fg_color="#3fb950",
                                  hover_color="#2ea043")
            tile._canvas.configure(
                image=None,
                text=f"Camera {cam_idx}\nStopped",
                text_color="#484f58"
            )
        else:
            ok = cam.start()
            if ok:
                tile._status_lbl.configure(
                    text="● On", text_color="#3fb950")
                tile._btn.configure(text="⏹",
                                     fg_color="#f85149",
                                     hover_color="#da3633")
                if not self.running:
                    self.running = True
                    self._update_tiles()

    # =========================================================
    #  UPDATE LOOP — pushes frames to all tiles
    # =========================================================

    def _update_tiles(self):
        """Recursively schedule frame updates for all tiles."""
        if not self.running:
            return

        for idx, tile in self.tiles.items():
            cam = self.manager.cameras.get(idx)
            if not cam or not cam.running:
                continue

            ok, frame = cam.read()
            if not ok or frame is None:
                continue

            # Enhance
            frame = self.enhancer.process(frame)

            # Detect faces
            if self.detection_enabled:
                faces = self.detector.detect_faces(frame)
                if faces and self.recognizer.is_trained:
                    rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = self.recognizer.recognize(rgb)
                    for r in results:
                        top, right, bottom, left = r["location"]
                        box   = (left, top, right - left, bottom - top)

                        # Report to coordinator
                        coordinator.report(
                            camera_id    = idx,
                            name         = r["name"],
                            confidence   = r["confidence"],
                            is_known     = r["is_known"],
                            face_quality = r["confidence"]
                        )

                        if r["is_known"]:
                            color = (0, 200, 80)
                            self._log_entry(r, idx)
                        else:
                            # Check coordinator before alerting
                            face_id      = f"unknown_cam{idx}_{top}_{left}"
                            coord_result = coordinator.should_alert(
                                camera_id = idx,
                                face_id   = face_id
                            )
                            if coord_result["alert"]:
                                color = (60, 80, 245)
                                alert_manager.trigger(
                                    alert_type   = "unknown_face",
                                    camera_id    = idx,
                                    camera_label = cam_label,
                                    frame        = frame
                                )
                                self._log_entry(r, idx)
                            elif coord_result["suppress"]:
                                color = (200, 160, 0)  # orange = suppressed
                            else:
                                color = (200, 200, 0)  # yellow = grace period

                        label = f"{r['name']} {r['confidence']:.0%}"
                        frame = self.detector.draw_boxes(
                            frame, [box],
                            labels=[label], colors=[color]
                        )
                elif faces:
                    frame = self.detector.draw_boxes(
                        frame, faces,
                        labels=["Face"] * len(faces),
                        colors=[(200, 200, 0)] * len(faces)
                    )

            # Resize to tile size
            frame_resized = cv2.resize(
                frame, (self.TILE_W, self.TILE_H)
            )
            rgb_frame = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            pil_img   = Image.fromarray(rgb_frame)
            ctk_img   = ctk.CTkImage(
                pil_img, size=(self.TILE_W, self.TILE_H)
            )

            tile._canvas.configure(image=ctk_img, text="")
            tile._canvas.image = ctk_img
            tile._fps_lbl.configure(text=f"FPS: {cam.fps:.0f}")

        # Schedule next update (~30ms = ~33 FPS cap)
        self.after(30, self._update_tiles)

    # =========================================================
    #  LOGGING
    # =========================================================

    def _log_entry(self, result: dict, camera_idx: int):
        key  = f"{result['name']}_{camera_idx}"
        now  = datetime.now()
        last = self.last_logged.get(key)
        if last and (now - last).total_seconds() < 60:
            return
        self.last_logged[key] = now

        cam_label = "Unknown"
        if camera_idx in self.manager.cameras:
            cam_label = self.manager.cameras[camera_idx].label

        db.add_log(
            user_id          = result.get("user_id"),
            name             = result["name"],
            camera_id        = camera_idx,
            camera_label     = cam_label,
            entry_date       = now.strftime("%Y-%m-%d"),
            entry_time       = now.strftime("%H:%M:%S"),
            status           = "known" if result["is_known"] else "unknown",
            confidence_score = result.get("confidence")
        )
        self.log_label.configure(
            text=f"✓  {result['name']}  logged from {cam_label}  at {now.strftime('%H:%M:%S')}",
            text_color="#3fb950"
        )

    # =========================================================
    #  ADD / REMOVE CAMERA DIALOGS
    # =========================================================

    def _open_add_camera_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Camera")
        dialog.geometry("380x320")
        dialog.configure(fg_color="#161b22")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="➕  Add New Camera",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#e6edf3").pack(pady=(24, 16))

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(padx=30, fill="x")

        # Index
        ctk.CTkLabel(form, text="Camera Index (0, 1, 2, 3)",
                     font=ctk.CTkFont(size=12), text_color="#8b949e",
                     anchor="w").pack(fill="x", pady=(0, 4))
        idx_var = ctk.StringVar(value="1")
        ctk.CTkOptionMenu(
            form, variable=idx_var,
            values=["0", "1", "2", "3"],
            fg_color="#21262d", button_color="#30363d",
            text_color="#e6edf3", height=36
        ).pack(fill="x", pady=(0, 12))

        # Label
        ctk.CTkLabel(form, text="Camera Label",
                     font=ctk.CTkFont(size=12), text_color="#8b949e",
                     anchor="w").pack(fill="x", pady=(0, 4))
        label_entry = ctk.CTkEntry(
            form, placeholder_text="e.g. Front Gate",
            height=36, fg_color="#21262d",
            border_color="#30363d", text_color="#e6edf3")
        label_entry.pack(fill="x", pady=(0, 12))

        # Location
        ctk.CTkLabel(form, text="Location",
                     font=ctk.CTkFont(size=12), text_color="#8b949e",
                     anchor="w").pack(fill="x", pady=(0, 4))
        loc_entry = ctk.CTkEntry(
            form, placeholder_text="e.g. Building Entrance",
            height=36, fg_color="#21262d",
            border_color="#30363d", text_color="#e6edf3")
        loc_entry.pack(fill="x", pady=(0, 12))

        msg = ctk.CTkLabel(form, text="",
                            font=ctk.CTkFont(size=12),
                            text_color="#f85149")
        msg.pack()

        def _save():
            idx      = int(idx_var.get())
            label    = label_entry.get().strip() or f"Camera {idx}"
            location = loc_entry.get().strip()   or "Unknown"

            ok = self.manager.add_camera(idx, label, location)
            if ok:
                dialog.destroy()
                self._rebuild_grid()
                self.status_label.configure(
                    text=f"● {len(self.manager.cameras)} camera(s) registered",
                    text_color="#8b949e"
                )
            else:
                msg.configure(
                    text="Camera index already registered or limit reached."
                )

        ctk.CTkButton(
            form, text="Add Camera",
            height=42, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8, command=_save
        ).pack(fill="x", pady=(8, 0))

    def _remove_camera(self, cam_idx: int):
        self.manager.remove_camera(cam_idx)
        self._rebuild_grid()

    # =========================================================
    #  CLEANUP
    # =========================================================

    def destroy(self):
        self.running = False
        self.manager.stop_all()
        super().destroy()