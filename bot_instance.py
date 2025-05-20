from pyrogram import Client
from config import *

bot = Client(
    "telegram_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)
