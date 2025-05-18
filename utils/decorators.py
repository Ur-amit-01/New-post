from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from functools import wraps

CHANNEL = "@FxLuv"

def must_join_channel(func):
    @wraps(func)
    async def decorator(client, message):
        try:
            user_member = await client.get_chat_member(CHANNEL, message.from_user.id)
            if user_member.status in ["left", "kicked"]:
                raise Exception()
        except Exception:
            return await message.reply_text(
                "To USe the Bot You must be a subscriber of our channel",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Join Channel", url="https://t.me/FxLuv")],
                ])
            )
        return await func(client, message)
    return decorator