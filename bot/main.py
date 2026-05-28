import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import BOT_TOKEN, ADMIN_IDS
from bot.database.db import DatabaseManager
from bot.middlewares.language import LanguageMiddleware
from bot.services.tracker import PriceTracker
from bot.services.deals_service import DealsService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, db: DatabaseManager) -> None:
    await db.init_db()
    logger.info("Database initialized")

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "🚀 <b>Price AI bot ishga tushdi!</b>", parse_mode="HTML")
        except Exception:
            pass


async def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Please configure .env file.")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    db = DatabaseManager()

    dp.message.middleware(LanguageMiddleware(db))
    dp.callback_query.middleware(LanguageMiddleware(db))

    from bot.handlers import start, search, tracking, history, ai_advice, wishlist, deals, admin

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(search.router)
    dp.include_router(tracking.router)
    dp.include_router(history.router)
    dp.include_router(ai_advice.router)
    dp.include_router(wishlist.router)
    dp.include_router(deals.router)

    tracker = PriceTracker()
    deals_service = DealsService()

    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")
    scheduler.add_job(
        tracker.check_prices,
        "interval",
        hours=2,
        args=[db, bot],
        id="price_tracker",
    )
    scheduler.add_job(
        deals_service.send_daily_deals,
        "cron",
        hour=9,
        minute=0,
        args=[bot, db],
        id="daily_deals",
    )
    scheduler.start()
    logger.info("Scheduler started")

    await on_startup(bot, db)

    logger.info("Bot started polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
