from datetime import date

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = (
        Index("ix_schedules_pib", "pib"),
        Index("ix_schedules_date", "work_date"),
        {"schema": None},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pib: Mapped[str] = mapped_column(String(200), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # робочий / вихідний
    day_name: Mapped[str] = mapped_column(String(20), nullable=False)
