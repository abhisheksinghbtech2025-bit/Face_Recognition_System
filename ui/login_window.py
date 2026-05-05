import customtkinter as ctk
import bcrypt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import APP_NAME, APP_VERSION, MAX_LOGIN_ATTEMPTS, THEME, COLOR_THEME
from database.db_manager import db

ctk.set_appearance_mode(THEME)
ctk.set_default_color_theme(COLOR_THEME)


class LoginWindow(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("480x620")
        self.resizable(False, False)
        self.configure(fg_color="#0d1117")

        self.update_idletasks()
        x = (self.winfo_screenwidth()  // 2) - (480 // 2)
        y = (self.winfo_screenheight() // 2) - (620 // 2)
        self.geometry(f"480x620+{x}+{y}")

        self.failed_attempts = 0
        self.show_password   = False

        self._build_ui()
        db.connect()

    def _build_ui(self):
        card = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=20,
                            border_width=1, border_color="#30363d")
        card.place(relx=0.5, rely=0.5, anchor="center",
                   relwidth=0.88, relheight=0.92)

        accent = ctk.CTkFrame(card, fg_color="#1f6feb", height=4, corner_radius=0)
        accent.pack(fill="x", side="top")

        icon_frame  = ctk.CTkFrame(card, fg_color="transparent")
        icon_frame.pack(pady=(30, 0))
        icon_circle = ctk.CTkFrame(icon_frame, fg_color="#1f6feb",
                                   width=72, height=72, corner_radius=36)
        icon_circle.pack()
        icon_circle.pack_propagate(False)
        ctk.CTkLabel(icon_circle, text="🔐",
                     font=ctk.CTkFont(size=32)).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text="Face Security System",
                     font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                     text_color="#e6edf3").pack(pady=(16, 2))
        ctk.CTkLabel(card, text="Sign in to your account",
                     font=ctk.CTkFont(size=13),
                     text_color="#8b949e").pack(pady=(0, 24))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(padx=40, fill="x")

        ctk.CTkLabel(form, text="Username",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c9d1d9", anchor="w").pack(fill="x", pady=(0, 6))

        self.username_entry = ctk.CTkEntry(
            form, placeholder_text="Enter your username",
            height=44, font=ctk.CTkFont(size=14),
            fg_color="#21262d", border_color="#30363d",
            border_width=1, text_color="#e6edf3",
            placeholder_text_color="#484f58", corner_radius=8)
        self.username_entry.pack(fill="x", pady=(0, 16))
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())

        ctk.CTkLabel(form, text="Password",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c9d1d9", anchor="w").pack(fill="x", pady=(0, 6))

        pass_row = ctk.CTkFrame(form, fg_color="transparent")
        pass_row.pack(fill="x", pady=(0, 8))

        self.password_entry = ctk.CTkEntry(
            pass_row, placeholder_text="Enter your password",
            height=44, font=ctk.CTkFont(size=14),
            fg_color="#21262d", border_color="#30363d",
            border_width=1, text_color="#e6edf3",
            placeholder_text_color="#484f58", corner_radius=8, show="●")
        self.password_entry.pack(side="left", fill="x", expand=True)
        self.password_entry.bind("<Return>", lambda e: self._attempt_login())

        ctk.CTkButton(pass_row, text="👁", width=44, height=44,
                      fg_color="#21262d", hover_color="#30363d",
                      border_color="#30363d", border_width=1,
                      corner_radius=8,
                      command=self._toggle_password).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(form, text="Login As",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c9d1d9", anchor="w").pack(fill="x", pady=(8, 6))

        self.role_var = ctk.StringVar(value="admin")
        role_row = ctk.CTkFrame(form, fg_color="transparent")
        role_row.pack(fill="x", pady=(0, 20))

        ctk.CTkRadioButton(role_row, text="Admin",
                           variable=self.role_var, value="admin",
                           font=ctk.CTkFont(size=13),
                           text_color="#c9d1d9",
                           fg_color="#1f6feb").pack(side="left", padx=(0, 20))

        ctk.CTkRadioButton(role_row, text="Security Staff",
                           variable=self.role_var, value="user",
                           font=ctk.CTkFont(size=13),
                           text_color="#c9d1d9",
                           fg_color="#1f6feb").pack(side="left")

        self.login_btn = ctk.CTkButton(
            form, text="Sign In", height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8, command=self._attempt_login)
        self.login_btn.pack(fill="x", pady=(0, 12))

        self.status_label = ctk.CTkLabel(
            form, text="", font=ctk.CTkFont(size=12),
            text_color="#f85149", wraplength=340)
        self.status_label.pack()

        ctk.CTkLabel(card, text=f"Face Security System  •  v{APP_VERSION}",
                     font=ctk.CTkFont(size=11),
                     text_color="#484f58").pack(side="bottom", pady=16)

    def _toggle_password(self):
        self.show_password = not self.show_password
        self.password_entry.configure(show="" if self.show_password else "●")

    def _attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        role     = self.role_var.get()

        if not username:
            self._show_error("Please enter your username.")
            return
        if not password:
            self._show_error("Please enter your password.")
            return
        if self.failed_attempts >= MAX_LOGIN_ATTEMPTS:
            self._show_error("Account locked. Contact administrator.")
            self.login_btn.configure(state="disabled")
            return

        self._show_loading()
        self.update()

        user_record = db.get_login(username)

        if not user_record:
            self._on_failed_login("Invalid username or password.")
            return
        if not user_record.get("is_active"):
            self._show_error("Account is disabled.")
            return
        if user_record.get("role") != role:
            self._on_failed_login(f"Account is not registered as '{role}'.")
            return

        try:
            password_ok = bcrypt.checkpw(
                password.encode("utf-8"),
                user_record["password_hash"].encode("utf-8")
            )
        except Exception:
            password_ok = False

        if not password_ok:
            db.increment_failed_attempts(username)
            self._on_failed_login("Invalid username or password.")
            return

        db.update_last_login(user_record["login_id"])
        self._on_login_success(user_record)

    def _on_login_success(self, user_record):
        self._show_success(f"Welcome, {user_record['username']}!")
        self.update()
        self.after(800, lambda: self._open_dashboard(user_record))

    def _open_dashboard(self, user_record):
        self.destroy()
        try:
            from ui.dashboard import Dashboard
            app = Dashboard(user=user_record)
            app.mainloop()
        except ImportError:
            root = ctk.CTk()
            root.title("Dashboard — Coming in Module 3")
            root.geometry("900x600")
            root.configure(fg_color="#0d1117")
            ctk.CTkLabel(
                root,
                text=f"✅  Login Successful!\n\nWelcome  {user_record['username']}  ({user_record['role']})\n\nDashboard coming in Module 3.",
                font=ctk.CTkFont(size=20),
                text_color="#3fb950"
            ).pack(expand=True)
            root.mainloop()

    def _on_failed_login(self, message):
        self.failed_attempts += 1
        remaining = MAX_LOGIN_ATTEMPTS - self.failed_attempts
        if remaining > 0:
            self._show_error(f"{message}  ({remaining} attempts left)")
        else:
            self._show_error("Account locked after too many failed attempts.")
            self.login_btn.configure(state="disabled")
        self._shake_window()
        self.password_entry.delete(0, "end")
        self.password_entry.focus()

    def _show_error(self, message):
        self.status_label.configure(text=f"⚠  {message}", text_color="#f85149")

    def _show_success(self, message):
        self.status_label.configure(text=f"✓  {message}", text_color="#3fb950")

    def _show_loading(self):
        self.status_label.configure(text="Signing in...", text_color="#8b949e")
        self.login_btn.configure(state="disabled", text="Please wait...")

    def _shake_window(self):
        orig_x = self.winfo_x()
        orig_y = self.winfo_y()
        offsets = [10, -10, 8, -8, 5, -5, 0]
        def _step(i=0):
            if i < len(offsets):
                self.geometry(f"+{orig_x + offsets[i]}+{orig_y}")
                self.after(40, lambda: _step(i + 1))
            else:
                self.geometry(f"+{orig_x}+{orig_y}")
                self.login_btn.configure(state="normal", text="Sign In")
        _step()


def launch_login():
    app = LoginWindow()
    app.mainloop()


if __name__ == "__main__":
    launch_login()