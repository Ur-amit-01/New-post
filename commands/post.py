from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import math
from bot_instance import bot
from database.mongodb import channels
from utils.decorators import must_join_channel
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Store user post drafts
user_drafts = {}

class PostDraft:
    def __init__(self, user_id):
        self.user_id = user_id
        self.media = None
        self.media_type = None
        self.caption = None
        self.buttons = []
        self.preview_message_id = None
        self.original_message = None
        self.self_destruct_time = None
        self.scheduled_time = None
        self.awaiting_buttons = False
        self.awaiting_schedule = False
        self.awaiting_content = True

def get_post_preview_keyboard(page=1):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Add URL Button", callback_data="post_add_buttons")],
        [InlineKeyboardButton("⏲️ Self-Destruct Timer", callback_data="post_timer")],
        [InlineKeyboardButton("📅 Schedule Post", callback_data="post_schedule")],
        [InlineKeyboardButton("📤 Send Post", callback_data="post_send")],
        [InlineKeyboardButton("❌ Cancel", callback_data="post_cancel")]
    ])

def get_timer_keyboard(current_time=None):
    duration_minutes = 0
    
    if current_time:
        time_diff = current_time - datetime.now()
        duration_minutes = int(time_diff.total_seconds() / 60)

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Self-destruct after: {duration_minutes} minutes", callback_data="timer_set")],
        [
            InlineKeyboardButton("-10m", callback_data="timer_minus_10"),
            InlineKeyboardButton("+10m", callback_data="timer_plus_10")
        ],
        [
            InlineKeyboardButton("-30m", callback_data="timer_minus_30"),
            InlineKeyboardButton("+30m", callback_data="timer_plus_30")
        ],
        [
            InlineKeyboardButton("-1h", callback_data="timer_minus_60"),
            InlineKeyboardButton("+1h", callback_data="timer_plus_60")
        ],
        [InlineKeyboardButton("None", callback_data="timer_none")],
        [InlineKeyboardButton("« Back", callback_data="post_preview")]
    ])

async def get_channel_keyboard(user_id, page=1, items_per_page=5):
    user_channels_list = []
    async for channel in channels.find({"user_id": user_id}):
        # Store the original channel ID without any formatting
        channel_id = str(channel["channel_id"]).replace('-100', '')
        user_channels_list.append({
            "id": channel_id,  # Store clean ID
            "title": channel["channel_title"]
        })
    
    total_channels = len(user_channels_list)
    total_pages = math.ceil(total_channels / items_per_page)
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    buttons = []
    # Add "Send to All" button at the top
    buttons.append([InlineKeyboardButton("📢 Send to All Channels", callback_data="send_all")])
    
    # Add channel buttons
    current_channels = user_channels_list[start_idx:end_idx]
    for channel in current_channels:
        buttons.append([
            InlineKeyboardButton(
                channel["title"], 
                callback_data=f"send_{channel['id']}"  # Using clean ID
            )
        ])
    
    # Add navigation buttons if needed
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("« Previous", callback_data=f"page_{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next »", callback_data=f"page_{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    
    # Add cancel button
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="post_cancel")])
    
    return InlineKeyboardMarkup(buttons)

@bot.on_message(filters.command("post") & filters.private)
@must_join_channel
async def post_command(client: bot, message: Message):
    try:
        user_id = message.from_user.id
        
        # Check if user has any connected channels
        user_channels = await channels.count_documents({"user_id": user_id})
        if user_channels == 0:
            return await message.reply_text(
                "❌ You don't have any connected channels.\n"
                "Use /connect to add a channel first."
            )
        
        # Create a new draft for the user
        user_drafts[user_id] = PostDraft(user_id)
        
        await message.reply_text(
            "📝 Send me what you want to post. It can be:\n"
            "• Text message\n"
            "• Photo\n"
            "• Video\n"
            "• Document\n"
            "• Audio\n"
            "• Voice\n"
            "• Sticker\n"
            "• GIF\n\n"
            "You can include a caption with your media."
        )
        
    except Exception as e:
        logger.error(f"Error in post_command: {str(e)}", exc_info=True)
        await message.reply_text("❌ An error occurred. Please try again later.")

