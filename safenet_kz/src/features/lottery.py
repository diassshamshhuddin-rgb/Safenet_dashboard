"""
Модуль выявления признаков платных розыгрышей и лотерей (Трек 1).
Ищет признаки:
- Платное участие (взнос, покупка билетов/номерков, перевод на карту)
- Случайный выбор (рандомайзер, колесо фортуны, лототрон, прямой эфир)
- Доход организатора (продажа слотов, сбор средств)
- Учитывает грамматику и порядок слов казахского и русского языков.
"""

import re
from typing import List
from src.core.types import EvidenceItem, TrackType
from src.preprocessing.pipeline import PreprocessingResult


PATTERNS_PAYMENT = [
    (re.compile(r'\b(?:билет\w*|номер\w*|слот\w*|орын\w*)\s*(?:бағасы|құны|цена|стоимость)?\s*(?:бар болғаны|всего)?\s*[:\-]?\s*(\d+[\s\d]*)\s*(?:тг|теңге|тенге|kzt|tg)\b', re.IGNORECASE),
     "Платный билет/номерок для участия", 30.0),
    (re.compile(r'\b(?:взнос\w*|жарна\w*|төлем\w*|оплата|қатысу жарнасы)\s*(?:за участие|үшін)?\s*(?:всего|бар болғаны)?\s*[:\-]?\s*(\d+[\s\d]*)\s*(?:тг|теңге|тенге|kzt|tg)?\b', re.IGNORECASE),
     "Взнос за участие в розыгрыше", 30.0),
    (re.compile(r'\b(?:перевод\w*|аудару|аударыңыз|скидывать|переводить)\s*(?:на\s+каспи|каспиге|kaspi|на карту|картаға)\b', re.IGNORECASE),
     "Требование перевода средств для участия (прямой порядок)", 20.0),
    (re.compile(r'\b(?:каспи\w*|kaspi\w*|карта\w*)\s*(?:арқылы|аркылы|бойынша|на)?\s*(?:аудару|аударыңыз|аудар|перевод\w*|скинуть|төлеу)\b', re.IGNORECASE),
     "Требование перевода средств (обратный порядок / каз. синтаксис)", 20.0),
    (re.compile(r'\b(?:покупай\w*|сатып ал\w*|бронь\w*|забирай\w*)\s*(?:билет\w*|номерок\w*|слот\w*|номер\w*)\b', re.IGNORECASE),
     "Призыв к покупке мест/билетов", 15.0),
]

PATTERNS_RANDOM = [
    (re.compile(r'\b(?:рандомайзер\w*|рандом\w*|randomizer\w*|random\w*)\b', re.IGNORECASE),
     "Определение победителя через цифровой рандомайзер", 20.0),
    (re.compile(r'\b(?:колесо фортуны|дөңгелек\w*|рулетка\w*|барабан\w*|лототрон\w*)\b', re.IGNORECASE),
     "Использование генератора случайности (колесо/барабан/лототрон)", 20.0),
    (re.compile(r'\b(?:жеребьевка|жеребе|розыгрыш в прямом эфире|тікелей эфир\w*|лайв\w*|прямой эфир\w*)\b', re.IGNORECASE),
     "Проведение розыгрыша/жеребьевки в эфире", 15.0),
    (re.compile(r'\b(?:ұтыс ойын\w*|мега[- ]ұтыс|розыгрыш\w*|лотерея\w*)\b', re.IGNORECASE),
     "Формат проведения розыгрыша / лотереи", 15.0),
]

PATTERNS_PRIZE = [
    (re.compile(r'\b(?:iphone|айфон|автомобиль|көлік|машина|elantra|camry|hyundai|500\s*000|1\s*000\s*000)\b', re.IGNORECASE),
     "Ценный материальный приз (авто, смартфон, крупная сумма)", 15.0),
]


def extract_lottery_features(prep: PreprocessingResult) -> List[EvidenceItem]:
    """Извлекает признаки платного розыгрыша из предобработанного текста."""
    evidence_list: List[EvidenceItem] = []
    texts_to_check = [prep.cleaned_text, prep.transliterated_text]
    seen_features = set()

    for text in texts_to_check:
        for pattern, feat_name, weight in PATTERNS_PAYMENT:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.LOTTERY,
                    description="Обнаружены признаки сбора денежных средств за участие в розыгрыше."
                ))
                seen_features.add(feat_name)

        for pattern, feat_name, weight in PATTERNS_RANDOM:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.LOTTERY,
                    description="Использование механизма случайного определения победителя."
                ))
                seen_features.add(feat_name)

        for pattern, feat_name, weight in PATTERNS_PRIZE:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.LOTTERY,
                    description="Заявлен крупный приз для привлечения внимания аудитории."
                ))
                seen_features.add(feat_name)

    # Наличие реквизитов в контексте розыгрыша
    has_lottery_term = any(w in t.lower() for t in texts_to_check for w in ["билет", "ұтыс", "розыгрыш", "жарна", "лото"])
    if (len(prep.entities["cards"]) > 0 or len(prep.entities["phones"]) > 0) and has_lottery_term:
        if "Реквизиты для перевода средств за участие" not in seen_features:
            evidence_list.append(EvidenceItem(
                feature_name="Реквизиты для перевода средств за участие",
                weight=20.0,
                snippet=f"Карта/тел: {prep.entities['cards'][:1] or prep.entities['phones'][:1]}",
                track=TrackType.LOTTERY,
                description="Указаны платежные реквизиты физического лица для оплаты участия."
            ))
            seen_features.add("Реквизиты для перевода средств за участие")

    return evidence_list