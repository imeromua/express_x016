"""Створення зображення з діапазону комірок Excel.

Налаштування зберігається в БД через SettingRepository:
  xlsx_path       — шлях до .xlsx файлу
  xlsx_sheet      — назва аркуша (дефаулт: перший)
  xlsx_cell_range — діапазон, напр. "A1:Z50"
Якщо налаштування не задані — повертає None.
"""

import io
from pathlib import Path
from typing import Optional

from loguru import logger

# Глобальний кеш шляху до поточного Excel-файлу
_current_xlsx_path: Optional[str] = None
_current_sheet: Optional[str] = None
_current_range: Optional[str] = None


def set_xlsx_config(
    xlsx_path: str,
    sheet: Optional[str] = None,
    cell_range: Optional[str] = None,
) -> None:
    """Оновлює глобальний конфіг (admin панель викликає після імпорту)."""
    global _current_xlsx_path, _current_sheet, _current_range
    _current_xlsx_path = xlsx_path
    _current_sheet = sheet
    _current_range = cell_range
    logger.info(f"[xlsx_screenshot] config updated: path={xlsx_path}, sheet={sheet}, range={cell_range}")


async def make_schedule_screenshot() -> Optional[str]:
    """
    Створює PNG-зображення з заданого діапазону комірок Excel-файлу.
    Повертає шлях до PNG або None.
    
    Вимоги: openpyxl, Pillow
    """
    if not _current_xlsx_path:
        logger.warning("[xlsx_screenshot] xlsx_path not configured")
        return None

    xlsx_file = Path(_current_xlsx_path)
    if not xlsx_file.exists():
        logger.error(f"[xlsx_screenshot] file not found: {xlsx_file}")
        return None

    try:
        import openpyxl
        from openpyxl.utils import column_index_from_string
        from PIL import Image, ImageDraw, ImageFont

        wb = openpyxl.load_workbook(xlsx_file, data_only=True)
        ws = wb[_current_sheet] if _current_sheet and _current_sheet in wb.sheetnames else wb.active

        # Визначаємо діапазон комірок
        if _current_range:
            try:
                cells = list(ws[_current_range])
            except Exception:
                cells = list(ws.iter_rows())
        else:
            cells = list(ws.iter_rows())

        if not cells:
            return None

        # Збираємо дані з комірок
        data = []
        for row in cells:
            data.append([str(cell.value or "") for cell in row])

        # Параметри рендерингу
        CELL_W, CELL_H = 120, 30
        PAD = 10
        cols = max(len(r) for r in data) if data else 1
        rows_count = len(data)
        img_w = cols * CELL_W + PAD * 2
        img_h = rows_count * CELL_H + PAD * 2

        img = Image.new("RGB", (img_w, img_h), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Спробуємо завантажити шрифт
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
            font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
        except Exception:
            font = ImageFont.load_default()
            font_bold = font

        # Малюємо таблицю
        for ri, row in enumerate(data):
            y = PAD + ri * CELL_H
            for ci, val in enumerate(row):
                x = PAD + ci * CELL_W
                fill = (240, 240, 255) if ri == 0 else (255, 255, 255)
                draw.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1],
                               fill=fill, outline=(180, 180, 180))
                f = font_bold if ri == 0 else font
                draw.text((x + 4, y + 6), val[:18], fill=(30, 30, 30), font=f)

        out_path = Path("/tmp/schedule_preview.png")
        img.save(out_path, "PNG")
        return str(out_path)

    except ImportError as e:
        logger.error(f"[xlsx_screenshot] missing library: {e}")
        return None
    except Exception as e:
        logger.error(f"[xlsx_screenshot] render error: {e}")
        return None
