"""Створення PNG з діапазону комірок Excel.

Піплайн:
  xlsx → openpyxl (вимикаємо header/footer) → tmp.xlsx
       → LibreOffice headless → PDF
       → pdf2image → PIL auto-crop (по небілому) → PNG
"""

import asyncio
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


# ─── Підготовка xlsx: вимикаємо колонтитули ─────────────────

def _strip_headers_footers(src: Path, dst: Path) -> None:
    """
    Копіює xlsx, вимикаючи всі header/footer на всіх аркушах.
    Також зменшуємо відступи сторінки до мінімальних.
    """
    import openpyxl
    from openpyxl.worksheet.header_footer import HeaderFooterItem

    wb = openpyxl.load_workbook(src)
    for ws in wb.worksheets:
        # Скидаємо header/footer
        ws.oddHeader.left.text = ""
        ws.oddHeader.center.text = ""
        ws.oddHeader.right.text = ""
        ws.oddFooter.left.text = ""
        ws.oddFooter.center.text = ""
        ws.oddFooter.right.text = ""
        ws.evenHeader.left.text = ""
        ws.evenHeader.center.text = ""
        ws.evenHeader.right.text = ""
        ws.evenFooter.left.text = ""
        ws.evenFooter.center.text = ""
        ws.evenFooter.right.text = ""
        ws.firstHeader.left.text = ""
        ws.firstHeader.center.text = ""
        ws.firstHeader.right.text = ""
        ws.firstFooter.left.text = ""
        ws.firstFooter.center.text = ""
        ws.firstFooter.right.text = ""

        # Мінімальні відступи сторінки (дюйми — боки таблиці не зрізало)
        ws.page_margins.left = 0.1
        ws.page_margins.right = 0.1
        ws.page_margins.top = 0.1
        ws.page_margins.bottom = 0.1
        ws.page_margins.header = 0.0
        ws.page_margins.footer = 0.0

    wb.save(dst)
    logger.info(f"[xlsx_screenshot] stripped headers/footers -> {dst}")


# ─── Auto-crop по пікселях ─────────────────────────────────────

def _auto_crop(img) -> Tuple[int, int, int, int]:
    """
    Знаходить межі небілого вмісту на зображенні.
    Повертає (left, top, right, bottom).
    """
    import numpy as np

    arr = np.array(img.convert("RGB"))
    mask = (arr[:, :, 0] < 240) | (arr[:, :, 1] < 240) | (arr[:, :, 2] < 240)

    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if not rows.any():
        return (0, 0, img.width, img.height)

    top = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left = int(np.argmax(cols))
    right = int(len(cols) - np.argmax(cols[::-1]))

    PAD = 8
    left = max(0, left - PAD)
    top = max(0, top - PAD)
    right = min(img.width, right + PAD)
    bottom = min(img.height, bottom + PAD)

    return (left, top, right, bottom)


# ─── Головна функція ─────────────────────────────────────────────────

def _render_sync() -> Optional[str]:
    """
    xlsx → strip headers → PDF (LibreOffice) → PNG (pdf2image) → auto-crop.
    """
    from pdf2image import convert_from_path

    xlsx_path = _config.get("xlsx_path")
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

        # 1. Копіюємо xlsx без колонтитулів
        tmp_xlsx = tmp_dir / xlsx_file.name
        try:
            _strip_headers_footers(xlsx_file, tmp_xlsx)
        except Exception as e:
            logger.warning(f"[xlsx_screenshot] strip failed ({e}), using original")
            shutil.copy2(xlsx_file, tmp_xlsx)

        # 2. LibreOffice: xlsx → PDF
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

        # 3. PDF → PIL Image
        try:
            pages = convert_from_path(str(pdf_path), dpi=DPI, first_page=1, last_page=1)
        except Exception as e:
            logger.error(f"[xlsx_screenshot] pdf2image error: {e}")
            return None

        if not pages:
            return None

        img = pages[0]
        logger.info(f"[xlsx_screenshot] full page: {img.width}x{img.height}px")

        # 4. Auto-crop по небілому
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

        # 5. Зберігаємо PNG
        out = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        out_path = Path(out.name)
        out.close()
        img.save(out_path, "PNG", optimize=True)
        logger.info(f"[xlsx_screenshot] saved -> {out_path}")
        return str(out_path)
