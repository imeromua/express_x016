from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """Зареєстрований співробітник."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    pib: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(10), default="staff", server_default="staff")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    joined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<User id={self.user_id} pib={self.pib!r} role={self.role!r}>"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
