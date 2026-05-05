# ============================================================
#   FaceSecuritySystem — ui/splash_screen.py
#   Module 12: Splash Screen shown on startup
# ============================================================

import customtkinter as ctk
import threading
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import APP_NAME, APP_VERSION


class SplashScreen(ctk.CTkToplevel):
    """
    Animated splash screen shown while the app loads.
    Shows logo, version, and loading progress.
    Automatically closes and launches login when done.
    """

    def __init__(self, on_done_callback):
        # Create a hidden root first
        self._root = ctk.CTk()
        self._root.withdraw()

        super().__init__(self._root)

        self.on_done = on_done_callback

        # Window setup
        self.geometry("480x320")
        self.resizable(False, False)
        self.configure(fg_color="#0d1117")
        self.overrideredirect(True)   # no title bar

        # Center on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  // 2) - 240
        y = (self.winfo_screenheight() // 2) - 160
        self.geometry(f"480x320+{x}+{y}")

        self._build_ui()
        self._start_loading()

    def _build_ui(self):
        # Border frame
        border = ctk.CTkFrame(self, fg_color="#1f6feb",
                               corner_radius=0)
        border.place(x=0, y=0, relwidth=1, height=4)

        # Icon
        icon_frame = ctk.CTkFrame(self, fg_color="#1f6feb",
                                   width=80, height=80,
                                   corner_radius=40)
        icon_frame.place(relx=0.5, y=60, anchor="center")
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text="🔐",
                     font=ctk.CTkFont(size=36)).place(
            relx=0.5, rely=0.5, anchor="center")

        # App name
        ctk.CTkLabel(self, text=APP_NAME,
                     font=ctk.CTkFont(
                         family="Segoe UI",
                         size=24, weight="bold"),
                     text_color="#e6edf3").place(
            relx=0.5, y=122, anchor="center")

        # Version
        ctk.CTkLabel(self, text=f"Version {APP_VERSION}",
                     font=ctk.CTkFont(size=12),
                     text_color="#484f58").place(
            relx=0.5, y=150, anchor="center")

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            self, width=360, height=6,
            fg_color="#21262d",
            progress_color="#1f6feb",
            corner_radius=3)
        self.progress.place(relx=0.5, y=220, anchor="center")
        self.progress.set(0)

        # Status text
        self.status_lbl = ctk.CTkLabel(
            self, text="Initializing...",
            font=ctk.CTkFont(size=11),
            text_color="#8b949e")
        self.status_lbl.place(relx=0.5, y=245, anchor="center")

        # Copyright
        ctk.CTkLabel(self,
                     text=f"© {datetime.now().year}  Face Security System",
                     font=ctk.CTkFont(size=10),
                     text_color="#30363d").place(
            relx=0.5, y=300, anchor="center")

    def _start_loading(self):
        steps = [
            (0.1,  "Loading configuration..."),
            (0.3,  "Connecting to database..."),
            (0.5,  "Loading face encodings..."),
            (0.7,  "Starting camera manager..."),
            (0.9,  "Preparing interface..."),
            (1.0,  "Ready!"),
        ]

        def _run():
            import time
            for progress, status in steps:
                time.sleep(0.4)
                self.after(0, lambda p=progress, s=status:
                           self._update(p, s))

            self.after(500, self._finish)

        threading.Thread(target=_run, daemon=True).start()

    def _update(self, progress: float, status: str):
        self.progress.set(progress)
        self.status_lbl.configure(text=status)

    def _finish(self):
        self.destroy()
        self._root.destroy()
        self.on_done()


def launch_with_splash():
    """Launch the app with splash screen → then login."""
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    def _open_login():
        from ui.login_window import launch_login
        launch_login()

    splash = SplashScreen(on_done_callback=_open_login)
    splash._root.mainloop()