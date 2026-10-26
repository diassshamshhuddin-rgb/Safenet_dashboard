"""
Модуль очистки и деобфускации текста (SafeNet KZ).
Устраняет подмену букв цифрами и спецсимволами, пробелы внутри ключевых слов, нормализует Unicode.
"""

import re
import unicodedata
from typing import Dict


# Таблица замен символов обфускации на кириллицу (leet speak / маскировка)
OBFUSCATION_MAP: Dict[str, str] = {
    '@': 'а',
    '0': 'о',
    '1': 'и',
    '3': 'з',
    '4': 'а',
    '6': 'б',
    '$': 'с',
    'u': 'и',
}

# Регулярные выражения для распознавания искусственно разделенных ключевых слов
SPACED_KEYWORDS = [
    (re.compile(r'\bк\s+а\s+з\s+и\s+н\s+о\b', re.IGNORECASE), 'казино'),
    (re.compile(r'\bп\s+и\s+р\s+а\s+м\s+и\s+д\s+а\b', re.IGNORECASE), 'пирамида'),
    (re.compile(r'\bс\s+л\s+о\s+т\b', re.IGNORECASE), 'слот'),
    (re.compile(r'\bб\s+и\s+л\s+е\s+т\b', re.IGNORECASE), 'билет'),
    (re.compile(r'\bв\s+з\s+н\s+о\s+с\b', re.IGNORECASE), 'взнос'),
    (re.compile(r'\bж\s+а\s+р\s+н\s+а\b', re.IGNORECASE), 'жарна'),
    (re.compile(r'\bұ\s+т\s+ы\s+с\b', re.IGNORECASE), 'ұтыс'),
    (re.compile(r'\bк\s+а\s+с\s+п\s+и\b', re.IGNORECASE), 'каспи'),
]

# Нормализация эмодзи в семантические маркеры
EMOJI_REPLACEMENTS = {
    '🎰': ' [СЛОТ_КАЗИНО] ',
    '🎲': ' [ИГРА_РАНДОМ] ',
    '💰': ' [ДЕНЬГИ] ',
    '💸': ' [ДЕНЬГИ] ',
    '💳': ' [КАРТА] ',
    '🔥': ' [СРОЧНОСТЬ] ',
    '⚡': ' [СРОЧНОСТЬ] ',
    '🎁': ' [ПОДАРОК_РОЗЫГРЫШ] ',
    '👑': ' [VIP_КУРАТОР] ',
}


def normalize_unicode(text: str) -> str:
    """Приводит текст к стандарту Unicode NFKC и очищает скрытые управляющие символы."""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'[\u200B-\u200D\uFEFF]', '', text)
    return text


def clean_obfuscation(text: str) -> str:
    """Устраняет обфускацию: пробелы между буквами слов, замену букв на @, 0, 4 и т.д."""
    text = normalize_unicode(text)
    
    # Заменяем известные эмодзи
    for emoji, token in EMOJI_REPLACEMENTS.items():
        text = text.replace(emoji, token)
        
    # Схлопываем слова с искусственными пробелами
    for pattern, replacement in SPACED_KEYWORDS:
        text = pattern.sub(replacement, text)
        
    # Точечная деобфускация внутри слов (к@зино, сл0т, бuлет, пuрамида)
    def deobfuscate_word(match):
        word = match.group(0)
        
        # Если слово чисто числовое (или код карты, телефон, сумма) — НЕ трогать цифры
        if word.isdigit():
            return word
            
        # Замены применяем только если в слове есть хотя бы одна буква и спецсимвол / подменяющая цифра
        has_letters = any(c.isalpha() for c in word)
        has_obfuscation = any(c in '@0134$u' for c in word.lower())
        
        if has_letters and has_obfuscation:
            clean_chars = []
            for c in word:
                c_low = c.lower()
                if c_low in OBFUSCATION_MAP:
                    clean_chars.append(OBFUSCATION_MAP[c_low])
                else:
                    clean_chars.append(c)
            return "".join(clean_chars)
            
        return word

    text = re.sub(r'\b[a-zA-Zа-яА-ЯёЁәіңғүұқөһӘІҢҒҮҰҚӨҺ0-9@$]{3,}\b', deobfuscate_word, text)
    
    # Удаляем лишние повторяющиеся пробелы
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text