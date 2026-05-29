"""
ScreenshotService — captura e salva screenshots com metadados.
"""

import os
from datetime import datetime

from settings import settings


class ScreenshotService:
    def __init__(self, base_dir: str = settings.SCREENSHOTS_DIR):
        os.makedirs(base_dir, exist_ok=True)
        self._base_dir = base_dir

    def save(self, image_bytes: bytes, job_id: str, label: str = "") -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{job_id}_{ts}_{label}.png" if label else f"{job_id}_{ts}.png"
        path = os.path.join(self._base_dir, filename)
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path
