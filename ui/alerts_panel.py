# ============================================================
#   FaceSecuritySystem — ui/alerts_panel.py
#   Module 10: Full Alerts Panel UI
# ============================================================

import customtkinter as ctk
import os
import sys
from PIL import Image
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.alert_manager import AlertManager


class AlertsPanel(ctk.CTkFrame):
    """
    Full Alerts Management Panel with 2 tabs:
      1. Live Alerts   — real-time unreviewed alerts with snapshots
      2. Alert History — full searchable alert history table
    """

    # Alert type colors
    TYPE_COLORS = {
        "unknown_face"    : ("#f85149", "#4a1a18"),
        "spoofing_attempt": ("#d29922", "#4a3a10"),
        "multiple_faces"  : ("#388bfd", "#163a6b"),
        "low_confidence"  : ("#8b949e", "#21262d"),
        "system_error"    : ("#f85149", "#4a1a18"),
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.am            = AlertManager()
        self._live_alerts  = []   # real-time alert queue
        self._build_ui()

        # Register callback for live updates
        self.am.add_callback(self._on_new_alert)

    # =========================================================
    #  UI BUILD
    # =========================================================

    def _build_ui(self):
        # ── Stats bar ─────────────────────────────────────────
        stats_bar = ctk.CTkFrame(
            self, fg_color="#161b22", height=52,
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        stats_bar.pack(fill="x", pady=(0, 10))
        stats_bar.pack_propagate(False)

        inner = ctk.CTkFrame(stats_bar, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self._stat_chips = {}
        for label, key, color in [
            ("Total Alerts",  "total",      "#8b949e"),
            ("Unreviewed",    "unreviewed", "#f85149"),
            ("Today",         "today",      "#d29922"),
        ]:
            chip = ctk.CTkFrame(inner, fg_color="#21262d",
                                 corner_radius=8)
            chip.pack(side="left", padx=8)
            ctk.CTkLabel(chip, text=label,
                         font=ctk.CTkFont(size=11),
                         text_color="#484f58").pack(
                side="left", padx=(10, 4), pady=8)
            val = ctk.CTkLabel(chip, text="—",
                                font=ctk.CTkFont(size=13, weight="bold"),
                                text_color=color)
            val.pack(side="left", padx=(0, 10), pady=8)
            self._stat_chips[key] = val

        # Mark all reviewed button
        ctk.CTkButton(
            inner, text="✓  Mark All Reviewed",
            height=34, width=160,
            font=ctk.CTkFont(size=12),
            fg_color="#21262d", hover_color="#3fb950",
            corner_radius=8,
            command=self._mark_all_reviewed
        ).pack(side="left", padx=16)

        # ── Tab bar ───────────────────────────────────────────
        tab_bar = ctk.CTkFrame(
            self, fg_color="#161b22", height=48,
            corner_radius=10,
            border_width=1, border_color="#21262d"
        )
        tab_bar.pack(fill="x", pady=(0, 10))
        tab_bar.pack_propagate(False)

        self._tab_btns   = {}
        self._tab_content = ctk.CTkFrame(self, fg_color="transparent")
        self._tab_content.pack(fill="both", expand=True)

        for tab_id, label in [
            ("live",    "🔴  Live Alerts"),
            ("history", "📋  Alert History"),
        ]:
            btn = ctk.CTkButton(
                tab_bar, text=label,
                height=36, width=160,
                font=ctk.CTkFont(size=13),
                fg_color="#21262d", hover_color="#30363d",
                text_color="#8b949e", corner_radius=8,
                command=lambda t=tab_id: self._switch_tab(t)
            )
            btn.pack(side="left", padx=(8, 4), pady=6)
            self._tab_btns[tab_id] = btn

        self._refresh_stats()
        self._switch_tab("live")

    def _switch_tab(self, tab_id: str):
        for tid, btn in self._tab_btns.items():
            if tid == tab_id:
                btn.configure(fg_color="#1f6feb", text_color="white")
            else:
                btn.configure(fg_color="#21262d", text_color="#8b949e")

        for w in self._tab_content.winfo_children():
            w.destroy()

        if   tab_id == "live":    self._tab_live()
        elif tab_id == "history": self._tab_history()

    # =========================================================
    #  TAB 1: LIVE ALERTS
    # =========================================================

    def _tab_live(self):
        outer = ctk.CTkFrame(
            self._tab_content, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        # Top action bar
        act_bar = ctk.CTkFrame(outer, fg_color="transparent")
        act_bar.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            act_bar, text="🔄  Refresh",
            height=34, width=110,
            font=ctk.CTkFont(size=13),
            fg_color="#21262d", hover_color="#30363d",
            corner_radius=8,
            command=self._switch_tab_live
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            act_bar, text="✓  Mark All Reviewed",
            height=34, width=170,
            font=ctk.CTkFont(size=13),
            fg_color="#21262d", hover_color="#3fb950",
            corner_radius=8,
            command=self._mark_all_reviewed
        ).pack(side="left")

        self._live_count = ctk.CTkLabel(
            act_bar, text="",
            font=ctk.CTkFont(size=12),
            text_color="#484f58"
        )
        self._live_count.pack(side="right")

        # Scroll area for alert cards
        self._live_scroll = ctk.CTkScrollableFrame(
            outer, fg_color="transparent", corner_radius=0)
        self._live_scroll.pack(fill="both", expand=True)

        self._render_live_alerts()

    def _switch_tab_live(self):
        self._switch_tab("live")

    def _render_live_alerts(self):
        for w in self._live_scroll.winfo_children():
            w.destroy()

        alerts = self.am.get_unreviewed()

        if hasattr(self, "_live_count"):
            self._live_count.configure(
                text=f"{len(alerts)} unreviewed alert(s)")

        if not alerts:
            # All clear
            clear_frame = ctk.CTkFrame(
                self._live_scroll, fg_color="transparent")
            clear_frame.pack(expand=True, pady=60)

            ctk.CTkLabel(clear_frame, text="✅",
                         font=ctk.CTkFont(size=56)).pack()
            ctk.CTkLabel(clear_frame,
                         text="All Clear!",
                         font=ctk.CTkFont(size=20, weight="bold"),
                         text_color="#3fb950").pack(pady=8)
            ctk.CTkLabel(clear_frame,
                         text="No unreviewed alerts at this time.",
                         font=ctk.CTkFont(size=13),
                         text_color="#484f58").pack()
            return

        for alert in alerts:
            self._make_alert_card(
                self._live_scroll, alert, show_review_btn=True)

    def _make_alert_card(self, parent, alert: dict,
                          show_review_btn: bool = True):
        """Build one alert card widget."""
        atype  = alert.get("alert_type", "unknown_face")
        colors = self.TYPE_COLORS.get(
            atype, ("#8b949e", "#21262d"))
        fg_color, bg_color = colors

        card = ctk.CTkFrame(parent, fg_color=bg_color,
                             corner_radius=10,
                             border_width=1, border_color=fg_color)
        card.pack(fill="x", pady=5)

        # Left accent stripe
        stripe = ctk.CTkFrame(card, fg_color=fg_color,
                               width=5, corner_radius=0)
        stripe.pack(side="left", fill="y")

        # Content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(side="left", fill="both",
                     expand=True, padx=14, pady=12)

        # Top row: type + time
        top_row = ctk.CTkFrame(content, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(
            top_row,
            text=f"⚠  {atype.replace('_',' ').title()}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=fg_color
        ).pack(side="left")

        ctk.CTkLabel(
            top_row,
            text=f"{alert.get('alert_date','')}  "
                 f"{str(alert.get('alert_time',''))[:8]}",
            font=ctk.CTkFont(size=12),
            text_color="#484f58"
        ).pack(side="right")

        # Camera info
        ctk.CTkLabel(
            content,
            text=f"📷  Camera {alert.get('camera_id','')}  —  "
                 f"{alert.get('camera_label','')}",
            font=ctk.CTkFont(size=12),
            text_color="#8b949e",
            anchor="w"
        ).pack(fill="x", pady=(4, 0))

        # Snapshot thumbnail
        snap = alert.get("snapshot_path")
        if snap and os.path.exists(snap):
            try:
                pil_img = Image.open(snap)
                pil_img.thumbnail((200, 130))
                ctk_img = ctk.CTkImage(pil_img, size=(200, 130))
                img_lbl = ctk.CTkLabel(
                    content, image=ctk_img, text="",
                    corner_radius=6)
                img_lbl.image = ctk_img
                img_lbl.pack(anchor="w", pady=(8, 0))
            except Exception:
                pass

        # Review button
        if show_review_btn:
            btn_row = ctk.CTkFrame(content, fg_color="transparent")
            btn_row.pack(fill="x", pady=(8, 0))

            ctk.CTkButton(
                btn_row,
                text="✓  Mark as Reviewed",
                height=30, width=160,
                font=ctk.CTkFont(size=12),
                fg_color="#21262d", hover_color="#3fb950",
                corner_radius=6,
                command=lambda aid=alert["alert_id"]:
                    self._mark_reviewed(aid)
            ).pack(side="left")

            # View snapshot button
            if snap and os.path.exists(snap):
                ctk.CTkButton(
                    btn_row,
                    text="🖼  View Snapshot",
                    height=30, width=140,
                    font=ctk.CTkFont(size=12),
                    fg_color="#21262d", hover_color="#30363d",
                    corner_radius=6,
                    command=lambda p=snap: self._view_snapshot(p)
                ).pack(side="left", padx=(8, 0))

    def _mark_reviewed(self, alert_id: int):
        self.am.mark_reviewed(alert_id)
        self._refresh_stats()
        self._render_live_alerts()

    def _mark_all_reviewed(self):
        self.am.mark_all_reviewed()
        self._refresh_stats()
        self._render_live_alerts()

    # =========================================================
    #  TAB 2: ALERT HISTORY
    # =========================================================

    def _tab_history(self):
        outer = ctk.CTkFrame(
            self._tab_content, fg_color="transparent")
        outer.pack(fill="both", expand=True)

        # Filter bar
        fbar = ctk.CTkFrame(outer, fg_color="#161b22",
                             corner_radius=10,
                             border_width=1, border_color="#21262d")
        fbar.pack(fill="x", pady=(0, 10))

        finner = ctk.CTkFrame(fbar, fg_color="transparent")
        finner.pack(padx=16, pady=10, fill="x")

        ctk.CTkLabel(finner, text="From:",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0,4))
        self._hist_from = ctk.CTkEntry(
            finner, width=110, height=32,
            placeholder_text="YYYY-MM-DD",
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12))
        self._hist_from.pack(side="left", padx=(0,10))

        ctk.CTkLabel(finner, text="To:",
                     font=ctk.CTkFont(size=12),
                     text_color="#8b949e").pack(side="left", padx=(0,4))
        self._hist_to = ctk.CTkEntry(
            finner, width=110, height=32,
            placeholder_text="YYYY-MM-DD",
            fg_color="#21262d", border_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12))
        self._hist_to.pack(side="left", padx=(0,10))

        self._hist_type = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(
            finner, variable=self._hist_type,
            values=["All", "unknown_face", "spoofing_attempt",
                    "multiple_faces", "low_confidence", "system_error"],
            width=170, height=32,
            fg_color="#21262d", button_color="#30363d",
            text_color="#e6edf3", font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0,10))

        ctk.CTkButton(
            finner, text="🔍  Search",
            height=32, width=90,
            font=ctk.CTkFont(size=12),
            fg_color="#1f6feb", hover_color="#388bfd",
            corner_radius=6,
            command=self._search_history
        ).pack(side="left", padx=(0,6))

        ctk.CTkButton(
            finner, text="Today",
            height=32, width=70,
            font=ctk.CTkFont(size=12),
            fg_color="#21262d", hover_color="#30363d",
            corner_radius=6,
            command=self._filter_today_hist
        ).pack(side="left")

        self._hist_count = ctk.CTkLabel(
            finner, text="",
            font=ctk.CTkFont(size=12),
            text_color="#484f58")
        self._hist_count.pack(side="right")

        # Table
        table = ctk.CTkFrame(outer, fg_color="#161b22",
                              corner_radius=10,
                              border_width=1, border_color="#21262d")
        table.pack(fill="both", expand=True)

        hist_cols = [
            ("#",          40),
            ("Type",      180),
            ("Date",      110),
            ("Time",       90),
            ("Camera",    130),
            ("Reviewed",   90),
            ("Snapshot",  100),
        ]
        hdr = ctk.CTkFrame(table, fg_color="#21262d",
                            corner_radius=0, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        for col, width in hist_cols:
            ctk.CTkLabel(hdr, text=col,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#8b949e",
                         width=width, anchor="w").pack(
                side="left", padx=10)

        self._hist_rows = ctk.CTkScrollableFrame(
            table, fg_color="transparent", corner_radius=0)
        self._hist_rows.pack(fill="both", expand=True)

        self._search_history()

    def _search_history(self):
        df   = self._hist_from.get().strip() or None
        dt   = self._hist_to.get().strip()   or None
        atype = self._hist_type.get()

        alerts = self.am.get_all_alerts(
            date_from  = df,
            date_to    = dt,
            alert_type = None if atype == "All" else atype
        )

        self._hist_count.configure(
            text=f"{len(alerts)} record(s)")

        for w in self._hist_rows.winfo_children():
            w.destroy()

        if not alerts:
            ctk.CTkLabel(self._hist_rows,
                         text="No alerts found for selected filters.",
                         font=ctk.CTkFont(size=13),
                         text_color="#484f58").pack(pady=40)
            return

        for i, alert in enumerate(alerts):
            row_bg  = "#161b22" if i % 2 == 0 else "#1a1f27"
            atype_  = alert.get("alert_type", "")
            colors  = self.TYPE_COLORS.get(
                atype_, ("#8b949e", "#21262d"))
            a_color = colors[0]

            reviewed     = alert.get("is_reviewed", 0)
            rev_text     = "✓ Yes" if reviewed else "✗ No"
            rev_color    = "#3fb950" if reviewed else "#f85149"
            snap         = alert.get("snapshot_path")
            has_snap     = snap and os.path.exists(str(snap))

            row = ctk.CTkFrame(self._hist_rows, fg_color=row_bg,
                                corner_radius=0, height=38)
            row.pack(fill="x")
            row.pack_propagate(False)

            for text, width in [
                (str(i + 1),                              40),
                (atype_.replace("_"," ").title(),        180),
                (str(alert.get("alert_date", "")),        110),
                (str(alert.get("alert_time", ""))[:8],    90),
                (str(alert.get("camera_label", "")),      130),
            ]:
                tc = a_color if text == atype_.replace(
                    "_"," ").title() else "#c9d1d9"
                ctk.CTkLabel(row, text=text,
                             font=ctk.CTkFont(size=12),
                             text_color=tc,
                             width=width, anchor="w").pack(
                    side="left", padx=10)

            ctk.CTkLabel(row, text=rev_text,
                         font=ctk.CTkFont(size=12),
                         text_color=rev_color,
                         width=90, anchor="w").pack(side="left", padx=10)

            if has_snap:
                ctk.CTkButton(
                    row, text="🖼 View",
                    width=80, height=26,
                    font=ctk.CTkFont(size=11),
                    fg_color="#21262d", hover_color="#30363d",
                    corner_radius=4,
                    command=lambda p=snap: self._view_snapshot(p)
                ).pack(side="left", padx=10)
            else:
                ctk.CTkLabel(row, text="—",
                             font=ctk.CTkFont(size=12),
                             text_color="#484f58",
                             width=100, anchor="w").pack(
                    side="left", padx=10)

    def _filter_today_hist(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._hist_from.delete(0, "end")
        self._hist_from.insert(0, today)
        self._hist_to.delete(0, "end")
        self._hist_to.insert(0, today)
        self._search_history()

    # =========================================================
    #  SNAPSHOT VIEWER
    # =========================================================

    def _view_snapshot(self, path: str):
        """Open a popup to show the alert snapshot image."""
        if not path or not os.path.exists(path):
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Alert Snapshot")
        dialog.configure(fg_color="#0d1117")
        dialog.grab_set()

        try:
            pil_img = Image.open(path)
            max_w, max_h = 800, 550
            pil_img.thumbnail((max_w, max_h))
            w, h    = pil_img.size
            ctk_img = ctk.CTkImage(pil_img, size=(w, h))

            dialog.geometry(f"{w + 40}x{h + 100}")

            ctk.CTkLabel(dialog, text=os.path.basename(path),
                         font=ctk.CTkFont(size=11),
                         text_color="#484f58").pack(pady=(12, 4))

            img_lbl = ctk.CTkLabel(dialog, image=ctk_img, text="")
            img_lbl.image = ctk_img
            img_lbl.pack(padx=20, pady=4)

            ctk.CTkButton(dialog, text="Close",
                          height=36, width=100,
                          fg_color="#21262d", hover_color="#30363d",
                          corner_radius=8,
                          command=dialog.destroy).pack(pady=10)

        except Exception as e:
            ctk.CTkLabel(dialog,
                         text=f"Could not load image:\n{e}",
                         font=ctk.CTkFont(size=13),
                         text_color="#f85149").pack(pady=30)
            dialog.geometry("300x150")

    # =========================================================
    #  LIVE ALERT CALLBACK
    # =========================================================

    def _on_new_alert(self, alert_data: dict):
        """
        Called automatically when AlertManager fires an alert.
        Updates the live tab in real-time.
        """
        self._live_alerts.insert(0, alert_data)
        self.after(0, self._refresh_stats)
        self.after(0, self._maybe_refresh_live)

    def _maybe_refresh_live(self):
        """Refresh live tab if it's currently active."""
        if hasattr(self, "_live_scroll"):
            self._render_live_alerts()

    # =========================================================
    #  STATS
    # =========================================================

    def _refresh_stats(self):
        stats = self.am.get_stats()
        self._stat_chips["total"].configure(
            text=str(stats["total"]))
        self._stat_chips["unreviewed"].configure(
            text=str(stats["unreviewed"]))
        self._stat_chips["today"].configure(
            text=str(stats["today"]))

    # =========================================================
    #  CLEANUP
    # =========================================================

    def destroy(self):
        self.am.remove_callback(self._on_new_alert)
        super().destroy()