# ============================================================
#   FaceSecuritySystem — ui/dataset_panel.py
#   Module 8: Full Dataset Management Panel
#   Add users, upload images, capture from camera,
#   view image gallery, delete, quality check, train model
# ============================================================

import customtkinter as ctk
import cv2
import threading
import os
import sys
from PIL import Image
from datetime import datetime
from tkinter import filedialog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import DEFAULT_CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT
from modules.dataset_manager import DatasetManager
from modules.face_recognizer import FaceRecognizer
from database.db_manager     import db


class DatasetPanel(ctk.CTkFrame):
    """
    Full Dataset Management Panel.

    Features:
      - View all registered users with image counts
      - Add new user with form
      - Upload photos from file browser
      - Capture photos directly from webcam
      - View image gallery per user
      - Delete individual images or all user images
      - Image quality checker (brightness, sharpness, face detected)
      - Train model button
      - Dataset statistics bar
    """

    def __init__(self, parent, is_admin: bool = True, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.is_admin = is_admin
        self.dm       = DatasetManager()
        self.recognizer = FaceRecognizer()

        self.selected_user = None   # currently selected user dict
        self.cap           = None   # webcam capture for photo taking
        self.capturing     = False

        self._build_ui()
        self._load_users()

    # =========================================================
    #  UI BUILD
    # =========================================================

    def _build_ui(self):
        # ── Stats bar ─────────────────────────────────────────
        self.stats_bar = ctk.CTkFrame(
            self, fg_color="#161b22", height=52,
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        self.stats_bar.pack(fill="x", pady=(0, 10))
        self.stats_bar.pack_propagate(False)

        stats_inner = ctk.CTkFrame(self.stats_bar, fg_color="transparent")
        stats_inner.place(relx=0.5, rely=0.5, anchor="center")

        self.stat_users  = self._stat_chip(stats_inner, "👥 Users",  "0", "#1f6feb")
        self.stat_images = self._stat_chip(stats_inner, "🖼 Images", "0", "#3fb950")
        self.stat_status = self._stat_chip(stats_inner, "🧠 Model",  "Not Trained", "#d29922")

        # ── Main layout: left list + right detail ─────────────
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True)

        # Left: user list
        self.left = ctk.CTkFrame(
            main, fg_color="#161b22", width=260,
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        self.left.pack(side="left", fill="y", padx=(0, 10))
        self.left.pack_propagate(False)

        # Left header
        left_hdr = ctk.CTkFrame(self.left, fg_color="#21262d",
                                  corner_radius=0, height=44)
        left_hdr.pack(fill="x")
        left_hdr.pack_propagate(False)

        ctk.CTkLabel(left_hdr, text="Registered Users",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#e6edf3").pack(
            side="left", padx=14, pady=10)

        if self.is_admin:
            ctk.CTkButton(
                left_hdr, text="➕",
                width=34, height=28,
                font=ctk.CTkFont(size=14),
                fg_color="#1f6feb", hover_color="#388bfd",
                corner_radius=6,
                command=self._open_add_user_dialog
            ).pack(side="right", padx=8)

        # Search bar
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *a: self._filter_users())
        search = ctk.CTkEntry(
            self.left,
            placeholder_text="🔍  Search users...",
            height=34,
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3",
            textvariable=self.search_var
        )
        search.pack(fill="x", padx=10, pady=8)

        # User list scroll
        self.user_list = ctk.CTkScrollableFrame(
            self.left, fg_color="transparent", corner_radius=0
        )
        self.user_list.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Right: detail panel
        self.right = ctk.CTkFrame(
            main, fg_color="#161b22",
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        self.right.pack(side="left", fill="both", expand=True)

        self._show_placeholder()

    def _stat_chip(self, parent, label, value, color):
        frame = ctk.CTkFrame(parent, fg_color="#21262d",
                              corner_radius=8)
        frame.pack(side="left", padx=8)
        ctk.CTkLabel(frame, text=label,
                     font=ctk.CTkFont(size=11),
                     text_color="#484f58").pack(
            side="left", padx=(10, 4), pady=8)
        lbl = ctk.CTkLabel(frame, text=value,
                            font=ctk.CTkFont(size=13, weight="bold"),
                            text_color=color)
        lbl.pack(side="left", padx=(0, 10), pady=8)
        return lbl

    def _show_placeholder(self):
        for w in self.right.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.right,
            text="👈\n\nSelect a user from the list\nto manage their face images.",
            font=ctk.CTkFont(size=14),
            text_color="#484f58",
            justify="center"
        ).place(relx=0.5, rely=0.5, anchor="center")

    # =========================================================
    #  USER LIST
    # =========================================================

    def _load_users(self):
        self._all_users = self.dm.get_all_users_with_images()
        self._update_stats()
        self._render_user_list(self._all_users)

    def _filter_users(self):
        query = self.search_var.get().strip().lower()
        if not query:
            self._render_user_list(self._all_users)
        else:
            filtered = [u for u in self._all_users
                        if query in u["full_name"].lower()
                        or query in (u.get("employee_id") or "").lower()
                        or query in (u.get("department") or "").lower()]
            self._render_user_list(filtered)

    def _render_user_list(self, users: list):
        for w in self.user_list.winfo_children():
            w.destroy()

        if not users:
            ctk.CTkLabel(
                self.user_list,
                text="No users found.",
                font=ctk.CTkFont(size=12),
                text_color="#484f58"
            ).pack(pady=20)
            return

        for user in users:
            self._make_user_row(user)

    def _make_user_row(self, user: dict):
        is_selected = (self.selected_user and
                       self.selected_user["user_id"] == user["user_id"])

        row_bg = "#1f6feb" if is_selected else "#21262d"

        row = ctk.CTkFrame(
            self.user_list, fg_color=row_bg,
            corner_radius=8, height=62
        )
        row.pack(fill="x", pady=3)
        row.pack_propagate(False)

        # Avatar
        av = ctk.CTkFrame(row, fg_color="#161b22" if is_selected else "#30363d",
                           width=36, height=36, corner_radius=18)
        av.place(x=10, rely=0.5, anchor="w")
        av.pack_propagate(False)
        ctk.CTkLabel(av,
                     text=user["full_name"][0].upper(),
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="white").place(
            relx=0.5, rely=0.5, anchor="center")

        # Name
        ctk.CTkLabel(row,
                     text=user["full_name"],
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="white" if is_selected else "#e6edf3",
                     anchor="w").place(x=56, y=10)

        # Image count
        img_color = "#3fb950" if user["image_count"] > 0 else "#f85149"
        ctk.CTkLabel(row,
                     text=f"🖼 {user['image_count']} image(s)",
                     font=ctk.CTkFont(size=11),
                     text_color=img_color if not is_selected else "white",
                     anchor="w").place(x=56, y=34)

        # Click binding
        row.bind("<Button-1>",
                 lambda e, u=user: self._select_user(u))
        for child in row.winfo_children():
            child.bind("<Button-1>",
                       lambda e, u=user: self._select_user(u))

    def _select_user(self, user: dict):
        self.selected_user = user
        # Refresh list to show selection highlight
        self._filter_users()
        # Show detail panel
        self._show_user_detail(user)

    def _update_stats(self):
        stats = self.dm.get_stats()
        self.stat_users.configure(text=str(stats["users"]))
        self.stat_images.configure(text=str(stats["images"]))
        if stats["trained"]:
            self.stat_status.configure(
                text="Trained ✓", text_color="#3fb950")
        else:
            self.stat_status.configure(
                text="Not Trained", text_color="#d29922")

    # =========================================================
    #  USER DETAIL PANEL
    # =========================================================

    def _show_user_detail(self, user: dict):
        for w in self.right.winfo_children():
            w.destroy()

        scroll = ctk.CTkScrollableFrame(
            self.right, fg_color="transparent"
        )
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # ── User info header ──────────────────────────────────
        info_card = ctk.CTkFrame(scroll, fg_color="#21262d",
                                  corner_radius=10)
        info_card.pack(fill="x", pady=(0, 16))

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(padx=16, pady=14, fill="x")

        # Big avatar
        av = ctk.CTkFrame(info_inner, fg_color="#1f6feb",
                           width=56, height=56, corner_radius=28)
        av.pack(side="left", padx=(0, 14))
        av.pack_propagate(False)
        ctk.CTkLabel(av, text=user["full_name"][0].upper(),
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="white").place(
            relx=0.5, rely=0.5, anchor="center")

        details = ctk.CTkFrame(info_inner, fg_color="transparent")
        details.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(details, text=user["full_name"],
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#e6edf3", anchor="w").pack(fill="x")
        ctk.CTkLabel(details,
                     text=f"{user.get('role','').title()}  •  "
                          f"{user.get('department','—')}  •  "
                          f"ID: {user.get('employee_id','—')}",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e", anchor="w").pack(fill="x")
        status_color = "#3fb950" if user.get("status") == "active" else "#f85149"
        ctk.CTkLabel(details,
                     text=f"● {user.get('status','').title()}  •  "
                          f"🖼 {user['image_count']} image(s)",
                     font=ctk.CTkFont(size=12),
                     text_color=status_color, anchor="w").pack(fill="x")

        # ── Action buttons ────────────────────────────────────
        if self.is_admin:
            btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
            btn_row.pack(fill="x", pady=(0, 16))

            ctk.CTkButton(
                btn_row, text="📁  Upload Photo",
                height=38, font=ctk.CTkFont(size=13),
                fg_color="#1f6feb", hover_color="#388bfd",
                corner_radius=8,
                command=lambda u=user: self._upload_photo(u)
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                btn_row, text="📸  Capture from Camera",
                height=38, font=ctk.CTkFont(size=13),
                fg_color="#21262d", hover_color="#30363d",
                corner_radius=8,
                command=lambda u=user: self._open_capture_dialog(u)
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                btn_row, text="🗑  Delete All Images",
                height=38, font=ctk.CTkFont(size=13),
                fg_color="#21262d", hover_color="#f85149",
                corner_radius=8,
                command=lambda u=user: self._delete_all_images(u)
            ).pack(side="left", padx=(0, 8))

            ctk.CTkButton(
                btn_row, text="🧠  Train Model",
                height=38, font=ctk.CTkFont(size=13),
                fg_color="#3fb950", hover_color="#2ea043",
                corner_radius=8,
                command=self._train_model
            ).pack(side="right")

        # ── Image gallery ─────────────────────────────────────
        ctk.CTkLabel(scroll, text="FACE IMAGE GALLERY",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#484f58",
                     anchor="w").pack(fill="x", pady=(0, 8))

        self.gallery_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.gallery_frame.pack(fill="x")

        self._render_gallery(user)

    # =========================================================
    #  GALLERY
    # =========================================================

    def _render_gallery(self, user: dict):
        for w in self.gallery_frame.winfo_children():
            w.destroy()

        images = self.dm.get_user_images(user["user_id"])

        if not images:
            ctk.CTkLabel(
                self.gallery_frame,
                text="No images yet.\nUpload or capture photos above.",
                font=ctk.CTkFont(size=13),
                text_color="#484f58",
                justify="center"
            ).pack(pady=30)
            return

        # Grid: 4 images per row
        cols = 4
        for i, img_path in enumerate(images):
            row_i = i // cols
            col_i = i  % cols

            card = ctk.CTkFrame(
                self.gallery_frame, fg_color="#21262d",
                corner_radius=8,
                border_width=1, border_color="#30363d"
            )
            card.grid(row=row_i, column=col_i,
                      padx=4, pady=4, sticky="nsew")
            self.gallery_frame.columnconfigure(col_i, weight=1)

            # Load thumbnail
            try:
                pil_img = Image.open(img_path)
                pil_img.thumbnail((120, 120))
                ctk_img = ctk.CTkImage(pil_img, size=(120, 100))
                img_lbl = ctk.CTkLabel(card, image=ctk_img, text="")
                img_lbl.image = ctk_img
                img_lbl.pack(padx=6, pady=(8, 4))
            except Exception:
                ctk.CTkLabel(card, text="⚠️\nBad image",
                             font=ctk.CTkFont(size=11),
                             text_color="#f85149").pack(
                    padx=6, pady=(8, 4))

            # Quality check badge
            quality = self.dm.check_image_quality(img_path)
            q_color = "#3fb950" if quality["ok"] else "#f85149"
            q_text  = "✓ Good" if quality["ok"] else "⚠ Issues"
            ctk.CTkLabel(card, text=q_text,
                         font=ctk.CTkFont(size=10),
                         text_color=q_color).pack()

            # Filename (short)
            ctk.CTkLabel(card,
                         text=os.path.basename(img_path)[:16] + "...",
                         font=ctk.CTkFont(size=9),
                         text_color="#484f58").pack()

            # Delete button
            if self.is_admin:
                ctk.CTkButton(
                    card, text="🗑",
                    width=30, height=24,
                    font=ctk.CTkFont(size=12),
                    fg_color="#21262d", hover_color="#f85149",
                    corner_radius=4,
                    command=lambda p=img_path, u=user:
                        self._delete_single_image(p, u)
                ).pack(pady=(2, 6))

    # =========================================================
    #  UPLOAD PHOTO
    # =========================================================

    def _upload_photo(self, user: dict):
        """Open file browser and add selected image."""
        path = filedialog.askopenfilename(
            title="Select Face Photo",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return

        result = self.dm.add_face_image(
            user_id    = user["user_id"],
            name       = user["full_name"],
            image_path = path
        )

        self._show_toast(result["message"], result["success"])
        if result["success"]:
            self._reload_user(user)

    # =========================================================
    #  CAPTURE FROM CAMERA
    # =========================================================

    def _open_capture_dialog(self, user: dict):
        """Open webcam capture dialog for taking face photos."""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Capture Photo — {user['full_name']}")
        dialog.geometry("700x560")
        dialog.configure(fg_color="#161b22")
        dialog.grab_set()

        ctk.CTkLabel(dialog,
                     text=f"📸  Capture Face Photos — {user['full_name']}",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#e6edf3").pack(pady=(16, 8))
        ctk.CTkLabel(dialog,
                     text="Position your face in the frame and click 'Take Photo'.\n"
                          "Take 3–5 photos from slightly different angles.",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e",
                     justify="center").pack()

        # Camera feed
        cam_label = ctk.CTkLabel(
            dialog,
            text="Starting camera...",
            fg_color="#0d1117",
            font=ctk.CTkFont(size=13),
            text_color="#484f58",
            width=640, height=360
        )
        cam_label.pack(padx=16, pady=10)

        status_lbl = ctk.CTkLabel(
            dialog, text="",
            font=ctk.CTkFont(size=12),
            text_color="#3fb950"
        )
        status_lbl.pack()

        count_lbl = ctk.CTkLabel(
            dialog, text="Photos taken: 0",
            font=ctk.CTkFont(size=12),
            text_color="#8b949e"
        )
        count_lbl.pack()

        photos_taken = [0]
        cap          = [None]
        running      = [True]

        def _start_cam():
            cap[0] = cv2.VideoCapture(DEFAULT_CAMERA_INDEX)
            if cap[0].isOpened():
                cap[0].set(cv2.CAP_PROP_FRAME_WIDTH,  640)
                cap[0].set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
                _update_feed()
            else:
                status_lbl.configure(
                    text="Could not open camera.",
                    text_color="#f85149")

        def _update_feed():
            if not running[0] or not cap[0] or not cap[0].isOpened():
                return
            ret, frame = cap[0].read()
            if ret:
                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                ctk_img = ctk.CTkImage(pil_img, size=(640, 360))
                cam_label.configure(image=ctk_img, text="")
                cam_label.image = ctk_img
                cam_label._frame = frame  # store for capture
            dialog.after(33, _update_feed)

        def _take_photo():
            frame = getattr(cam_label, "_frame", None)
            if frame is None:
                status_lbl.configure(
                    text="No frame available.",
                    text_color="#f85149")
                return

            result = self.dm.capture_and_save(
                user_id = user["user_id"],
                name    = user["full_name"],
                frame   = frame
            )
            if result["success"]:
                photos_taken[0] += 1
                count_lbl.configure(
                    text=f"Photos taken: {photos_taken[0]}")
                status_lbl.configure(
                    text=f"✓ Photo {photos_taken[0]} saved!",
                    text_color="#3fb950")
            else:
                status_lbl.configure(
                    text=result["message"],
                    text_color="#f85149")

        def _close():
            running[0] = False
            if cap[0]:
                cap[0].release()
            dialog.destroy()
            self._reload_user(user)

        # Buttons
        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=8)

        ctk.CTkButton(
            btn_row, text="📸  Take Photo",
            height=42, width=160,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8, command=_take_photo
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_row, text="✓  Done",
            height=42, width=120,
            font=ctk.CTkFont(size=14),
            fg_color="#3fb950", hover_color="#2ea043",
            corner_radius=8, command=_close
        ).pack(side="left", padx=8)

        threading.Thread(target=_start_cam, daemon=True).start()

    # =========================================================
    #  DELETE IMAGES
    # =========================================================

    def _delete_single_image(self, img_path: str, user: dict):
        self.dm.delete_image(img_path)
        self._reload_user(user)

    def _delete_all_images(self, user: dict):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Delete")
        dialog.geometry("360x200")
        dialog.configure(fg_color="#161b22")
        dialog.grab_set()

        ctk.CTkLabel(dialog,
                     text="🗑  Delete All Images?",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#e6edf3").pack(pady=(28, 8))
        ctk.CTkLabel(dialog,
                     text=f"This will delete all face photos for\n"
                          f"{user['full_name']}.\nThis cannot be undone.",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e",
                     justify="center").pack()

        row = ctk.CTkFrame(dialog, fg_color="transparent")
        row.pack(pady=20)

        ctk.CTkButton(row, text="Cancel", width=100, height=36,
                      fg_color="#21262d", hover_color="#30363d",
                      corner_radius=8,
                      command=dialog.destroy).pack(side="left", padx=8)

        def _confirm():
            result = self.dm.delete_user_images(user["user_id"])
            dialog.destroy()
            self._show_toast(result["message"], result["success"])
            self._reload_user(user)

        ctk.CTkButton(row, text="Delete All", width=110, height=36,
                      fg_color="#f85149", hover_color="#da3633",
                      corner_radius=8,
                      command=_confirm).pack(side="left", padx=8)

    # =========================================================
    #  ADD USER DIALOG
    # =========================================================

    def _open_add_user_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New User")
        dialog.geometry("420x500")
        dialog.configure(fg_color="#161b22")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="👤  Add New User",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#e6edf3").pack(pady=(24, 16))

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(padx=30, fill="x")

        fields = {}
        defs   = [
            ("full_name",   "Full Name *"),
            ("employee_id", "Employee / Student ID"),
            ("department",  "Department"),
            ("email",       "Email"),
            ("phone",       "Phone"),
        ]
        for key, label in defs:
            ctk.CTkLabel(form, text=label,
                         font=ctk.CTkFont(size=12),
                         text_color="#8b949e",
                         anchor="w").pack(fill="x", pady=(6, 2))
            e = ctk.CTkEntry(form, height=36,
                              fg_color="#21262d",
                              border_color="#30363d",
                              text_color="#e6edf3",
                              corner_radius=6)
            e.pack(fill="x")
            fields[key] = e

        ctk.CTkLabel(form, text="Role",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e",
                     anchor="w").pack(fill="x", pady=(6, 2))
        role_var = ctk.StringVar(value="staff")
        ctk.CTkOptionMenu(
            form, variable=role_var,
            values=["staff", "student", "admin", "visitor"],
            fg_color="#21262d", button_color="#30363d",
            text_color="#e6edf3", height=36
        ).pack(fill="x")

        msg = ctk.CTkLabel(form, text="",
                            font=ctk.CTkFont(size=12),
                            text_color="#f85149")
        msg.pack(pady=(8, 0))

        def _save():
            name = fields["full_name"].get().strip()
            if not name:
                msg.configure(text="Full Name is required.")
                return
            uid = db.add_user(
                full_name   = name,
                employee_id = fields["employee_id"].get().strip() or None,
                department  = fields["department"].get().strip()  or None,
                role        = role_var.get(),
                image_path  = None,
                email       = fields["email"].get().strip()       or None,
                phone       = fields["phone"].get().strip()       or None,
            )
            if uid:
                dialog.destroy()
                self._load_users()
                self._show_toast(f"User '{name}' added!", True)
            else:
                msg.configure(text="Error saving. Check for duplicates.")

        ctk.CTkButton(
            form, text="Save User",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8, command=_save
        ).pack(fill="x", pady=(16, 0))

    # =========================================================
    #  TRAIN MODEL
    # =========================================================

    def _train_model(self):
        self.stat_status.configure(
            text="Training...", text_color="#d29922")

        def _run():
            stats = self.recognizer.train()
            self.after(0, lambda s=stats: self._on_train_done(s))

        threading.Thread(target=_run, daemon=True).start()

    def _on_train_done(self, stats):
        trained = stats.get("trained", 0)
        if trained > 0:
            self.stat_status.configure(
                text=f"Trained ✓ ({trained})",
                text_color="#3fb950")
        else:
            self.stat_status.configure(
                text="Train Failed", text_color="#f85149")

        self._update_stats()

        d = ctk.CTkToplevel(self)
        d.title("Training Complete")
        d.geometry("320x210")
        d.configure(fg_color="#161b22")
        d.grab_set()

        ctk.CTkLabel(d, text="🧠  Training Complete",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#e6edf3").pack(pady=(24, 8))
        ctk.CTkLabel(d,
                     text=f"✅  {stats.get('trained', 0)} face(s) encoded\n"
                          f"❌  {stats.get('failed',  0)} image(s) failed\n"
                          f"📁  {stats.get('total_images', 0)} total images",
                     font=ctk.CTkFont(size=13),
                     text_color="#8b949e",
                     justify="left").pack(pady=8)
        ctk.CTkButton(d, text="OK", width=100, height=36,
                      fg_color="#1f6feb", corner_radius=8,
                      command=d.destroy).pack(pady=12)

    # =========================================================
    #  HELPERS
    # =========================================================

    def _reload_user(self, user: dict):
        """Reload user data and refresh the detail panel."""
        self._load_users()
        # Re-select same user
        for u in self._all_users:
            if u["user_id"] == user["user_id"]:
                self.selected_user = u
                self._show_user_detail(u)
                break

    def _show_toast(self, message: str, success: bool = True):
        """Show a temporary status message."""
        color = "#3fb950" if success else "#f85149"
        toast = ctk.CTkToplevel(self)
        toast.title("")
        toast.geometry("320x70")
        toast.configure(fg_color="#161b22")
        toast.overrideredirect(True)

        # Center the toast
        x = self.winfo_rootx() + self.winfo_width()  // 2 - 160
        y = self.winfo_rooty() + self.winfo_height() // 2 - 35
        toast.geometry(f"320x70+{x}+{y}")

        ctk.CTkLabel(toast, text=message,
                     font=ctk.CTkFont(size=13),
                     text_color=color).place(
            relx=0.5, rely=0.5, anchor="center")

        toast.after(2000, toast.destroy)