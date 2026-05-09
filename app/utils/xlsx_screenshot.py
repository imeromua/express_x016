"""Створення PNG з діапазону комірок Excel.

Піплайн:
  xlsx -> LibreOffice headless -> PDF -> pdf2image -> PIL crop -> PNG

Замість розрахунку по одиницях openpyxl (ненадійно) —
визначаємо межі таблиці автоматично по пікселях PNG
(пошук першого небілого пікселя з кожного боку).
"""

import asyncio
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

_config: dict = {"xlsx_path": None, "sheet": None, "cell_range": None}
_LO_BIN: str = shutil.which("libreoffice") or shutil.which("soffice") or "libreoffice"


def set_xlsx_config(
    xlsx_path: Optional[str],
    sheet: Optional[str] = None,
    cell_range: Optional[str] = None,
) -> None:
    _config["xlsx_path"] = xlsx_path
    _config["sheet"] = sheet
    _config["cell_range"] = cell_range
    logger.info(
        f"[xlsx_screenshot] config: path={xlsx_path}, "
        f"sheet={sheet}, range={cell_range}"
    )


async def make_schedule_screenshot() -> Optional[str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _render_sync)


# ─── Автоматичне визначення меж таблиці на PNG ────────────────────

def _auto_crop(img) -> Tuple[int, int, int, int]:
    """
    Автоматично знаходить межі небілого вмісту на зображенні.
    Повертає (left, top, right, bottom) або повні розміри якщо нічого не знайшло.
    """
    import numpy as np

    arr = np.array(img.convert("RGB"))
    # Маска: пікселі які не білі (R<240 або G<240 або B<240)
    mask = (arr[:, :, 0] < 240) | (arr[:, :, 1] < 240) | (arr[:, :, 2] < 240)

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if not rows.any():
        return (0, 0, img.width, img.height)

    top = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left = int(np.argmax(cols))
    right = int(len(cols) - np.argmax(cols[::-1]))

    # Додаємо невеликий відступ (щоб не зрізати межі)
    PAD = 8
    left = max(0, left - PAD)
    top = max(0, top - PAD)
    right = min(img.width, right + PAD)
    bottom = min(img.height, bottom + PAD)

    return (left, top, right, bottom)


# ─── Головна функція рендерингу ───────────────────────────────────────

def _render_sync() -> Optional[str]:
    """xlsx → PDF (LibreOffice) → PNG (pdf2image) → auto-crop по небілому вмісту."""
    from pdf2image import convert_from_path

    xlsx_path = _config.get("xlsx_path")
    sheet_name = _config.get("sheet")

    if not xlsx_path:
        logger.warning("[xlsx_screenshot] xlsx_path not configured")
        return None

    xlsx_file = Path(xlsx_path)
    if not xlsx_file.exists():
        logger.error(f"[xlsx_screenshot] file not found: {xlsx_file}")
        return None

    DPI = 200

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        tmp_xlsx = tmp_dir / xlsx_file.name
        shutil.copy2(xlsx_file, tmp_xlsx)

        # LibreOffice: xlsx → PDF
        lo_result = subprocess.run(
            [
                _LO_BIN, "--headless", "--norestore", "--nofirststartwizard",
                "--convert-to", "pdf",
                "--outdir", str(tmp_dir),
                str(tmp_xlsx),
            ],
            capture_output=True, text=True, timeout=60,
        )
        if lo_result.returncode != 0:
            logger.error(f"[xlsx_screenshot] LibreOffice error: {lo_result.stderr}")
            return None

        pdf_path = tmp_dir / (tmp_xlsx.stem + ".pdf")
        if not pdf_path.exists():
            logger.error(f"[xlsx_screenshot] PDF not found: {pdf_path}")
            return None

        # PDF → PIL Image (перша сторінка)
        try:
            pages = convert_from_path(str(pdf_path), dpi=DPI, first_page=1, last_page=1)
        except Exception as e:
            logger.error(f"[xlsx_screenshot] pdf2image error: {e}")
            return None

        if not pages:
            return None

        img = pages[0]
        logger.info(f"[xlsx_screenshot] full page: {img.width}x{img.height}px")

        # Auto-crop: відрізаємо білі поля навколо таблиці
        try:
            box = _auto_crop(img)
            left, top, right, bottom = box
            logger.info(f"[xlsx_screenshot] auto-crop box: {box}")
            if right > left and bottom > top:
                img = img.crop(box)
                logger.info(f"[xlsx_screenshot] cropped: {img.width}x{img.height}px")
        except ImportError:
            logger.warning("[xlsx_screenshot] numpy not available, skipping auto-crop")
        except Exception as e:
            logger.warning(f"[xlsx_screenshot] auto-crop failed: {e}, using full page")

        # Зберігаємо PNG
        out = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        out_path = Path(out.name)
        out.close()
        img.save(out_path, "PNG", optimize=True)
        logger.info(f"[xlsx_screenshot] saved -> {out_path}")
        return str(out_path)
