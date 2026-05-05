# ============================================================
#   FaceSecuritySystem — ui/dashboard.py
#   Module 3: Main Dashboard with sidebar navigation
# ============================================================

import customtkinter as ctk
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import APP_NAME, APP_VERSION, THEME
from database.db_manager import db


class Dashboard(ctk.CTk):
    """
    Main dashboard window.
    Contains sidebar navigation and swappable content panels.
    """

    def __init__(self, user: dict):
        super().__init__()

        self.user         = user
        self.is_admin     = user.get("role") == "admin"
        self.active_panel = None
        self.theme_mode   = THEME

        # ── Window ────────────────────────────────────────────
        self.title(f"{APP_NAME}  —  {user['username']}  ({user['role'].title()})")
        self.geometry("1200x720")
        self.minsize(1000, 640)
        self.configure(fg_color="#0d1117")

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  // 2) - (1200 // 2)
        y = (self.winfo_screenheight() // 2) - (720  // 2)
        self.geometry(f"1200x720+{x}+{y}")

        # ── Build Layout ──────────────────────────────────────
        self._build_sidebar()
        self._build_main_area()
        self._build_topbar()

        # ── Show default panel ────────────────────────────────
        self._show_panel("home")

        # ── Clock updater ─────────────────────────────────────
        self._update_clock()

    # =========================================================
    #  SIDEBAR
    # =========================================================

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, fg_color="#161b22", width=220,
            corner_radius=0, border_width=1,
            border_color="#21262d"
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # ── Logo area ─────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="#1f6feb",
                                   height=64, corner_radius=0)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)

        ctk.CTkLabel(
            logo_frame, text="🔐  FaceSec",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color="white"
        ).place(relx=0.5, rely=0.5, anchor="center")

        # ── User info ─────────────────────────────────────────
        user_card = ctk.CTkFrame(self.sidebar, fg_color="#21262d",
                                  corner_radius=10)
        user_card.pack(fill="x", padx=12, pady=14)

        avatar = ctk.CTkFrame(user_card, fg_color="#1f6feb",
                               width=38, height=38, corner_radius=19)
        avatar.pack(side="left", padx=(10, 8), pady=10)
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar,
                     text=self.user["username"][0].upper(),
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(user_card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=10)
        ctk.CTkLabel(info, text=self.user["username"],
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#e6edf3", anchor="w").pack(fill="x")
        role_color = "#1f6feb" if self.is_admin else "#3fb950"
        ctk.CTkLabel(info, text=self.user["role"].title(),
                     font=ctk.CTkFont(size=11),
                     text_color=role_color, anchor="w").pack(fill="x")

        # ── Nav label ─────────────────────────────────────────
        ctk.CTkLabel(self.sidebar, text="NAVIGATION",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#484f58",
                     anchor="w").pack(fill="x", padx=18, pady=(8, 4))

        # ── Nav buttons ───────────────────────────────────────
        self.nav_buttons = {}

        nav_items = [
            ("home",     "🏠",  "Overview"),
            ("camera",   "📷",  "Live Camera"),
            ("logs",     "📋",  "Entry Logs"),
            ("alerts",   "🔔",  "Alerts"),
        ]
        if self.is_admin:
            nav_items += [
                ("dataset",  "👥",  "Dataset / Users"),
                ("reports",  "📊",  "Reports"),
                ("settings", "⚙️",  "Settings"),
            ]

        for panel_id, icon, label in nav_items:
            btn = self._make_nav_btn(panel_id, icon, label)
            self.nav_buttons[panel_id] = btn

        # ── Spacer ────────────────────────────────────────────
        ctk.CTkFrame(self.sidebar, fg_color="transparent").pack(
            fill="both", expand=True)

        # ── Theme toggle ──────────────────────────────────────
        ctk.CTkLabel(self.sidebar, text="APPEARANCE",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#484f58",
                     anchor="w").pack(fill="x", padx=18, pady=(0, 4))

        theme_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        theme_row.pack(fill="x", padx=12, pady=(0, 8))

        self.theme_switch = ctk.CTkSwitch(
            theme_row, text="Dark Mode",
            font=ctk.CTkFont(size=12),
            text_color="#8b949e",
            fg_color="#30363d",
            progress_color="#1f6feb",
            command=self._toggle_theme
        )
        self.theme_switch.pack(side="left", padx=6)
        if self.theme_mode == "dark":
            self.theme_switch.select()

        # ── Logout ────────────────────────────────────────────
        ctk.CTkButton(
            self.sidebar, text="⏻  Logout",
            height=38,
            font=ctk.CTkFont(size=13),
            fg_color="#21262d",
            hover_color="#f85149",
            text_color="#8b949e",
            corner_radius=8,
            command=self._logout
        ).pack(fill="x", padx=12, pady=(0, 14))

    def _make_nav_btn(self, panel_id, icon, label):
        btn = ctk.CTkButton(
            self.sidebar,
            text=f"  {icon}   {label}",
            height=42,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color="#21262d",
            text_color="#8b949e",
            anchor="w",
            corner_radius=8,
            command=lambda p=panel_id: self._show_panel(p)
        )
        btn.pack(fill="x", padx=12, pady=2)
        return btn

    # =========================================================
    #  TOP BAR
    # =========================================================

    def _build_topbar(self):
        self.topbar = ctk.CTkFrame(
            self.main_area, fg_color="#161b22",
            height=56, corner_radius=0,
            border_width=1, border_color="#21262d"
        )
        self.topbar.pack(fill="x", side="top")
        self.topbar.pack_propagate(False)

        # Panel title
        self.topbar_title = ctk.CTkLabel(
            self.topbar, text="Overview",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#e6edf3"
        )
        self.topbar_title.pack(side="left", padx=24)

        # Clock
        self.clock_label = ctk.CTkLabel(
            self.topbar, text="",
            font=ctk.CTkFont(size=13),
            text_color="#8b949e"
        )
        self.clock_label.pack(side="right", padx=24)

        # Date
        self.date_label = ctk.CTkLabel(
            self.topbar, text="",
            font=ctk.CTkFont(size=13),
            text_color="#484f58"
        )
        self.date_label.pack(side="right", padx=(0, 8))

    # =========================================================
    #  MAIN AREA
    # =========================================================

    def _build_main_area(self):
        self.main_area = ctk.CTkFrame(
            self, fg_color="#0d1117", corner_radius=0
        )
        self.main_area.pack(side="left", fill="both", expand=True)

        # Content frame — panels are placed here
        self.content = ctk.CTkFrame(
            self.main_area, fg_color="#0d1117", corner_radius=0
        )
        self.content.pack(fill="both", expand=True, padx=0, pady=0)

    # =========================================================
    #  PANEL SWITCHER
    # =========================================================

    def _show_panel(self, panel_id: str):
        # Highlight active nav button
        for pid, btn in self.nav_buttons.items():
            if pid == panel_id:
                btn.configure(fg_color="#21262d", text_color="#e6edf3")
            else:
                btn.configure(fg_color="transparent", text_color="#8b949e")

        # Clear content area
        for widget in self.content.winfo_children():
            widget.destroy()

        self.active_panel = panel_id

        # Panel titles
        titles = {
            "home":     "Overview",
            "camera":   "Live Camera",
            "logs":     "Entry Logs",
            "alerts":   "Alerts",
            "dataset":  "Dataset / Users",
            "reports":  "Reports",
            "settings": "Settings",
        }
        self.topbar_title.configure(text=titles.get(panel_id, ""))

        # Load panel
        if   panel_id == "home":     self._panel_home()
        elif panel_id == "camera":   self._panel_camera()
        elif panel_id == "logs":     self._panel_logs()
        elif panel_id == "alerts":   self._panel_alerts()
        elif panel_id == "dataset":  self._panel_dataset()
        elif panel_id == "reports":  self._panel_reports()
        elif panel_id == "settings": self._panel_settings()

    # =========================================================
    #  PANEL: HOME / OVERVIEW
    # =========================================================

    def _panel_home(self):
        scroll = ctk.CTkScrollableFrame(
            self.content, fg_color="transparent", corner_radius=0
        )
        scroll.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Welcome banner ────────────────────────────────────
        banner = ctk.CTkFrame(scroll, fg_color="#1f6feb",
                               corner_radius=12, height=90)
        banner.pack(fill="x", pady=(0, 20))
        banner.pack_propagate(False)

        ctk.CTkLabel(
            banner,
            text=f"👋  Welcome back, {self.user['username']}!",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color="white"
        ).place(x=24, y=18)
        ctk.CTkLabel(
            banner,
            text=f"Today is {datetime.now().strftime('%A, %d %B %Y')}",
            font=ctk.CTkFont(size=13),
            text_color="#cce0ff"
        ).place(x=24, y=54)

        # ── Stats cards ───────────────────────────────────────
        ctk.CTkLabel(scroll, text="SYSTEM OVERVIEW",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#484f58",
                     anchor="w").pack(fill="x", pady=(0, 10))

        stats_row = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 20))
        stats_row.columnconfigure((0, 1, 2, 3), weight=1, uniform="s")

        # Fetch live stats from DB
        users_count   = len(db.get_all_users())
        logs_today    = len(db.get_logs(
            date_from=datetime.now().strftime("%Y-%m-%d"),
            date_to  =datetime.now().strftime("%Y-%m-%d")
        ))
        alerts_count  = len(db.get_unreviewed_alerts())
        cameras_count = len(db.get_active_cameras())

        cards = [
            ("👥", "Registered Users",  str(users_count),   "#1f6feb", "#163a6b"),
            ("📋", "Entries Today",     str(logs_today),    "#3fb950", "#1a4226"),
            ("🔔", "Pending Alerts",    str(alerts_count),  "#f85149", "#4a1a18"),
            ("📷", "Active Cameras",    str(cameras_count), "#d29922", "#4a3a10"),
        ]

        for col, (icon, label, value, fg, bg) in enumerate(cards):
            card = ctk.CTkFrame(stats_row, fg_color=bg,
                                corner_radius=12, height=110)
            card.grid(row=0, column=col, padx=6, sticky="ew")
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=icon,
                         font=ctk.CTkFont(size=28)).place(x=16, y=14)
            ctk.CTkLabel(card, text=value,
                         font=ctk.CTkFont(size=28, weight="bold"),
                         text_color=fg).place(x=16, y=48)
            ctk.CTkLabel(card, text=label,
                         font=ctk.CTkFont(size=12),
                         text_color="#8b949e").place(x=16, y=82)

        # ── Recent entries table ──────────────────────────────
        ctk.CTkLabel(scroll, text="RECENT ENTRIES",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#484f58",
                     anchor="w").pack(fill="x", pady=(0, 10))

        table_frame = ctk.CTkFrame(scroll, fg_color="#161b22",
                                    corner_radius=12,
                                    border_width=1, border_color="#21262d")
        table_frame.pack(fill="x")

        # Table header
        header = ctk.CTkFrame(table_frame, fg_color="#21262d",
                               corner_radius=0, height=38)
        header.pack(fill="x")
        header.pack_propagate(False)

        for col_text, width in [("Name", 180), ("Date", 120),
                                  ("Time", 100), ("Camera", 120),
                                  ("Status", 100)]:
            ctk.CTkLabel(header, text=col_text,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#8b949e",
                         width=width, anchor="w").pack(
                side="left", padx=12)

        # Table rows
        recent_logs = db.get_logs()[:10]
        if not recent_logs:
            ctk.CTkLabel(table_frame,
                         text="No entries yet. Start the camera to begin logging.",
                         font=ctk.CTkFont(size=13),
                         text_color="#484f58").pack(pady=30)
        else:
            for i, log in enumerate(recent_logs):
                row_bg = "#161b22" if i % 2 == 0 else "#1a1f27"
                row = ctk.CTkFrame(table_frame, fg_color=row_bg,
                                    corner_radius=0, height=38)
                row.pack(fill="x")
                row.pack_propagate(False)

                status_color = "#3fb950" if log["status"] == "known" else "#f85149"

                for text, width in [
                    (str(log.get("name", "")),         180),
                    (str(log.get("entry_date", "")),   120),
                    (str(log.get("entry_time", ""))[:8], 100),
                    (str(log.get("camera_label", "")), 120),
                ]:
                    ctk.CTkLabel(row, text=text,
                                 font=ctk.CTkFont(size=12),
                                 text_color="#c9d1d9",
                                 width=width, anchor="w").pack(
                        side="left", padx=12)

                ctk.CTkLabel(row,
                             text=log.get("status", "").title(),
                             font=ctk.CTkFont(size=12),
                             text_color=status_color,
                             width=100, anchor="w").pack(side="left", padx=12)

        # ── Quick actions ─────────────────────────────────────
        ctk.CTkLabel(scroll, text="QUICK ACTIONS",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#484f58",
                     anchor="w").pack(fill="x", pady=(20, 10))

        actions_row = ctk.CTkFrame(scroll, fg_color="transparent")
        actions_row.pack(fill="x")

        actions = [
            ("📷  Open Camera",    "camera",  "#1f6feb"),
            ("📋  View All Logs",  "logs",    "#21262d"),
            ("🔔  Check Alerts",   "alerts",  "#21262d"),
        ]
        if self.is_admin:
            actions.append(("👥  Manage Users", "dataset", "#21262d"))

        for label, panel, color in actions:
            ctk.CTkButton(
                actions_row, text=label,
                height=42, font=ctk.CTkFont(size=13),
                fg_color=color, hover_color="#388bfd",
                corner_radius=8,
                command=lambda p=panel: self._show_panel(p)
            ).pack(side="left", padx=(0, 10))

    # =========================================================
    #  PANEL: CAMERA  (placeholder — built in Module 7)
    # =========================================================

    def _panel_camera(self):
        try:
            # Tab switcher: Single Camera | Multi Camera
            outer = ctk.CTkFrame(self.content, fg_color="transparent")
            outer.pack(fill="both", expand=True, padx=24, pady=20)

            tab_bar = ctk.CTkFrame(outer, fg_color="#161b22",
                                    height=44, corner_radius=10,
                                    border_width=1, border_color="#21262d")
            tab_bar.pack(fill="x", pady=(0, 10))
            tab_bar.pack_propagate(False)

            content_frame = ctk.CTkFrame(outer, fg_color="transparent")
            content_frame.pack(fill="both", expand=True)

            self._active_cam_panel = None

            def _show_single():
                for w in content_frame.winfo_children():
                    w.destroy()
                from ui.camera_panel import CameraPanel
                panel = CameraPanel(content_frame)
                panel.pack(fill="both", expand=True)
                self._active_cam_panel = panel
                single_btn.configure(fg_color="#1f6feb", text_color="white")
                multi_btn.configure(fg_color="#21262d", text_color="#8b949e")

            def _show_multi():
                for w in content_frame.winfo_children():
                    w.destroy()
                from ui.multi_camera_panel import MultiCameraPanel
                panel = MultiCameraPanel(content_frame)
                panel.pack(fill="both", expand=True)
                self._active_cam_panel = panel
                multi_btn.configure(fg_color="#1f6feb", text_color="white")
                single_btn.configure(fg_color="#21262d", text_color="#8b949e")

            single_btn = ctk.CTkButton(
                tab_bar, text="📷  Single Camera",
                height=36, width=160,
                font=ctk.CTkFont(size=13),
                fg_color="#1f6feb", hover_color="#388bfd",
                corner_radius=8, command=_show_single)
            single_btn.pack(side="left", padx=(8, 4), pady=4)

            multi_btn = ctk.CTkButton(
                tab_bar, text="📷📷  Multi Camera",
                height=36, width=160,
                font=ctk.CTkFont(size=13),
                fg_color="#21262d", hover_color="#30363d",
                corner_radius=8, command=_show_multi)
            multi_btn.pack(side="left", padx=4, pady=4)

            # Default to single camera
            _show_single()

        except Exception as e:
            self._coming_soon_panel(
                "📷", "Camera Error",
                f"Could not load camera panel:\n{e}",
                "#f85149"
            )

    # =========================================================
    #  PANEL: LOGS
    # =========================================================

    def _panel_logs(self):
        try:
            from ui.logs_panel import LogsPanel
            panel = LogsPanel(self.content)
            panel.pack(fill="both", expand=True, padx=16, pady=16)
        except Exception as e:
            self._coming_soon_panel(
                "📋", "Logs Error",
                f"Could not load logs panel:\n{e}",
                "#f85149"
            )

    # =========================================================
    #  PANEL: ALERTS
    # =========================================================

    def _panel_alerts(self):
        try:
            from ui.alerts_panel import AlertsPanel
            panel = AlertsPanel(self.content)
            panel.pack(fill="both", expand=True, padx=16, pady=16)
        except Exception as e:
            self._coming_soon_panel(
                "🔔", "Alerts Error",
                f"Could not load alerts panel:\n{e}",
                "#f85149"
            )

    # =========================================================
    #  PANEL: DATASET (Admin only)
    # =========================================================

    def _panel_dataset(self):
        if not self.is_admin:
            self._access_denied()
            return
        try:
            from ui.dataset_panel import DatasetPanel
            panel = DatasetPanel(
                self.content, is_admin=self.is_admin)
            panel.pack(fill="both", expand=True, padx=16, pady=16)
        except Exception as e:
            self._coming_soon_panel(
                "👥", "Dataset Error",
                f"Could not load dataset panel:\n{e}",
                "#f85149"
            )

    def _open_add_user_dialog(self):
        self._user_dialog(mode="add")

    def _open_edit_user_dialog(self, user):
        self._user_dialog(mode="edit", user=user)

    def _user_dialog(self, mode="add", user=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add User" if mode == "add" else "Edit User")
        dialog.geometry("420x540")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#161b22")
        dialog.grab_set()

        ctk.CTkLabel(dialog,
                     text="Add New User" if mode == "add" else "Edit User",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color="#e6edf3").pack(pady=(24, 16))

        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(padx=30, fill="x")

        fields = {}
        field_defs = [
            ("full_name",   "Full Name"),
            ("employee_id", "Employee / Student ID"),
            ("department",  "Department"),
            ("email",       "Email"),
            ("phone",       "Phone"),
        ]

        for key, label in field_defs:
            ctk.CTkLabel(form, text=label,
                         font=ctk.CTkFont(size=12),
                         text_color="#8b949e",
                         anchor="w").pack(fill="x", pady=(6, 2))
            entry = ctk.CTkEntry(form, height=36,
                                  fg_color="#21262d",
                                  border_color="#30363d",
                                  text_color="#e6edf3",
                                  corner_radius=6)
            entry.pack(fill="x")
            if mode == "edit" and user:
                entry.insert(0, str(user.get(key, "") or ""))
            fields[key] = entry

        # Role dropdown
        ctk.CTkLabel(form, text="Role",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e",
                     anchor="w").pack(fill="x", pady=(6, 2))
        role_var = ctk.StringVar(
            value=user.get("role", "staff") if user else "staff"
        )
        ctk.CTkOptionMenu(
            form, variable=role_var,
            values=["staff", "student", "admin", "visitor"],
            fg_color="#21262d", button_color="#30363d",
            text_color="#e6edf3", height=36
        ).pack(fill="x")

        # Status message
        msg_label = ctk.CTkLabel(form, text="",
                                  font=ctk.CTkFont(size=12),
                                  text_color="#f85149")
        msg_label.pack(pady=(10, 0))

        def _save():
            name = fields["full_name"].get().strip()
            if not name:
                msg_label.configure(text="Full Name is required.")
                return

            if mode == "add":
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
                    self._show_panel("dataset")
                else:
                    msg_label.configure(text="Error saving user. Check for duplicates.")
            else:
                ok = db.update_user(
                    user["user_id"],
                    full_name   = name,
                    employee_id = fields["employee_id"].get().strip() or None,
                    department  = fields["department"].get().strip()  or None,
                    role        = role_var.get(),
                    email       = fields["email"].get().strip()       or None,
                    phone       = fields["phone"].get().strip()       or None,
                )
                if ok:
                    dialog.destroy()
                    self._show_panel("dataset")
                else:
                    msg_label.configure(text="Error updating user.")

        ctk.CTkButton(
            form,
            text="Save User" if mode == "add" else "Update User",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8,
            command=_save
        ).pack(fill="x", pady=(16, 0))

    def _delete_user(self, user_id):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Delete")
        dialog.geometry("360x180")
        dialog.configure(fg_color="#161b22")
        dialog.grab_set()

        ctk.CTkLabel(dialog,
                     text="Delete this user?",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#e6edf3").pack(pady=(30, 8))
        ctk.CTkLabel(dialog,
                     text="This will permanently remove the user\nand all their face data.",
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
            db.delete_user(user_id)
            dialog.destroy()
            self._show_panel("dataset")

        ctk.CTkButton(row, text="Delete", width=100, height=36,
                      fg_color="#f85149", hover_color="#da3633",
                      corner_radius=8,
                      command=_confirm).pack(side="left", padx=8)

    # =========================================================
    #  PANEL: REPORTS  (placeholder — Module 11)
    # =========================================================

    def _panel_reports(self):
        try:
            from ui.reports_panel import ReportsPanel
            panel = ReportsPanel(self.content)
            panel.pack(fill="both", expand=True, padx=16, pady=16)
        except Exception as e:
            self._coming_soon_panel(
                "📊", "Reports Error",
                f"Could not load reports panel:\n{e}",
                "#f85149"
            )

    # =========================================================
    #  PANEL: SETTINGS  (Admin only)
    # =========================================================

    def _panel_settings(self):
        if not self.is_admin:
            self._access_denied()
            return

        scroll = ctk.CTkScrollableFrame(
            self.content, fg_color="transparent"
        )
        scroll.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(scroll, text="System Settings",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="#e6edf3",
                     anchor="w").pack(fill="x", pady=(0, 20))

        settings_keys = [
            ("recognition_tolerance", "Recognition Tolerance",
             "Face match strictness (0.0–1.0, lower = stricter)"),
            ("liveness_required",     "Liveness Check Required",
             "1 = enabled, 0 = disabled"),
            ("alert_sound",           "Alert Sound",
             "1 = enabled, 0 = disabled"),
            ("low_light_enhancement", "Low-Light Enhancement",
             "1 = enabled, 0 = disabled"),
            ("session_timeout_min",   "Session Timeout (minutes)",
             "Auto-logout after inactivity"),
            ("max_login_attempts",    "Max Login Attempts",
             "Lockout after this many failures"),
        ]

        entries = {}
        for key, label, desc in settings_keys:
            card = ctk.CTkFrame(scroll, fg_color="#161b22",
                                 corner_radius=10,
                                 border_width=1, border_color="#21262d")
            card.pack(fill="x", pady=6)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=12)

            ctk.CTkLabel(inner, text=label,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color="#c9d1d9",
                         anchor="w").pack(fill="x")
            ctk.CTkLabel(inner, text=desc,
                         font=ctk.CTkFont(size=11),
                         text_color="#484f58",
                         anchor="w").pack(fill="x")

            entry = ctk.CTkEntry(inner, height=34,
                                  fg_color="#21262d",
                                  border_color="#30363d",
                                  text_color="#e6edf3",
                                  corner_radius=6, width=200)
            entry.pack(anchor="w", pady=(6, 0))

            current = db.get_setting(key)
            if current:
                entry.insert(0, current)
            entries[key] = entry

        def _save_settings():
            for key, entry in entries.items():
                val = entry.get().strip()
                if val:
                    db.update_setting(key, val)
            saved_label.configure(text="✓  Settings saved!", text_color="#3fb950")
            self.after(2000, lambda: saved_label.configure(text=""))

        saved_label = ctk.CTkLabel(scroll, text="",
                                    font=ctk.CTkFont(size=13),
                                    text_color="#3fb950")
        saved_label.pack(pady=(8, 4))

        ctk.CTkButton(
            scroll, text="💾  Save Settings",
            height=44, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8, command=_save_settings
        ).pack(anchor="w", pady=(0, 30))

    # =========================================================
    #  HELPERS
    # =========================================================

    def _coming_soon_panel(self, icon, title, subtitle, color):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.pack(expand=True)

        ctk.CTkLabel(frame, text=icon,
                     font=ctk.CTkFont(size=64)).pack(pady=(0, 16))
        ctk.CTkLabel(frame, text=title,
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=color).pack()
        ctk.CTkLabel(frame, text=subtitle,
                     font=ctk.CTkFont(size=14),
                     text_color="#484f58",
                     justify="center").pack(pady=8)

        ctk.CTkLabel(frame, text="🔧  Coming in a future module",
                     font=ctk.CTkFont(size=12),
                     text_color="#30363d").pack(pady=(16, 0))

    def _access_denied(self):
        frame = ctk.CTkFrame(self.content, fg_color="transparent")
        frame.pack(expand=True)
        ctk.CTkLabel(frame, text="🔒",
                     font=ctk.CTkFont(size=64)).pack(pady=(0, 16))
        ctk.CTkLabel(frame, text="Access Denied",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#f85149").pack()
        ctk.CTkLabel(frame, text="This section is for Admins only.",
                     font=ctk.CTkFont(size=14),
                     text_color="#484f58").pack(pady=8)

    def _toggle_theme(self):
        if self.theme_mode == "dark":
            self.theme_mode = "light"
            ctk.set_appearance_mode("light")
        else:
            self.theme_mode = "dark"
            ctk.set_appearance_mode("dark")

    def _update_clock(self):
        now = datetime.now()
        self.clock_label.configure(
            text=now.strftime("%H:%M:%S")
        )
        self.date_label.configure(
            text=now.strftime("%d %b %Y  •  ")
        )
        self.after(1000, self._update_clock)

    def _logout(self):
        self.destroy()
        from ui.login_window import launch_login
        launch_login()