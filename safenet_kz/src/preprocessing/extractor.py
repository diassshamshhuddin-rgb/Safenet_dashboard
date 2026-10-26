"""
Модуль извлечения сущностей и маскирования персональных данных (ПДн).
Строго соблюдает требования Закона РК «О персональных данных и их защите».
Не сохраняет реальные номера телефонов и банковских карт.
"""

import re
from typing import Dict, List, Any


# Регулярные выражения для поиска реквизитов
REGEX_CARD = re.compile(r'\b(?:\d{4}[ -]?){3}(\d{4})\b')
REGEX_PHONE = re.compile(r'(?:\+?7|8)\s*\(?(\d{3})\)?[\s-]*\d{3}[\s-]*\d{2}[\s-]*(\d{2})')
REGEX_URL = re.compile(r'https?://[^\s/$.?#].[^\s]*|\b[a-zA-Z0-9-]+\.(?:test|kz|com|net|org|xyz|online|site|me|io)\b[^\s]*', re.IGNORECASE)
REGEX_PROMO = re.compile(r'\b(?:промокод|код|бонус|кодқа|промо)[\s:=]+([A-Z0-9_]{4,15})\b', re.IGNORECASE)
REGEX_SUMS = re.compile(r'(\d+[\s\d]*)\s*(?:тг|теңге|тенге|kzt|т\b)', re.IGNORECASE)


def mask_phone_match(match: re.Match) -> str:
    """Маскирует телефон: оставляет префикс +7 и последние 2 цифры (+7 *** ***-**-12)."""
    last_two = match.group(2)
    return f"+7 *** ***-**-{last_two}"


def mask_card_match(match: re.Match) -> str:
    """Маскирует карту: оставляет только последние 4 цифры (**** **** **** 1234)."""
    last_four = match.group(1)
    return f"**** **** **** {last_four}"


def mask_personal_data(text: str) -> str:
    """Заменяет все телефоны и номера карт на безопасные маски."""
    masked = REGEX_PHONE.sub(mask_phone_match, text)
    masked = REGEX_CARD.sub(mask_card_match, masked)
    return masked


def extract_entities(text: str) -> Dict[str, Any]:
    """
    Извлекает сущности из текста:
    - телефоны (маскированные)
    - карты (маскированные и хэш/хвост для графа)
    - ссылки и домены
    - промокоды
    - суммы
    """
    phones = []
    for m in REGEX_PHONE.finditer(text):
        phones.append(mask_phone_match(m))
        
    cards = []
    card_tails = []
    for m in REGEX_CARD.finditer(text):
        cards.append(mask_card_match(m))
        card_tails.append(m.group(1))
        
    urls = REGEX_URL.findall(text)
    domains = []
    for u in urls:
        # Извлекаем чистый домен
        domain_match = re.search(r'://([^/:]+)|([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', u)
        if domain_match:
            d = domain_match.group(1) or domain_match.group(2)
            domains.append(d.lower())
            
    promos = REGEX_PROMO.findall(text)
    
    sums = []
    for s in REGEX_SUMS.findall(text):
        clean_s = re.sub(r'\s+', '', s)
        try:
            sums.append(int(clean_s))
        except ValueError:
            pass
            
    return {
        "phones": list(set(phones)),
        "cards": list(set(cards)),
        "card_tails": list(set(card_tails)),
        "urls": list(set(urls)),
        "domains": list(set(domains)),
        "promocodes": list(set(promos)),
        "amounts": sums,
    }