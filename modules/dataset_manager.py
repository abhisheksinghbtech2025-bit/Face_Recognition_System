# ============================================================
#   FaceSecuritySystem — modules/dataset_manager.py
#   Module 8: Dataset Management
#   Handles adding, updating, deleting face images for users
# ============================================================

import os
import sys
import shutil
import cv2
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import DATASET_DIR, ENCODINGS_FILE
from database.db_manager import db


class DatasetManager:
    """
    Manages the face image dataset on disk and in the database.

    Folder structure:
        dataset/faces/
            John_Doe_1/          ← <FirstName_LastName_userID>
                20240101_120000.jpg
                20240101_120001.jpg
            Jane_Smith_2/
                20240101_130000.jpg

    Usage:
        dm = DatasetManager()
        dm.add_face_image(user_id=1, name="John Doe", image_path="photo.jpg")
        dm.delete_user_images(user_id=1)
        images = dm.get_user_images(user_id=1)
    """

    def __init__(self):
        os.makedirs(DATASET_DIR, exist_ok=True)
        print("[DATASET] DatasetManager ready.")

    # =========================================================
    #  FOLDER HELPERS
    # =========================================================

    def get_user_folder(self, user_id: int, name: str) -> str:
        """
        Return the dataset folder path for a user.
        Creates it if it doesn't exist.
        Format: dataset/faces/John_Doe_1/
        """
        folder_name = f"{name.strip().replace(' ', '_')}_{user_id}"
        folder_path = os.path.join(DATASET_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def find_user_folder(self, user_id: int) -> str | None:
        """
        Find existing folder for user_id by scanning dataset dir.
        Returns path or None if not found.
        """
        if not os.path.exists(DATASET_DIR):
            return None
        for folder in os.listdir(DATASET_DIR):
            folder_path = os.path.join(DATASET_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
            parts = folder.rsplit("_", 1)
            if len(parts) == 2:
                try:
                    if int(parts[1]) == user_id:
                        return folder_path
                except ValueError:
                    continue
        return None

    # =========================================================
    #  IMAGE OPERATIONS
    # =========================================================

    def add_face_image(self, user_id: int, name: str,
                       image_path: str) -> dict:
        """
        Copy an image into the user's dataset folder.

        Args:
            user_id:    Database user ID
            name:       Full name of the user
            image_path: Source image file path

        Returns:
            {"success": bool, "path": str, "message": str}
        """
        if not os.path.exists(image_path):
            return {"success": False, "path": None,
                    "message": f"Source image not found: {image_path}"}

        # Validate it's an image
        valid_ext = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
        if not image_path.lower().endswith(valid_ext):
            return {"success": False, "path": None,
                    "message": "Invalid file type. Use JPG, PNG, or BMP."}

        # Check image can be opened
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "path": None,
                    "message": "Could not read image file."}

        # Get or create user folder
        folder = self.get_user_folder(user_id, name)

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        ext       = os.path.splitext(image_path)[1].lower()
        dst_name  = f"{timestamp}{ext}"
        dst_path  = os.path.join(folder, dst_name)

        try:
            shutil.copy2(image_path, dst_path)
            # Update image_path in DB
            db.update_user(user_id, image_path=dst_path)
            print(f"[DATASET] Image added: {dst_path}")
            return {"success": True, "path": dst_path,
                    "message": "Image added successfully."}
        except Exception as e:
            return {"success": False, "path": None,
                    "message": f"Copy failed: {e}"}

    def capture_and_save(self, user_id: int, name: str,
                         frame: np.ndarray) -> dict:
        """
        Save a frame directly from the camera as a face image.

        Args:
            user_id: Database user ID
            name:    Full name
            frame:   BGR numpy array from OpenCV

        Returns:
            {"success": bool, "path": str, "message": str}
        """
        folder    = self.get_user_folder(user_id, name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dst_path  = os.path.join(folder, f"{timestamp}.jpg")

        try:
            cv2.imwrite(dst_path, frame)
            db.update_user(user_id, image_path=dst_path)
            print(f"[DATASET] Captured image saved: {dst_path}")
            return {"success": True, "path": dst_path,
                    "message": "Image captured and saved."}
        except Exception as e:
            return {"success": False, "path": None,
                    "message": f"Save failed: {e}"}

    def get_user_images(self, user_id: int) -> list:
        """
        Get all image paths for a user.
        Returns list of file paths.
        """
        folder = self.find_user_folder(user_id)
        if not folder:
            return []

        valid_ext = (".jpg", ".jpeg", ".png", ".bmp")
        images    = []
        for f in os.listdir(folder):
            if f.lower().endswith(valid_ext):
                images.append(os.path.join(folder, f))
        return sorted(images)

    def delete_image(self, image_path: str) -> bool:
        """Delete a single image file."""
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"[DATASET] Deleted image: {image_path}")
                return True
        except Exception as e:
            print(f"[DATASET] Delete failed: {e}")
        return False

    def delete_user_images(self, user_id: int) -> dict:
        """
        Delete ALL images for a user and remove their folder.

        Returns:
            {"success": bool, "deleted": int, "message": str}
        """
        folder = self.find_user_folder(user_id)
        if not folder:
            return {"success": True, "deleted": 0,
                    "message": "No images found."}
        try:
            images  = self.get_user_images(user_id)
            count   = len(images)
            shutil.rmtree(folder)
            print(f"[DATASET] Deleted folder: {folder} ({count} images)")
            return {"success": True, "deleted": count,
                    "message": f"Deleted {count} image(s)."}
        except Exception as e:
            return {"success": False, "deleted": 0,
                    "message": f"Folder delete failed: {e}"}

    # =========================================================
    #  DATASET STATS
    # =========================================================

    def get_stats(self) -> dict:
        """
        Return overall dataset statistics.
        """
        if not os.path.exists(DATASET_DIR):
            return {"users": 0, "images": 0, "trained": False}

        users  = 0
        images = 0
        valid_ext = (".jpg", ".jpeg", ".png", ".bmp")

        for folder in os.listdir(DATASET_DIR):
            folder_path = os.path.join(DATASET_DIR, folder)
            if not os.path.isdir(folder_path):
                continue
            users += 1
            for f in os.listdir(folder_path):
                if f.lower().endswith(valid_ext):
                    images += 1

        trained = os.path.exists(ENCODINGS_FILE)
        return {
            "users"   : users,
            "images"  : images,
            "trained" : trained,
            "enc_file": ENCODINGS_FILE if trained else None,
        }

    def get_all_users_with_images(self) -> list:
        """
        Return list of all users from DB with their image counts.
        """
        users  = db.get_all_users()
        result = []
        for user in users:
            images = self.get_user_images(user["user_id"])
            result.append({
                **user,
                "image_count": len(images),
                "images"     : images,
            })
        return result

    # =========================================================
    #  IMAGE QUALITY CHECK
    # =========================================================

    def check_image_quality(self, image_path: str) -> dict:
        """
        Check if an image is suitable for face recognition training.

        Returns:
            {
              "ok"        : bool,
              "face_found": bool,
              "brightness": float,
              "sharpness" : float,
              "issues"    : list of str
            }
        """
        issues = []
        img = cv2.imread(image_path)

        if img is None:
            return {"ok": False, "face_found": False,
                    "brightness": 0, "sharpness": 0,
                    "issues": ["Cannot read image"]}

        # Brightness check
        hsv        = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        brightness = float(hsv[:, :, 2].mean())
        if brightness < 40:
            issues.append("Image too dark")
        elif brightness > 220:
            issues.append("Image too bright / overexposed")

        # Sharpness check (Laplacian variance)
        gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if sharpness < 50:
            issues.append("Image is blurry")

        # Face detection check
        cascade_path = cv2.data.haarcascades + \
                       "haarcascade_frontalface_default.xml"
        detector     = cv2.CascadeClassifier(cascade_path)
        faces        = detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
        )
        face_found = len(faces) > 0
        if not face_found:
            issues.append("No face detected in image")

        return {
            "ok"        : len(issues) == 0,
            "face_found": face_found,
            "brightness": round(brightness, 1),
            "sharpness" : round(sharpness, 1),
            "issues"    : issues,
        }


# Module-level singleton
dataset_manager = DatasetManager()