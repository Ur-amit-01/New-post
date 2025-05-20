from motor.motor_asyncio import AsyncIOMotorClient
from config import *
import logging

logger = logging.getLogger(__name__)

try:
    client = AsyncIOMotorClient(Config.MONGO_URI)
    db = client['channel_bot']
    channels = db['channels']
    
    # Test the connection
    client.admin.command('ping')
    logger.info("MongoDB Connected Successfully!")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")
    raise Exception("MongoDB Connection Failed!")
