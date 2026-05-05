import mysql.connector
from mysql.connector import Error
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import DB_CONFIG

class DatabaseManager:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.connection = None
        return cls._instance

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("[DB] Connected successfully.")
                return True
        except Error as e:
            print(f"[DB ERROR] {e}")
            self.connection = None
        return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def is_connected(self):
        return self.connection is not None and self.connection.is_connected()

    def ensure_connected(self):
        if not self.is_connected():
            self.connect()

    def execute(self, query, params=()):
        self.ensure_connected()
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            cursor.close()
            return True
        except Error as e:
            print(f"[DB ERROR] {e}")
            return False

    def execute_get_id(self, query, params=()):
        self.ensure_connected()
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            last_id = cursor.lastrowid
            cursor.close()
            return last_id
        except Error as e:
            print(f"[DB ERROR] {e}")
            return None

    def fetch_one(self, query, params=()):
        self.ensure_connected()
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)
            row = cursor.fetchone()
            cursor.close()
            return row
        except Error as e:
            print(f"[DB ERROR] {e}")
            return None

    def fetch_all(self, query, params=()):
        self.ensure_connected()
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        except Error as e:
            print(f"[DB ERROR] {e}")
            return []

    # ── Users ─────────────────────────────────────────────────
    def add_user(self, full_name, employee_id, department, role, image_path, email, phone):
        return self.execute_get_id(
            "INSERT INTO users (full_name,employee_id,department,role,image_path,email,phone) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (full_name, employee_id, department, role, image_path, email, phone)
        )

    def get_all_users(self):
        return self.fetch_all("SELECT * FROM users ORDER BY created_at DESC")

    def get_user_by_id(self, user_id):
        return self.fetch_one("SELECT * FROM users WHERE user_id=%s", (user_id,))

    def update_user(self, user_id, **fields):
        if not fields: return False
        set_clause = ", ".join(f"{k}=%s" for k in fields)
        return self.execute(f"UPDATE users SET {set_clause} WHERE user_id=%s", (*fields.values(), user_id))

    def delete_user(self, user_id):
        return self.execute("DELETE FROM users WHERE user_id=%s", (user_id,))

    # ── Login ─────────────────────────────────────────────────
    def get_login(self, username):
        return self.fetch_one("SELECT * FROM login_credentials WHERE username=%s", (username,))

    def update_last_login(self, login_id):
        self.execute("UPDATE login_credentials SET last_login=NOW(), failed_attempts=0 WHERE login_id=%s", (login_id,))

    def increment_failed_attempts(self, username):
        self.execute("UPDATE login_credentials SET failed_attempts=failed_attempts+1 WHERE username=%s", (username,))

    # ── Logs ──────────────────────────────────────────────────
    def add_log(self, user_id, name, camera_id, camera_label, entry_date, entry_time, status, confidence_score=None, snapshot_path=None):
        return self.execute_get_id(
            "INSERT INTO entry_logs (user_id,name,camera_id,camera_label,entry_date,entry_time,status,confidence_score,snapshot_path) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (user_id, name, camera_id, camera_label, entry_date, entry_time, status, confidence_score, snapshot_path)
        )

    def get_logs(self, date_from=None, date_to=None, status=None):
        query = "SELECT * FROM entry_logs WHERE 1=1"
        params = []
        if date_from: query += " AND entry_date>=%s"; params.append(date_from)
        if date_to:   query += " AND entry_date<=%s"; params.append(date_to)
        if status:    query += " AND status=%s";      params.append(status)
        return self.fetch_all(query + " ORDER BY entry_date DESC, entry_time DESC", tuple(params))

    # ── Alerts ────────────────────────────────────────────────
    def add_alert(self, alert_type, camera_id, camera_label, snapshot_path, alert_date, alert_time):
        return self.execute_get_id(
            "INSERT INTO alerts (alert_type,camera_id,camera_label,snapshot_path,alert_date,alert_time) VALUES (%s,%s,%s,%s,%s,%s)",
            (alert_type, camera_id, camera_label, snapshot_path, alert_date, alert_time)
        )

    def get_unreviewed_alerts(self):
        return self.fetch_all("SELECT * FROM alerts WHERE is_reviewed=0 ORDER BY created_at DESC")

    # ── Settings ──────────────────────────────────────────────
    def get_setting(self, key):
        row = self.fetch_one("SELECT setting_value FROM system_settings WHERE setting_key=%s", (key,))
        return row["setting_value"] if row else None

    def update_setting(self, key, value):
        return self.execute("UPDATE system_settings SET setting_value=%s WHERE setting_key=%s", (value, key))

    # ── Cameras ───────────────────────────────────────────────
    def get_active_cameras(self):
        return self.fetch_all("SELECT * FROM cameras WHERE is_active=1 ORDER BY camera_id")

db = DatabaseManager()