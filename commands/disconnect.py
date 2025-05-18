from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot_instance import bot
from utils.decorators import must_join_channel
from database.mongodb import channels
import math
import logging

# Change logging level to INFO and remove debug statements
logger = logging.getLogger(__name__)

PAGE_SIZE = 5

def build_channels_keyboard(user_channels, page, total_pages):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    buttons = []
    for ch in user_channels[start:end]:
        title = ch.get("channel_title", "Unknown")
        cid = str(ch["channel_id"])
        btn_text = f"{title}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"confirm_disconnect:{cid}:{page}")])
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
    if end < len(user_channels):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    return InlineKeyboardMarkup(buttons)

def build_confirmation_keyboard(channel_id, page):
    buttons = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"disconnect:{channel_id}:{page}"),
            InlineKeyboardButton("❌ No", callback_data=f"cancel_disconnect:{page}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

@bot.on_callback_query(filters.regex(r"^confirm_disconnect:(\-?\d+):(\d+)$"))
async def confirm_disconnect_callback(client, callback_query: CallbackQuery):
    try:
        channel_id, page = callback_query.data.split(":")[1:]
        channel = await channels.find_one({"channel_id": int(channel_id)})
        channel_title = channel.get("channel_title", "Unknown")
        
        await callback_query.edit_message_text(
            f"Are you sure you want to disconnect {channel_title}?",
            reply_markup=build_confirmation_keyboard(channel_id, page)
        )
    except Exception as e:
        logger.error(f"Confirmation error: {str(e)}")
        await callback_query.answer("An error occurred. Please try again.")

@bot.on_callback_query(filters.regex(r"^cancel_disconnect:(\d+)$"))
async def cancel_disconnect_callback(client, callback_query: CallbackQuery):
    try:
        page = int(callback_query.data.split(":")[1])
        user_channels = [ch async for ch in channels.find({"user_id": callback_query.from_user.id})]
        total_pages = math.ceil(len(user_channels) / PAGE_SIZE)
        
        await callback_query.edit_message_text(
            "Select a channel to disconnect:",
            reply_markup=build_channels_keyboard(user_channels, page, total_pages)
        )
    except Exception as e:
        logger.error(f"Cancel error: {str(e)}")
        await callback_query.answer("An error occurred. Please try again.")

@bot.on_message(filters.command(["disconnect"]) & filters.private)
@must_join_channel
async def disconnect_command(client, message: Message):
    user_id = message.from_user.id
    try:
        # Test MongoDB connection
        await channels.find_one({})
        
        # Get user channels
        user_channels = []
        async for ch in channels.find({"user_id": user_id}):
            user_channels.append(ch)
        
        if not user_channels:
            return await message.reply_text("❌ You haven't connected any channels yet.")
        
        # Build and send keyboard
        total_pages = math.ceil(len(user_channels) / PAGE_SIZE)
        keyboard = build_channels_keyboard(user_channels, 0, total_pages)
        
        await message.reply_text(
            "Select a channel to disconnect:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in disconnect command: {str(e)}")
        await message.reply_text("An error occurred. Please try again later.")

@bot.on_callback_query(filters.regex(r"^disconnect:(\-?\d+):(\d+)$"))
async def disconnect_channel_callback(client, callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        channel_id, page = callback_query.data.split(":")[1:]
        page = int(page)
        logger.info(f"Disconnecting channel {channel_id} for user {user_id}")
        
        # Delete channel
        result = await channels.delete_one({
            "user_id": user_id, 
            "channel_id": int(channel_id)
        })
        logger.info(f"Delete result: {result.deleted_count}")
        
        # Get updated channel list
        user_channels = [ch async for ch in channels.find({"user_id": user_id})]
        total_pages = max(1, math.ceil(len(user_channels) / PAGE_SIZE))
        
        if result.deleted_count > 0:
            text = "✅ Channel disconnected successfully!"
        else:
            text = "❌ Failed to disconnect channel."
            
        # Update message
        if user_channels:
            await callback_query.edit_message_text(
                text + "\n\nSelect another channel to disconnect:",
                reply_markup=build_channels_keyboard(
                    user_channels, 
                    min(page, total_pages-1), 
                    total_pages
                )
            )
        else:
            await callback_query.edit_message_text(
                text + "\n\nNo more channels connected."
            )
            
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        await callback_query.answer("An error occurred. Please try again.")