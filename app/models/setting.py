from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Setting(Base):
    """
    Конфігурація бота, що зберігається в БД.
    Приклади ключів:
      - forbidden_words  → JSON-список рядків
      - url_whitelist    → JSON-список доменів
      - onboarding_rules → Markdown-текст правил
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<Setting key={self.key!r}>"
