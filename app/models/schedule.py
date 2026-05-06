from datetime import date

from sqlalchemy import Boolean, Date, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (
        Index("ix_schedules_pib", "pib"),
        Index("ix_schedules_date", "work_date"),
        UniqueConstraint("pib", "work_date", name="uq_schedule_pib_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pib: Mapped[str] = mapped_column(String(200), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    # is_working: True = робочий день, False = вихідний
    is_working: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    day_name: Mapped[str] = mapped_column(String(20), nullable=False)
