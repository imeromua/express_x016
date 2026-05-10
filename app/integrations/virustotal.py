"""VirusTotal API v3 — перевірка URL і файлів.

Обмеження free tier: 4 запити/хв
Protection:
- Redis кеш за SHA256 хешем (URL/файл): TTL=24h
- Whitelist доменів з БД (не перевіряємо)
- Якщо API key не налаштовано — пропуск без помилки
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
from enum import Enum
from typing import Optional

import aiohttp
from loguru import logger
from redis.asyncio import Redis

_VT_BASE = "https://www.virustotal.com/api/v3"
_CACHE_TTL = 86400   # 24 годи
_TIMEOUT = aiohttp.ClientTimeout(total=30)
_POLL_INTERVAL = 5   # секунд між поллінгом аналізу
_POLL_ATTEMPTS = 6   # макс 30 секунд на файл


class VTVerdict(str, Enum):
    CLEAN      = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS  = "malicious"
    UNKNOWN    = "unknown"
    SKIPPED    = "skipped"   # API key відсутній або whitelist


# ─── URL ────────────────────────────────────────────────────────

def _url_id(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()


def _cache_key_url(url: str) -> str:
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"vt:url:{h}"


def _cache_key_file(sha256: str) -> str:
    return f"vt:file:{sha256[:16]}"


async def check_url(
    url: str,
    api_key: str,
    redis: Redis,
) -> VTVerdict:
    if not api_key:
        return VTVerdict.SKIPPED

    cache_key = _cache_key_url(url)
    cached = await redis.get(cache_key)
    if cached:
        logger.debug(f"[VT-URL] Кеш: {url[:60]} → {cached}")
        return VTVerdict(cached)

    headers = {"x-apikey": api_key}
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.post(
                f"{_VT_BASE}/urls",
                headers=headers,
                data={"url": url},
            ) as resp:
                if resp.status not in (200, 201):
                    logger.warning(f"[VT-URL] submit error {resp.status}: {url[:60]}")
                    return VTVerdict.UNKNOWN

            async with session.get(
                f"{_VT_BASE}/urls/{_url_id(url)}",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    return VTVerdict.UNKNOWN
                data = await resp.json()

        verdict = _parse_stats(data)
        await redis.setex(cache_key, _CACHE_TTL, verdict.value)
        logger.info(f"[VT-URL] {url[:60]} → {verdict.value}")
        return verdict

    except aiohttp.ClientError as e:
        logger.warning(f"[VT-URL] Мережа: {e}")
        return VTVerdict.UNKNOWN
    except Exception as e:
        logger.error(f"[VT-URL] Помилка: {e}")
        return VTVerdict.UNKNOWN


# ─── Файли ────────────────────────────────────────────────────────

async def check_file(
    file_bytes: bytes,
    api_key: str,
    redis: Redis,
    filename: str = "file",
) -> VTVerdict:
    """
    Перевіряє файл через VT:
    1. SHA256 → перевіряємо кеш в Redis
    2. Запит GET /files/{sha256} — чи вже відомий VT
    3. Якщо невідомий — завантажуємо файл (POST /files)
    4. Поллінг аналізу (GET /analyses/{id})
    5. Кешуємо і повертаємо вердикт
    """
    if not api_key:
        return VTVerdict.SKIPPED

    sha256 = hashlib.sha256(file_bytes).hexdigest()
    cache_key = _cache_key_file(sha256)

    cached = await redis.get(cache_key)
    if cached:
        logger.debug(f"[VT-FILE] Кеш: {filename} ({sha256[:8]}) → {cached}")
        return VTVerdict(cached)

    headers = {"x-apikey": api_key}
    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            # 1. Перевіряємо чи VT вже знає цей хеш
            async with session.get(
                f"{_VT_BASE}/files/{sha256}",
                headers=headers,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    verdict = _parse_stats(data)
                    await redis.setex(cache_key, _CACHE_TTL, verdict.value)
                    logger.info(f"[VT-FILE] known {filename} → {verdict.value}")
                    return verdict

            # 2. Невідомий — завантажуємо
            form = aiohttp.FormData()
            form.add_field("file", file_bytes, filename=filename)
            async with session.post(
                f"{_VT_BASE}/files",
                headers=headers,
                data=form,
            ) as resp:
                if resp.status not in (200, 201):
                    logger.warning(f"[VT-FILE] upload error {resp.status}")
                    return VTVerdict.UNKNOWN
                upload_data = await resp.json()

            analysis_id = upload_data["data"]["id"]

            # 3. Поллінг аналізу
            for attempt in range(_POLL_ATTEMPTS):
                await asyncio.sleep(_POLL_INTERVAL)
                async with session.get(
                    f"{_VT_BASE}/analyses/{analysis_id}",
                    headers=headers,
                ) as resp:
                    if resp.status != 200:
                        continue
                    analysis = await resp.json()
                    status = (
                        analysis.get("data", {})
                        .get("attributes", {})
                        .get("status", "")
                    )
                    if status == "completed":
                        verdict = _parse_stats(analysis)
                        await redis.setex(cache_key, _CACHE_TTL, verdict.value)
                        logger.info(f"[VT-FILE] {filename} → {verdict.value} (attempt {attempt+1})")
                        return verdict

            logger.warning(f"[VT-FILE] Таймаут аналізу: {filename}")
            return VTVerdict.UNKNOWN

    except aiohttp.ClientError as e:
        logger.warning(f"[VT-FILE] Мережа: {e}")
        return VTVerdict.UNKNOWN
    except Exception as e:
        logger.error(f"[VT-FILE] Помилка: {e}")
        return VTVerdict.UNKNOWN


# ─── Парсинг ───────────────────────────────────────────────────────

def _parse_stats(data: dict) -> VTVerdict:
    try:
        attrs = data["data"]["attributes"]
        stats = attrs.get("last_analysis_stats") or attrs.get("stats", {})
        malicious  = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        if malicious >= 3:
            return VTVerdict.MALICIOUS
        if malicious >= 1 or suspicious >= 3:
            return VTVerdict.SUSPICIOUS
        return VTVerdict.CLEAN
    except (KeyError, TypeError):
        return VTVerdict.UNKNOWN
