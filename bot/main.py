import asyncio
import logging
import signal

from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import BOT_TOKEN, ADMIN_IDS, PORT
from bot.database.db import DatabaseManager
from bot.health_server import start_health_server
from bot.services.tracker import PriceTracker
from bot.services.deals_service import DealsService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    db = DatabaseManager()
    await db.init_db()
    application.bot_data["db"] = db
    logger.info("Database initialized")

    for admin_id in ADMIN_IDS:
        try:
            await application.bot.send_message(
                admin_id,
                "🚀 <b>Price AI bot ishga tushdi!</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass


def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Please configure .env file.")
        return

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    from bot.handlers import start, search, tracking, history, ai_advice, wishlist, deals, admin

    all_handlers = (
        start.get_handlers()
        + search.get_handlers()
        + tracking.get_handlers()
        + history.get_handlers()
        + ai_advice.get_handlers()
        + wishlist.get_handlers()
        + deals.get_handlers()
        + admin.get_handlers()
    )

    for handler in all_handlers:
        app.add_handler(handler)

    tracker = PriceTracker()
    deals_service = DealsService()

    scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

    async def run() -> None:
        health_runner = await start_health_server(PORT)

        async with app:
            db = app.bot_data.get("db")
            scheduler.add_job(
                tracker.check_prices,
                "interval",
                hours=2,
                args=[db, app.bot],
                id="price_tracker",
            )
            scheduler.add_job(
                deals_service.send_daily_deals,
                "cron",
                hour=9,
                minute=0,
                args=[app.bot, db],
                id="daily_deals",
            )
            scheduler.start()
            logger.info("Scheduler started")

            await app.start()
            await app.updater.start_polling(allowed_updates=["message", "callback_query"])

            logger.info("Bot started polling...")

            stop_event = asyncio.Event()
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGTERM, stop_event.set)
            loop.add_signal_handler(signal.SIGINT, stop_event.set)
            await stop_event.wait()

            logger.info("Shutting down...")
            await app.updater.stop()
            await app.stop()
            scheduler.shutdown()
            await health_runner.cleanup()

    asyncio.run(run())


if __name__ == "__main__":
    main()
