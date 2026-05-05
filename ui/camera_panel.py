# ============================================================
#   FaceSecuritySystem — ui/camera_panel.py
#   Module 4 + 5: Live camera with face detection,
#                 recognition AND liveness checking
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
from config.config import (
    CAMERA_WIDTH, CAMERA_HEIGHT, DEFAULT_CAMERA_INDEX,
    BLINKS_REQUIRED
)
from modules.face_detector   import FaceDetector
from modules.face_recognizer import FaceRecognizer
from modules.liveness        import LivenessDetector
from modules.low_light       import LowLightEnhancer
from modules.alert_manager   import alert_manager
from modules.camera_coordinator import coordinator
from database.db_manager     import db


class CameraPanel(ctk.CTkFrame):

    COLOR_KNOWN   = (0, 200, 80)
    COLOR_UNKNOWN = (60, 80, 245)
    COLOR_PENDING = (200, 200, 0)

    def __init__(self, parent,
                 camera_index: int = DEFAULT_CAMERA_INDEX, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.camera_index       = camera_index
        self.cap                = None
        self.running            = False
        self._thread            = None

        self.detector           = FaceDetector()
        self.recognizer         = FaceRecognizer()
        self.enhancer           = LowLightEnhancer()

        self.detection_enabled  = True
        self.liveness_enabled   = True
        self.low_light_enabled  = True

        self.liveness_sessions  = {}
        self.confirmed_live     = {}
        self.last_logged        = {}
        self.coordinator_enabled = True
        self._unknown_face_ids   = {}   # track unknown faces per frame

        self._build_ui()

    # =========================================================
    #  UI BUILD
    # =========================================================

    def _build_ui(self):
        # Controls bar
        ctrl = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10,
                             border_width=1, border_color="#21262d")
        ctrl.pack(fill="x", pady=(0, 10))
        row = ctk.CTkFrame(ctrl, fg_color="transparent")
        row.pack(padx=16, pady=10, fill="x")

        ctk.CTkLabel(row, text="Camera:", font=ctk.CTkFont(size=13),
                     text_color="#8b949e").pack(side="left", padx=(0, 6))
        self.cam_var = ctk.StringVar(value=str(self.camera_index))
        ctk.CTkOptionMenu(row, variable=self.cam_var,
                           values=["0","1","2","3"],
                           width=80, height=32,
                           fg_color="#21262d", button_color="#30363d",
                           text_color="#c9d1d9",
                           font=ctk.CTkFont(size=12)
                           ).pack(side="left", padx=(0,14))

        self.toggle_btn = ctk.CTkButton(
            row, text="▶  Start Camera", height=34, width=140,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3fb950", hover_color="#2ea043",
            corner_radius=8, command=self._toggle_camera)
        self.toggle_btn.pack(side="left", padx=(0,10))

        ctk.CTkButton(row, text="🧠  Train Model", height=34, width=140,
                       font=ctk.CTkFont(size=13),
                       fg_color="#1f6feb", hover_color="#388bfd",
                       corner_radius=8,
                       command=self._train_model
                       ).pack(side="left", padx=(0,14))

        self.detect_switch = ctk.CTkSwitch(
            row, text="Detection", font=ctk.CTkFont(size=12),
            text_color="#8b949e", fg_color="#30363d",
            progress_color="#1f6feb",
            command=lambda: setattr(
                self, "detection_enabled",
                bool(self.detect_switch.get())))
        self.detect_switch.select()
        self.detect_switch.pack(side="left", padx=(0,10))

        self.liveness_switch = ctk.CTkSwitch(
            row, text="Liveness", font=ctk.CTkFont(size=12),
            text_color="#8b949e", fg_color="#30363d",
            progress_color="#d29922",
            command=lambda: setattr(
                self, "liveness_enabled",
                bool(self.liveness_switch.get())))
        self.liveness_switch.select()
        self.liveness_switch.pack(side="left")

        self.ll_switch = ctk.CTkSwitch(
            row, text="Low-Light", font=ctk.CTkFont(size=12),
            text_color="#8b949e", fg_color="#30363d",
            progress_color="#3fb950",
            command=lambda: setattr(
                self, "low_light_enabled",
                bool(self.ll_switch.get())))
        self.ll_switch.select()
        self.ll_switch.pack(side="left", padx=(10,0))

        self.coord_switch = ctk.CTkSwitch(
            row, text="Coordinator", font=ctk.CTkFont(size=12),
            text_color="#8b949e", fg_color="#30363d",
            progress_color="#a371f7",
            command=lambda: setattr(
                self, "coordinator_enabled",
                bool(self.coord_switch.get())))
        self.coord_switch.select()
        self.coord_switch.pack(side="left", padx=(10,0))

        self.status_label = ctk.CTkLabel(
            row, text="● Camera Off",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f85149")
        self.status_label.pack(side="right")

        # Main area
        main_row = ctk.CTkFrame(self, fg_color="transparent")
        main_row.pack(fill="both", expand=True)

        self.canvas = ctk.CTkLabel(
            main_row,
            text="📷\n\nCamera not started\nClick 'Start Camera' to begin",
            font=ctk.CTkFont(size=14), text_color="#484f58",
            fg_color="#161b22", corner_radius=10)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Right sidebar
        right = ctk.CTkFrame(main_row, fg_color="#161b22", width=230,
                              corner_radius=10,
                              border_width=1, border_color="#21262d")
        right.pack(side="left", fill="y", padx=(10,0))
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="DETECTIONS",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#484f58").pack(
            pady=(14,4), padx=14, anchor="w")

        self.detect_list = ctk.CTkScrollableFrame(
            right, fg_color="transparent", corner_radius=0)
        self.detect_list.pack(fill="both", expand=True, padx=8, pady=(0,8))

        stats = ctk.CTkFrame(right, fg_color="#21262d", corner_radius=8)
        stats.pack(fill="x", padx=8, pady=(0,8))
        self.faces_label = ctk.CTkLabel(
            stats, text="Faces: 0",
            font=ctk.CTkFont(size=12), text_color="#8b949e")
        self.faces_label.pack(pady=(6,2))
        self.fps_label = ctk.CTkLabel(
            stats, text="FPS: —",
            font=ctk.CTkFont(size=12), text_color="#484f58")
        self.fps_label.pack(pady=(0,6))
        self.brightness_label = ctk.CTkLabel(
            stats, text="Brightness: —",
            font=ctk.CTkFont(size=12), text_color="#484f58")
        self.brightness_label.pack(pady=(0,6))

        self.coord_label = ctk.CTkLabel(
            stats, text="Coord: Active",
            font=ctk.CTkFont(size=12), text_color="#a371f7")
        self.coord_label.pack(pady=(0,6))

        # Liveness bar
        lv_bar = ctk.CTkFrame(right, fg_color="#1a1f27", corner_radius=8,
                               border_width=1, border_color="#30363d")
        lv_bar.pack(fill="x", padx=8, pady=(0,10))
        ctk.CTkLabel(lv_bar, text="LIVENESS",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#484f58").pack(
            anchor="w", padx=10, pady=(8,2))
        self.liveness_msg = ctk.CTkLabel(
            lv_bar, text="Not started",
            font=ctk.CTkFont(size=11), text_color="#8b949e",
            wraplength=190)
        self.liveness_msg.pack(anchor="w", padx=10, pady=(0,4))
        self.liveness_progress = ctk.CTkProgressBar(
            lv_bar, height=6,
            fg_color="#21262d", progress_color="#d29922")
        self.liveness_progress.set(0)
        self.liveness_progress.pack(fill="x", padx=10, pady=(0,10))

        # Log strip
        log_strip = ctk.CTkFrame(self, fg_color="#161b22", height=44,
                                  corner_radius=10,
                                  border_width=1, border_color="#21262d")
        log_strip.pack(fill="x", pady=(10,0))
        log_strip.pack_propagate(False)
        self.log_label = ctk.CTkLabel(
            log_strip, text="No entries logged yet.",
            font=ctk.CTkFont(size=12), text_color="#484f58")
        self.log_label.place(relx=0.5, rely=0.5, anchor="center")

    # =========================================================
    #  CAMERA CONTROL
    # =========================================================

    def _toggle_camera(self):
        if self.running: self._stop_camera()
        else:            self._start_camera()

    def _start_camera(self):
        self.cap = cv2.VideoCapture(int(self.cam_var.get()))
        if not self.cap.isOpened():
            self.status_label.configure(
                text="● Camera Error", text_color="#f85149")
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.running = True
        self.toggle_btn.configure(
            text="⏹  Stop Camera",
            fg_color="#f85149", hover_color="#da3633")
        self.status_label.configure(
            text="● Camera On", text_color="#3fb950")
        self._thread = threading.Thread(
            target=self._capture_loop, daemon=True)
        self._thread.start()

    def _stop_camera(self):
        self.running = False
        if self.cap: self.cap.release(); self.cap = None
        self.toggle_btn.configure(
            text="▶  Start Camera",
            fg_color="#3fb950", hover_color="#2ea043")
        self.status_label.configure(
            text="● Camera Off", text_color="#f85149")
        self.canvas.configure(
            image=None,
            text="📷\n\nCamera stopped.",
            text_color="#484f58")

    # =========================================================
    #  CAPTURE LOOP
    # =========================================================

    def _capture_loop(self):
        fps_count = 0
        fps_start = datetime.now()

        while self.running:
            if not self.cap or not self.cap.isOpened(): break
            ret, frame = self.cap.read()
            if not ret: continue

            # Low-light enhancement
            if self.low_light_enabled:
                frame = self.enhancer.process(frame)
            brightness = round(self.enhancer.get_brightness(frame), 1)
            self.after(0, lambda b=brightness:
                       self.brightness_label.configure(
                           text=f"Brightness: {b:.0f}",
                           text_color=(
                               "#f85149" if b < 40 else
                               "#d29922" if b < 80 else
                               "#3fb950"
                           )))

            results  = []
            faces_xy = []

            if self.detection_enabled:
                faces_xy = self.detector.detect_faces(frame)

                if faces_xy and self.recognizer.is_trained:
                    rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = self.recognizer.recognize(rgb)

                    for r in results:
                        top, right, bottom, left = r["location"]
                        box   = (left, top, right-left, bottom-top)
                        color = self.COLOR_PENDING

                        # ── Report to coordinator ─────────────
                        if self.coordinator_enabled:
                            coordinator.report(
                                camera_id    = self.camera_index,
                                name         = r["name"],
                                confidence   = r["confidence"],
                                is_known     = r["is_known"],
                                face_quality = r["confidence"]
                            )

                        if self.liveness_enabled:
                            lv = self._run_liveness(frame, r["name"], box)
                            r["liveness"] = lv
                            live_ok = lv["is_live"]
                        else:
                            live_ok = True

                        if r["is_known"]:
                            # Known person ✅
                            color = self.COLOR_KNOWN if live_ok else self.COLOR_PENDING
                            if live_ok:
                                self._log_entry(r)
                        else:
                            # Unknown — check coordinator before alerting
                            face_id = f"unknown_cam{self.camera_index}_{top}_{left}"
                            if self.coordinator_enabled:
                                coord_result = coordinator.should_alert(
                                    camera_id = self.camera_index,
                                    face_id   = face_id
                                )
                                r["coord"] = coord_result
                                if coord_result["alert"]:
                                    # Truly unknown — alert!
                                    color = self.COLOR_UNKNOWN
                                    self._log_entry(r)
                                    self._trigger_alert(r, frame)
                                elif coord_result["suppress"]:
                                    # Another camera knows this person
                                    color = (200, 160, 0)  # orange = suppressed
                                    r["suppressed"] = True
                                else:
                                    # Still in grace period
                                    color = self.COLOR_PENDING
                            else:
                                # Coordinator off — alert immediately
                                color = self.COLOR_UNKNOWN
                                self._log_entry(r)
                                self._trigger_alert(r, frame)

                        label = f"{r['name']}  {r['confidence']:.0%}"
                        frame = self.detector.draw_boxes(
                            frame, [box], labels=[label], colors=[color])

                elif faces_xy:
                    frame = self.detector.draw_boxes(
                        frame, faces_xy,
                        labels=["Face"]*len(faces_xy),
                        colors=[self.COLOR_PENDING]*len(faces_xy))

            # FPS
            fps_count += 1
            diff = (datetime.now() - fps_start).total_seconds()
            if diff >= 1.0:
                fps = fps_count / diff
                fps_count = 0; fps_start = datetime.now()
                self.after(0, lambda f=fps:
                           self.fps_label.configure(text=f"FPS: {f:.0f}"))

            rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)
            ctk_img = ctk.CTkImage(pil_img, size=(pil_img.width, pil_img.height))
            fc      = len(results) if results else len(faces_xy)

            self.after(0, lambda img=ctk_img, fc=fc,
                       res=list(results): self._update_ui(img, fc, res))

    # =========================================================
    #  LIVENESS SESSION
    # =========================================================

    def _run_liveness(self, frame, name, face_box):
        confirmed_at = self.confirmed_live.get(name)
        if confirmed_at:
            age = (datetime.now() - confirmed_at).total_seconds()
            if age < 300:
                return {"is_live": True,
                        "message": f"✅  Live (confirmed {int(age)}s ago)",
                        "progress": 1.0, "blinks": 0,
                        "blinks_required": BLINKS_REQUIRED,
                        "movement": True, "ear": 0.0,
                        "timed_out": False, "elapsed": 0.0}
            else:
                del self.confirmed_live[name]

        if name not in self.liveness_sessions:
            self.liveness_sessions[name] = LivenessDetector()

        session = self.liveness_sessions[name]
        if session.timed_out:
            self.liveness_sessions[name] = LivenessDetector()
            session = self.liveness_sessions[name]

        result = session.check(frame, face_box)
        if result["is_live"]:
            self.confirmed_live[name] = datetime.now()
            del self.liveness_sessions[name]
        return result

    # =========================================================
    #  UI UPDATE
    # =========================================================

    def _update_ui(self, ctk_image, face_count, results):
        if not self.running: return
        self.canvas.configure(image=ctk_image, text="")
        self.canvas.image = ctk_image
        self.faces_label.configure(text=f"Faces: {face_count}")
        # Update coordinator status
        if self.coordinator_enabled:
            status = coordinator.get_status()
            known_count = len(status.get("known_cache", {}))
            self.coord_label.configure(
                text=f"Coord: {known_count} known cached",
                text_color="#a371f7"
            )
        else:
            self.coord_label.configure(
                text="Coord: Off", text_color="#484f58")

        for w in self.detect_list.winfo_children(): w.destroy()

        if not results:
            ctk.CTkLabel(self.detect_list, text="No faces detected",
                         font=ctk.CTkFont(size=11),
                         text_color="#484f58").pack(pady=8)
            self.liveness_msg.configure(text="No face")
            self.liveness_progress.set(0)
            return

        for r in results:
            is_live      = r.get("liveness", {}).get("is_live", True)
            is_suppressed= r.get("suppressed", False)
            coord        = r.get("coord", {})

            if r["is_known"] and is_live:
                name_color = "#3fb950"   # green  = known + live
            elif r["is_known"]:
                name_color = "#d29922"   # yellow = known + checking liveness
            elif is_suppressed:
                name_color = "#d29922"   # orange = unknown but suppressed
            else:
                name_color = "#f85149"   # red    = truly unknown

            card = ctk.CTkFrame(self.detect_list,
                                 fg_color="#21262d", corner_radius=6)
            card.pack(fill="x", pady=3)
            ctk.CTkLabel(card, text=r["name"],
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=name_color,
                         anchor="w").pack(fill="x", padx=10, pady=(6,0))
            ctk.CTkLabel(card, text=f"Conf: {r['confidence']:.0%}",
                         font=ctk.CTkFont(size=11), text_color="#8b949e",
                         anchor="w").pack(fill="x", padx=10)
            live_text  = "✅ Live" if is_live else "👁 Checking..."
            live_color = "#3fb950" if is_live else "#d29922"
            ctk.CTkLabel(card, text=live_text,
                         font=ctk.CTkFont(size=11), text_color=live_color,
                         anchor="w").pack(fill="x", padx=10)

            # Coordinator status line
            if not r["is_known"]:
                if is_suppressed:
                    coord_text  = "🛡 Suppressed (known elsewhere)"
                    coord_color = "#d29922"
                elif coord.get("alert"):
                    coord_text  = "⚠ Alert fired!"
                    coord_color = "#f85149"
                else:
                    wait = coord.get("waiting_seconds", 0)
                    coord_text  = f"⏳ Grace: {wait:.1f}s"
                    coord_color = "#484f58"
                ctk.CTkLabel(card, text=coord_text,
                             font=ctk.CTkFont(size=10),
                             text_color=coord_color,
                             anchor="w").pack(fill="x", padx=10, pady=(0,6))
            else:
                ctk.CTkLabel(card, text="",
                             font=ctk.CTkFont(size=10)).pack(pady=(0,4))

        lv = results[0].get("liveness")
        if lv:
            msg_color = "#3fb950" if lv["is_live"] else "#d29922"
            self.liveness_msg.configure(
                text=lv["message"], text_color=msg_color)
            self.liveness_progress.set(lv["progress"])
            self.liveness_progress.configure(
                progress_color="#3fb950" if lv["is_live"] else "#d29922")

    # =========================================================
    #  LOGGING
    # =========================================================

    def _log_entry(self, result):
        name = result["name"]
        now  = datetime.now()
        last = self.last_logged.get(name)
        if last and (now - last).total_seconds() < 60: return
        self.last_logged[name] = now
        db.add_log(
            user_id=result.get("user_id"), name=name,
            camera_id=self.camera_index,
            camera_label=f"Camera {self.camera_index}",
            entry_date=now.strftime("%Y-%m-%d"),
            entry_time=now.strftime("%H:%M:%S"),
            status="known" if result["is_known"] else "unknown",
            confidence_score=result.get("confidence"))
        self.after(0, lambda n=name, t=now.strftime("%H:%M:%S"):
                   self.log_label.configure(
                       text=f"✓  Logged: {n}  at {t}",
                       text_color="#3fb950"))

    # =========================================================
    #  TRAINING
    # =========================================================

    def _train_model(self):
        self.status_label.configure(
            text="⏳ Training...", text_color="#d29922")
        threading.Thread(
            target=lambda: self.after(
                0, lambda s=self.recognizer.train():
                self._on_train_done(s)),
            daemon=True).start()

    def _on_train_done(self, stats):
        trained = stats.get("trained", 0)
        self.status_label.configure(
            text=f"✓ Trained {trained} face(s)" if trained > 0
                 else "✘ No faces trained",
            text_color="#3fb950" if trained > 0 else "#f85149")
        d = ctk.CTkToplevel(self)
        d.title("Training Complete")
        d.geometry("320x210")
        d.configure(fg_color="#161b22")
        d.grab_set()
        ctk.CTkLabel(d, text="🧠  Training Complete",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#e6edf3").pack(pady=(24,8))
        ctk.CTkLabel(d,
                     text=f"✅  {stats.get('trained',0)} face(s) encoded\n"
                          f"❌  {stats.get('failed',0)} failed\n"
                          f"📁  {stats.get('total_images',0)} images",
                     font=ctk.CTkFont(size=13),
                     text_color="#8b949e",
                     justify="left").pack(pady=8)
        ctk.CTkButton(d, text="OK", width=100, height=36,
                      fg_color="#1f6feb", corner_radius=8,
                      command=d.destroy).pack(pady=12)

    def _trigger_alert(self, result: dict, frame=None):
        """Fire an alert for an unknown face."""
        alert_manager.trigger(
            alert_type   = "unknown_face",
            camera_id    = self.camera_index,
            camera_label = f"Camera {self.camera_index}",
            frame        = frame
        )

    def destroy(self):
        self._stop_camera()
        super().destroy()