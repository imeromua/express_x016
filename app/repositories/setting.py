import json
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting
from app.repositories.base import BaseRepository


class SettingRepository(BaseRepository):

    async def get(self, key: str) -> Optional[str]:
        result = await self.session.execute(
            select(Setting.value).where(Setting.key == key)
        )
        return result.scalar_one_or_none()

    async def set(self, key: str, value: str) -> None:
        stmt = (
            insert(Setting)
            .values(key=key, value=value)
            .on_conflict_do_update(
                index_elements=["key"],
                set_={"value": value},
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_json(self, key: str, default: Any = None) -> Any:
        raw = await self.get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return default

    async def set_json(self, key: str, value: Any) -> None:
        await self.set(key, json.dumps(value, ensure_ascii=False))

    async def get_forbidden_words(self) -> List[str]:
        return await self.get_json("forbidden_words", default=[])

    async def set_forbidden_words(self, words: List[str]) -> None:
        await self.set_json("forbidden_words", words)

    async def get_url_whitelist(self) -> List[str]:
        return await self.get_json("url_whitelist", default=[])

    async def get_onboarding_rules(self) -> str:
        return await self.get("onboarding_rules") or _DEFAULT_RULES


_DEFAULT_RULES = """\
👋 *Ласкаво просимо до групи Epicentr-Express Samar\!*

Для вступу до спільноти необхідно:

✅ Ознайомитись з правилами
✅ Підтвердити згоду
✅ Поділитись контактом для верифікації

*Правила групи:*
1\. Поважайте колег
2\. Жодного спаму та реклами
3\. Лише робочі теми в чаті
4\. Заборонено ненормативну лексику
5\. Посилання — лише з дозволу адміністратора

_Після верифікації ви автоматично отримаєте доступ до групи\._
"""
