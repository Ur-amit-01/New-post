from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot_instance import bot
from utils.decorators import must_join_channel
from database.mongodb import channels

@bot.on_message(filters.command("channels") & filters.private)
@must_join_channel
async def list_channels(client: bot, message: Message):
    user_id = message.from_user.id
    
    try:
        # Get all channels for this user
        user_channels = []
        async for channel in channels.find({"user_id": user_id}):
            user_channels.append(channel)
        
        if not user_channels:
            return await message.reply_text(
                "❌ You haven't connected any channels yet.\n"
                "Use /connect to add a channel."
            )
        
        # Create the channels list message
        channels_text = "🔗 Your Connected Channels:\n\n"
        
        for idx, channel in enumerate(user_channels, 1):
            channel_title = channel.get('channel_title', 'Unknown')
            channel_username = channel.get('channel_username', 'Private Channel')
            
            channels_text += f"{idx}. {channel_title}\n"
            if channel_username:
                channels_text += f"    @{channel_username}\n"
            channels_text += "\n"
        
        # Add footer
        channels_text += "\nUse /connect to add more channels."
        
        # Create keyboard with manage button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Manage Channels", callback_data="manage_channels")]
        ])
        
        await message.reply_text(
            channels_text,
            reply_markup=keyboard
        )
        
    except Exception as e:
        await message.reply_text(
            "❌ Failed to fetch channels list.\n"
            "Please try again later."
        )