"""
Тесты мультимодального модуля SafeNet KZ (OCR скриншотов).
"""

from pathlib import Path
from PIL import Image
from src.multimodal.ocr_extractor import OCRExtractor
from src.scoring.engine import ScoringEngine
from src.core.types import InputCase, TrackType, RiskLevel


PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = PROJECT_ROOT / "data" / "synthetic" / "images"


def test_image_preprocessing():
    extractor = OCRExtractor()
    img = Image.new("RGB", (200, 100), color=(100, 100, 100))
    processed = extractor.preprocess_image_for_ocr(img)
    assert processed.size == (200, 100)
    assert processed.mode == "L" or processed.mode == "1"


def test_ocr_extraction_from_synthetic_image():
    extractor = OCRExtractor()
    pyramid_img = str(IMAGES_DIR / "ocr_pyramid_sample.png")
    
    text = extractor.extract_text_from_image(pyramid_img)
    assert len(text) > 0
    assert "10000" in text
    assert "Kaspi" in text or "каспи" in text.lower()


def test_multimodal_case_analysis():
    engine = ScoringEngine()
    pyramid_img = str(IMAGES_DIR / "ocr_pyramid_sample.png")
    
    # Случай, где в тексте поста почти ничего нет, а вся схема в скриншоте
    case = InputCase(
        id="case_multimodal_01",
        text="Смотрите закрепленный скриншот и пишите в личку!",
        image_paths=[pyramid_img],
        channel_or_account="@secret_group",
        platform="telegram"
    )
    
    result = engine.analyze_case(case)
    
    assert result.primary_track == TrackType.PYRAMID
    assert result.score >= 60.0
    assert any("OCR" in f.feature_name or "скриншот" in f.feature_name.lower() for f in result.triggered_features)


def test_multimodal_benign_image():
    engine = ScoringEngine()
    benign_img = str(IMAGES_DIR / "ocr_benign_sample.png")
    
    case = InputCase(
        id="case_multimodal_benign",
        text="Условия в картинке",
        image_paths=[benign_img],
        channel_or_account="@store_kz",
        platform="instagram"
    )
    
    result = engine.analyze_case(case)
    assert result.level == RiskLevel.LOW
    assert result.primary_track == TrackType.BENIGN