# First, update the handle_post_content filter to be more specific
@bot.on_message(filters.private & filters.incoming & ~filters.command(["connect", "start", "help", "post", "disconnect"]) & ~filters.regex(r"^.+\s*-\s*https?://.*$"))
async def handle_post_content(client: bot, message: Message):
    try:
        user_id = message.from_user.id
        draft = user_drafts.get(user_id)
        
        if not draft:
            return
            
        # Skip if waiting for button input
        if draft.awaiting_buttons:
            return
            
        # Check if user is in post creation mode
        if not draft.awaiting_content:
            return
            
        draft.original_message = message
        
        # Handle different types of content
        if message.photo:
            draft.media_type = "photo"
            draft.media = message.photo.file_id
            draft.caption = message.caption
        elif message.video:
            draft.media_type = "video"
            draft.media = message.video.file_id
            draft.caption = message.caption
        elif message.document:
            draft.media_type = "document"
            draft.media = message.document.file_id
            draft.caption = message.caption
        elif message.audio:
            draft.media_type = "audio"
            draft.media = message.audio.file_id
            draft.caption = message.caption
        elif message.voice:
            draft.media_type = "voice"
            draft.media = message.voice.file_id
            draft.caption = message.caption
        elif message.sticker:
            draft.media_type = "sticker"
            draft.media = message.sticker.file_id
        elif message.animation:  # For GIFs
            draft.media_type = "animation"
            draft.media = message.animation.file_id
            draft.caption = message.caption
        elif message.text:
            draft.media_type = "text"
            draft.media = message.text
            draft.caption = message.text
        draft.awaiting_content = False
        await send_post_preview(client, user_id)
        
    except Exception as e:
        logger.error(f"Error in handle_post_content: {str(e)}", exc_info=True)

# Then, update the handle_button_input filter to specifically catch URL format
@bot.on_message(filters.private & filters.incoming & filters.regex(r"^.+\s*-\s*https?://.*$") & ~filters.command(["connect", "start", "help", "post", "disconnect"]))
async def handle_button_input(client, message: Message):
    try:
        user_id = message.from_user.id
        draft = user_drafts.get(user_id)
        
        if not draft or not draft.awaiting_buttons:
            return
            
        logger.info(f"Processing button input for user {user_id}: {message.text}")
        
        try:
            parts = message.text.split("-", 1)
            if len(parts) != 2:
                raise ValueError("Invalid format")
                
            button_text, button_url = [x.strip() for x in parts]
            
            if not button_url.startswith(('http://', 'https://', 't.me/')):
                raise ValueError("Invalid URL. URL must start with http://, https://, or t.me/")
            
            draft.buttons.append({
                "text": button_text,
                "url": button_url
            })
            
            draft.awaiting_buttons = False
            await message.reply_text(f"✅ Button '{button_text}' added!")
            await send_post_preview(client, user_id)
            
        except ValueError as e:
            await message.reply_text(
                f"❌ Error: {str(e)}\n"
                "Please try again with the correct format:\n"
                "Button Name - https://example.com"
            )
            
    except Exception as e:
        logger.error(f"Error in handle_button_input: {str(e)}", exc_info=True)
        await message.reply_text("❌ Error processing button. Please try again.")

