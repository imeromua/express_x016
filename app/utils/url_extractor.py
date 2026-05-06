"""Витягує URL з Telegram повідомлення через MessageEntity."""

from typing import List, Optional
from urllib.parse import urlparse

from aiogram.types import Message, MessageEntity


def extract_urls(message: Message) -> List[str]:
    """
    Повертає список URL з entities повідомлення.
    Пріоритет: text_link.url > entity типу 'url' > витягуємо з тексту.
    """
    entities: Optional[List[MessageEntity]] = message.entities or message.caption_entities
    if not entities:
        return []

    text = message.text or message.caption or ""
    urls: List[str] = []

    for entity in entities:
        if entity.type == "text_link" and entity.url:
            urls.append(entity.url)
        elif entity.type == "url":
            raw = text[entity.offset: entity.offset + entity.length]
            if not raw.startswith(("http://", "https://")):
                raw = "https://" + raw
            urls.append(raw)

    return list(dict.fromkeys(urls))  # дедублікація, зберігаємо порядок


def get_domain(url: str) -> str:
    """Повертає домен без www."""
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def is_whitelisted(url: str, whitelist: List[str]) -> bool:
    """True якщо домен або його суфікс є в whitelist."""
    domain = get_domain(url)
    for allowed in whitelist:
        if domain == allowed or domain.endswith("." + allowed):
            return True
    return False
