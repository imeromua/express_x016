"""XLSX-парсер графіків.

⚠️  ЗАГЛУШКА: структура колонок уточнюється після отримання
    реального файлу від замовника.

Очікувана структура (буде оновлено):
    Колонка A: ПІБ
    Колонка B: Дата (date або рядок DD.MM.YYYY)
    Колонка C: Статус ('робочий' / 'вихідний' або аналоги)
    Колонка D: День тижня (опціонально, можна обчислити)

Після отримання реального файлу:
    1. Уточнити назви/індекси колонок
    2. Уточнити формат дати
    3. Уточнити можливі значення статусу та їх нормалізацію
    4. Видалити цей TODO-блок
"""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import List

from loguru import logger

# Нормалізація статусів — розширити після отримання реального файлу
_STATUS_WORKING = frozenset(["робочий", "р", "work", "w", "1", "+"])
_STATUS_DAY_OFF = frozenset(["вихідний", "в", "off", "o", "0", "-"])

_DAY_NAMES_UK = [
    "Понеділок", "Вівторок", "Середа",
    "Четвер", "П'ятниця", "Субота", "Неділя",
]


class XlsxParseError(Exception):  # noqa: N818
    """Помилка парсингу файлу."""


class ParsedRow:
    """Один рядок графіка після парсингу."""
    __slots__ = ("pib", "work_date", "status", "day_name")

    def __init__(self, pib: str, work_date: date, status: str, day_name: str) -> None:
        self.pib = pib
        self.work_date = work_date
        self.status = status
        self.day_name = day_name

    def to_dict(self) -> dict:
        return {
            "pib": self.pib,
            "work_date": self.work_date,
            "status": self.status,
            "day_name": self.day_name,
        }


def parse_schedule_xlsx(file_bytes: bytes) -> List[dict]:
    """
    Парсить .xlsx-файл графіка та повертає список dict для UPSERT.

    ⚠️  STUB: колонки захардкоджені як A=ПІБ, B=Дата, C=Статус, D=День.
        Після отримання реального файлу — уточнити COL_* константи нижче.

    Raises:
        XlsxParseError: якщо файл некоректний або порожній.
    """
    try:
        import pandas as pd
    except ImportError:
        raise XlsxParseError("pandas не встановлено")

    # ── TODO: уточнити після отримання реального файлу ──────────────────
    COL_PIB = 0       # індекс або назва колонки ПІБ
    COL_DATE = 1      # індекс або назва колонки Дата
    COL_STATUS = 2    # індекс або назва колонки Статус
    COL_DAY = 3       # індекс або назва колонки День тижня (або None)
    HEADER_ROW = 0    # рядок заголовків (0 = перший рядок)
    # ────────────────────────────────────────────────────────────────────

    try:
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            header=HEADER_ROW,
            engine="openpyxl",
        )
    except Exception as e:
        raise XlsxParseError(f"Не вдалося відкрити файл: {e}") from e

    if df.empty:
        raise XlsxParseError("Файл не містить даних")

    rows: List[dict] = []
    errors: List[str] = []

    for idx, row in df.iterrows():
        try:
            pib = _parse_pib(row.iloc[COL_PIB])
            work_date = _parse_date(row.iloc[COL_DATE])
            status = _parse_status(row.iloc[COL_STATUS])

            # День тижня: беремо з файлу або обчислюємо
            if COL_DAY is not None and COL_DAY < len(row):
                day_name = str(row.iloc[COL_DAY]).strip() or _weekday_name(work_date)
            else:
                day_name = _weekday_name(work_date)

            rows.append(ParsedRow(pib, work_date, status, day_name).to_dict())

        except (ValueError, TypeError) as e:
            errors.append(f"Рядок {idx + 2}: {e}")
            continue

    if errors:
        logger.warning(f"[xlsx_parser] Пропущено {len(errors)} рядків: {errors[:5]}")

    if not rows:
        raise XlsxParseError("Жодного коректного рядка не знайдено")

    logger.info(f"[xlsx_parser] Розпізнано {len(rows)} записів, пропущено {len(errors)}")
    return rows


# ── Приватні хелпери ──────────────────────────────────────────────────────────

def _parse_pib(value) -> str:
    if not value or str(value).strip() in ("", "nan", "None"):
        raise ValueError("Порожнє ПІБ")
    return str(value).strip()


def _parse_date(value) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    # Рядкові формати — розширити за потреби
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Не вдалося розпізнати дату: {value!r}")


def _parse_status(value) -> str:
    raw = str(value).strip().lower()
    if raw in _STATUS_WORKING:
        return "робочий"
    if raw in _STATUS_DAY_OFF:
        return "вихідний"
    raise ValueError(f"Невідомий статус: {value!r}")


def _weekday_name(d: date) -> str:
    return _DAY_NAMES_UK[d.weekday()]
