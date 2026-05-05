# ============================================================
#   FaceSecuritySystem — main.py
#   Module 12: Final Integration — App Entry Point
#   Command: python main.py
# ============================================================

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def check_requirements():
    required = {
        "customtkinter"   : "customtkinter",
        "cv2"             : "opencv-python",
        "face_recognition": "face-recognition",
        "PIL"             : "Pillow",
        "mysql.connector" : "mysql-connector-python",
        "bcrypt"          : "bcrypt",
        "numpy"           : "numpy",
        "reportlab"       : "reportlab",
        "openpyxl"        : "openpyxl",
        "scipy"           : "scipy",
        "imutils"         : "imutils",
    }
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print("=" * 55)
        print("  Missing required packages!")
        print("=" * 55)
        print(f"\n  Run:  pip install {' '.join(missing)}\n")
        return False
    return True


def check_database():
    try:
        from database.db_manager import db
        ok = db.connect()
        if not ok:
            print("=" * 55)
            print("  Cannot connect to MySQL!")
            print("  1. Make sure MySQL is running")
            print("  2. Check password in config/config.py")
            print("  3. Run: python setup.py")
            print("=" * 55)
            return False
        return True
    except Exception as e:
        print(f"  Database error: {e}")
        return False


def launch():
    print("=" * 55)
    print("  Face Security System — Starting")
    print("=" * 55)

    print("\n  Checking packages...")
    if not check_requirements():
        input("\n  Press Enter to exit...")
        sys.exit(1)
    print("  All packages OK")

    print("  Checking database...")
    if not check_database():
        input("\n  Press Enter to exit...")
        sys.exit(1)
    print("  Database connected")

    print("  Launching...\n")
    print("=" * 55)

    from ui.login_window import launch_login
    launch_login()


if __name__ == "__main__":
    launch()