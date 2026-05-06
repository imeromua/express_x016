from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatType

router = Router(name="user")
# Працює лише в приватних повідомленнях
# — фільтр підключимо в bot.py через F.chat.type
