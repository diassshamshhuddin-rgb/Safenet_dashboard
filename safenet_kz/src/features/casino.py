"""
Модуль выявления признаков скрытого продвижения онлайн-казино (Трек 2).
Ищет признаки:
- Реферальные ссылки, зеркала, промокоды
- Нативная реклама («заносы», «как я поднял денег», скриншоты выводов)
- Гемблинг-лексика (слоты, фриспины, куш, занос)
- Призывы к переходу в профиль/закреп за ссылкой
"""

import re
from typing import List
from src.core.types import EvidenceItem, TrackType
from src.preprocessing.pipeline import PreprocessingResult


PATTERNS_GAMBLING_LEXICON = [
    (re.compile(r'\b(?:казино|casino|слот|слоты|слотка|фриспины|sweet bonanza|aviator|авиатор|занос|джекпот)\b', re.IGNORECASE),
     "Гемблинг-терминология (слоты/казино/игры)", 25.0),
    (re.compile(r'\[СЛОТ_КАЗИНО\]'),
     "Символика игровых автоматов (эмодзи слотов)", 15.0),
    (re.compile(r'\b(?:поднял|сорвал куш|вывел|выигрыш|ұтып алдым|шығарып алдым|закинул\s*\d+)\b', re.IGNORECASE),
     "Нативная демонстрация легкого выигрыша («занос»)", 20.0),
    (re.compile(r'\b(?:бонус\s*\+?\d+%\s*|200\s*фриспинов|без верификации|моментальный вывод)\b', re.IGNORECASE),
     "Завлекающее предложение бонусов и легкого вывода", 20.0),
]

PATTERNS_LINKS_AND_MIRRORS = [
    (re.compile(r'\b(?:зеркало|айна|ссылка в шапке|ссылка в профиле|сілтеме профильде|сілтеме шапкада|ссылка в закрепе)\b', re.IGNORECASE),
     "Использование зеркал и ссылок-прокладок в описании профиля", 25.0),
    (re.compile(r'\b(?:промокод|код|промо|promocode)[\s:=]+([A-Z0-9_]{3,})\b', re.IGNORECASE),
     "Указание реферального промокода для бонуса", 20.0),
    (re.compile(r'(?:\?|&)(?:ref|aff|partner|promo|bonus)=', re.IGNORECASE),
     "Партнерские/реферальные метки в ссылке", 25.0),
]


def extract_casino_features(prep: PreprocessingResult) -> List[EvidenceItem]:
    """Извлекает признаки скрытого продвижения онлайн-казино."""
    evidence_list: List[EvidenceItem] = []
    texts_to_check = [prep.cleaned_text, prep.transliterated_text]
    seen_features = set()

    for text in texts_to_check:
        # 1. Лексика гемблинга и нативной рекламы
        for pattern, feat_name, weight in PATTERNS_GAMBLING_LEXICON:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.CASINO,
                    description="Использование терминологии онлайн-казино и демонстрация выигрышей."
                ))
                seen_features.add(feat_name)

        # 2. Зеркала, ссылки и промокоды
        for pattern, feat_name, weight in PATTERNS_LINKS_AND_MIRRORS:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.CASINO,
                    description="Наличие признаков маскированной переадресации или реферальной программы."
                ))
                seen_features.add(feat_name)

    # 3. Анализ извлеченных доменов и промокодов
    for domain in prep.entities.get("domains", []):
        if any(g in domain.lower() for g in ["slot", "casino", "spin", "win", "lucky", "bet", "bonus"]):
            if "Подозрительное доменное имя гемблинг-тематики" not in seen_features:
                evidence_list.append(EvidenceItem(
                    feature_name="Подозрительное доменное имя гемблинг-тематики",
                    weight=25.0,
                    snippet=domain,
                    track=TrackType.CASINO,
                    description=f"В тексте обнаружена ссылка на сторонний домен игровой тематики: {domain}"
                ))
                seen_features.add("Подозрительное доменное имя гемблинг-тематики")

    if len(prep.entities.get("promocodes", [])) > 0 and "Реферальный промокод" not in seen_features:
        evidence_list.append(EvidenceItem(
            feature_name="Реферальный промокод",
            weight=15.0,
            snippet=", ".join(prep.entities["promocodes"]),
            track=TrackType.CASINO,
            description="Обнаружены уникальные промокоды для привлечения аудитории по реферальной схеме."
        ))
        seen_features.add("Реферальный промокод")

    return evidence_list