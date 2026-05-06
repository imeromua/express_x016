from datetime import date

from sqlalchemy import Date, String, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Schedule(Base):
    """
    Графік роботи співробітника на конкретну дату.
    UPSERT: ON CONFLICT (pib, work_date) DO UPDATE
    """

    __tablename__ = "schedules"

    __table_args__ = (
        UniqueConstraint("pib", "work_date", name="uq_schedule_pib_date"),
        Index("ix_schedule_pib", "pib"),
        Index("ix_schedule_work_date", "work_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pib: Mapped[str] = mapped_column(String(255), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 'робочий' або 'вихідний'
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    day_name: Mapped[str] = mapped_column(String(20), nullable=False)

    def __repr__(self) -> str:
        return f"<Schedule pib={self.pib!r} date={self.work_date} status={self.status!r}>"

    @property
    def is_working(self) -> bool:
        return self.status == "робочий"
