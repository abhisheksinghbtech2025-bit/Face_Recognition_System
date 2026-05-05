# ============================================================
#   FaceSecuritySystem — ui/logs_panel.py
#   Module 9: Entry Logs & Attendance UI Panel
#   Full logs table, attendance view, daily stats, filters
# ============================================================

import customtkinter as ctk
import sys
import os
from datetime import datetime, timedelta
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.logger import EntryLogger


class LogsPanel(ctk.CTkFrame):
    """
    Full Logs & Attendance Panel with 3 tabs:
      1. Entry Logs    — full filterable log table
      2. Attendance    — daily attendance per user
      3. Summary       — attendance summary over date range
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.logger = EntryLogger()
        self._build_ui()

    # =========================================================
    #  UI BUILD
    # =========================================================

    def _build_ui(self):
        # ── Tab bar ───────────────────────────────────────────
        tab_bar = ctk.CTkFrame(
            self, fg_color="#161b22", height=48,
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        tab_bar.pack(fill="x", pady=(0, 10))
        tab_bar.pack_propagate(False)

        self.tab_btns    = {}
        self.active_tab  = None
        self.tab_content = ctk.CTkFrame(
            self, fg_color="transparent"
        )
        self.tab_content.pack(fill="both", expand=True)

        tabs = [
            ("logs",       "📋  Entry Logs"),
            ("attendance", "✅  Attendance"),
            ("summary",    "📊  Summary"),
        ]

        for tab_id, label in tabs:
            btn = ctk.CTkButton(
                tab_bar, text=label,
                height=36, width=150,
                font=ctk.CTkFont(size=13),
                fg_color="#21262d",
                hover_color="#30363d",
                text_color="#8b949e",
                corner_radius=8,
                command=lambda t=tab_id: self._switch_tab(t)
            )
            btn.pack(side="left", padx=(8, 4), pady=6)
            self.tab_btns[tab_id] = btn

        self._switch_tab("logs")

    def _switch_tab(self, tab_id: str):
        for tid, btn in self.tab_btns.items():
            if tid == tab_id:
                btn.configure(fg_color="#1f6feb", text_color="white")
            else:
                btn.configure(fg_color="#21262d", text_color="#8b949e")

        for w in self.tab_content.winfo_children():
            w.destroy()

        self.active_tab = tab_id
        if   tab_id == "logs":       self._tab_logs()
        elif tab_id == "attendance":  self._tab_attendance()
        elif tab_id == "summary":     self._tab_summary()

    # =========================================================
    #  TAB 1: ENTRY LOGS
    # =========================================================

    def _tab_logs(self):
        outer = ctk.CTkFrame(self.tab_content, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        # ── Filter bar ────────────────────────────────────────
        fbar = ctk.CTkFrame(outer, fg_color="#161b22",
                             corner_radius=10,
                             border_width=1, border_color="#21262d")
        fbar.pack(fill="x", pady=(0, 10))

        finner = ctk.CTkFrame(fbar, fg_color="transparent")
        finner.pack(padx=16, pady=10, fill="x")

        # Date from
        ctk.CTkLabel(finner, text="From:",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.log_from = ctk.CTkEntry(
            finner, width=110, height=32,
            placeholder_text="YYYY-MM-DD",
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12))
        self.log_from.pack(side="left", padx=(0, 10))
        self.log_from.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Date to
        ctk.CTkLabel(finner, text="To:",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.log_to = ctk.CTkEntry(
            finner, width=110, height=32,
            placeholder_text="YYYY-MM-DD",
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12))
        self.log_to.pack(side="left", padx=(0, 10))
        self.log_to.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Status filter
        ctk.CTkLabel(finner, text="Status:",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0, 4))
        self.log_status = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(
            finner, variable=self.log_status,
            values=["All", "known", "unknown", "spoofing_attempt"],
            width=150, height=32,
            fg_color="#21262d", button_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 10))

        # Name search
        self.log_name = ctk.CTkEntry(
            finner, width=130, height=32,
            placeholder_text="Search name...",
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12))
        self.log_name.pack(side="left", padx=(0, 10))

        # Search button
        ctk.CTkButton(
            finner, text="🔍  Search",
            height=32, width=100,
            font=ctk.CTkFont(size=12),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=6,
            command=self._search_logs
        ).pack(side="left", padx=(0, 6))

        # Today shortcut
        ctk.CTkButton(
            finner, text="Today",
            height=32, width=70,
            font=ctk.CTkFont(size=12),
            fg_color="#21262d", hover_color="#30363d",
            corner_radius=6,
            command=self._filter_today
        ).pack(side="left")

        # Record count
        self.log_count = ctk.CTkLabel(
            finner, text="",
            font=ctk.CTkFont(size=12),
            text_color="#484f58")
        self.log_count.pack(side="right")

        # ── Stats row ─────────────────────────────────────────
        stats_row = ctk.CTkFrame(outer, fg_color="transparent")
        stats_row.pack(fill="x", pady=(0, 10))

        self.stat_chips = {}
        for label, key, color in [
            ("Total",    "total",   "#8b949e"),
            ("Known",    "known",   "#3fb950"),
            ("Unknown",  "unknown", "#f85149"),
            ("Spoofing", "spoof",   "#d29922"),
        ]:
            chip = ctk.CTkFrame(stats_row, fg_color="#161b22",
                                 corner_radius=8,
                                 border_width=1, border_color="#21262d")
            chip.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(chip, text=label,
                         font=ctk.CTkFont(size=11),
                         text_color="#484f58").pack(
                side="left", padx=(10, 4), pady=8)
            val_lbl = ctk.CTkLabel(chip, text="0",
                                    font=ctk.CTkFont(size=13, weight="bold"),
                                    text_color=color)
            val_lbl.pack(side="left", padx=(0, 10), pady=8)
            self.stat_chips[key] = val_lbl

        # ── Table ─────────────────────────────────────────────
        table_frame = ctk.CTkFrame(outer, fg_color="#161b22",
                                    corner_radius=10,
                                    border_width=1, border_color="#21262d")
        table_frame.pack(fill="both", expand=True)

        # Header
        cols = [
            ("#",          40),
            ("Name",       160),
            ("Date",       110),
            ("Time",       90),
            ("Camera",     130),
            ("Status",     110),
            ("Confidence", 100),
        ]

        hdr = ctk.CTkFrame(table_frame, fg_color="#21262d",
                            corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        for col, width in cols:
            ctk.CTkLabel(hdr, text=col,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#8b949e",
                         width=width, anchor="w").pack(
                side="left", padx=10)

        # Rows
        self.log_rows_frame = ctk.CTkScrollableFrame(
            table_frame, fg_color="transparent", corner_radius=0
        )
        self.log_rows_frame.pack(fill="both", expand=True)

        self._search_logs()

    def _search_logs(self):
        status = self.log_status.get()
        name   = self.log_name.get().strip()
        df     = self.log_from.get().strip()
        dt     = self.log_to.get().strip()

        logs = self.logger.get_logs(
            date_from = df or None,
            date_to   = dt or None,
            status    = None if status == "All" else status,
            name      = name or None
        )

        self.log_count.configure(text=f"{len(logs)} record(s)")

        # Update stats
        known    = sum(1 for l in logs if l["status"] == "known")
        unknown  = sum(1 for l in logs if l["status"] == "unknown")
        spoof    = sum(1 for l in logs if l["status"] == "spoofing_attempt")
        self.stat_chips["total"].configure(text=str(len(logs)))
        self.stat_chips["known"].configure(text=str(known))
        self.stat_chips["unknown"].configure(text=str(unknown))
        self.stat_chips["spoof"].configure(text=str(spoof))

        # Clear rows
        for w in self.log_rows_frame.winfo_children():
            w.destroy()

        if not logs:
            ctk.CTkLabel(self.log_rows_frame,
                         text="No entries found for selected filters.",
                         font=ctk.CTkFont(size=13),
                         text_color="#484f58").pack(pady=40)
            return

        for i, log in enumerate(logs):
            row_bg  = "#161b22" if i % 2 == 0 else "#1a1f27"
            status_ = log.get("status", "")
            s_color = ("#3fb950" if status_ == "known"
                       else "#f85149" if status_ == "unknown"
                       else "#d29922")
            conf    = (f"{log['confidence_score']:.0%}"
                       if log.get("confidence_score") else "—")

            row = ctk.CTkFrame(self.log_rows_frame, fg_color=row_bg,
                                corner_radius=0, height=36)
            row.pack(fill="x")
            row.pack_propagate(False)

            for text, width in [
                (str(i + 1),                           40),
                (str(log.get("name", "")),            160),
                (str(log.get("entry_date", "")),      110),
                (str(log.get("entry_time", ""))[:8],   90),
                (str(log.get("camera_label", "")),    130),
            ]:
                ctk.CTkLabel(row, text=text,
                             font=ctk.CTkFont(size=12),
                             text_color="#c9d1d9",
                             width=width, anchor="w").pack(
                    side="left", padx=10)

            ctk.CTkLabel(row, text=status_.title(),
                         font=ctk.CTkFont(size=12),
                         text_color=s_color,
                         width=110, anchor="w").pack(side="left", padx=10)

            ctk.CTkLabel(row, text=conf,
                         font=ctk.CTkFont(size=12),
                         text_color="#8b949e",
                         width=100, anchor="w").pack(side="left", padx=10)

    def _filter_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_from.delete(0, "end")
        self.log_from.insert(0, today)
        self.log_to.delete(0, "end")
        self.log_to.insert(0, today)
        self._search_logs()

    # =========================================================
    #  TAB 2: DAILY ATTENDANCE
    # =========================================================

    def _tab_attendance(self):
        outer = ctk.CTkFrame(self.tab_content, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        # ── Date selector ─────────────────────────────────────
        ctrl = ctk.CTkFrame(outer, fg_color="#161b22",
                             corner_radius=10,
                             border_width=1, border_color="#21262d")
        ctrl.pack(fill="x", pady=(0, 10))
        inner = ctk.CTkFrame(ctrl, fg_color="transparent")
        inner.pack(padx=16, pady=10, fill="x")

        ctk.CTkLabel(inner, text="Date:",
                     font=ctk.CTkFont(size=13),
                     text_color="#8b949e").pack(side="left", padx=(0, 8))

        self.att_date = ctk.CTkEntry(
            inner, width=130, height=34,
            placeholder_text="YYYY-MM-DD",
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=13))
        self.att_date.pack(side="left", padx=(0, 10))
        self.att_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ctk.CTkButton(
            inner, text="📋  Load Attendance",
            height=34, width=160,
            font=ctk.CTkFont(size=13),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8,
            command=self._load_attendance
        ).pack(side="left", padx=(0, 10))

        # Yesterday
        ctk.CTkButton(
            inner, text="◀ Yesterday",
            height=34, width=110,
            font=ctk.CTkFont(size=12),
            fg_color="#21262d", hover_color="#30363d",
            corner_radius=8,
            command=lambda: self._shift_att_date(-1)
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            inner, text="Today",
            height=34, width=80,
            font=ctk.CTkFont(size=12),
            fg_color="#21262d", hover_color="#30363d",
            corner_radius=8,
            command=lambda: self._set_att_date(
                datetime.now().strftime("%Y-%m-%d"))
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            inner, text="Tomorrow ▶",
            height=34, width=110,
            font=ctk.CTkFont(size=12),
            fg_color="#21262d", hover_color="#30363d",
            corner_radius=8,
            command=lambda: self._shift_att_date(1)
        ).pack(side="left")

        # Summary chips
        self.att_chips = {}
        chip_row = ctk.CTkFrame(outer, fg_color="transparent")
        chip_row.pack(fill="x", pady=(0, 10))

        for label, key, color in [
            ("Present", "present", "#3fb950"),
            ("Late",    "late",    "#d29922"),
            ("Absent",  "absent",  "#f85149"),
            ("Total",   "total",   "#8b949e"),
        ]:
            chip = ctk.CTkFrame(chip_row, fg_color="#161b22",
                                 corner_radius=8,
                                 border_width=1, border_color="#21262d")
            chip.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(chip, text=label,
                         font=ctk.CTkFont(size=11),
                         text_color="#484f58").pack(
                side="left", padx=(10, 4), pady=8)
            val = ctk.CTkLabel(chip, text="—",
                                font=ctk.CTkFont(size=13, weight="bold"),
                                text_color=color)
            val.pack(side="left", padx=(0, 10), pady=8)
            self.att_chips[key] = val

        # Table
        table = ctk.CTkFrame(outer, fg_color="#161b22",
                              corner_radius=10,
                              border_width=1, border_color="#21262d")
        table.pack(fill="both", expand=True)

        # Header
        att_cols = [
            ("#",           40),
            ("Name",       200),
            ("Department", 160),
            ("Role",       100),
            ("Status",     100),
            ("Entry Time", 110),
        ]
        hdr = ctk.CTkFrame(table, fg_color="#21262d",
                            corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        for col, width in att_cols:
            ctk.CTkLabel(hdr, text=col,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#8b949e",
                         width=width, anchor="w").pack(
                side="left", padx=10)

        self.att_rows = ctk.CTkScrollableFrame(
            table, fg_color="transparent", corner_radius=0)
        self.att_rows.pack(fill="both", expand=True)

        self._load_attendance()

    def _load_attendance(self):
        target = self.att_date.get().strip()
        try:
            datetime.strptime(target, "%Y-%m-%d")
        except ValueError:
            return

        records = self.logger.get_attendance_for_date(target)

        present = sum(1 for r in records if r["status"] == "Present")
        late    = sum(1 for r in records if r["status"] == "Late")
        absent  = sum(1 for r in records if r["status"] == "Absent")

        self.att_chips["present"].configure(text=str(present))
        self.att_chips["late"].configure(text=str(late))
        self.att_chips["absent"].configure(text=str(absent))
        self.att_chips["total"].configure(text=str(len(records)))

        for w in self.att_rows.winfo_children():
            w.destroy()

        if not records:
            ctk.CTkLabel(self.att_rows,
                         text="No users registered yet.",
                         font=ctk.CTkFont(size=13),
                         text_color="#484f58").pack(pady=40)
            return

        for i, rec in enumerate(records):
            row_bg = "#161b22" if i % 2 == 0 else "#1a1f27"
            s      = rec["status"]
            s_color = ("#3fb950" if s == "Present"
                       else "#d29922" if s == "Late"
                       else "#f85149")

            row = ctk.CTkFrame(self.att_rows, fg_color=row_bg,
                                corner_radius=0, height=38)
            row.pack(fill="x")
            row.pack_propagate(False)

            for text, width in [
                (str(i + 1),              40),
                (rec["name"],            200),
                (rec["department"],      160),
                (rec["role"].title(),    100),
            ]:
                ctk.CTkLabel(row, text=text,
                             font=ctk.CTkFont(size=12),
                             text_color="#c9d1d9",
                             width=width, anchor="w").pack(
                    side="left", padx=10)

            ctk.CTkLabel(row, text=s,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=s_color,
                         width=100, anchor="w").pack(side="left", padx=10)

            ctk.CTkLabel(row, text=rec["entry_time"],
                         font=ctk.CTkFont(size=12),
                         text_color="#8b949e",
                         width=110, anchor="w").pack(side="left", padx=10)

    def _shift_att_date(self, days: int):
        current = self.att_date.get().strip()
        try:
            d = datetime.strptime(current, "%Y-%m-%d")
            new_d = d + timedelta(days=days)
            self._set_att_date(new_d.strftime("%Y-%m-%d"))
        except ValueError:
            pass

    def _set_att_date(self, date_str: str):
        self.att_date.delete(0, "end")
        self.att_date.insert(0, date_str)
        self._load_attendance()

    # =========================================================
    #  TAB 3: ATTENDANCE SUMMARY
    # =========================================================

    def _tab_summary(self):
        outer = ctk.CTkFrame(self.tab_content, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        # ── Date range selector ───────────────────────────────
        ctrl = ctk.CTkFrame(outer, fg_color="#161b22",
                             corner_radius=10,
                             border_width=1, border_color="#21262d")
        ctrl.pack(fill="x", pady=(0, 10))
        inner = ctk.CTkFrame(ctrl, fg_color="transparent")
        inner.pack(padx=16, pady=10, fill="x")

        ctk.CTkLabel(inner, text="From:",
                     font=ctk.CTkFont(size=13),
                     text_color="#8b949e").pack(side="left", padx=(0, 6))
        self.sum_from = ctk.CTkEntry(
            inner, width=120, height=34,
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=13))
        self.sum_from.pack(side="left", padx=(0, 12))
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        self.sum_from.insert(0, week_ago)

        ctk.CTkLabel(inner, text="To:",
                     font=ctk.CTkFont(size=13),
                     text_color="#8b949e").pack(side="left", padx=(0, 6))
        self.sum_to = ctk.CTkEntry(
            inner, width=120, height=34,
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=13))
        self.sum_to.pack(side="left", padx=(0, 12))
        self.sum_to.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ctk.CTkButton(
            inner, text="📊  Generate Summary",
            height=34, width=180,
            font=ctk.CTkFont(size=13),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=8,
            command=self._load_summary
        ).pack(side="left", padx=(0, 10))

        # Presets
        for label, days in [("Last 7 days", 7),
                              ("Last 30 days", 30)]:
            ctk.CTkButton(
                inner, text=label,
                height=34, width=110,
                font=ctk.CTkFont(size=12),
                fg_color="#21262d", hover_color="#30363d",
                corner_radius=8,
                command=lambda d=days: self._preset_summary(d)
            ).pack(side="left", padx=(0, 6))

        # Table
        table = ctk.CTkFrame(outer, fg_color="#161b22",
                              corner_radius=10,
                              border_width=1, border_color="#21262d")
        table.pack(fill="both", expand=True, pady=(10, 0))

        sum_cols = [
            ("#",           40),
            ("Name",       170),
            ("Department", 150),
            ("Present",     80),
            ("Late",        70),
            ("Absent",      80),
            ("Days",        70),
            ("Attendance",  110),
        ]
        hdr = ctk.CTkFrame(table, fg_color="#21262d",
                            corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        for col, width in sum_cols:
            ctk.CTkLabel(hdr, text=col,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#8b949e",
                         width=width, anchor="w").pack(
                side="left", padx=10)

        self.sum_rows = ctk.CTkScrollableFrame(
            table, fg_color="transparent", corner_radius=0)
        self.sum_rows.pack(fill="both", expand=True)

        self._load_summary()

    def _load_summary(self):
        df = self.sum_from.get().strip()
        dt = self.sum_to.get().strip()

        try:
            datetime.strptime(df, "%Y-%m-%d")
            datetime.strptime(dt, "%Y-%m-%d")
        except ValueError:
            return

        summary = self.logger.get_attendance_summary(df, dt)

        for w in self.sum_rows.winfo_children():
            w.destroy()

        users = summary.get("users", [])
        if not users:
            ctk.CTkLabel(self.sum_rows,
                         text="No data for this date range.",
                         font=ctk.CTkFont(size=13),
                         text_color="#484f58").pack(pady=40)
            return

        for i, u in enumerate(users):
            row_bg = "#161b22" if i % 2 == 0 else "#1a1f27"
            pct    = u["percentage"]
            pct_color = ("#3fb950" if pct >= 80
                         else "#d29922" if pct >= 60
                         else "#f85149")

            row = ctk.CTkFrame(self.sum_rows, fg_color=row_bg,
                                corner_radius=0, height=38)
            row.pack(fill="x")
            row.pack_propagate(False)

            for text, width in [
                (str(i + 1),         40),
                (u["name"],         170),
                (u["department"],   150),
            ]:
                ctk.CTkLabel(row, text=text,
                             font=ctk.CTkFont(size=12),
                             text_color="#c9d1d9",
                             width=width, anchor="w").pack(
                    side="left", padx=10)

            ctk.CTkLabel(row, text=str(u["present"]),
                         font=ctk.CTkFont(size=12),
                         text_color="#3fb950",
                         width=80, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(u["late"]),
                         font=ctk.CTkFont(size=12),
                         text_color="#d29922",
                         width=70, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(u["absent"]),
                         font=ctk.CTkFont(size=12),
                         text_color="#f85149",
                         width=80, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(u["total_days"]),
                         font=ctk.CTkFont(size=12),
                         text_color="#8b949e",
                         width=70, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=f"{pct}%",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=pct_color,
                         width=110, anchor="w").pack(side="left", padx=10)

    def _preset_summary(self, days: int):
        today    = datetime.now()
        from_d   = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        to_d     = today.strftime("%Y-%m-%d")
        self.sum_from.delete(0, "end")
        self.sum_from.insert(0, from_d)
        self.sum_to.delete(0, "end")
        self.sum_to.insert(0, to_d)
        self._load_summary()