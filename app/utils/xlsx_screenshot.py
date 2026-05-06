"""Створення PNG з діапазону комірок Excel.

Konfig зберігається в БД і завантажується в пам'ять при старті бота.
Адмін може оновити налаштування без перезапуску через адмін-панель.
"""

import asyncio
from pathlib import Path
from typing import Optional

from loguru import logger

_config: dict = {"xlsx_path": None, "sheet": None, "cell_range": None}


def set_xlsx_config(
    xlsx_path: Optional[str],
    sheet: Optional[str] = None,
    cell_range: Optional[str] = None,
) -> None:
    """Оновлює in-memory конфіг. Викликається при старті і після змін адміном."""
    _config["xlsx_path"] = xlsx_path
    _config["sheet"] = sheet
    _config["cell_range"] = cell_range
    logger.info(
        f"[xlsx_screenshot] config: path={xlsx_path}, "
        f"sheet={sheet}, range={cell_range}"
    )


async def make_schedule_screenshot() -> Optional[str]:
    """
    Async-обгортка над синхронним рендерингом.
    Виконує рендеринг у ThreadPoolExecutor щоб не блокувати event loop.
    Повертає шлях до PNG або None.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _render_sync)


def _render_sync() -> Optional[str]:
    """Синхронний рендеринг таблиці Excel → PNG."""
    xlsx_path = _config.get("xlsx_path")
    sheet_name = _config.get("sheet")
    cell_range = _config.get("cell_range")

    if not xlsx_path:
        logger.warning("[xlsx_screenshot] xlsx_path not configured")
        return None

    xlsx_file = Path(xlsx_path)
    if not xlsx_file.exists():
        logger.error(f"[xlsx_screenshot] file not found: {xlsx_file}")
        return None

    try:
        import openpyxl
        from PIL import Image, ImageDraw, ImageFont

        wb = openpyxl.load_workbook(xlsx_file, data_only=True)
        if sheet_name and sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        if cell_range:
            try:
                raw_cells = list(ws[cell_range])
            except Exception:
                raw_cells = list(ws.iter_rows())
        else:
            raw_cells = list(ws.iter_rows())

        if not raw_cells:
            logger.warning("[xlsx_screenshot] empty cell range")
            return None

        data = [[str(c.value if c.value is not None else "") for c in row]
                for row in raw_cells]

        # автоширина колонки за найдовшим значенням
        try:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            font = ImageFont.truetype(font_path, 13)
            font_bold = ImageFont.truetype(font_bold_path, 13)
        except Exception:
            font = ImageFont.load_default()
            font_bold = font

        # вимірюємо ширини колонок
        tmp_img = Image.new("RGB", (1, 1))
        tmp_draw = ImageDraw.Draw(tmp_img)
        col_widths = []
        num_cols = max(len(r) for r in data) if data else 1
        for ci in range(num_cols):
            max_w = 60
            for row in data:
                if ci < len(row):
                    val = row[ci][:30]
                    try:
                        bbox = tmp_draw.textbbox((0, 0), val, font=font)
                        w = bbox[2] - bbox[0] + 16
                    except Exception:
                        w = len(val) * 8 + 16
                    max_w = max(max_w, w)
            col_widths.append(min(max_w, 200))

        CELL_H = 28
        PAD = 8
        img_w = sum(col_widths) + PAD * 2
        img_h = len(data) * CELL_H + PAD * 2

        img = Image.new("RGB", (img_w, img_h), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        for ri, row in enumerate(data):
            y = PAD + ri * CELL_H
            x = PAD
            for ci, val in enumerate(row):
                w = col_widths[ci] if ci < len(col_widths) else 80
                fill = (220, 230, 255) if ri == 0 else (
                    (245, 245, 245) if ri % 2 == 0 else (255, 255, 255)
                )
                draw.rectangle(
                    [x, y, x + w - 1, y + CELL_H - 1],
                    fill=fill,
                    outline=(180, 180, 200),
                )
                f = font_bold if ri == 0 else font
                draw.text(
                    (x + 4, y + 6),
                    val[:28],
                    fill=(20, 20, 60),
                    font=f,
                )
                x += w

        out_path = Path("/tmp/schedule_preview.png")
        img.save(out_path, "PNG", optimize=True)
        logger.info(f"[xlsx_screenshot] rendered {img_w}x{img_h} px -> {out_path}")
        return str(out_path)

    except ImportError as e:
        logger.error(f"[xlsx_screenshot] missing library: {e}")
        return None
    except Exception as e:
        logger.error(f"[xlsx_screenshot] render error: {e}")
        return None
