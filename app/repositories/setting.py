from __future__ import annotations

import json
from typing import List

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting

_KEY_FORBIDDEN = "forbidden_words"
_KEY_URL_WHITELIST = "url_whitelist"
_KEY_ONBOARDING_RULES = "onboarding_rules"
_KEY_XLSX_PATH = "xlsx_path"
_KEY_XLSX_SHEET = "xlsx_sheet"
_KEY_XLSX_RANGE = "xlsx_cell_range"

_DEFAULT_WHITELIST = [
    "t.me", "telegram.org", "youtube.com", "youtu.be",
    "google.com", "wikipedia.org",
]

_DEFAULT_RULES = (
    "ℹ️ *Правила спільноти:*\n\n"
    "1\. Шанобливо спілкуємо з колегами\n"
    "2\. Не розповсюджуємо сторонні посилання\n"
    "3\. Не спамимо та не флудимо\n"
    "4\. Тематика виключно робоча"
)


class SettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _get(self, key: str) -> str | None:
        result = await self._s.execute(
            select(Setting.value).where(Setting.key == key)
        )
        return result.scalar_one_or_none()

    async def _set(self, key: str, value: str) -> None:
        stmt = (
            insert(Setting)
            .values(key=key, value=value)
            .on_conflict_do_update(
                index_elements=[Setting.key],
                set_={"value": value},
            )
        )
        await self._s.execute(stmt)
        await self._s.commit()

    async def get_forbidden_words(self) -> List[str]:
        raw = await self._get(_KEY_FORBIDDEN)
        if not raw:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    async def set_forbidden_words(self, words: List[str]) -> None:
        await self._set(_KEY_FORBIDDEN, json.dumps(words, ensure_ascii=False))

    async def get_url_whitelist(self) -> List[str]:
        raw = await self._get(_KEY_URL_WHITELIST)
        if not raw:
            return _DEFAULT_WHITELIST
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return _DEFAULT_WHITELIST

    async def get_onboarding_rules(self) -> str:
        raw = await self._get(_KEY_ONBOARDING_RULES)
        return raw if raw else _DEFAULT_RULES

    async def set_onboarding_rules(self, text: str) -> None:
        await self._set(_KEY_ONBOARDING_RULES, text)

    # ─── Excel налаштування ──────────────────────────────────────

    async def get_xlsx_config(self) -> dict:
        """Повертає налаштування Excel: path, sheet, cell_range."""
        return {
            "xlsx_path": await self._get(_KEY_XLSX_PATH),
            "xlsx_sheet": await self._get(_KEY_XLSX_SHEET),
            "xlsx_cell_range": await self._get(_KEY_XLSX_RANGE),
        }

    async def set_xlsx_path(self, path: str) -> None:
        await self._set(_KEY_XLSX_PATH, path)

    async def set_xlsx_sheet(self, sheet: str) -> None:
        await self._set(_KEY_XLSX_SHEET, sheet)

    async def set_xlsx_range(self, cell_range: str) -> None:
        await self._set(_KEY_XLSX_RANGE, cell_range)
