"""
Модуль снижения ложных срабатываний (FPR Mitigator).
Выявляет признаки легального контента:
- Бесплатные конкурсы («участие абсолютно бесплатное», «никаких взносов»)
- Предупреждения госорганов (АФМ РК, ҚМА, полиция)
- Официальная благотворительность с отчетностью и выписками
- Государственные финансовые программы и легальные банковские депозиты (КФГД)
- Официальный ритейл и киберспортивные соревнования
"""

import re
from typing import List, Tuple
from src.core.types import EvidenceItem, TrackType
from src.preprocessing.pipeline import PreprocessingResult


BENIGN_PATTERNS = [
    # 1. Бесплатные активности
    (re.compile(r'\b(?:участие\s+абсолютно\s+бесплатное|никаких\s+взносов|мүлдем\s+тегін|қатысу\s+тегін|ешқандай\s+төлем\s+жоқ|без\s+взносов|тегін\s+конкурс)\b', re.IGNORECASE),
     "Явное указание на бесплатность участия (отсутствие взносов)", -45.0),
    (re.compile(r'\b(?:подпишись\s+на\s+нас|отметь\s+\d+\s+друзей|лайк\s+басыңыз|достарыңды\s+белгілеңіз)\b', re.IGNORECASE),
     "Стандартная механика вовлечения бесплатного конкурса (репост/отметка)", -20.0),

    # 2. Предупреждения регуляторов и правоохранительных органов
    (re.compile(r'\b(?:агентство по финансовому мониторингу|афм|қма|сақ болуға шақырады|предупреждает граждан|никогда не переводите|қаржылық пирамидалардан сақ)\b', re.IGNORECASE),
     "Официальное предупреждение уполномоченных органов (АФМ РК)", -60.0),
    (re.compile(r'\b(?:финансовая грамотность|қаржылық сауаттылық|депозиты надежнее)\b', re.IGNORECASE),
     "Просветительский материал по финансовой грамотности", -40.0),

    # 3. Легальные банковские гарантии и официальные фонды
    (re.compile(r'\b(?:кфгд|қдкбқ|фонд гарантирования депозитов|гарантия государства|лицензия аррфр)\b', re.IGNORECASE),
     "Легальный банковский продукт под защитой КФГД", -50.0),
    (re.compile(r'\b(?:қайырымдылық қоры|благотворительный фонд|медицинские выписки|отчетность публикуется)\b', re.IGNORECASE),
     "Верифицированная благотворительная деятельность с отчетностью", -50.0),

    # 4. Официальная торговля и спорт
    (re.compile(r'\b(?:официальная гарантия|рассрочка 0-0-24|kaspi red|дүкеннің туған күніне|турнир по cs2|киберспорт)\b', re.IGNORECASE),
     "Официальный ритейл / спорт / киберспорт", -35.0),
]


def extract_benign_mitigation(prep: PreprocessingResult) -> Tuple[float, List[EvidenceItem]]:
    """
    Вычисляет скидку к скору риска и формирует перечень смягчающих признаков.
    """
    mitigation_discount = 0.0
    mitigation_items: List[EvidenceItem] = []
    
    texts_to_check = [prep.cleaned_text, prep.transliterated_text]
    seen_features = set()

    for text in texts_to_check:
        for pattern, feat_name, weight in BENIGN_PATTERNS:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                mitigation_items.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,  # отрицательный вес
                    snippet=snippet,
                    track=TrackType.BENIGN,
                    description="Обнаружены признаки легального информационного, просветительского или благотворительного контента."
                ))
                seen_features.add(feat_name)
                mitigation_discount += abs(weight)

    return mitigation_discount, mitigation_items