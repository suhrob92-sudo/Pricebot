import logging
from typing import Optional

from bot.config import PRICE_DROP_THRESHOLD
from bot.utils.formatter import format_price, calc_discount

logger = logging.getLogger(__name__)


class PriceTracker:
    async def check_prices(self, db, bot) -> None:
        try:
            tracked = await db.get_all_active_tracked()
            logger.info(f"Checking prices for {len(tracked)} tracked products")

            from bot.services.price_comparator import PriceComparator
            comparator = PriceComparator()

            for item in tracked:
                try:
                    await self._check_single(item, db, bot, comparator)
                except Exception as e:
                    logger.error(f"Error checking product {item.get('product_id')}: {e}")
        except Exception as e:
            logger.error(f"PriceTracker.check_prices error: {e}")

    async def _check_single(self, item: dict, db, bot, comparator) -> None:
        product_name = item.get("name", "")
        old_price = item.get("current_price", 0)
        marketplace = item.get("marketplace", "")
        target_price = item.get("target_price")
        notify_any = item.get("notify_any_drop", 1)
        user_id = item.get("user_id")
        product_id = item.get("product_id")

        search_data = await comparator.search_all(product_name)
        results = search_data.get("results", [])

        same_marketplace = [r for r in results if r.marketplace == marketplace]
        if not same_marketplace:
            same_marketplace = results

        if not same_marketplace:
            return

        new_price = min(same_marketplace, key=lambda x: x.price).price
        new_url = min(same_marketplace, key=lambda x: x.price).url

        if new_price <= 0 or new_price >= old_price:
            await db.update_product_price(product_id, new_price)
            await db.save_price_history(product_id, new_price)
            return

        discount = calc_discount(old_price, new_price)

        should_notify = False
        if target_price and new_price <= target_price:
            should_notify = True
        elif notify_any and discount >= PRICE_DROP_THRESHOLD:
            should_notify = True

        if should_notify:
            await self.notify_user(
                bot, user_id, product_name, marketplace, old_price, new_price, discount, new_url
            )

        await db.update_product_price(product_id, new_price)
        await db.save_price_history(product_id, new_price)

    async def notify_user(
        self,
        bot,
        user_telegram_id: int,
        product_name: str,
        marketplace: str,
        old_price: float,
        new_price: float,
        discount: float,
        url: str,
    ) -> None:
        try:
            old_str = format_price(old_price)
            new_str = format_price(new_price)
            text = (
                f"📉 <b>Narx tushdi!</b>\n\n"
                f"🏷 {product_name}\n"
                f"📍 {marketplace}\n"
                f"💰 {old_str} → <b>{new_str}</b>\n"
                f"📊 Chegirma: <b>{discount}%</b>\n\n"
                f"🛒 <a href='{url}'>Ko'rish</a>"
            )
            await bot.send_message(user_telegram_id, text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Failed to notify user {user_telegram_id}: {e}")
