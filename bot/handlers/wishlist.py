import logging

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from bot.config import MAX_WISHLIST_ITEMS
from bot.keyboards.main_menu import get_back_keyboard
from bot.keyboards.inline_kb import get_wishlist_keyboard
from bot.middlewares.language import get_user_lang

logger = logging.getLogger(__name__)

WISHLIST_ADD = 1


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


def _build_wishlist_keyboard(items: list, lang: str) -> InlineKeyboardMarkup:
    add_label = "➕ Qo'shish" if lang == "uz" else "➕ Добавить"
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if lang == "uz" else RU

    rows = []
    for item in items[:8]:
        rows.append([InlineKeyboardButton(
            f"🗑 {item['product_name'][:25]}",
            callback_data=f"wish:remove:{item['id']}",
        )])
    rows.append([
        InlineKeyboardButton(add_label, callback_data="wish:add_new"),
        InlineKeyboardButton(t["btn_back"], callback_data="menu:main"),
    ])
    return InlineKeyboardMarkup(rows)


async def cb_wishlist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)

    if not db:
        await query.edit_message_text(
            t["no_wishlist"],
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )
        return

    user_id = query.from_user.id
    items = await db.get_user_wishlist(user_id)

    if not items:
        add_label = "➕ Qo'shish" if lang == "uz" else "➕ Добавить"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(add_label, callback_data="wish:add_new")],
            [InlineKeyboardButton(t["btn_back"], callback_data="menu:main")],
        ])
        await query.edit_message_text(
            t["no_wishlist"],
            reply_markup=kb,
            parse_mode="HTML",
        )
        return

    header = t.get("wishlist_header", "📋 <b>Mening ro'yxatim</b>\n\n")
    lines = [f"{i}. 📦 <b>{item['product_name']}</b>" for i, item in enumerate(items, 1)]
    text = header + "\n".join(lines)
    text += f"\n\n📊 {len(items)}/{MAX_WISHLIST_ITEMS}"

    kb = _build_wishlist_keyboard(items, lang)
    await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")


async def cb_wishlist_add_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)
    await query.message.reply_text(
        t["wishlist_prompt"],
        reply_markup=get_back_keyboard(lang, "menu:wishlist"),
        parse_mode="HTML",
    )
    return WISHLIST_ADD


async def cb_add_to_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    product = await db.get_product(product_id)
    if not product:
        await query.answer("❌ Mahsulot topilmadi", show_alert=True)
        return

    success = await db.add_to_wishlist(user_id, product["name"])
    if success:
        await query.answer(t["wishlist_added"].format(name=product["name"][:30]), show_alert=True)
    else:
        await query.answer(t.get("wishlist_limit", "⚠️ Ro'yxat to'ldi"), show_alert=True)


async def handle_wishlist_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, update.effective_user.id)

    t = get_texts(lang)
    product_name = update.message.text.strip()
    user_id = update.effective_user.id

    if not product_name or len(product_name) < 2:
        await update.message.reply_text(
            t.get("error_general", "❌ Xatolik"),
            parse_mode="HTML",
        )
        return WISHLIST_ADD

    if not db:
        await update.message.reply_text("❌ DB xatolik")
        return ConversationHandler.END

    success = await db.add_to_wishlist(user_id, product_name)

    if success:
        await update.message.reply_text(
            t["wishlist_added"].format(name=product_name),
            reply_markup=get_back_keyboard(lang, "menu:wishlist"),
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            t.get("wishlist_limit", "⚠️ Ro'yxat to'ldi."),
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )

    return ConversationHandler.END


async def cb_remove_from_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

    wish_id = int(query.data.split(":")[2])
    user_id = query.from_user.id

    await db.remove_from_wishlist(wish_id, user_id)
    await query.answer(t.get("wishlist_removed", "✅ O'chirildi"), show_alert=True)

    items = await db.get_user_wishlist(user_id)
    if not items:
        add_label = "➕ Qo'shish" if lang == "uz" else "➕ Добавить"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(add_label, callback_data="wish:add_new")],
            [InlineKeyboardButton(t["btn_back"], callback_data="menu:main")],
        ])
        await query.edit_message_text(
            t["no_wishlist"],
            reply_markup=kb,
            parse_mode="HTML",
        )
        return

    header = t.get("wishlist_header", "📋 <b>Mening ro'yxatim</b>\n\n")
    lines = [f"{i}. 📦 <b>{item['product_name']}</b>" for i, item in enumerate(items, 1)]
    text = header + "\n".join(lines)

    kb = _build_wishlist_keyboard(items, lang)
    try:
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


async def cancel_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, update.effective_user.id)

    await update.message.reply_text(
        "❌ Bekor qilindi." if lang == "uz" else "❌ Отменено.",
        reply_markup=get_back_keyboard(lang, "menu:main"),
    )
    return ConversationHandler.END


def get_handlers():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_wishlist_add_new, pattern=r"^wish:add_new$")],
        states={
            WISHLIST_ADD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wishlist_input),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_wishlist),
            CommandHandler("start", cancel_wishlist),
        ],
        per_message=False,
    )
    return [
        CallbackQueryHandler(cb_wishlist_menu, pattern=r"^menu:wishlist$"),
        conv_handler,
        CallbackQueryHandler(cb_add_to_wishlist, pattern=r"^wish:add:\d+$"),
        CallbackQueryHandler(cb_remove_from_wishlist, pattern=r"^wish:remove:\d+$"),
    ]
