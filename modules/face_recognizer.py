# ============================================================
#   FaceSecuritySystem — modules/face_recognizer.py
#   Module 4: Face Recognition — encode, compare, identify
# ============================================================

import face_recognition
import numpy as np
import pickle
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import (
    RECOGNITION_TOLERANCE, ENCODINGS_FILE,
    DATASET_DIR, UNKNOWN_LABEL
)
from database.db_manager import db


class FaceRecognizer:
    """
    Encodes known faces and matches detected faces against them.

    Workflow:
        1. Admin adds users + images via Dataset panel
        2. Call train() to generate encodings from those images
        3. During live detection, call recognize() to identify faces
    """

    def __init__(self):
        self.known_encodings = []   # list of 128-d face encoding arrays
        self.known_names     = []   # list of names matching each encoding
        self.known_user_ids  = []   # list of user_id matching each encoding
        self._load_encodings()

    # =========================================================
    #  TRAINING
    # =========================================================

    def train(self) -> dict:
        """
        Scan the dataset folder, encode every face image,
        and save encodings to disk.

        Folder structure expected:
            dataset/faces/
                John_Doe_1/
                    photo1.jpg
                    photo2.jpg
                Jane_Smith_5/
                    photo1.jpg

        The folder name format: <FullName>_<user_id>

        Returns:
            {"trained": int, "failed": int, "total_images": int}
        """
        print("[RECOGNIZER] Starting training...")

        all_encodings = []
        all_names     = []
        all_user_ids  = []

        trained = 0
        failed  = 0
        total   = 0

        if not os.path.exists(DATASET_DIR):
            print("[RECOGNIZER] Dataset directory not found.")
            return {"trained": 0, "failed": 0, "total_images": 0}

        for person_folder in os.listdir(DATASET_DIR):
            folder_path = os.path.join(DATASET_DIR, person_folder)
            if not os.path.isdir(folder_path):
                continue

            # Parse folder name: "John_Doe_1" → name="John Doe", id=1
            parts = person_folder.rsplit("_", 1)
            if len(parts) == 2:
                name    = parts[0].replace("_", " ")
                try:
                    user_id = int(parts[1])
                except ValueError:
                    name    = person_folder.replace("_", " ")
                    user_id = None
            else:
                name    = person_folder.replace("_", " ")
                user_id = None

            for img_file in os.listdir(folder_path):
                if not img_file.lower().endswith(
                        (".jpg", ".jpeg", ".png", ".bmp")):
                    continue

                total += 1
                img_path = os.path.join(folder_path, img_file)

                try:
                    image     = face_recognition.load_image_file(img_path)
                    encodings = face_recognition.face_encodings(image)

                    if encodings:
                        all_encodings.append(encodings[0])
                        all_names.append(name)
                        all_user_ids.append(user_id)
                        trained += 1
                        print(f"   ✔ Encoded: {name} — {img_file}")
                    else:
                        failed += 1
                        print(f"   ✘ No face found in: {img_path}")

                except Exception as e:
                    failed += 1
                    print(f"   ✘ Error encoding {img_path}: {e}")

        # Save to disk
        data = {
            "encodings" : all_encodings,
            "names"     : all_names,
            "user_ids"  : all_user_ids,
            "trained_at": datetime.now().isoformat()
        }
        os.makedirs(os.path.dirname(ENCODINGS_FILE), exist_ok=True)
        with open(ENCODINGS_FILE, "wb") as f:
            pickle.dump(data, f)

        # Update in-memory encodings
        self.known_encodings = all_encodings
        self.known_names     = all_names
        self.known_user_ids  = all_user_ids

        print(f"[RECOGNIZER] Training complete: "
              f"{trained} encoded, {failed} failed, {total} total images.")

        return {"trained": trained, "failed": failed, "total_images": total}

    def _load_encodings(self):
        """Load saved encodings from disk into memory."""
        if not os.path.exists(ENCODINGS_FILE):
            print("[RECOGNIZER] No encodings file found. Run train() first.")
            return

        try:
            with open(ENCODINGS_FILE, "rb") as f:
                data = pickle.load(f)
            self.known_encodings = data.get("encodings", [])
            self.known_names     = data.get("names",     [])
            self.known_user_ids  = data.get("user_ids",  [])
            print(f"[RECOGNIZER] Loaded {len(self.known_encodings)} "
                  f"face encoding(s) from disk.")
        except Exception as e:
            print(f"[RECOGNIZER] Failed to load encodings: {e}")

    def reload(self):
        """Reload encodings from disk (call after training)."""
        self._load_encodings()

    # =========================================================
    #  RECOGNITION
    # =========================================================

    def recognize(self, frame_rgb: np.ndarray) -> list:
        """
        Find and identify all faces in a single RGB frame.

        Args:
            frame_rgb: RGB image (face_recognition uses RGB, not BGR)

        Returns:
            List of dicts:
            [
              {
                "name"      : "John Doe",
                "user_id"   : 3,
                "confidence": 0.87,
                "location"  : (top, right, bottom, left),
                "is_known"  : True
              },
              ...
            ]
        """
        if not self.known_encodings:
            return []

        # Detect face locations (faster model)
        locations = face_recognition.face_locations(
            frame_rgb, model="hog"
        )
        if not locations:
            return []

        # Get encodings for detected faces
        encodings = face_recognition.face_encodings(frame_rgb, locations)

        results = []
        for encoding, location in zip(encodings, locations):
            result = self._match_encoding(encoding, location)
            results.append(result)

        return results

    def _match_encoding(self, encoding: np.ndarray,
                         location: tuple) -> dict:
        """
        Compare one encoding against all known encodings.
        Returns the best match result dict.
        """
        # Compare against all known faces
        distances = face_recognition.face_distance(
            self.known_encodings, encoding
        )

        best_idx      = int(np.argmin(distances))
        best_distance = float(distances[best_idx])
        confidence    = max(0.0, 1.0 - best_distance)

        if best_distance <= RECOGNITION_TOLERANCE:
            return {
                "name"      : self.known_names[best_idx],
                "user_id"   : self.known_user_ids[best_idx],
                "confidence": round(confidence, 3),
                "location"  : location,
                "is_known"  : True
            }
        else:
            return {
                "name"      : UNKNOWN_LABEL,
                "user_id"   : None,
                "confidence": round(confidence, 3),
                "location"  : location,
                "is_known"  : False
            }

    # =========================================================
    #  UTILITIES
    # =========================================================

    def encode_single_image(self, image_path: str):
        """
        Encode a single image file.
        Returns the encoding array, or None if no face found.
        """
        try:
            image     = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                return encodings[0]
        except Exception as e:
            print(f"[RECOGNIZER] encode_single_image error: {e}")
        return None

    def add_face_to_dataset(self, user_id: int, name: str,
                             image_path: str) -> bool:
        """
        Copy an image into the correct dataset folder for a user.
        Returns True on success.
        """
        folder_name = f"{name.replace(' ', '_')}_{user_id}"
        folder_path = os.path.join(DATASET_DIR, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        import shutil
        ext      = os.path.splitext(image_path)[1]
        dst_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        dst_path = os.path.join(folder_path, dst_name)

        try:
            shutil.copy2(image_path, dst_path)
            print(f"[RECOGNIZER] Image saved to dataset: {dst_path}")
            return True
        except Exception as e:
            print(f"[RECOGNIZER] Failed to save image: {e}")
            return False

    @property
    def is_trained(self) -> bool:
        """True if at least one face encoding is loaded."""
        return len(self.known_encodings) > 0

    @property
    def known_count(self) -> int:
        """Number of known face encodings loaded."""
        return len(self.known_encodings)