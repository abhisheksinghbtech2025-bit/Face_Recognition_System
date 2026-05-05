import bcrypt
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import BCRYPT_ROUNDS, SESSION_TIMEOUT_MIN
from database.db_manager import db


class AuthManager:

    def __init__(self):
        self._session       = None
        self._session_start = None

    @staticmethod
    def hash_password(plain_password: str) -> str:
        salt   = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, stored_hash: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                stored_hash.encode("utf-8")
            )
        except Exception as e:
            print(f"[AUTH ERROR] {e}")
            return False

    def login(self, username: str, password: str, expected_role: str):
        user = db.get_login(username)
        if not user:
            return False, "Invalid username or password."
        if not user.get("is_active"):
            return False, "Account is disabled. Contact administrator."
        if user.get("role") != expected_role:
            return False, f"This account is not registered as '{expected_role}'."
        if user.get("failed_attempts", 0) >= 5:
            return False, "Account locked due to too many failed attempts."
        if not self.verify_password(password, user["password_hash"]):
            db.increment_failed_attempts(username)
            return False, "Invalid username or password."
        db.update_last_login(user["login_id"])
        self._session       = user
        self._session_start = time.time()
        print(f"[AUTH] Login success: {username} ({expected_role})")
        return True, user

    def logout(self):
        self._session       = None
        self._session_start = None

    def is_logged_in(self) -> bool:
        if not self._session or not self._session_start:
            return False
        elapsed_min = (time.time() - self._session_start) / 60
        if elapsed_min > SESSION_TIMEOUT_MIN:
            self.logout()
            return False
        return True

    def get_current_user(self):
        if self.is_logged_in():
            return self._session
        return None

    def is_admin(self) -> bool:
        user = self.get_current_user()
        return user is not None and user.get("role") == "admin"

    def refresh_session(self):
        if self._session:
            self._session_start = time.time()

    def create_account(self, username, password, role, user_id=None):
        existing = db.get_login(username)
        if existing:
            return False, f"Username '{username}' already exists."
        if role not in ("admin", "user"):
            return False, "Role must be 'admin' or 'user'."
        if len(password) < 6:
            return False, "Password must be at least 6 characters."
        hashed   = self.hash_password(password)
        login_id = db.execute_get_id(
            "INSERT INTO login_credentials (username, password_hash, role, user_id) VALUES (%s,%s,%s,%s)",
            (username, hashed, role, user_id)
        )
        if login_id:
            return True, login_id
        return False, "Database error while creating account."

    def change_password(self, username, old_password, new_password):
        user = db.get_login(username)
        if not user:
            return False, "User not found."
        if not self.verify_password(old_password, user["password_hash"]):
            return False, "Current password is incorrect."
        if len(new_password) < 6:
            return False, "Password must be at least 6 characters."
        new_hash = self.hash_password(new_password)
        success  = db.execute(
            "UPDATE login_credentials SET password_hash=%s WHERE username=%s",
            (new_hash, username)
        )
        if success:
            return True, "Password changed successfully."
        return False, "Database error."


auth = AuthManager()