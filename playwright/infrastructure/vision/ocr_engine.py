"""
OCREngine — wrapper PaddleOCR para OCR localizado.
NUNCA roda OCR na tela inteira; recebe crop (bytes ou ndarray).
PaddleOCR é opcional — se não instalado, lança erro apenas quando chamado.
"""

from __future__ import annotations

try:
    import numpy as np
    from paddleocr import PaddleOCR

    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False


class OCREngine:
    def __init__(self, lang: str = "pt", use_gpu: bool = False):
        if not _PADDLE_AVAILABLE:
            raise RuntimeError(
                "PaddleOCR não instalado. Execute: pip install paddleocr paddlepaddle"
            )
        self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu, show_log=False)

    def extract_text(self, image) -> list[str]:
        """Retorna lista de strings detectadas na região."""
        result = self._ocr.ocr(image, cls=True)
        texts = []
        for line in result or []:
            for item in line or []:
                if item and len(item) >= 2 and item[1]:
                    texts.append(item[1][0])
        return texts

    def find_text(self, image, target: str) -> bool:
        texts = self.extract_text(image)
        return any(target.lower() in t.lower() for t in texts)
