from aiogram import Router

from app.handlers.group import triggers

# Імпортуємо з повної папки, щоб уникнути плутанину з початковим
# імпортом якщо там існують інші хендлери (напр. virustotal, forbidden_words)
try:
    from app.handlers.group import virustotal as vt_module
    _has_vt = True
except ImportError:
    _has_vt = False

router = Router(name="group")
router.include_router(triggers.router)
if _has_vt:
    router.include_router(vt_module.router)
