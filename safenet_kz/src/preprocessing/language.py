"""
Модуль детекции языка для SafeNet KZ.
Определяет присутствие русского, казахского, смешанного текста или транслита.
"""

import re
from typing import List


KAZAKH_SPECIFIC_CHARS = set("әіңғүұқөһӘІҢҒҮҰҚӨҺ")
KAZAKH_KEYWORDS = {
    "үшін", "бар", "жоқ", "теңге", "тг", "орын", "тікелей", "жеңімпаз", "ақша",
    "қатысу", "аударым", "жарна", "ұтыс", "көлік", "салым", "көбейту", "дөңгелек",
    "досыңды", "билет", "қалды", "кепілдік", "қор", "қайырымдылық"
}

RUSSIAN_KEYWORDS = {
    "для", "есть", "нет", "рублей", "тенге", "мест", "прямом", "победитель", "деньги",
    "участие", "перевод", "взнос", "выигрыш", "машина", "вклад", "умножение", "колесо",
    "друга", "билет", "осталось", "гарантия", "фонд", "благотворительность"
}


def detect_language(text: str) -> List[str]:
    """
    Определяет языковую специфику текста.
    Возвращает список тегов: 'kk', 'ru', 'mixed', 'translit'.
    """
    detected = []
    text_lower = text.lower()
    
    # 1. Проверка специфических букв казахского алфавита
    has_kz_letters = any(c in KAZAKH_SPECIFIC_CHARS for c in text)
    
    # 2. Проверка лексических маркеров
    words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁәіңғүұқөһӘІҢҒҮҰҚӨҺ]+\b', text_lower)
    word_set = set(words)
    
    kz_matches = len(word_set.intersection(KAZAKH_KEYWORDS))
    ru_matches = len(word_set.intersection(RUSSIAN_KEYWORDS))
    
    # 3. Проверка транслита (латиница при отсутствии большого числа URL)
    latin_words = [w for w in words if re.fullmatch(r'[a-zA-Z]+', w) and len(w) > 2]
    total_words = len(words) if len(words) > 0 else 1
    latin_ratio = len(latin_words) / total_words
    
    is_translit = latin_ratio > 0.35 and any(w in {"kaspi", "utys", "akshany", "kobeitu", "bilet", "kzt", "efirde"} for w in latin_words)
    
    if is_translit:
        detected.append("translit")
        
    if has_kz_letters or kz_matches > 0:
        detected.append("kk")
        
    # Проверка на русский
    cyrillic_words = [w for w in words if re.search(r'[а-яА-ЯёЁ]', w)]
    if ru_matches > 0 or (len(cyrillic_words) > 0 and not has_kz_letters):
        detected.append("ru")
        
    if "kk" in detected and "ru" in detected:
        detected.append("mixed")
        
    if not detected:
        detected.append("ru")  # Дефолт по ТЗ
        
    return detected