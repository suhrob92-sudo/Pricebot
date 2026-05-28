import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from bot.keyboards.main_menu import get_back_keyboard
from bot.middlewares.language import get_user_lang
from bot.utils.formatter import format_price_history_table, format_price

logger = logging.getLogger(__name__)


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


async def cb_show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)

    if not db:
        await query.message.reply_text(
            t.get("no_history", "📭 Narx tarixi mavjud emas."),
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )
        return

    product_id = int(query.data.split(":")[2])
    product = await db.get_product(product_id)

    if not product:
        await query.answer("❌ Mahsulot topilmadi", show_alert=True)
        return

    history = await db.get_price_history(product_id, days=90)

    if not history:
        await query.message.reply_text(
            t.get("no_history", "📭 Narx tarixi mavjud emas."),
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )
        return

    name = product["name"][:50]
    marketplace = product["marketplace"]
    current_price = format_price(product["current_price"], product.get("currency", "UZS"))

    history_table = format_price_history_table(history, lang)

    if len(history) >= 2:
        oldest = history[0]["price"]
        newest = history[-1]["price"]
        if oldest > newest:
            trend = "📉 Narx tushdi" if lang == "uz" else "📉 Цена снизилась"
        elif oldest < newest:
            trend = "📈 Narx ko'tarildi" if lang == "uz" else "📈 Цена выросла"
        else:
            trend = "➡️ Narx o'zgarmadi" if lang == "uz" else "➡️ Цена не изменилась"
    else:
        trend = ""

    header = t.get("history_header", "📈 <b>Narx tarixi</b>\n\n")
    text = (
        f"{header}"
        f"📦 <b>{name}</b>\n"
        f"📍 {marketplace}\n"
        f"💰 Joriy narx: <b>{current_price}</b>\n\n"
        f"📊 So'nggi narxlar:\n{history_table}\n\n"
        f"{trend}"
    )

    await query.message.reply_text(
        text,
        reply_markup=get_back_keyboard(lang, "menu:main"),
        parse_mode="HTML",
    )


def get_handlers():
    return [
        CallbackQueryHandler(cb_show_history, pattern=r"^history:show:\d+$"),
    ]
