import re, os
from os import environ

id_pattern = re.compile(r'^.\d+$') 

API_ID = os.environ.get("API_ID", "22012880")
API_HASH = os.environ.get("API_HASH", "5b0e07f5a96d48b704eb9850d274fe1d")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8113642693:AAG9yJpZjyhKIP_nhsIIoc8ZsiTJ-gsudLU")
MONGO_URI = os.environ.get("DB_URL","mongodb+srv://uramit0001:EZ1u5bfKYZ52XeGT@cluster0.qnbzn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
