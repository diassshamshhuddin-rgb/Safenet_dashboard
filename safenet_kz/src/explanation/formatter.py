"""
Форматирование и валидация объяснительного слоя решений SafeNet KZ.
Гарантирует отсутствие обвинительных формулировок и соответствие формату для дашборда аналитика.
"""

from typing import List, Dict, Any
from src.core.types import AnalysisExplanation, EvidenceItem


FORBIDDEN_WORDS = [
    "мошенник", "мошенники", "мошенничество (факт)", "нелегально", "незаконно",
    "виновен", "преступник", "преступление", "лохотрон", "скам"
]


def validate_explanation_compliance(explanation: AnalysisExplanation) -> bool:
    """
    Проверяет, что в текстах объяснений и описаниях признаков
    отсутствуют юридические вердикты и обвинительные слова.
    """
    text_corpus = (
        explanation.disclaimer + " " +
        " ".join(item.feature_name + " " + item.description for item in explanation.triggered_features)
    ).lower()

    for word in FORBIDDEN_WORDS:
        if word in text_corpus:
            return False
    return True


def format_evidence_table(explanation: AnalysisExplanation) -> List[Dict[str, Any]]:
    """Форматирует сработавшие признаки в табличный вид для дашборда."""
    table = []
    for item in explanation.triggered_features:
        table.append({
            "Признак": item.feature_name,
            "Вклад в риск": f"{item.weight:+.1f}",
            "Цитата / фрагмент": item.snippet,
            "Пояснение": item.description,
            "Трек": item.track.value,
        })
    return table