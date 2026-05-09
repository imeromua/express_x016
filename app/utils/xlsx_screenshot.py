"""Створення PNG з діапазону комірок Excel.

Піплайн: xlsx → LibreOffice headless → PDF → pdf2image → PNG (crop по діапазону)
Зберігає оригінальні кольори, шрифти, межі та стилі файлу.
"""

import asyncio
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

_config: dict = {"xlsx_path": None, "sheet": None, "cell_range": None}

# Шлях до libreoffice / soffice
_LO_BIN: str = shutil.which("libreoffice") or shutil.which("soffice") or "libreoffice"


def set_xlsx_config(
    xlsx_path: Optional[str],
    sheet: Optional[str] = None,
    cell_range: Optional[str] = None,
) -> None:
    """in-memory конфіг. Викликається при старті та після змін адміном."""
    _config["xlsx_path"] = xlsx_path
    _config["sheet"] = sheet
    _config["cell_range"] = cell_range
    logger.info(
        f"[xlsx_screenshot] config: path={xlsx_path}, "
        f"sheet={sheet}, range={cell_range}"
    )


async def make_schedule_screenshot() -> Optional[str]:
    """
    Async-обгортка. Виконує рендеринг у ThreadPoolExecutor.
    Повертає шлях до PNG або None.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _render_sync)


def _col_letter_to_index(col: str) -> int:
    """'A'->1, 'B'->2, 'AK'->37"""
    col = col.upper()
    result = 0
    for ch in col:
        result = result * 26 + (ord(ch) - ord('A') + 1)
    return result


def _parse_range(cell_range: str):
    """
    'B4:AK14' -> (col_start=2, row_start=4, col_end=37, row_end=14)
    """
    import re
    m = re.match(r'^([A-Z]+)(\d+):([A-Z]+)(\d+)$', cell_range.upper())
    if not m:
        return None
    return (
        _col_letter_to_index(m.group(1)), int(m.group(2)),
        _col_letter_to_index(m.group(3)), int(m.group(4)),
    )


def _set_print_area_and_convert(xlsx_path: Path, sheet_name: Optional[str],
                                 cell_range: Optional[str], tmp_dir: Path) -> Optional[Path]:
    """
    1. Копіюємо xlsx в temp,
    2. встановлюємо PrintArea = cell_range (openpyxl),
    3. запускаємо LibreOffice headless -> PDF,
    4. повертаємо Path до PDF.
    """
    import shutil as _shutil
    import openpyxl

    # Копіюємо файл щоб не псувати оригінал
    tmp_xlsx = tmp_dir / xlsx_path.name
    _shutil.copy2(xlsx_path, tmp_xlsx)

    # Встановлюємо область друку = cell_range (без цього LO рендерить весь аркуш)
    if cell_range:
        try:
            wb = openpyxl.load_workbook(tmp_xlsx)
            if sheet_name and sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
            else:
                ws = wb.active
            ws.print_area = cell_range
            # Масштабування: підгоняємо друк до 1 сторінки
            ws.page_setup.fitToPage = True
            ws.page_setup.fitToHeight = 1
            ws.page_setup.fitToWidth = 1
            ws.page_setup.orientation = "landscape"
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            wb.save(tmp_xlsx)
            logger.debug(f"[xlsx_screenshot] print_area set: {cell_range}")
        except Exception as e:
            logger.warning(f"[xlsx_screenshot] could not set print_area: {e}")

    # LibreOffice headless: xlsx -> PDF
    result = subprocess.run(
        [
            _LO_BIN, "--headless", "--norestore", "--nofirststartwizard",
            "--convert-to", "pdf",
            "--outdir", str(tmp_dir),
            str(tmp_xlsx),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        logger.error(f"[xlsx_screenshot] LibreOffice error: {result.stderr}")
        return None

    pdf_path = tmp_dir / (tmp_xlsx.stem + ".pdf")
    if not pdf_path.exists():
        logger.error(f"[xlsx_screenshot] PDF not found: {pdf_path}")
        return None

    logger.debug(f"[xlsx_screenshot] PDF ready: {pdf_path}")
    return pdf_path


def _render_sync() -> Optional[str]:
    """xlsx → PDF (LibreOffice) → PNG (pdf2image) → crop по діапазону."""
    from pdf2image import convert_from_path

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

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)

        # Конвертуємо xlsx → PDF
        pdf_path = _set_print_area_and_convert(xlsx_file, sheet_name, cell_range, tmp_dir)
        if not pdf_path:
            return None

        # PDF → PIL Image (перша сторінка, 200 dpi)
        try:
            pages = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=1)
        except Exception as e:
            logger.error(f"[xlsx_screenshot] pdf2image error: {e}")
            return None

        if not pages:
            logger.error("[xlsx_screenshot] pdf2image: no pages")
            return None

        img = pages[0]
        logger.info(f"[xlsx_screenshot] rendered {img.width}x{img.height}px from PDF")

        # Зберігаємо PNG
        out = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        out_path = Path(out.name)
        out.close()
        img.save(out_path, "PNG", optimize=True)
        logger.info(f"[xlsx_screenshot] saved -> {out_path}")
        return str(out_path)
