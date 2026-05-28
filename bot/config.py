import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: List[int] = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/pricebot.db")
PORT: int = int(os.getenv("PORT", "8080"))

SUPPORTED_LANGUAGES = ["uz", "ru"]
DEFAULT_LANGUAGE = "uz"

MARKETPLACES = {
    "uzum": {"name": "Uzum Market", "emoji": "🟠", "url": "https://uzum.uz"},
    "olcha": {"name": "Olcha.uz", "emoji": "🔴", "url": "https://olcha.uz"},
    "texnomart": {"name": "Texnomart", "emoji": "🔵", "url": "https://texnomart.uz"},
    "mediapark": {"name": "Mediapark", "emoji": "🟢", "url": "https://mediapark.uz"},
    "ozon": {"name": "Ozon", "emoji": "🟣", "url": "https://ozon.ru"},
    "wildberries": {"name": "Wildberries", "emoji": "🩷", "url": "https://wildberries.ru"},
}

PRICE_DROP_THRESHOLD = 5  # percent
MAX_TRACKED_PRODUCTS = 20
MAX_WISHLIST_ITEMS = 50
