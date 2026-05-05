# ============================================================
#   FaceSecuritySystem — modules/logger.py
#   Module 9: Entry Logging & Attendance Tracking
#   Handles all log creation, attendance marking, and queries
# ============================================================

import sys
import os
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import db


class EntryLogger:
    """
    Handles all entry logging and attendance tracking.

    Features:
        - Log every face recognition event
        - Mark attendance (Present / Late / Absent)
        - Query logs by date, name, status, camera
        - Generate attendance summary per user
        - Throttle duplicate logs (once per minute per person)

    Usage:
        logger = EntryLogger()
        logger.log(name="John", user_id=1, camera_id=0,
                   camera_label="Front Gate", status="known",
                   confidence=0.92)
        summary = logger.get_attendance_summary("2024-01-01", "2024-01-31")
    """

    # Work hours config
    WORK_START_HOUR  = 9    # 9:00 AM
    LATE_AFTER_HOUR  = 9
    LATE_AFTER_MIN   = 15   # Late if after 9:15 AM

    def __init__(self):
        self._throttle = {}   # name → last log datetime
        print("[LOGGER] EntryLogger ready.")

    # =========================================================
    #  CORE LOG METHOD
    # =========================================================

    def log(self, name: str, user_id, camera_id: int,
            camera_label: str, status: str,
            confidence: float = None,
            snapshot_path: str = None,
            throttle_seconds: int = 60) -> dict:
        """
        Log a recognition event to the database.

        Args:
            name:             Person's name or "Unknown"
            user_id:          DB user ID (None for unknowns)
            camera_id:        Camera index number
            camera_label:     Human-readable camera name
            status:           "known" | "unknown" | "spoofing_attempt"
            confidence:       Recognition confidence 0.0-1.0
            snapshot_path:    Path to saved snapshot (optional)
            throttle_seconds: Min seconds between logs for same person

        Returns:
            {"logged": bool, "log_id": int, "reason": str}
        """
        now = datetime.now()

        # Throttle check — avoid flooding DB
        last = self._throttle.get(name)
        if last and (now - last).total_seconds() < throttle_seconds:
            return {
                "logged" : False,
                "log_id" : None,
                "reason" : f"Throttled — last logged {int((now-last).total_seconds())}s ago"
            }

        self._throttle[name] = now

        log_id = db.add_log(
            user_id          = user_id,
            name             = name,
            camera_id        = camera_id,
            camera_label     = camera_label,
            entry_date       = now.strftime("%Y-%m-%d"),
            entry_time       = now.strftime("%H:%M:%S"),
            status           = status,
            confidence_score = round(confidence, 3) if confidence else None,
            snapshot_path    = snapshot_path
        )

        if log_id:
            print(f"[LOGGER] Logged: {name} | {status} | "
                  f"Cam {camera_id} | {now.strftime('%H:%M:%S')}")
            return {"logged": True, "log_id": log_id, "reason": "OK"}

        return {"logged": False, "log_id": None, "reason": "DB error"}

    # =========================================================
    #  QUERY METHODS
    # =========================================================

    def get_logs(self, date_from: str = None,
                 date_to:   str = None,
                 status:    str = None,
                 name:      str = None,
                 camera_id: int = None,
                 limit:     int = None) -> list:
        """
        Flexible log query with multiple filters.

        Args:
            date_from:  "YYYY-MM-DD" start date
            date_to:    "YYYY-MM-DD" end date
            status:     "known" | "unknown" | "spoofing_attempt"
            name:       Filter by person name (partial match)
            camera_id:  Filter by specific camera
            limit:      Max number of rows to return

        Returns:
            List of log dicts ordered by newest first
        """
        query  = "SELECT * FROM entry_logs WHERE 1=1"
        params = []

        if date_from:
            query += " AND entry_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND entry_date <= %s"
            params.append(date_to)
        if status:
            query += " AND status = %s"
            params.append(status)
        if name:
            query += " AND name LIKE %s"
            params.append(f"%{name}%")
        if camera_id is not None:
            query += " AND camera_id = %s"
            params.append(camera_id)

        query += " ORDER BY entry_date DESC, entry_time DESC"

        if limit:
            query += f" LIMIT {int(limit)}"

        return db.fetch_all(query, tuple(params))

    def get_today_logs(self) -> list:
        """Return all logs for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_logs(date_from=today, date_to=today)

    def get_recent_logs(self, count: int = 20) -> list:
        """Return the most recent N log entries."""
        return self.get_logs(limit=count)

    # =========================================================
    #  ATTENDANCE
    # =========================================================

    def get_attendance_for_date(self, target_date: str) -> list:
        """
        Get attendance status for all registered users on a date.

        Returns list of dicts:
        [
          {
            "user_id"     : 1,
            "name"        : "John Doe",
            "status"      : "Present" | "Late" | "Absent",
            "entry_time"  : "09:05:00" or None,
            "department"  : "Engineering",
          },
          ...
        ]
        """
        users = db.get_all_users()
        logs  = self.get_logs(date_from=target_date, date_to=target_date,
                               status="known")

        # Map: user_id → earliest log time that day
        first_entry = {}
        for log in logs:
            uid  = log.get("user_id")
            time = str(log.get("entry_time", ""))
            if uid and (uid not in first_entry or time < first_entry[uid]):
                first_entry[uid] = time

        results = []
        for user in users:
            uid        = user["user_id"]
            entry_time = first_entry.get(uid)

            if entry_time:
                # Determine Present vs Late
                h, m = int(entry_time[:2]), int(entry_time[3:5])
                if (h > self.LATE_AFTER_HOUR or
                        (h == self.LATE_AFTER_HOUR and
                         m > self.LATE_AFTER_MIN)):
                    att_status = "Late"
                else:
                    att_status = "Present"
            else:
                att_status = "Absent"

            results.append({
                "user_id"    : uid,
                "name"       : user["full_name"],
                "department" : user.get("department", "—"),
                "role"       : user.get("role", "—"),
                "status"     : att_status,
                "entry_time" : entry_time or "—",
            })

        return results

    def get_attendance_summary(self, date_from: str,
                                date_to: str) -> dict:
        """
        Summarise attendance between two dates.

        Returns:
        {
          "total_days"   : int,
          "users"        : [
            {
              "name"       : str,
              "present"    : int,
              "late"       : int,
              "absent"     : int,
              "percentage" : float
            },
            ...
          ]
        }
        """
        # Build date range
        start  = datetime.strptime(date_from, "%Y-%m-%d").date()
        end    = datetime.strptime(date_to,   "%Y-%m-%d").date()
        days   = [(start + timedelta(days=i))
                  for i in range((end - start).days + 1)]

        users      = db.get_all_users()
        all_logs   = self.get_logs(date_from=date_from,
                                    date_to=date_to, status="known")

        # Group logs by user_id and date
        presence = {}   # {user_id: {date_str: entry_time}}
        for log in all_logs:
            uid  = log.get("user_id")
            d    = str(log.get("entry_date", ""))
            t    = str(log.get("entry_time", ""))
            if uid:
                if uid not in presence:
                    presence[uid] = {}
                if d not in presence[uid] or t < presence[uid][d]:
                    presence[uid][d] = t

        summary_users = []
        for user in users:
            uid      = user["user_id"]
            present  = 0
            late     = 0
            absent   = 0

            for day in days:
                d_str      = day.strftime("%Y-%m-%d")
                entry_time = presence.get(uid, {}).get(d_str)

                if entry_time:
                    h = int(entry_time[:2])
                    m = int(entry_time[3:5])
                    if (h > self.LATE_AFTER_HOUR or
                            (h == self.LATE_AFTER_HOUR
                             and m > self.LATE_AFTER_MIN)):
                        late += 1
                    else:
                        present += 1
                else:
                    absent += 1

            total_days  = len(days)
            percentage  = round(
                ((present + late) / total_days * 100)
                if total_days else 0, 1
            )

            summary_users.append({
                "user_id"   : uid,
                "name"      : user["full_name"],
                "department": user.get("department", "—"),
                "present"   : present,
                "late"      : late,
                "absent"    : absent,
                "total_days": total_days,
                "percentage": percentage,
            })

        return {
            "date_from" : date_from,
            "date_to"   : date_to,
            "total_days": len(days),
            "users"     : summary_users,
        }

    # =========================================================
    #  STATISTICS
    # =========================================================

    def get_daily_stats(self, target_date: str = None) -> dict:
        """
        Quick stats for a single day.
        Defaults to today if no date given.
        """
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        logs     = self.get_logs(date_from=target_date,
                                  date_to=target_date)
        known    = [l for l in logs if l["status"] == "known"]
        unknown  = [l for l in logs if l["status"] == "unknown"]
        spoofing = [l for l in logs if l["status"] == "spoofing_attempt"]

        unique_known = len(set(
            l["user_id"] for l in known if l.get("user_id")
        ))

        return {
            "date"          : target_date,
            "total_entries" : len(logs),
            "known"         : len(known),
            "unknown"       : len(unknown),
            "spoofing"      : len(spoofing),
            "unique_people" : unique_known,
        }

    def get_hourly_breakdown(self, target_date: str = None) -> list:
        """
        Count entries per hour for a given date.
        Returns list of 24 values (one per hour).
        """
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")

        logs    = self.get_logs(date_from=target_date,
                                 date_to=target_date)
        counts  = [0] * 24
        for log in logs:
            t = str(log.get("entry_time", "00:00:00"))
            try:
                hour = int(t[:2])
                counts[hour] += 1
            except Exception:
                pass
        return counts

    def get_top_people(self, date_from: str = None,
                        date_to: str = None,
                        limit: int = 10) -> list:
        """
        Return top N most frequent visitors in a date range.
        """
        query  = """
            SELECT name, user_id, COUNT(*) as visit_count
            FROM entry_logs
            WHERE status = 'known'
        """
        params = []
        if date_from:
            query += " AND entry_date >= %s"
            params.append(date_from)
        if date_to:
            query += " AND entry_date <= %s"
            params.append(date_to)
        query += f" GROUP BY name, user_id ORDER BY visit_count DESC LIMIT {limit}"

        return db.fetch_all(query, tuple(params))


# Module-level singleton
entry_logger = EntryLogger()