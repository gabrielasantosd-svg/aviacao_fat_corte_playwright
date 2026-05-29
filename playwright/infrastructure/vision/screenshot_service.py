"""
ScreenshotService - captura e salva screenshots com metadados.
"""

from datetime import datetime
from pathlib import Path

from settings import settings


class ScreenshotService:
    def __init__(self, base_dir: str = settings.SCREENSHOTS_DIR):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, image_bytes: bytes, job_id: str, label: str = "") -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{job_id}_{ts}_{label}.png" if label else f"{job_id}_{ts}.png"
        path = self._base_dir / filename
        with path.open("wb") as f:
            f.write(image_bytes)
        return str(path)
