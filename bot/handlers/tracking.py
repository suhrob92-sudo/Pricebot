import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
)

from bot.keyboards.main_menu import get_back_keyboard
from bot.keyboards.inline_kb import get_tracking_list_keyboard
from bot.middlewares.language import get_user_lang
from bot.utils.formatter import format_tracking_item

logger = logging.getLogger(__name__)


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


async def cb_tracking_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)

    if not db:
        await query.edit_message_text(
            t["no_tracking"],
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )
        return

    user_id = query.from_user.id
    tracked = await db.get_user_tracked_products(user_id)

    if not tracked:
        await query.edit_message_text(
            t["no_tracking"],
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )
        return

    text = t["tracking_list"]
    for item in tracked[:5]:
        text += format_tracking_item(item, lang) + "\n\n"

    kb = get_tracking_list_keyboard(tracked, lang, page=0)
    await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")


async def cb_track_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)

    if not db:
        await query.answer("❌ DB xatolik", show_alert=True)
        return

    product_id = int(query.data.split(":")[2])
    user_id = query.from_user.id

    from bot.config import MAX_TRACKED_PRODUCTS
    tracked = await db.get_user_tracked_products(user_id)
    if len(tracked) >= MAX_TRACKED_PRODUCTS:
        await query.answer(
            t["track_limit"].format(limit=MAX_TRACKED_PRODUCTS),
            show_alert=True,
        )
        return

    success = await db.add_tracked_product(user_id, product_id, target_price=None)
    if success:
        await query.answer(t["track_added"], show_alert=True)
    else:
        await query.answer(t.get("already_tracking", "ℹ️ Allaqachon kuzatilmoqda"), show_alert=True)


async def cb_track_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)

    if not db:
        await query.answer("❌ DB xatolik", show_alert=True)
        return

    tracking_id = int(query.data.split(":")[2])
    user_id = query.from_user.id

    await db.remove_tracked_product(tracking_id, user_id)
    await query.answer(t.get("tracking_removed", "✅ O'chirildi"), show_alert=True)

    tracked = await db.get_user_tracked_products(user_id)
    if not tracked:
        await query.edit_message_text(
            t["no_tracking"],
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )
        return

    text = t["tracking_list"]
    for item in tracked[:5]:
        text += format_tracking_item(item, lang) + "\n\n"

    kb = get_tracking_list_keyboard(tracked, lang, page=0)
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


async def cb_track_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)
    page = int(query.data.split(":")[2])
    user_id = query.from_user.id

    if not db:
        return

    tracked = await db.get_user_tracked_products(user_id)
    if not tracked:
        return

    start = page * 5
    text = t["tracking_list"]
    for item in tracked[start:start + 5]:
        text += format_tracking_item(item, lang) + "\n\n"

    kb = get_tracking_list_keyboard(tracked, lang, page=page)
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


def get_handlers():
    return [
        CallbackQueryHandler(cb_tracking_menu, pattern=r"^menu:tracking$"),
        CallbackQueryHandler(cb_track_add, pattern=r"^track:add:\d+$"),
        CallbackQueryHandler(cb_track_remove, pattern=r"^track:remove:\d+$"),
        CallbackQueryHandler(cb_track_page, pattern=r"^track:page:\d+$"),
    ]
