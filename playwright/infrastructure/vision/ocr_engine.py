"""
OCREngine e um wrapper do PaddleOCR para OCR localizado.
Nunca roda OCR na tela inteira; recebe crop em bytes ou ndarray.
PaddleOCR e opcional e so gera erro quando o engine e instanciado.
"""

from __future__ import annotations

try:
    from paddleocr import PaddleOCR

    _PADDLE_AVAILABLE = True
except ImportError:
    _PADDLE_AVAILABLE = False


class OCREngine:
    def __init__(self, lang: str = "pt", use_gpu: bool = False):
        if not _PADDLE_AVAILABLE:
            raise RuntimeError(
                "PaddleOCR nao instalado. Execute: pip install paddleocr paddlepaddle"
            )
        self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=use_gpu, show_log=False)

    def extract_text(self, image) -> list[str]:
        """Retorna a lista de strings detectadas na regiao."""
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
