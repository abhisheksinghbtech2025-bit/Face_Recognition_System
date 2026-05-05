# ============================================================
#   FaceSecuritySystem — modules/low_light.py
#   Module 6: Low-Light Image Enhancement
#   Techniques: Histogram Equalization, CLAHE, Gamma Correction,
#               Brightness/Contrast Auto-Fix, Denoising
# ============================================================

import cv2
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import LOW_LIGHT_ENABLED, GAMMA_VALUE


class LowLightEnhancer:
    """
    Improves image quality in poor lighting conditions.

    Methods available:
        1. auto_enhance()     — Smart auto-detect + fix (recommended)
        2. gamma_correction() — Brighten dark images
        3. clahe()            — Contrast Limited Adaptive Histogram Equalization
        4. histogram_eq()     — Basic histogram equalization
        5. denoise()          — Remove noise from dark frames
        6. brightness_contrast() — Manual brightness/contrast control

    Usage:
        enhancer = LowLightEnhancer()
        enhanced = enhancer.auto_enhance(frame)
    """

    def __init__(self):
        self.enabled      = LOW_LIGHT_ENABLED
        self.gamma        = GAMMA_VALUE
        self.method       = "auto"       # auto | gamma | clahe | hist | none

        # CLAHE object (reused for performance)
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # Pre-build gamma lookup table (256 values, very fast)
        self._gamma_table = self._build_gamma_table(self.gamma)

        print(f"[LOW_LIGHT] Enhancer ready. Gamma={self.gamma}, "
              f"Method={self.method}, Enabled={self.enabled}")

    # =========================================================
    #  MAIN ENTRY POINT
    # =========================================================

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        Main method — call this on every camera frame.
        Checks if enhancement is needed, applies it if so.

        Args:
            frame: BGR image from OpenCV

        Returns:
            Enhanced BGR frame (or original if not needed)
        """
        if not self.enabled:
            return frame

        if self.method == "auto":
            return self.auto_enhance(frame)
        elif self.method == "gamma":
            return self.gamma_correction(frame, self.gamma)
        elif self.method == "clahe":
            return self.clahe(frame)
        elif self.method == "hist":
            return self.histogram_eq(frame)
        else:
            return frame

    def auto_enhance(self, frame: np.ndarray) -> np.ndarray:
        """
        Smart enhancement — measures brightness and
        applies the right technique automatically.

        Brightness levels:
            > 120 : Image is bright enough, no change
            80–120: Apply light gamma correction
            40–80 : Apply CLAHE
            < 40  : Apply gamma + CLAHE combined
        """
        brightness = self._measure_brightness(frame)

        if brightness > 120:
            # Already bright — no enhancement needed
            return frame
        elif brightness > 80:
            # Slightly dark — light gamma
            return self.gamma_correction(frame, gamma=1.3)
        elif brightness > 40:
            # Moderately dark — CLAHE
            return self.clahe(frame)
        else:
            # Very dark — gamma + CLAHE + denoise
            enhanced = self.gamma_correction(frame, gamma=2.0)
            enhanced = self.clahe(enhanced)
            enhanced = self.denoise(enhanced)
            return enhanced

    # =========================================================
    #  TECHNIQUE 1 — GAMMA CORRECTION
    # =========================================================

    def gamma_correction(self, frame: np.ndarray,
                          gamma: float = None) -> np.ndarray:
        """
        Apply gamma correction to brighten a dark image.

        gamma > 1.0 → brighter (use for dark images)
        gamma < 1.0 → darker  (use for overexposed images)
        gamma = 1.0 → no change

        Uses a precomputed lookup table for speed (very fast).
        """
        if gamma is None:
            gamma = self.gamma

        # Rebuild table only if gamma changed
        if gamma != self.gamma:
            table = self._build_gamma_table(gamma)
        else:
            table = self._gamma_table

        return cv2.LUT(frame, table)

    # =========================================================
    #  TECHNIQUE 2 — CLAHE
    # =========================================================

    def clahe(self, frame: np.ndarray) -> np.ndarray:
        """
        Contrast Limited Adaptive Histogram Equalization.

        Much better than basic histogram equalization because:
        - Works on small regions (tiles) independently
        - Avoids over-amplifying noise
        - Preserves local contrast

        Converts to LAB color space, applies CLAHE to L channel,
        then converts back to BGR.
        """
        lab   = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_eq  = self._clahe.apply(l)
        lab_eq = cv2.merge([l_eq, a, b])
        return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    # =========================================================
    #  TECHNIQUE 3 — HISTOGRAM EQUALIZATION
    # =========================================================

    def histogram_eq(self, frame: np.ndarray) -> np.ndarray:
        """
        Basic global histogram equalization.
        Spreads intensity values across the full range.
        Simpler than CLAHE but can over-enhance.
        """
        yuv          = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
        return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

    # =========================================================
    #  TECHNIQUE 4 — DENOISE
    # =========================================================

    def denoise(self, frame: np.ndarray,
                strength: int = 7) -> np.ndarray:
        """
        Remove noise from dark/grainy frames.
        Uses Non-Local Means Denoising.

        strength: 3–10 (higher = more smoothing, but slower)
        """
        return cv2.fastNlMeansDenoisingColored(
            frame,
            None,
            h           = strength,
            hColor      = strength,
            templateWindowSize = 7,
            searchWindowSize   = 21
        )

    # =========================================================
    #  TECHNIQUE 5 — BRIGHTNESS / CONTRAST MANUAL
    # =========================================================

    def brightness_contrast(self, frame: np.ndarray,
                             brightness: int = 30,
                             contrast:   int = 30) -> np.ndarray:
        """
        Manual brightness and contrast adjustment.

        brightness: -255 to +255 (positive = brighter)
        contrast:   -255 to +255 (positive = more contrast)
        """
        beta  = brightness
        alpha = (contrast + 127) / 127.0   # convert to multiplier
        return cv2.convertScaleAbs(frame, alpha=alpha, beta=beta)

    # =========================================================
    #  HELPERS
    # =========================================================

    @staticmethod
    def _measure_brightness(frame: np.ndarray) -> float:
        """
        Measure average brightness of a frame.
        Returns value 0–255. Lower = darker.
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return float(hsv[:, :, 2].mean())

    @staticmethod
    def _build_gamma_table(gamma: float) -> np.ndarray:
        """
        Build a 256-entry lookup table for gamma correction.
        Using LUT is much faster than computing per-pixel.
        """
        inv_gamma = 1.0 / gamma
        table     = np.array([
            ((i / 255.0) ** inv_gamma) * 255
            for i in range(256)
        ], dtype=np.uint8)
        return table

    def set_gamma(self, gamma: float):
        """Update gamma value and rebuild lookup table."""
        self.gamma        = max(0.1, min(5.0, gamma))
        self._gamma_table = self._build_gamma_table(self.gamma)
        print(f"[LOW_LIGHT] Gamma updated to {self.gamma}")

    def set_method(self, method: str):
        """
        Set enhancement method.
        Options: 'auto', 'gamma', 'clahe', 'hist', 'none'
        """
        valid = ("auto", "gamma", "clahe", "hist", "none")
        if method in valid:
            self.method = method
            print(f"[LOW_LIGHT] Method set to: {method}")
        else:
            print(f"[LOW_LIGHT] Invalid method. Choose from: {valid}")

    def toggle(self, enabled: bool = None):
        """Enable or disable enhancement. Toggles if no arg given."""
        if enabled is None:
            self.enabled = not self.enabled
        else:
            self.enabled = enabled
        print(f"[LOW_LIGHT] Enhancement {'enabled' if self.enabled else 'disabled'}")

    def get_brightness(self, frame: np.ndarray) -> float:
        """Public brightness measurement."""
        return self._measure_brightness(frame)

    def get_stats(self, frame: np.ndarray) -> dict:
        """
        Return brightness stats for a frame.
        Useful for displaying in the UI.
        """
        brightness = self._measure_brightness(frame)
        gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return {
            "brightness"  : round(brightness, 1),
            "std_dev"     : round(float(gray.std()), 1),
            "min_pixel"   : int(gray.min()),
            "max_pixel"   : int(gray.max()),
            "is_dark"     : brightness < 80,
            "is_very_dark": brightness < 40,
        }