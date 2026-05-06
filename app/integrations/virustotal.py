"""VirusTotal API v3 — перевірка URL.

Обмеження free tier: 4 запити/хв
Протидія:
- Кеш результату в Redis: vt:url:{hash} TTL=24h
- Whitelist доменів з БД (не перевіряємо)
- Якщо API key не налаштовано — перевірка пропускається без помилки
"""

from __future__ import annotations

import base64
import hashlib
from enum import Enum
from typing import Optional

import aiohttp
from loguru import logger
from redis.asyncio import Redis

_VT_URL_ENDPOINT = "https://www.virustotal.com/api/v3/urls"
_VT_ANALYSIS_ENDPOINT = "https://www.virustotal.com/api/v3/urls/{}"
_CACHE_TTL = 86400  # 24 години
_TIMEOUT = aiohttp.ClientTimeout(total=10)


class VTVerdict(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"   # API key відсутній або whitelist


def _url_id(url: str) -> str:
    """VirusTotal URL id = base64url(url) без '='."""
    return base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()


def _cache_key(url: str) -> str:
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"vt:url:{h}"


async def check_url(
    url: str,
    api_key: str,
    redis: Redis,
) -> VTVerdict:
    """
    Перевіряє URL через VirusTotal.
    1. Перевіряє Redis-кеш (TTL=24h)
    2. Надсилає URL на аналіз
    3. Отримує вердикт з аналізу
    4. Кешує результат
    """
    if not api_key:
        return VTVerdict.SKIPPED

    cache_key = _cache_key(url)

    # Перевіряємо кеш
    cached = await redis.get(cache_key)
    if cached:
        logger.debug(f"[VT] Кеш: {url[:60]} → {cached}")
        return VTVerdict(cached)

    headers = {"x-apikey": api_key}

    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            # Крок 1: надсилаємо URL на сканування
            async with session.post(
                _VT_URL_ENDPOINT,
                headers=headers,
                data={"url": url},
            ) as resp:
                if resp.status not in (200, 201):
                    logger.warning(f"[VT] Помилка submit {resp.status}: {url[:60]}")
                    return VTVerdict.UNKNOWN

            # Крок 2: читаємо результат за url_id
            url_id = _url_id(url)
            async with session.get(
                _VT_ANALYSIS_ENDPOINT.format(url_id),
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    return VTVerdict.UNKNOWN
                data = await resp.json()

        verdict = _parse_verdict(data)
        await redis.setex(cache_key, _CACHE_TTL, verdict.value)
        logger.info(f"[VT] {url[:60]} → {verdict.value}")
        return verdict

    except aiohttp.ClientError as e:
        logger.warning(f"[VT] Мережа недоступна: {e}")
        return VTVerdict.UNKNOWN
    except Exception as e:
        logger.error(f"[VT] Неочікувана помилка: {e}")
        return VTVerdict.UNKNOWN


def _parse_verdict(data: dict) -> VTVerdict:
    try:
        stats = (
            data["data"]["attributes"]["last_analysis_stats"]
        )
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)

        if malicious >= 3:
            return VTVerdict.MALICIOUS
        if malicious >= 1 or suspicious >= 3:
            return VTVerdict.SUSPICIOUS
        return VTVerdict.CLEAN
    except (KeyError, TypeError):
        return VTVerdict.UNKNOWN
