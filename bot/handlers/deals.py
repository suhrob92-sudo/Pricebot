import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from bot.keyboards.main_menu import get_back_keyboard
from bot.middlewares.language import get_user_lang
from bot.services.deals_service import DealsService

logger = logging.getLogger(__name__)

deals_service = DealsService()


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


async def cb_deals_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)

    await query.edit_message_text(
        t.get("deals_header", "🔥 <b>Bugungi TOP chegirmalar</b>\n\n") + "⏳ Yuklanmoqda...",
        parse_mode="HTML",
    )

    try:
        deals = await deals_service.get_top_deals(db, limit=10)
        text = deals_service.format_deals_post(deals, lang)

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(t.get("btn_back", "◀️ Orqaga"), callback_data="menu:main"),
        ]])

        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Deals handler error: {e}")
        await query.edit_message_text(
            t.get("no_deals", "😔 Bugun chegirmalar topilmadi."),
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )


async def cb_post_deals_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    from bot.config import ADMIN_IDS
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Ruxsat yo'q", show_alert=True)
        return

    db = context.application.bot_data.get("db")

    try:
        await deals_service.send_daily_deals(context.bot, db)
        await query.answer("✅ Kanalga yuborildi!", show_alert=True)
    except Exception as e:
        logger.error(f"Post deals error: {e}")
        await query.answer("❌ Xatolik yuz berdi", show_alert=True)


def get_handlers():
    return [
        CallbackQueryHandler(cb_deals_menu, pattern=r"^menu:deals$"),
        CallbackQueryHandler(cb_post_deals_to_channel, pattern=r"^admin:post_deals$"),
    ]
