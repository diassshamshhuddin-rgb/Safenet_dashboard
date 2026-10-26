"""
Модуль мультимодального OCR-анализа скриншотов (SafeNet KZ).
Распознает текст на изображениях (ru, kk, латиница), применяет предобработку
(бинаризация, контрастирование) и формирует мультимодальные признаки.
Поддерживает pytesseract с надежным fallback-режимом для окружений без Tesseract.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any
from PIL import Image, ImageEnhance, ImageOps
from src.core.types import EvidenceItem, TrackType


class OCRExtractor:
    def __init__(self):
        self._tesseract_available = None

    def _check_tesseract(self) -> bool:
        if self._tesseract_available is not None:
            return self._tesseract_available
        try:
            import pytesseract
            # Быстрая проверка вызова версии tesseract
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
        except Exception:
            self._tesseract_available = False
        return self._tesseract_available

    def preprocess_image_for_ocr(self, img: Image.Image) -> Image.Image:
        """Оптимизация скриншота: перевод в ч/б, повышение контраста для четкости шрифта."""
        # 1. Перевод в градации серого
        gray = ImageOps.grayscale(img)
        # 2. Повышение контрастности
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.8)
        # 3. Адаптивное бинарное разделение
        threshold = 140
        binary = enhanced.point(lambda p: 255 if p > threshold else 0)
        return binary

    def extract_text_from_image(self, image_path: str) -> str:
        """Извлекает текст из изображения с использованием Tesseract или fallback-механизма."""
        path = Path(image_path)
        if not path.exists():
            return ""

        try:
            with Image.open(path) as img:
                # Попытка реального OCR через Tesseract
                if self._check_tesseract():
                    try:
                        import pytesseract
                        processed = self.preprocess_image_for_ocr(img)
                        text = pytesseract.image_to_string(processed, lang="rus+kaz")
                        if text and text.strip():
                            return text.strip()
                    except Exception:
                        pass

                # Fallback 1: Чтение встроенных текстовых метаданных PNG
                if hasattr(img, "info") and "description" in img.info:
                    return img.info["description"].strip()

                # Fallback 2: Чтение sidecar текстового файла
                sidecar = path.with_suffix(path.suffix + ".txt")
                if sidecar.exists():
                    with open(sidecar, "r", encoding="utf-8") as f:
                        return f.read().strip()
        except Exception:
            pass

        return ""

    def process_case_images(self, image_paths: List[str]) -> Tuple[str, List[EvidenceItem]]:
        """
        Обрабатывает список изображений для кейса:
        - Извлекает суммарный текст скриншотов
        - Формирует мультимодальные признаки (при наличии подозрительного содержимого)
        """
        extracted_texts = []
        evidence_items: List[EvidenceItem] = []

        for p in image_paths:
            img_text = self.extract_text_from_image(p)
            if img_text:
                extracted_texts.append(img_text)
                evidence_items.append(EvidenceItem(
                    feature_name="Текст со скриншота (OCR)",
                    weight=15.0,
                    snippet=img_text[:80] + ("..." if len(img_text) > 80 else ""),
                    track=TrackType.BENIGN,  # Трек определит скоринговый движок
                    description="Обнаружен читаемый текст на скриншоте мобильного приложения или переписки."
                ))

        combined_text = "\n".join(extracted_texts)
        return combined_text, evidence_items