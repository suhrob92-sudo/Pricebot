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

from bot.keyboards.main_menu import get_back_keyboard
from bot.keyboards.inline_kb import get_results_navigation_keyboard, get_product_actions_keyboard
from bot.middlewares.language import get_user_lang
from bot.services.price_comparator import PriceComparator

logger = logging.getLogger(__name__)

comparator = PriceComparator()

SEARCH_QUERY = 1


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


async def cb_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)
    await query.edit_message_text(
        t["search_prompt"],
        reply_markup=get_back_keyboard(lang, "menu:main"),
        parse_mode="HTML",
    )
    return SEARCH_QUERY


async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, update.effective_user.id)

    t = get_texts(lang)
    query_text = update.message.text.strip()

    if not query_text or len(query_text) < 2:
        await update.message.reply_text(
            t.get("error_general", "❌ Xatolik"),
            parse_mode="HTML",
        )
        return SEARCH_QUERY

    searching_msg = await update.message.reply_text(t["searching"], parse_mode="HTML")

    try:
        search_data = await comparator.search_all(query_text)
        results = search_data.get("results", [])
        total = search_data.get("total", 0)

        if db:
            await db.save_search(update.effective_user.id, query_text, total)

        try:
            await searching_msg.delete()
        except Exception:
            pass

        if not results:
            from bot.config import SCRAPERAPI_KEY
            if not SCRAPERAPI_KEY:
                no_key_msg = (
                    "⚙️ <b>Scraper kaliti yo'q</b>\n\n"
                    "Narxlarni qidirish uchun <code>SCRAPERAPI_KEY</code> kerak.\n\n"
                    "1. scraperapi.com da bepul ro'yxatdan o'ting (5000 req/oy)\n"
                    "2. Render → Environment → <code>SCRAPERAPI_KEY</code> = sizning kalit\n"
                    "3. Botni qayta ishga tushiring"
                    if lang == "uz" else
                    "⚙️ <b>Ключ скрапера не настроен</b>\n\n"
                    "Для поиска цен нужен <code>SCRAPERAPI_KEY</code>.\n\n"
                    "1. Зарегистрируйтесь на scraperapi.com (5000 req/мес бесплатно)\n"
                    "2. Render → Environment → <code>SCRAPERAPI_KEY</code> = ваш ключ\n"
                    "3. Перезапустите бота"
                )
                await update.message.reply_text(
                    no_key_msg,
                    reply_markup=get_back_keyboard(lang, "menu:main"),
                    parse_mode="HTML",
                )
            else:
                await update.message.reply_text(
                    t["no_results"].format(query=query_text),
                    reply_markup=get_back_keyboard(lang, "menu:main"),
                    parse_mode="HTML",
                )
            return ConversationHandler.END

        text = comparator.format_results_text(search_data, query_text, lang)

        saved_items = []
        if db:
            for r in results:
                try:
                    pid = await db.save_product(
                        name=r.name,
                        marketplace=r.marketplace,
                        url=r.url,
                        image_url=r.image_url,
                        price=r.price,
                        currency=r.currency,
                    )
                    r.id = pid
                    saved_items.append({"id": pid, "name": r.name})
                except Exception as e:
                    logger.error(f"Error saving product: {e}")

        context.user_data["last_search_results"] = saved_items
        context.user_data["last_search_query"] = query_text

        kb = get_results_navigation_keyboard(saved_items, lang, 0, query_text)
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Search handler error: {e}")
        try:
            await searching_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            t.get("error_general", "❌ Xatolik yuz berdi."),
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )

    return ConversationHandler.END


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, update.effective_user.id)

    await update.message.reply_text(
        "❌ Bekor qilindi." if lang == "uz" else "❌ Отменено.",
        reply_markup=get_back_keyboard(lang, "menu:main"),
    )
    return ConversationHandler.END


async def cb_product_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    product_id = int(query.data.split(":")[2])

    if not db:
        await query.answer("❌ DB xatolik", show_alert=True)
        return

    product = await db.get_product(product_id)
    if not product:
        await query.answer("❌ Mahsulot topilmadi", show_alert=True)
        return

    from bot.utils.formatter import format_price, get_marketplace_emoji

    t = get_texts(lang)
    price_str = format_price(product["current_price"], product.get("currency", "UZS"))
    emoji = get_marketplace_emoji(product["marketplace"])

    text = (
        f"{emoji} <b>{product['name']}</b>\n\n"
        f"📍 {product['marketplace']}\n"
        f"💰 <b>{price_str}</b>\n"
    )
    if product.get("url"):
        text += f"🔗 <a href='{product['url']}'>Ko'rish</a>"

    await query.message.reply_text(
        text,
        reply_markup=get_product_actions_keyboard(product_id, lang),
        parse_mode="HTML",
    )


def get_handlers():
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_search_menu, pattern=r"^menu:search$")],
        states={
            SEARCH_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_query),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_search),
            CommandHandler("start", cancel_search),
        ],
        per_message=False,
    )
    return [
        conv_handler,
        CallbackQueryHandler(cb_product_view, pattern=r"^product:view:\d+$"),
    ]
