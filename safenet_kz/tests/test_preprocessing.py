"""
Тесты для модуля препроцессинга SafeNet KZ.
Проверяют деобфускацию, определение языков, транслитерацию и маскирование ПДн.
"""

from src.preprocessing import (
    clean_obfuscation,
    transliterate_latin_to_cyrillic,
    detect_language,
    extract_entities,
    mask_personal_data,
    preprocess_text,
)


def test_clean_obfuscation():
    # Замена символов на кириллицу
    raw = "Заходи в к@зино и крути сл0ты! Получи бuлет на р0зыгрыш"
    cleaned = clean_obfuscation(raw)
    assert "казино" in cleaned.lower()
    assert "слоты" in cleaned.lower()
    assert "билет" in cleaned.lower()
    assert "розыгрыш" in cleaned.lower()

    # Схлопывание пробелов
    spaced = "Вход в к а з и н о закрыт, но п и р а м и д а работает!"
    cleaned_spaced = clean_obfuscation(spaced)
    assert "казино" in cleaned_spaced
    assert "пирамида" in cleaned_spaced


def test_transliteration():
    translit_text = "akshany kobeitu kaspi arkyly bilet bagasy 1000 tg"
    cyr = transliterate_latin_to_cyrillic(translit_text)
    assert "акшаны" in cyr
    assert "кобейту" in cyr
    assert "каспи" in cyr
    assert "билет" in cyr


def test_language_detection():
    kazakh_text = "Бар болғаны 100 билет. Жеребе тікелей эфирде өтеді."
    langs_kz = detect_language(kazakh_text)
    assert "kk" in langs_kz

    russian_text = "Бесплатный конкурс в прямом эфире! Участие без взносов."
    langs_ru = detect_language(russian_text)
    assert "ru" in langs_ru

    mixed_text = "IPHONE 16 розыгрышына қатыс! Билет бағасы всего 1000 тенге."
    langs_mixed = detect_language(mixed_text)
    assert "mixed" in langs_mixed or ("kk" in langs_mixed and "ru" in langs_mixed)

    translit_text = "akshany kobeitu kaspi arkyly bilet utys"
    langs_translit = detect_language(translit_text)
    assert "translit" in langs_translit


def test_entity_extraction_and_masking():
    raw_text = (
        "Переводите 15 000 тг на карту 4400 4301 9876 5432 или Kaspi по номеру "
        "+7 701 999 88 12. Промокод: SAFEKZ, ссылка: https://lucky-slot777.test/bonus"
    )
    
    # Проверка извлечения
    entities = extract_entities(raw_text)
    assert "5432" in entities["card_tails"]
    assert "lucky-slot777.test" in entities["domains"]
    assert "SAFEKZ" in entities["promocodes"]
    assert 15000 in entities["amounts"]
    
    # Проверка маскирования ПДн
    masked = mask_personal_data(raw_text)
    assert "4400 4301 9876 5432" not in masked
    assert "5432" in masked
    assert "**** **** **** 5432" in masked
    assert "+7 701 999 88 12" not in masked
    assert "+7 *** ***-**-12" in masked


def test_preprocess_pipeline():
    text = "🔥 Срочно! к@зино дарит 5000 тг. Рега: https://win-kazakhstan.test Промо: WIN500 карта 5169 4931 1111 2222"
    result = preprocess_text(text)
    assert "[СРОЧНОСТЬ]" in result.cleaned_text
    assert "казино" in result.cleaned_text
    assert "**** **** **** 2222" in result.masked_text
    assert "win-kazakhstan.test" in result.entities["domains"]