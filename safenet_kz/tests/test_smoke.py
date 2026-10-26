"""
Smoke-тест структуры репозитория и базовых типов SafeNet KZ.
"""

from src.core.config import AppConfig
from src.core.types import (
    TrackType,
    RiskLevel,
    AnalystDecision,
    InputCase,
    EvidenceItem,
    AnalysisExplanation,
)


def test_config_loads_properly():
    config = AppConfig.load()
    assert config.app_name == "SafeNet KZ Prototype"
    assert "не выносит вердиктов" in config.disclaimer
    assert config.get_risk_level_label(85.0) == "Высокий"
    assert config.get_risk_level_label(55.0) == "Средний"
    assert config.get_risk_level_label(15.0) == "Низкий"


def test_core_types():
    evidence = EvidenceItem(
        feature_name="Сбор средств на карту Kaspi",
        weight=25.0,
        snippet="переводите на каспи по номеру +7701***",
        track=TrackType.PYRAMID,
        description="Признак требования перевода на карту физического лица"
    )
    assert evidence.weight == 25.0
    assert evidence.track == TrackType.PYRAMID

    explanation = AnalysisExplanation(
        score=75.5,
        level=RiskLevel.HIGH,
        primary_track=TrackType.PYRAMID,
        triggered_features=[evidence],
    )
    assert explanation.level == RiskLevel.HIGH
    assert len(explanation.triggered_features) == 1
    assert "законодательством" in explanation.disclaimer