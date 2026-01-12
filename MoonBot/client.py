from telethon import TelegramClient
from MoonBot import config

# Inisialisasi Bot Client saja (jangan di-start dulu di sini jika ingin lazy load, 
# tapi start() di Telethon bersifat blocking untuk login/auth, jadi sebaiknya dipisah)

# Kita buat instance saja dulu
bot = TelegramClient('MoonBot/bot_session', config.DEFAULT_API_ID, config.DEFAULT_API_HASH)