# Update the callback handler for timer actions
@bot.on_callback_query(filters.regex(r"^post_|^timer_|^page_|^send_"))
async def post_callback_handler(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        logger.info(f"Callback received: {data} from user {user_id}")
        
        draft = user_drafts.get(user_id)
        
        if user_id not in user_drafts and not data.startswith("page_"):
            logger.warning(f"No draft found for user {user_id}")
            await callback_query.answer("Post creation session expired. Start again with /post")
            return
        
        if data.startswith("post_"):
            action = data.split("_", 1)[1]
            logger.info(f"Post action: {action}")
            
            if action == "add_buttons":
                logger.info(f"User {user_id} requested to add buttons")
                draft.awaiting_buttons = True
                draft.awaiting_content = False
                
                # Edit the preview message to ask for URL
                await callback_query.message.edit_text(
                    "🔗 Send me the button in format:\n"
                    "`Button Name - URL`\n\n"
                    "Example: Download - https://example.com",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("« Back", callback_data="post_preview")
                    ]])
                )
                
            elif action == "timer":
                await callback_query.message.edit_text(
                    "⏲️ Select self-destruct timer:",
                    reply_markup=get_timer_keyboard()
                )
                
            elif action == "schedule":
                await callback_query.message.reply_text(
                    "📅 Send me the date and time in format:\n"
                    "YYYY-MM-DD HH:MM\n\n"
                    "Example: 2024-01-01 15:30"
                )
                draft.awaiting_schedule = True
                
            elif action == "send":
                confirm_keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Yes", callback_data="post_confirm_send"),
                        InlineKeyboardButton("❌ No", callback_data="post_preview")
                    ]
                ])
                await callback_query.message.edit_text(
                    "Are you sure you want to send this post?",
                    reply_markup=confirm_keyboard
                )
                
            elif action == "confirm_send":
                page = 1
                keyboard = await get_channel_keyboard(user_id, page)
                await callback_query.message.edit_text(
                    "Select a channel to post to:",
                    reply_markup=keyboard
                )
                
            elif action == "preview":
                await send_post_preview(client, user_id)
                
            elif action == "cancel":
                if user_id in user_drafts:
                    del user_drafts[user_id]
                await callback_query.message.edit_text("Post creation cancelled.")
        
        elif data.startswith("timer_"):
            timer_action = data.split("_", 1)[1]
            
            if timer_action == "none":
                draft.self_destruct_time = None
                await callback_query.answer("Self-destruct timer removed")
                await send_post_preview(client, user_id)
            elif timer_action == "timer":
                # Set initial time to 60 minutes if not set
                if not draft.self_destruct_time:
                    draft.self_destruct_time = datetime.now() + timedelta(minutes=60)
                await callback_query.message.edit_text(
                    "⏲️ Set self-destruct timer\n\n"
                    "Message will be deleted after the specified duration\n"
                    "Use buttons to adjust:",
                    reply_markup=get_timer_keyboard(draft.self_destruct_time)
                )
            elif timer_action.startswith(("plus_", "minus_")):
                action, minutes = timer_action.split("_")
                minutes = int(minutes)
                
                if draft.self_destruct_time is None:
                    draft.self_destruct_time = datetime.now() + timedelta(minutes=60)
                
                if action == "plus":
                    draft.self_destruct_time += timedelta(minutes=minutes)
                else:  # minus
                    new_time = draft.self_destruct_time - timedelta(minutes=minutes)
                    if new_time > datetime.now():
                        draft.self_destruct_time = new_time
                time_diff = draft.self_destruct_time - datetime.now()
                duration_minutes = int(time_diff.total_seconds() / 60)
                
                await callback_query.answer(f"Self-destruct set to: {duration_minutes} minutes")
                
                await callback_query.message.edit_text(
                    "⏲️ Set self-destruct timer\n\n"
                    "Message will be deleted after the specified duration\n"
                    "Use buttons to adjust:",
                    reply_markup=get_timer_keyboard(draft.self_destruct_time)
                )
            elif timer_action == "info":
                await callback_query.answer("Current self-destruct time")
        
        # First, add handling for page navigation in post_callback_handler
        elif data.startswith("page_"):
            page = int(data.split("_")[1])
            keyboard = await get_channel_keyboard(user_id, page)
            await callback_query.message.edit_text(
                "Select a channel to post to:",
                reply_markup=keyboard
            )
        
        elif data.startswith("send_"):
            send_target = data.split("_")[1]
            
            try:
                if send_target == "all":
                    channels_list = []
                    async for channel in channels.find({"user_id": user_id}):
                        channel_id = str(channel["channel_id"])
                        # Remove any -100 prefix and get only the last 10 digits
                        clean_id = ''.join(filter(str.isdigit, channel_id))[-10:]
                        formatted_id = int(f"-100{clean_id}")
                        channels_list.append(formatted_id)
                        logger.info(f"Processed channel ID: {formatted_id}")
                    
                    success_count = 0
                    for channel_id in channels_list:
                        try:
                            preview_markup = None
                            if draft.buttons:
                                keyboard = []
                                for button in draft.buttons:
                                    keyboard.append([InlineKeyboardButton(button["text"], url=button["url"])])
                                preview_markup = InlineKeyboardMarkup(keyboard)
                            
                            logger.info(f"Attempting to send to channel: {channel_id}")
                            
                            if draft.media_type == "photo":
                                await client.send_photo(
                                    chat_id=channel_id,
                                    photo=draft.media,
                                    caption=draft.caption,
                                    reply_markup=preview_markup
                                )
                            elif draft.media_type == "video":
                                await client.send_video(
                                    chat_id=channel_id,
                                    video=draft.media,
                                    caption=draft.caption,
                                    reply_markup=preview_markup
                                )
                            elif draft.media_type == "document":
                                await client.send_document(
                                    chat_id=channel_id,
                                    document=draft.media,
                                    caption=draft.caption,
                                    reply_markup=preview_markup
                                )
                            elif draft.media_type == "text":
                                await client.send_message(
                                    chat_id=channel_id,
                                    text=draft.caption,
                                    reply_markup=preview_markup
                                )
                            success_count += 1
                        except Exception as e:
                            logger.error(f"Error sending to channel {channel_id}: {str(e)}")
                            continue  # Continue with next channel even if one fails
                    
                    # Delete the draft after sending
                    if user_id in user_drafts:
                        del user_drafts[user_id]
                    
                    await callback_query.message.edit_text(
                        f"✅ Post sent to {success_count} channels successfully!"
                    )
                else:
                    # Send to specific channel
                    # Get the clean numeric ID and format it properly
                    clean_id = ''.join(filter(str.isdigit, send_target))
                    channel_id = int(f"-100{clean_id}")
                    
                    preview_markup = None
                    if draft.buttons:
                        keyboard = []
                        for button in draft.buttons:
                            keyboard.append([InlineKeyboardButton(button["text"], url=button["url"])])
                        preview_markup = InlineKeyboardMarkup(keyboard)
                    
                    logger.info(f"Attempting to send to single channel: {channel_id}")
                    
                    if draft.media_type == "photo":
                        await client.send_photo(
                            chat_id=channel_id,
                            photo=draft.media,
                            caption=draft.caption,
                            reply_markup=preview_markup
                        )
                    elif draft.media_type == "video":
                        await client.send_video(
                            chat_id=channel_id,
                            video=draft.media,
                            caption=draft.caption,
                            reply_markup=preview_markup
                        )
                    elif draft.media_type == "document":
                        await client.send_document(
                            chat_id=channel_id,
                            document=draft.media,
                            caption=draft.caption,
                            reply_markup=preview_markup
                        )
                    elif draft.media_type == "text":
                        await client.send_message(
                            chat_id=channel_id,
                            text=draft.caption,
                            reply_markup=preview_markup
                        )
                    
                    # Delete the draft after sending
                    if user_id in user_drafts:
                        del user_drafts[user_id]
                    
                    await callback_query.message.edit_text("✅ Post sent successfully!")
                
            except Exception as e:
                logger.error(f"Error in sending post: {str(e)}")
                await callback_query.message.edit_text(
                    "❌ Error sending post. Please try again."
                )
        
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error in post_callback_handler: {str(e)}", exc_info=True)
        await callback_query.answer("❌ Error processing your request. Please try again.")

