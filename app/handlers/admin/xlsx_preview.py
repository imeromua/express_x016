"""Передпогляд скріншоту графіка для адміна."""

import os
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, FSInputFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin import kb_back_to_xlsx
from app.utils.xlsx_screenshot import make_schedule_screenshot, _config
from app.utils.text import esc

router = Router(name="admin:xlsx_preview")
router.callback_query.filter(IsAdminFilter())


@router.callback_query(F.data == "xlsx:preview")
async def cb_xlsx_preview(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer()

    # Перевіряємо наявність конфігу
    xlsx_path = _config.get("xlsx_path")
    cell_range = _config.get("cell_range") or "весь аркуш"
    sheet = _config.get("sheet") or "перший"

    if not xlsx_path or not Path(xlsx_path).exists():
        await callback.message.answer(
            "❌ Файл не знайдено\. Спочатку завантажте *\.xlsx* файл\.",
            reply_markup=kb_back_to_xlsx(),
            parse_mode="MarkdownV2",
        )
        return

    status = await callback.message.answer(
        f"⏳ Роблю скріншот\.\.\. діапазон `{esc(cell_range)}`, аркуш `{esc(sheet)}`",
        parse_mode="MarkdownV2",
    )

    try:
        png_path = await make_schedule_screenshot()
    except Exception as e:
        logger.error(f"[xlsx_preview] render error: {e}")
        await status.edit_text(
            f"❌ Помилка рендерингу: `{esc(str(e))}`",
            reply_markup=kb_back_to_xlsx(),
            parse_mode="MarkdownV2",
        )
        return

    if not png_path:
        await status.edit_text(
            "❌ Не вдалося створити скріншот\. Перевірте налаштування\.",
            reply_markup=kb_back_to_xlsx(),
            parse_mode="MarkdownV2",
        )
        return

    try:
        await status.delete()
        await bot.send_photo(
            chat_id=callback.from_user.id,
            photo=FSInputFile(png_path),
            caption=(
                f"📸 *Передпогляд графіка*\n"
                f"📄 `{esc(Path(xlsx_path).name)}`\n"
                f"📌 Діапазон: `{esc(cell_range)}`\n"
                f"📄 Аркуш: `{esc(sheet)}`"
            ),
            reply_markup=kb_back_to_xlsx(),
            parse_mode="MarkdownV2",
        )
        logger.info(f"[xlsx_preview] sent to admin {callback.from_user.id}")
    except Exception as e:
        logger.error(f"[xlsx_preview] send error: {e}")
        await callback.message.answer(
            f"❌ Помилка відправки: `{esc(str(e))}`",
            reply_markup=kb_back_to_xlsx(),
            parse_mode="MarkdownV2",
        )
    finally:
        # Видаляємо тимчасовий PNG
        try:
            os.unlink(png_path)
        except Exception:
            pass
