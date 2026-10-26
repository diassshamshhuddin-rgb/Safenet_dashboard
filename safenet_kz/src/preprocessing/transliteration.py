"""
Модуль транслитерации латиницы (каз/рус) в кириллицу для SafeNet KZ.
Позволяет единым лексическим модулям анализировать тексты, написанные транслитом.
"""

import re

# Таблица транслитерации диграфов и букв (латиница -> кириллица по фонетическому соответствию)
TRANSLIT_PAIRS = [
    ('sh', 'ш'),
    ('ch', 'ч'),
    ('zh', 'ж'),
    ('kh', 'х'),
    ('ts', 'ц'),
    ('ya', 'я'),
    ('yu', 'ю'),
    ('ye', 'е'),
    ('yo', 'ё'),
    ('gh', 'ғ'),
    ('q', 'қ'),
    ('ei', 'ей'),
    ('ai', 'ай'),
    ('oi', 'ой'),
    ('ui', 'уй'),
    ('ay', 'ай'),
    ('oy', 'ой'),
    ('ey', 'ей'),
    ('iy', 'ий'),
    ('uy', 'уй'),
    ('w', 'в'),
    ('a', 'а'),
    ('b', 'б'),
    ('v', 'в'),
    ('g', 'г'),
    ('d', 'д'),
    ('e', 'е'),
    ('z', 'з'),
    ('i', 'и'),
    ('y', 'ы'),
    ('k', 'к'),
    ('l', 'л'),
    ('m', 'м'),
    ('n', 'н'),
    ('o', 'о'),
    ('p', 'п'),  # p -> п (kaspi -> каспи)
    ('r', 'р'),  # r -> р
    ('s', 'с'),
    ('t', 'т'),
    ('u', 'у'),
    ('f', 'ф'),
    ('h', 'х'),
    ('j', 'ж'),
    ('c', 'с'),
]


def transliterate_latin_to_cyrillic(text: str) -> str:
    """Транслитерирует слова, написанные латиницей, в кириллицу для выявления признаков."""
    # Сохраняем ссылки и домены без изменений
    urls = []
    def save_url(m):
        urls.append(m.group(0))
        return f"__URL_PLACEHOLDER_{len(urls)-1}__"

    text_no_urls = re.sub(r'https?://\S+|www\.\S+|\b\S+\.test\b', save_url, text)

    words = text_no_urls.split()
    converted_words = []
    
    for word in words:
        if word.startswith("__URL_PLACEHOLDER_"):
            converted_words.append(word)
            continue
            
        has_latin = bool(re.search(r'[a-zA-Z]', word))
        if has_latin:
            res = word.lower()
            for lat, cyr in TRANSLIT_PAIRS:
                res = res.replace(lat, cyr)
            converted_words.append(res)
        else:
            converted_words.append(word)
            
    result = " ".join(converted_words)
    
    # Возвращаем ссылки
    for i, url in enumerate(urls):
        result = result.replace(f"__URL_PLACEHOLDER_{i}__", url)
        
    return result