async def send_post_preview(client, user_id):
    try:
        draft = user_drafts[user_id]
        
        # Create URL buttons if any
        preview_markup = None
        if draft.buttons:
            keyboard = []
            for button in draft.buttons:
                keyboard.append([InlineKeyboardButton(button["text"], url=button["url"])])
            preview_markup = InlineKeyboardMarkup(keyboard)

        # Delete previous preview if exists
        if draft.preview_message_id:
            try:
                await client.delete_messages(user_id, draft.preview_message_id)
            except Exception:
                pass

        # Send the preview based on media type with URL buttons
        if draft.media_type == "photo":
            preview = await client.send_photo(
                chat_id=user_id,
                photo=draft.media,
                caption=draft.caption,
                reply_markup=preview_markup
            )
        elif draft.media_type == "video":
            preview = await client.send_video(
                chat_id=user_id,
                video=draft.media,
                caption=draft.caption,
                reply_markup=preview_markup
            )
        elif draft.media_type == "document":
            preview = await client.send_document(
                chat_id=user_id,
                document=draft.media,
                caption=draft.caption
            )
        elif draft.media_type == "audio":
            preview = await client.send_audio(
                chat_id=user_id,
                audio=draft.media,
                caption=draft.caption
            )
        elif draft.media_type == "voice":
            preview = await client.send_voice(
                chat_id=user_id,
                voice=draft.media,
                caption=draft.caption
            )
        elif draft.media_type == "sticker":
            preview = await client.send_sticker(
                chat_id=user_id,
                sticker=draft.media
            )
        elif draft.media_type == "animation":
            preview = await client.send_animation(
                chat_id=user_id,
                animation=draft.media,
                caption=draft.caption
            )
        elif draft.media_type == "text":
            preview = await client.send_message(
                chat_id=user_id,
                text=draft.caption,
                reply_markup=preview_markup
            )

        # Store preview message ID
        draft.preview_message_id = preview.id

        # Send action keyboard as a separate message
        if not draft.awaiting_buttons:  # Only send action keyboard if not waiting for button input
            await client.send_message(
                chat_id=user_id,
                text="👇 Choose an action:",
                reply_markup=get_post_preview_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Error in send_post_preview: {str(e)}", exc_info=True)
        await client.send_message(
            chat_id=user_id,
            text="❌ Error creating preview. Please try again."
        )