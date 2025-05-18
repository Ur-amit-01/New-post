from pyrogram import filters
from bot_instance import bot
from utils.decorators import must_join_channel
from commands.connect import waiting_users  # Import waiting_users

@bot.on_message(filters.command("start") & filters.private)
@must_join_channel
async def start_command(client, message):
    user_id = message.from_user.id
    
    # Clear waiting state if exists
    if user_id in waiting_users:
        del waiting_users[user_id]
    
    await message.reply_text(
        "👋 Hello! Welcome to the bot.\n"
        "Use /help to see available commands."
    )