from datetime import date
from typing import List

from app.models.schedule import Schedule
from app.utils.text import esc

_MONTHS = [
    "січня", "лютого", "березня", "квітня", "травня", "червня",
    "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
]


def _fmt_date(d: date) -> str:
    """Формат: '8 травня'."""
    return f"{d.day} {_MONTHS[d.month - 1]}"


def format_schedule(records: List[Schedule], pib: str) -> str:
    """
    Форматує список записів графіка у MarkdownV2.

    Логіка:
    - Робочі дні: 'Дата (День) — робочий 🟢'
    - Послідовні вихідні групуються:
      '8 та 9 травня (Субота, Неділя) — вихідний 🔴'
    """
    if not records:
        return (
            f"📭 Графік для *{esc(pib)}* не знайдено\.\n"
            "Перевірте правильність прізвища або зверніться до адміністратора\."
        )

    lines: List[str] = [f"📅 *Графік: {esc(pib)}*\n"]

    i = 0
    while i < len(records):
        rec = records[i]

        if rec.is_working:
            lines.append(
                f"🟢 *{esc(_fmt_date(rec.work_date))}* "
                f"\\({esc(rec.day_name)}\\) — робочий"
            )
            i += 1
        else:
            # Збираємо групу послідовних вихідних
            group = [rec]
            j = i + 1
            while j < len(records) and not records[j].is_working:
                group.append(records[j])
                j += 1

            if len(group) == 1:
                lines.append(
                    f"🔴 *{esc(_fmt_date(rec.work_date))}* "
                    f"\\({esc(rec.day_name)}\\) — вихідний"
                )
            else:
                dates_str = esc(" та ".join(_fmt_date(r.work_date) for r in group))
                days_str = esc(", ".join(r.day_name for r in group))
                lines.append(
                    f"🔴 *{dates_str}* \\({days_str}\\) — вихідний"
                )
            i = j

    return "\n".join(lines)
