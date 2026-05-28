import asyncio
import logging
from typing import List

from bot.services.scrapers.base import ProductResult
from bot.services.price_comparator import PriceComparator

logger = logging.getLogger(__name__)

POPULAR_QUERIES = [
    "iPhone", "Samsung Galaxy", "Xiaomi", "AirPods", "Samsung TV",
    "Asus laptop", "Lenovo", "PlayStation", "Xbox", "smartwatch",
    "refrigerator", "washing machine", "air conditioner",
]


class DealsService:
    def __init__(self):
        self.comparator = PriceComparator()

    async def get_top_deals(self, db, limit: int = 10) -> List[dict]:
        try:
            all_history = await db.get_all_active_tracked()
            deals = []

            for item in all_history[:20]:
                product_id = item.get("product_id")
                current_price = item.get("current_price", 0)
                history = await db.get_price_history(product_id, days=30)

                if len(history) < 2:
                    continue

                max_price = max(h["price"] for h in history)
                if max_price > current_price and current_price > 0:
                    discount = round((max_price - current_price) / max_price * 100, 1)
                    if discount >= 5:
                        deals.append({
                            "name": item.get("name", ""),
                            "marketplace": item.get("marketplace", ""),
                            "url": item.get("url", ""),
                            "old_price": max_price,
                            "new_price": current_price,
                            "discount": discount,
                            "currency": item.get("currency", "UZS"),
                        })

            deals.sort(key=lambda x: x["discount"], reverse=True)
            return deals[:limit]

        except Exception as e:
            logger.error(f"DealsService.get_top_deals error: {e}")
            return []

    def format_deals_post(self, deals: List[dict], language: str = "uz") -> str:
        if not language:
            language = "uz"

        if not deals:
            return (
                "😔 Bugun katta chegirmalar topilmadi."
                if language == "uz"
                else "😔 Сегодня больших скидок не найдено."
            )

        title = "🔥 <b>Bugungi TOP chegirmalar</b>" if language == "uz" else "🔥 <b>Топ скидки сегодня</b>"
        lines = [title, ""]

        for i, deal in enumerate(deals[:10], 1):
            from bot.utils.formatter import format_price, get_marketplace_emoji
            emoji = get_marketplace_emoji(deal["marketplace"])
            old_p = format_price(deal["old_price"], deal.get("currency", "UZS"))
            new_p = format_price(deal["new_price"], deal.get("currency", "UZS"))
            url = deal.get("url", "")
            name = deal["name"][:50]
            discount = deal["discount"]

            line = (
                f"{i}. {emoji} <b>{name}</b>\n"
                f"   <s>{old_p}</s> → <b>{new_p}</b>  📉 -{discount}%"
            )
            if url:
                line += f"\n   🔗 <a href='{url}'>Ko'rish</a>" if language == "uz" else f"\n   🔗 <a href='{url}'>Смотреть</a>"
            lines.append(line)

        return "\n\n".join(lines)

    async def send_daily_deals(self, bot, db) -> None:
        from bot.config import CHANNEL_ID
        if not CHANNEL_ID:
            logger.info("CHANNEL_ID not set, skipping daily deals post")
            return

        try:
            deals = await self.get_top_deals(db, limit=10)
            text = self.format_deals_post(deals)
            await bot.send_message(CHANNEL_ID, text, parse_mode="HTML")
            logger.info("Daily deals post sent to channel")
        except Exception as e:
            logger.error(f"Failed to send daily deals: {e}")
