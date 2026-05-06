from __future__ import annotations

import json
from typing import List

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting

_KEY_FORBIDDEN = "forbidden_words"
_KEY_URL_WHITELIST = "url_whitelist"

_DEFAULT_WHITELIST = [
    "t.me", "telegram.org", "youtube.com", "youtu.be",
    "google.com", "wikipedia.org",
]


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
