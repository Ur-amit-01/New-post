from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import (
    ChatAdminRequired, 
    ChannelPrivate, 
    UserNotParticipant, 
    UsernameNotOccupied,
    UsernameInvalid
)
from bot_instance import bot
from utils.decorators import must_join_channel
from database.mongodb import channels, db
import asyncio
import logging

logger = logging.getLogger(__name__)

# Store users waiting for channel input
waiting_users = {}

# First handler stays the same
@bot.on_message(filters.command("connect") & filters.private)
@must_join_channel
async def connect_command(client: bot, message: Message):
    try:
        await db.command("ping")
        user_id = message.from_user.id
        waiting_users[user_id] = True
        
        await message.reply_text(
            "Please forward a message from the channel/group you want to connect,\n"
            "or send the channel/group username or ID."
        )
    except Exception as e:
        logger.error(f"MongoDB connection error: {str(e)}")
        await message.reply_text("Database connection error. Please try again later.")

# Update the handler in connect.py
@bot.on_message(filters.private & filters.incoming & ~filters.command(["connect", "start", "help", "post", "disconnect"]))
async def handle_channel_input(client: bot, message: Message):
    user_id = message.from_user.id
    
    # Only process if user is waiting for channel input
    if user_id not in waiting_users:
        # Let other handlers process this message
        message.continue_propagation()
        return
    
    # Process channel connection
    try:
        del waiting_users[user_id]
        
        if message.forward_from_chat:
            channel_id = message.forward_from_chat.id
            channel_title = message.forward_from_chat.title
            channel_username = message.forward_from_chat.username
        else:
            channel_input = message.text.strip()
            try:
                chat = await client.get_chat(channel_input)
                channel_id = chat.id
                channel_title = chat.title
                channel_username = chat.username
            except UsernameNotOccupied:
                return await message.reply_text("This username does not exist. Please check and try again.")
            except UsernameInvalid:
                return await message.reply_text("Invalid username format. Please check and try again.")
            except Exception:
                return await message.reply_text("Unable to find this channel/group. Please verify the information and try again.")
        
        # Check if channel already connected
        existing_channel = await channels.find_one({"channel_id": channel_id})
        if existing_channel:
            return await message.reply_text("This channel is already connected to the bot!")
        
        try:
            bot_member = await client.get_chat_member(channel_id, (await client.get_me()).id)
            logger.info(f"Bot status: {bot_member.status}")
            logger.info(f"Channel ID: {channel_id}")
            logger.info(f"Channel Title: {channel_title}")
            
            # First try to send a message without checking status
            try:
                test_msg = await client.send_message(
                    channel_id,
                    "Testing bot permissions... This message will be deleted."
                )
                logger.info("Test message sent successfully")
                await asyncio.sleep(2)
                await test_msg.delete()
                logger.info("Test message deleted successfully")
                
                # If we get here, the bot has the required permissions
                try:
                    # Save to database
                    result = await channels.insert_one({
                        "user_id": user_id,
                        "channel_id": channel_id,
                        "channel_title": channel_title,
                        "channel_username": channel_username,
                        "added_on": message.date
                    })
                    
                    if result.inserted_id:
                        await message.reply_text(
                            f"✅ Successfully connected to {channel_title}!"
                        )
                    else:
                        raise Exception("Database insertion failed")
                        
                except Exception as db_error:
                    logger.error(f"Database error: {str(db_error)}")
                    await message.reply_text("Failed to save channel information. Please try again.")
                
            except Exception as test_error:
                logger.error(f"Test message error: {str(test_error)}")
                return await message.reply_text(
                    "Failed to send/delete test message.\n"
                    "Please make sure I have these permissions:\n"
                    "- Send Messages\n"
                    "- Delete Messages"
                )
            
        except UserNotParticipant:
            return await message.reply_text(
                "I'm not a member of this channel/group.\n"
                "Please add me as an administrator first!"
            )
        except ChatAdminRequired:
            return await message.reply_text(
                "I need admin permissions to function properly.\n"
                "Please make sure I have the following rights:\n"
                "- Send Messages\n"
                "- Delete Messages"
            )
        except ChannelPrivate:
            return await message.reply_text(
                "I cannot access this channel/group.\n"
                "Make sure:\n"
                "1. The channel/group is public or I'm a member\n"
                "2. You have the right to add admins"
            )
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error in handle_channel_input: {error_message}")
        await message.reply_text(
            "❌ Error occurred while processing your request:\n"
            f"{error_message}\n\n"
            "Please try again or contact support if the issue persists."
        )