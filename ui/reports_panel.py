# ============================================================
#   FaceSecuritySystem — ui/reports_panel.py
#   Module 11: Reports & Export UI Panel
# ============================================================

import customtkinter as ctk
import os
import sys
import threading
import subprocess
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.report_exporter import ReportExporter


class ReportsPanel(ctk.CTkFrame):
    """
    Reports & Export Panel.

    Two sections:
      Left  — Generate new reports with options
      Right — Previously exported files list
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.exporter = ReportExporter()
        self._build_ui()
        self._load_files()

    # =========================================================
    #  UI BUILD
    # =========================================================

    def _build_ui(self):
        # ── Page title ────────────────────────────────────────
        title_bar = ctk.CTkFrame(
            self, fg_color="#161b22", height=52,
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        title_bar.pack(fill="x", pady=(0, 12))
        title_bar.pack_propagate(False)

        ctk.CTkLabel(
            title_bar,
            text="📊  Reports & Export",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#e6edf3"
        ).pack(side="left", padx=20, pady=14)

        ctk.CTkLabel(
            title_bar,
            text="Generate PDF and Excel reports from your security data",
            font=ctk.CTkFont(size=12),
            text_color="#484f58"
        ).pack(side="left")

        # ── Two column layout ─────────────────────────────────
        columns = ctk.CTkFrame(self, fg_color="transparent")
        columns.pack(fill="both", expand=True)

        # Left column — report generator
        self.left = ctk.CTkFrame(
            columns, fg_color="#161b22",
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        self.left.pack(side="left", fill="both",
                       expand=True, padx=(0, 8))

        # Right column — exported files list
        self.right = ctk.CTkFrame(
            columns, fg_color="#161b22",
            width=320, corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        self.right.pack(side="left", fill="y")
        self.right.pack_propagate(False)

        self._build_left_panel()
        self._build_right_panel()

    # =========================================================
    #  LEFT PANEL — Report Generator
    # =========================================================

    def _build_left_panel(self):
        scroll = ctk.CTkScrollableFrame(
            self.left, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # ── Date range selector ───────────────────────────────
        ctk.CTkLabel(scroll, text="DATE RANGE",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#484f58",
                     anchor="w").pack(fill="x", pady=(0, 8))

        date_frame = ctk.CTkFrame(scroll, fg_color="#21262d",
                                   corner_radius=8)
        date_frame.pack(fill="x", pady=(0, 16))

        date_inner = ctk.CTkFrame(date_frame, fg_color="transparent")
        date_inner.pack(padx=14, pady=12, fill="x")

        # From
        ctk.CTkLabel(date_inner, text="From:",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0, 6))
        self.date_from = ctk.CTkEntry(
            date_inner, width=120, height=34,
            placeholder_text="YYYY-MM-DD",
            fg_color="#161b22", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12)
        )
        self.date_from.pack(side="left", padx=(0, 14))
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        self.date_from.insert(0, week_ago)

        # To
        ctk.CTkLabel(date_inner, text="To:",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0, 6))
        self.date_to = ctk.CTkEntry(
            date_inner, width=120, height=34,
            placeholder_text="YYYY-MM-DD",
            fg_color="#161b22", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12)
        )
        self.date_to.pack(side="left", padx=(0, 14))
        self.date_to.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Quick presets
        preset_row = ctk.CTkFrame(
            date_frame, fg_color="transparent")
        preset_row.pack(padx=14, pady=(0, 12), fill="x")

        ctk.CTkLabel(preset_row, text="Quick:",
                     font=ctk.CTkFont(size=11),
                     text_color="#484f58").pack(
            side="left", padx=(0, 8))

        for label, days in [
            ("Today", 0), ("Last 7 Days", 7),
            ("Last 30 Days", 30), ("Last 90 Days", 90)
        ]:
            ctk.CTkButton(
                preset_row, text=label,
                height=28, width=100,
                font=ctk.CTkFont(size=11),
                fg_color="#30363d", hover_color="#484f58",
                corner_radius=6,
                command=lambda d=days: self._set_preset(d)
            ).pack(side="left", padx=(0, 6))

        # ── Report cards ──────────────────────────────────────
        ctk.CTkLabel(scroll, text="AVAILABLE REPORTS",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#484f58",
                     anchor="w").pack(fill="x", pady=(0, 8))

        # Report card definitions
        reports = [
            {
                "title"   : "Entry Logs Report",
                "icon"    : "📋",
                "desc"    : "All face recognition events with name, time, camera and confidence score.",
                "formats" : [("Excel", "#3fb950", self._export_logs_excel),
                              ("PDF",   "#1f6feb", self._export_logs_pdf)],
                "color"   : "#163a6b",
                "border"  : "#1f6feb",
            },
            {
                "title"   : "Attendance Report",
                "icon"    : "✅",
                "desc"    : "Daily attendance showing Present / Late / Absent status for each registered user.",
                "formats" : [("Excel", "#3fb950", self._export_attendance_excel),
                              ("PDF",   "#1f6feb", self._export_attendance_pdf)],
                "color"   : "#1a4226",
                "border"  : "#3fb950",
            },
            {
                "title"   : "Alerts Report",
                "icon"    : "🔔",
                "desc"    : "All security alerts including unknown faces, spoofing attempts and system errors.",
                "formats" : [("Excel", "#3fb950", self._export_alerts_excel)],
                "color"   : "#4a1a18",
                "border"  : "#f85149",
            },
        ]

        for report in reports:
            self._make_report_card(scroll, report)

        # ── Status message ────────────────────────────────────
        self.status_label = ctk.CTkLabel(
            scroll, text="",
            font=ctk.CTkFont(size=13),
            text_color="#3fb950",
            wraplength=500
        )
        self.status_label.pack(pady=(16, 0))

    def _make_report_card(self, parent, report: dict):
        """Build one report type card."""
        card = ctk.CTkFrame(
            parent, fg_color=report["color"],
            corner_radius=10,
            border_width=1, border_color=report["border"]
        )
        card.pack(fill="x", pady=(0, 10))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=16, pady=14, fill="x")

        # Title row
        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row,
            text=f"{report['icon']}  {report['title']}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e6edf3"
        ).pack(side="left")

        # Export buttons
        btn_row = ctk.CTkFrame(title_row, fg_color="transparent")
        btn_row.pack(side="right")

        for fmt_label, fmt_color, fmt_cmd in report["formats"]:
            ctk.CTkButton(
                btn_row,
                text=f"⬇  {fmt_label}",
                height=32, width=100,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=fmt_color,
                hover_color="#2ea043" if fmt_color == "#3fb950"
                            else "#388bfd",
                corner_radius=6,
                command=fmt_cmd
            ).pack(side="left", padx=(6, 0))

        # Description
        ctk.CTkLabel(
            inner,
            text=report["desc"],
            font=ctk.CTkFont(size=12),
            text_color="#8b949e",
            anchor="w",
            wraplength=480
        ).pack(fill="x", pady=(6, 0))

    # =========================================================
    #  RIGHT PANEL — Exported Files
    # =========================================================

    def _build_right_panel(self):
        # Header
        hdr = ctk.CTkFrame(self.right, fg_color="#21262d",
                            corner_radius=0, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="📁  Exported Files",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#e6edf3").pack(
            side="left", padx=14, pady=10)

        ctk.CTkButton(
            hdr, text="🔄",
            width=32, height=28,
            font=ctk.CTkFont(size=13),
            fg_color="#21262d", hover_color="#30363d",
            corner_radius=6,
            command=self._load_files
        ).pack(side="right", padx=8)

        # Open folder button
        ctk.CTkButton(
            self.right,
            text="📂  Open Exports Folder",
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color="#21262d", hover_color="#30363d",
            corner_radius=8,
            command=self._open_exports_folder
        ).pack(fill="x", padx=10, pady=(8, 4))

        # Files scroll list
        self.files_scroll = ctk.CTkScrollableFrame(
            self.right, fg_color="transparent", corner_radius=0)
        self.files_scroll.pack(
            fill="both", expand=True, padx=8, pady=(0, 8))

    def _load_files(self):
        """Refresh the exported files list."""
        for w in self.files_scroll.winfo_children():
            w.destroy()

        files = self.exporter.get_export_files()

        if not files:
            ctk.CTkLabel(
                self.files_scroll,
                text="No exports yet.\nGenerate a report first.",
                font=ctk.CTkFont(size=12),
                text_color="#484f58",
                justify="center"
            ).pack(pady=30)
            return

        for f in files:
            self._make_file_row(f)

    def _make_file_row(self, file_info: dict):
        """Build one file row in the exports list."""
        is_excel = file_info["type"] == "Excel"
        is_pdf   = file_info["type"] == "PDF"

        icon      = "📗" if is_excel else "📕" if is_pdf else "📄"
        color     = "#3fb950" if is_excel else "#1f6feb" if is_pdf else "#8b949e"

        card = ctk.CTkFrame(
            self.files_scroll, fg_color="#21262d",
            corner_radius=8
        )
        card.pack(fill="x", pady=3)

        # Icon + name
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(top, text=icon,
                     font=ctk.CTkFont(size=14)).pack(side="left")
        ctk.CTkLabel(
            top,
            text=file_info["name"][:28] + "..."
                 if len(file_info["name"]) > 28
                 else file_info["name"],
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=color
        ).pack(side="left", padx=(6, 0))

        # Meta row
        meta = ctk.CTkFrame(card, fg_color="transparent")
        meta.pack(fill="x", padx=10, pady=(0, 4))

        ctk.CTkLabel(
            meta,
            text=f"{file_info['modified']}  •  {file_info['size']}",
            font=ctk.CTkFont(size=10),
            text_color="#484f58"
        ).pack(side="left")

        # Open button
        ctk.CTkButton(
            meta,
            text="Open",
            width=52, height=22,
            font=ctk.CTkFont(size=10),
            fg_color="#30363d", hover_color="#484f58",
            corner_radius=4,
            command=lambda p=file_info["path"]:
                self._open_file(p)
        ).pack(side="right")

    # =========================================================
    #  EXPORT ACTIONS
    # =========================================================

    def _run_export(self, fn, *args):
        """Run an export function in background thread."""
        self.status_label.configure(
            text="⏳  Generating report...",
            text_color="#d29922"
        )

        def _thread():
            result = fn(*args)
            self.after(0, lambda r=result: self._on_export_done(r))

        threading.Thread(target=_thread, daemon=True).start()

    def _on_export_done(self, result: dict):
        """Handle export completion."""
        if result["success"]:
            self.status_label.configure(
                text=f"✅  {result['message']}\n"
                     f"Saved to: {result['path']}",
                text_color="#3fb950"
            )
            self._load_files()   # refresh file list
        else:
            self.status_label.configure(
                text=f"❌  Export failed: {result['message']}",
                text_color="#f85149"
            )

    def _get_dates(self):
        """Get current date range from inputs."""
        df = self.date_from.get().strip() or None
        dt = self.date_to.get().strip()   or None
        return df, dt

    def _export_logs_excel(self):
        df, dt = self._get_dates()
        self._run_export(
            self.exporter.export_logs_excel, df, dt)

    def _export_logs_pdf(self):
        df, dt = self._get_dates()
        self._run_export(
            self.exporter.export_logs_pdf, df, dt)

    def _export_attendance_excel(self):
        df, dt = self._get_dates()
        if not df or not dt:
            self.status_label.configure(
                text="⚠  Please set both From and To dates.",
                text_color="#d29922")
            return
        self._run_export(
            self.exporter.export_attendance_excel, df, dt)

    def _export_attendance_pdf(self):
        df, dt = self._get_dates()
        if not df or not dt:
            self.status_label.configure(
                text="⚠  Please set both From and To dates.",
                text_color="#d29922")
            return
        self._run_export(
            self.exporter.export_attendance_pdf, df, dt)

    def _export_alerts_excel(self):
        df, dt = self._get_dates()
        self._run_export(
            self.exporter.export_alerts_excel, df, dt)

    # =========================================================
    #  HELPERS
    # =========================================================

    def _set_preset(self, days: int):
        """Set date range to a preset."""
        today  = datetime.now()
        if days == 0:
            from_d = today.strftime("%Y-%m-%d")
        else:
            from_d = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        to_d = today.strftime("%Y-%m-%d")

        self.date_from.delete(0, "end")
        self.date_from.insert(0, from_d)
        self.date_to.delete(0, "end")
        self.date_to.insert(0, to_d)

    def _open_file(self, path: str):
        """Open a file with the default system application."""
        try:
            if os.name == "nt":        # Windows
                os.startfile(path)
            elif sys.platform == "darwin":  # Mac
                subprocess.Popen(["open", path])
            else:                      # Linux
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.status_label.configure(
                text=f"Could not open file: {e}",
                text_color="#f85149")

    def _open_exports_folder(self):
        """Open the exports folder in file explorer."""
        from config.config import EXPORTS_DIR
        try:
            if os.name == "nt":
                os.startfile(EXPORTS_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", EXPORTS_DIR])
            else:
                subprocess.Popen(["xdg-open", EXPORTS_DIR])
        except Exception as e:
            self.status_label.configure(
                text=f"Could not open folder: {e}",
                text_color="#f85149")