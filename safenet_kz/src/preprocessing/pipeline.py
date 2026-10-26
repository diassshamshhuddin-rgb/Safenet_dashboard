"""
Единый пайплайн препроцессинга SafeNet KZ.
Выполняет деобфускацию, определение языков, транслитерацию, извлечение сущностей и маскирование ПДн.
"""

from typing import Dict, Any, List
from .normalizer import clean_obfuscation
from .transliteration import transliterate_latin_to_cyrillic
from .language import detect_language
from .extractor import extract_entities, mask_personal_data


class PreprocessingResult:
    def __init__(
        self,
        raw_text: str,
        cleaned_text: str,
        transliterated_text: str,
        masked_text: str,
        languages: List[str],
        entities: Dict[str, Any]
    ):
        self.raw_text = raw_text
        self.cleaned_text = cleaned_text
        self.transliterated_text = transliterated_text
        self.masked_text = masked_text
        self.languages = languages
        self.entities = entities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cleaned_text": self.cleaned_text,
            "transliterated_text": self.transliterated_text,
            "masked_text": self.masked_text,
            "languages": self.languages,
            "entities": self.entities,
        }


def preprocess_text(text: str) -> PreprocessingResult:
    """Полная цепочка предобработки входящего текстового сообщения."""
    # 1. Деобфускация и нормализация Unicode / эмодзи
    cleaned = clean_obfuscation(text)
    
    # 2. Определение языка
    langs = detect_language(cleaned)
    
    # 3. Транслитерация для выявления замаскированных признаков
    transliterated = transliterate_latin_to_cyrillic(cleaned)
    
    # 4. Извлечение сущностей (по исходному и очищенному)
    entities = extract_entities(text)
    
    # 5. Маскирование ПДн (для безопасного отображения аналитику и логирования)
    masked = mask_personal_data(cleaned)
    
    return PreprocessingResult(
        raw_text=text,
        cleaned_text=cleaned,
        transliterated_text=transliterated,
        masked_text=masked,
        languages=langs,
        entities=entities
    )