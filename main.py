import importlib
import os
from bot_instance import bot
from pyrogram import idle
import logging
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load commands dynamically
def load_commands():
    try:
        commands_path = os.path.join(os.path.dirname(__file__), "commands")
        for filename in os.listdir(commands_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = f"commands.{filename[:-3]}"
                try:
                    logger.info(f"Loading module: {module_name}")
                    module = importlib.import_module(module_name)
                    logger.info(f"Successfully loaded: {module_name}")
                except Exception as module_error:
                    logger.error(f"Failed to load {module_name}: {str(module_error)}")
    except Exception as e:
        logger.error(f"Error loading commands: {str(e)}")

async def main():
    try:
        await bot.start()
        me = await bot.get_me()
        logger.info(f"Bot Connected Successfully!")
        logger.info(f"Bot Username: @{me.username}")
        logger.info(f"Bot Name: {me.first_name}")
        logger.info("Commands loaded and ready!")
        await idle()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    try:
        logger.info("Bot is starting...")
        load_commands()
        bot.run(main())
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")