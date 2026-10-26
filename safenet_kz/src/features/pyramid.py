"""
Модуль выявления признаков финансовых пирамид в мессенджерах (Трек 3).
Ищет признаки:
- Нереалистичные обещания гарантированного сверхдохода («вложи 5000 — забери 15000», «салымыңыз 10к, пайдасы 20к»)
- Искусственная срочность и психологическое давление («осталось 2 места», «орын саны: 3 орын»)
- Реферальные бонусы за привлечение новых участников
- Имитация выплат (скриншоты, отзывы-прогревы)
- Переводы на личные карты и Kaspi под видом «кассы взаимопомощи» / «кураторов»
"""

import re
from typing import List
from src.core.types import EvidenceItem, TrackType
from src.preprocessing.pipeline import PreprocessingResult


PATTERNS_UNREALISTIC_RETURN = [
    (re.compile(r'\b(?:вложи|инвестируй|салыңыз|салып|қосыңыз|косыныз)\s*(\d+[\s\d]*)\s*(?:тг|теңге|тенге|kzt)?\s*[-—–]?\s*(?:получи|забери|алыңыз|аласың|түседі|туседи)\s*(\d+[\s\d]*)', re.IGNORECASE),
     "Обещание кратного умножения вложенных средств", 35.0),
    (re.compile(r'\b(?:салымыңыз|салым)\s*(\d+[\s\d]*)\s*(?:тг|теңге|тенге|kzt)?\s*(?:болса)?\s*[,.\-]?\s*(?:пайдасы|пайда)\s*(\d+[\s\d]*)', re.IGNORECASE),
     "Обещание фиксированной прибыли на сумму вклада (каз. синтаксис)", 35.0),
    (re.compile(r'\b(?:ақшаны көбейту|акшаны кобейту|2 еселеу|умножаем вложения|доходность\s*\d+%\s*в день|пассивный доход без рисков)\b', re.IGNORECASE),
     "Обещание гарантированного сверхдохода без рыночных рисков", 30.0),
    (re.compile(r'\b(?:гарантия\s*100%|100%\s*(?:кепілдік|гарантия|кепилдик)|без риска|кепілдендірілген(?:\s+пайда)?)(?!\w)', re.IGNORECASE),
     "Заверение в абсолютной гарантии доходности", 25.0),
    (re.compile(r'\b(?:инвестиция\w*|инвестиционный\w*)\s*(?:в telegram|в whatsapp|пул|проект)\b', re.IGNORECASE),
     "Инвестиционные предложения в нерегулируемых каналах мессенджеров", 20.0),
]

PATTERNS_URGENCY = [
    (re.compile(r'\b(?:осталось(?:\s+всего)?|қалғаны|орын саны|қалды)\s*[:\-]?\s*(\d+)\s*(?:мест\w*|орын\w*)?\b', re.IGNORECASE),
     "Создание искусственного дефицита мест («осталось N мест»)", 20.0),
    (re.compile(r'\b(?:успей зайти|места тают|қазір жазбасаңыз үлгермейсіз|шұғыл|срочно|успей сегодня)\b', re.IGNORECASE),
     "Психологическое давление фактором срочности", 15.0),
    (re.compile(r'\[СРОЧНОСТЬ\]'),
     "Маркеры срочности и ажиотажа (эмодзи огня/молнии)", 10.0),
]

PATTERNS_REFERRAL_AND_STRUCTURE = [
    (re.compile(r'\b(?:приглашенного друга|досыңды шақырсаң|реферальн\w*\s*(?:бонус\w*|программ\w*|систем\w*)|бонус за привлечение|партнерка)\b', re.IGNORECASE),
     "Реферальная система выплат за привлечение новых участников", 25.0),
    (re.compile(r'\b(?:касса взаимопомощи|өзара көмек кассасы|инвестиционный пул|закрытый пул)\b', re.IGNORECASE),
     "Маскировка под «кассу взаимопомощи» или «закрытый инвест-клуб»", 25.0),
    (re.compile(r'\b(?:куратор\w*|менеджер\w*|кураторға|пиши куратору|жазыңыз)\b', re.IGNORECASE),
     "Указание на куратора/администратора схемы в мессенджере", 20.0),
]

PATTERNS_PAYMENT_PROOF = [
    (re.compile(r'\b(?:скриншоты довольных|выплаты идут нон-стоп|выплачено более|төлем түсті|чектер мен пікірлер)\b', re.IGNORECASE),
     "Публикация фиктивных подтверждений выплат и отзывов-прогревов", 15.0),
]


def extract_pyramid_features(prep: PreprocessingResult) -> List[EvidenceItem]:
    """Извлекает признаки финансовой пирамиды из текста сообщения."""
    evidence_list: List[EvidenceItem] = []
    texts_to_check = [prep.cleaned_text, prep.transliterated_text]
    seen_features = set()

    for text in texts_to_check:
        for pattern, feat_name, weight in PATTERNS_UNREALISTIC_RETURN:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.PYRAMID,
                    description="Выявлены признаки нереалистичных инвестиционных обещаний и быстрой прибыли."
                ))
                seen_features.add(feat_name)

        for pattern, feat_name, weight in PATTERNS_URGENCY:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.PYRAMID,
                    description="Использование триггеров срочности для ускорения перевода денег жертвой."
                ))
                seen_features.add(feat_name)

        for pattern, feat_name, weight in PATTERNS_REFERRAL_AND_STRUCTURE:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.PYRAMID,
                    description="Признак многоуровневого привлечения участников и координации кураторами."
                ))
                seen_features.add(feat_name)

        for pattern, feat_name, weight in PATTERNS_PAYMENT_PROOF:
            if feat_name in seen_features:
                continue
            m = pattern.search(text)
            if m:
                snippet = m.group(0)
                evidence_list.append(EvidenceItem(
                    feature_name=feat_name,
                    weight=weight,
                    snippet=snippet,
                    track=TrackType.PYRAMID,
                    description="Использование скриншотов чеков для формирования доверия вкладчиков."
                ))
                seen_features.add(feat_name)

    # Признак требования перевода на карту/Kaspi при наличии признаков схемы
    has_transfer_marker = any(w in t.lower() for t in texts_to_check for w in ["каспи", "kaspi", "карт", "перевод", "аудар", "төлем", "оплат"])
    if has_transfer_marker:
        if any(f.track == TrackType.PYRAMID for f in evidence_list):
            if "Сбор средств на личную карту/Kaspi" not in seen_features:
                reqs = prep.entities['cards'][:1] or prep.entities['phones'][:1] or ["Kaspi/карта"]
                evidence_list.append(EvidenceItem(
                    feature_name="Сбор средств на личную карту/Kaspi",
                    weight=20.0,
                    snippet=f"Реквизиты/способ: {reqs}",
                    track=TrackType.PYRAMID,
                    description="Требование перевода инвестиций на карту физлица или через Kaspi."
                ))
                seen_features.add("Сбор средств на личную карту/Kaspi")

    return evidence_list