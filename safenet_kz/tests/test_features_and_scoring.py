"""
Тесты для модулей признаков 3-х треков, скоринга и объяснительного слоя.
"""

from src.scoring.engine import ScoringEngine
from src.core.types import RiskLevel, TrackType
from src.explanation.formatter import validate_explanation_compliance, format_evidence_table


def test_track1_lottery_detection():
    engine = ScoringEngine()
    text = "🔥 Розыгрыш IPHONE 16! Билет бағасы 1500 тг. Перевод на Kaspi +77011112233. Выбор через рандомайзер в прямом эфире!"
    res = engine.analyze_text(text)
    
    assert res.primary_track == TrackType.LOTTERY
    assert res.score >= 50.0
    assert any("билет" in f.feature_name.lower() or "билет" in f.snippet.lower() for f in res.triggered_features)
    assert any("рандомайзер" in f.feature_name.lower() or "рандомайзер" in f.snippet.lower() for f in res.triggered_features)
    assert validate_explanation_compliance(res) is True


def test_track2_casino_detection():
    engine = ScoringEngine()
    text = "🎰 Ребята, поднял за вечер 350 000 тг в слотах! Ссылка на зеркало в шапке: https://lucky-slot777.test/reg?ref=BONUS100 Промокод: SAFEKZ"
    res = engine.analyze_text(text)
    
    assert res.primary_track == TrackType.CASINO
    assert res.score >= 60.0
    assert any("гемблинг" in f.feature_name.lower() or "слот" in f.snippet.lower() for f in res.triggered_features)
    assert validate_explanation_compliance(res) is True


def test_track3_pyramid_detection():
    engine = ScoringEngine()
    text = "💰 Вложи 5000 тг — забери 15 000 тг уже завтра! Гарантия 100%. Осталось 3 места! Перевод на Kaspi +77019998877 куратору."
    res = engine.analyze_text(text)
    
    assert res.primary_track == TrackType.PYRAMID
    assert res.score >= 70.0
    assert res.level == RiskLevel.HIGH
    assert any("умножения" in f.feature_name.lower() for f in res.triggered_features)
    assert any("дефицита" in f.feature_name.lower() for f in res.triggered_features)
    assert validate_explanation_compliance(res) is True


def test_hard_negatives_mitigation():
    engine = ScoringEngine()
    
    # 1. Бесплатный конкурс
    free_contest = "🎁 Бесплатный конкурс! Подпишись, поставь лайк и отметь 2 друзей. Участие абсолютно бесплатное, никаких взносов и оплат! Итоги в эфире через рандом."
    res_free = engine.analyze_text(free_contest)
    assert res_free.level == RiskLevel.LOW
    assert res_free.score < 40.0
    assert res_free.primary_track == TrackType.BENIGN

    # 2. Предупреждение АФМ РК
    afm_warning = "⚠️ Агентство по финансовому мониторингу РК (АФМ) предупреждает граждан: не переводите деньги организаторам финансовых пирамид, обещающим быстрый доход."
    res_afm = engine.analyze_text(afm_warning)
    assert res_afm.level == RiskLevel.LOW
    assert res_afm.score < 20.0
    assert res_afm.primary_track == TrackType.BENIGN


def test_evidence_table_formatting():
    engine = ScoringEngine()
    text = "Вложи 5000 тг получи 15000 тг на Kaspi"
    res = engine.analyze_text(text)
    table = format_evidence_table(res)
    assert len(table) > 0
    assert "Признак" in table[0]
    assert "Вклад в риск" in table[0]
    assert "Цитата / фрагмент" in table[0]