import os, sys
import mysql.connector
from mysql.connector import Error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from config.config import DB_CONFIG

def run():
    print("=" * 50)
    print("  Face Security System — Setup")
    print("=" * 50)

    # Step 1: Create folders
    print("\n[1] Creating folders...")
    folders = [
        "config", "database", "modules", "ui",
        "dataset/faces", "logs/snapshots", "exports", "assets"
    ]
    for f in folders:
        os.makedirs(os.path.join(BASE_DIR, f), exist_ok=True)
        print(f"    ✔ {f}/")

    # Step 2: Create __init__.py files
    print("\n[2] Creating package files...")
    for pkg in ["config", "database", "modules", "ui"]:
        path = os.path.join(BASE_DIR, pkg, "__init__.py")
        if not os.path.exists(path):
            open(path, "w").close()
            print(f"    ✔ {pkg}/__init__.py")

    # Step 3: Setup database
    print("\n[3] Setting up database...")
    schema_path = os.path.join(BASE_DIR, "database", "schema.sql")
    try:
        cfg = DB_CONFIG.copy()
        cfg.pop("database")
        conn = mysql.connector.connect(**cfg)
        cursor = conn.cursor()
        with open(schema_path, "r") as f:
            for stmt in f.read().split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        cursor.execute(stmt)
                        conn.commit()
                    except Error as e:
                        if "already exists" not in str(e).lower():
                            print(f"    ⚠ {e}")
        cursor.close()
        conn.close()
        print("    ✔ Database and tables created!")
        print("    ✔ Default admin: admin / Admin@123")
    except Error as e:
        print(f"    ✘ Database error: {e}")
        print("    → Check MySQL is running & password in config/config.py")

    # Step 4: Check packages
    print("\n[4] Checking packages...")
    packages = ["customtkinter","cv2","face_recognition","mysql.connector","bcrypt","reportlab","pandas"]
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"    ✔ {pkg}")
        except ImportError:
            print(f"    ✘ {pkg} MISSING — run: pip install -r requirements.txt")

    print("\n" + "=" * 50)
    print("  Done! Now run: python main.py")
    print("=" * 50)

if __name__ == "__main__":
    run()