import os
import time
import hashlib
from datetime import datetime
from typing import Tuple

from PIL import Image

from .capture import ScreenCapture
from .ocr import OcrEngine


class MonitorController:
    def __init__(
        self,
        output_dir: str,
        interval: float,
        capture: ScreenCapture,
        ocr: OcrEngine,
        detect_mode: str = "ocr",
    ):
        self.output_dir = output_dir
        self.interval = max(0.2, float(interval))
        self.capture = capture
        self.ocr = ocr
        self.detect_mode = detect_mode  # "ocr", "image", or "both"
        self.last_text_hash = None
        self.last_image_hash = None
        self.last_saved_path = None
        self.last_change_at = None
        os.makedirs(output_dir, exist_ok=True)

    @staticmethod
    def _text_hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def _image_hash(image: Image.Image) -> str:
        """Fast perceptual hash of image pixels for change detection."""
        return hashlib.sha256(image.tobytes()).hexdigest()

    @staticmethod
    def _print_change_summary(detect_mode, image_hash, text_hash):
        if detect_mode == "image":
            print(f"Image hash: {image_hash}")
        elif detect_mode == "ocr":
            print(f"OCR hash: {text_hash}")
        else:
            print(f"Image hash: {image_hash} | OCR hash: {text_hash}")

    def _save_image(self, image: Image.Image) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{ts}.png"
        filepath = os.path.join(self.output_dir, filename)
        image.save(filepath)
        self.last_saved_path = filepath
        print(f"Saved: {filepath}")
        return filepath

    def process_once(self) -> Tuple[Image.Image, str, bool]:
        screenshot = self.capture.capture()
        
        # Determine change based on detection mode
        changed = False
        text = ""
        current_text_hash = None
        current_image_hash = None

        if self.detect_mode in ("image", "both"):
            current_image_hash = self._image_hash(screenshot)
            if self.last_image_hash != current_image_hash:
                changed = True
                self.last_image_hash = current_image_hash

        if self.detect_mode in ("ocr", "both"):
            text = self.ocr.image_to_text(screenshot)
            current_text_hash = self._text_hash(text)
            if self.last_text_hash != current_text_hash:
                changed = True
                self.last_text_hash = current_text_hash

        if changed:
            self.last_change_at = datetime.now()
            self._save_image(screenshot)
            self._print_change_summary(
                self.detect_mode,
                current_image_hash,
                current_text_hash,
            )
        
        return screenshot, text, changed

    def status_summary(self) -> str:
        monitor = self.capture.monitor_summary() if hasattr(self.capture, "monitor_summary") else "unknown"
        ocr_status = self.ocr.status_message or "OCR not checked"
        last_change = self.last_change_at.strftime("%Y-%m-%d %H:%M:%S") if self.last_change_at else "never"
        last_saved = os.path.basename(self.last_saved_path) if self.last_saved_path else "none"
        return (
            f"Monitor: {monitor} | OCR: {ocr_status} | "
            f"Last change: {last_change} | Saved: {last_saved}"
        )

    def run_headless(self):
        print("Starting window monitor (headless)… Press Ctrl+C to stop")
        self.capture.ensure_monitor_selected(gui=False)
        if not self.ocr.ensure_tesseract():
            print(
                "Warning: Tesseract not found. OCR will be empty until it's "
                "installed or configured via --tesseract-cmd."
            )
        try:
            while True:
                self.process_once()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
        except (RuntimeError, OSError, ValueError) as e:
            print(f"\nStopped due to error: {e}")
