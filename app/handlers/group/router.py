from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatType

router = Router(name="group")
# Хендлер працює лише в групах
# — фільтр підключимо в bot.py через middleware
