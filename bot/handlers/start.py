import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from bot.keyboards.main_menu import get_main_menu, get_language_keyboard, get_settings_keyboard
from bot.middlewares.language import get_user_lang, ensure_user

logger = logging.getLogger(__name__)


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data.get("db")
    user = update.effective_user

    db_user = {}
    if db:
        db_user = await ensure_user(db, user)
        if db_user.get("is_banned"):
            lang = db_user.get("language", "uz")
            t = get_texts(lang)
            await update.message.reply_text(t["banned_message"])
            return

    lang = db_user.get("language") if db_user else None

    # New users or users without language set: show language selection first
    if not lang:
        await update.message.reply_text(
            "🌐 Tilni tanlang / Выберите язык:",
            reply_markup=get_language_keyboard(),
        )
        return

    t = get_texts(lang)
    name = user.full_name or user.username or "Foydalanuvchi"
    await update.message.reply_text(
        t["welcome"].format(name=name),
        reply_markup=get_main_menu(lang),
        parse_mode="HTML",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, update.effective_user.id)
    t = get_texts(lang)
    await update.message.reply_text(
        t.get("help_text", t["welcome"].format(name="")),
        reply_markup=get_main_menu(lang),
        parse_mode="HTML",
    )


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=get_language_keyboard(),
    )


async def cb_lang_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    lang = query.data.split(":")[1]
    if lang not in ["uz", "ru"]:
        await query.answer("❌ Noto'g'ri til", show_alert=True)
        return

    db = context.application.bot_data.get("db")
    if db:
        await db.update_user_language(query.from_user.id, lang)

    t = get_texts(lang)
    user = query.from_user
    name = user.full_name or user.username or "Foydalanuvchi"

    await query.edit_message_text(
        t["welcome"].format(name=name),
        reply_markup=get_main_menu(lang),
        parse_mode="HTML",
    )


async def cb_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)
    await query.edit_message_text(
        t["main_menu"],
        reply_markup=get_main_menu(lang),
        parse_mode="HTML",
    )


async def cb_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)
    await query.edit_message_text(
        t.get("settings_menu", "⚙️ Sozlamalar"),
        reply_markup=get_settings_keyboard(lang),
        parse_mode="HTML",
    )


async def cb_change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=get_language_keyboard(),
    )


def get_handlers():
    return [
        CommandHandler("start", cmd_start),
        CommandHandler("help", cmd_help),
        CommandHandler("language", cmd_language),
        CallbackQueryHandler(cb_lang_set, pattern=r"^lang:(uz|ru)$"),
        CallbackQueryHandler(cb_main_menu, pattern=r"^menu:main$"),
        CallbackQueryHandler(cb_settings, pattern=r"^menu:settings$"),
        CallbackQueryHandler(cb_change_language, pattern=r"^settings:language$"),
    ]
