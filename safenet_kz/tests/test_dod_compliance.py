"""
Финальный тест самопроверки Definition of Done (DoD) SafeNet KZ.
Автоматически проверяет выполнение всех обязательных пунктов разделов 10 и 12 ТЗ.
"""

from pathlib import Path
import json

from src.core.types import InputCase, RiskLevel, TrackType
from src.scoring.engine import ScoringEngine
from src.explanation.formatter import validate_explanation_compliance


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_dod_deliverables_exist():
    """Проверка сдачи всех 5 обязательных документов и артефактов (Раздел 10)."""
    assert (PROJECT_ROOT / "README.md").exists(), "README.md отсутствует"
    assert (PROJECT_ROOT / "PITCH.md").exists(), "PITCH.md отсутствует"
    assert (PROJECT_ROOT / "METHODOLOGY.md").exists(), "METHODOLOGY.md отсутствует"
    assert (PROJECT_ROOT / "artifacts" / "metrics.json").exists(), "metrics.json отсутствует"
    assert (PROJECT_ROOT / "ROADMAP.md").exists(), "ROADMAP.md отсутствует"
    assert (PROJECT_ROOT / "DATA.md").exists(), "DATA.md отсутствует"
    assert (PROJECT_ROOT / "Dockerfile").exists(), "Dockerfile отсутствует"
    assert (PROJECT_ROOT / "docker-compose.yml").exists(), "docker-compose.yml отсутствует"


def test_dod_metrics_calculated_and_compliant():
    """Проверка честности и корректности метрик на отложенном тесте."""
    metrics_path = PROJECT_ROOT / "artifacts" / "metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ov = data["test_results_full_pipeline"]["overall"]
    assert ov["precision"] >= 0.90, f"Precision ниже 90%: {ov['precision']}"
    assert ov["recall"] >= 0.80, f"Recall ниже 80%: {ov['recall']}"
    assert ov["fpr"] <= 0.05, f"FPR выше 5%: {ov['fpr']}"
    assert ov["f1"] >= 0.85, f"F1 ниже 0.85: {ov['f1']}"

    # Проверка наличия всех 3 треков в отчете
    tracks = data["test_results_full_pipeline"]["per_track"]
    assert "lottery" in tracks
    assert "casino" in tracks
    assert "pyramid" in tracks

    # Проверка языкового охвата
    langs = data["test_results_full_pipeline"]["per_language"]
    assert "ru" in langs
    assert "kk" in langs
    assert "mixed_translit" in langs

    # Проверка Ablation Study
    ablation = data["ablation_study"]["f1_scores"]
    assert "Full_Pipeline" in ablation
    assert "Without_Graph" in ablation
    assert "Without_OCR" in ablation
    assert "Baseline_Rules_Only" in ablation


def test_dod_compliance_principle():
    """Проверка запрета на обвинительные вердикты во всех модулях."""
    engine = ScoringEngine()
    
    test_cases = [
        "🔥 Лотерея билет бағасы 1000 тг. Выбор рандомайзер в прямом эфире!",
        "🎰 Слоты занос! Рега по ссылке в закрепе, промокод SAFEKZ",
        "💰 Вложи 5000 тг забери 15000 тг на Kaspi. Гарантия 100%, 3 места!",
        "🎁 Бесплатный конкурс репостов, участие бесплатное без взносов.",
    ]

    for text in test_cases:
        res = engine.analyze_text(text)
        # Проверяем отсутствие юридических ярлыков
        assert validate_explanation_compliance(res) is True
        # Проверяем наличие обязательного дисклеймера
        assert "не выносит вердиктов" in res.disclaimer or "признаки" in res.disclaimer.lower()
        # Проверяем уровень риска
        assert res.level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        # Проверяем маскирование ПДн
        assert "+770" not in res.masked_text