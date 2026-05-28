import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from bot.keyboards.main_menu import get_back_keyboard
from bot.middlewares.language import get_user_lang

logger = logging.getLogger(__name__)

AI_QUERY = 1


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


async def cb_ai_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, query.from_user.id)

    t = get_texts(lang)
    await query.edit_message_text(
        t["ai_prompt"],
        reply_markup=get_back_keyboard(lang, "menu:main"),
        parse_mode="HTML",
    )
    return AI_QUERY


async def handle_ai_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    db = context.application.bot_data.get("db")
    lang = "uz"
    if db:
        lang = await get_user_lang(db, update.effective_user.id)

    t = get_texts(lang)
    query_text = update.message.text.strip()

    if not query_text:
        return AI_QUERY

    thinking_msg = await update.message.reply_text(t["ai_thinking"], parse_mode="HTML")

    try:
        from bot.config import ANTHROPIC_API_KEY
        from bot.services.ai_advisor import AIAdvisor

        advisor = AIAdvisor(ANTHROPIC_API_KEY)
        response = await advisor.get_advice(query_text, lang)

        try:
            await thinking_msg.delete()
        except Exception:
            pass

        await update.message.reply_text(
            response,
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"AI advice handler error: {e}")
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(
            t.get("ai_error", "❌ Xatolik yuz berdi."),
            reply_markup=get_back_keyboard(lang, "menu:main"),
            parse_mode="HTML",
        )

    return ConversationHandler.END


async def cancel_ai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        entry_points=[CallbackQueryHandler(cb_ai_menu, pattern=r"^menu:ai$")],
        states={
            AI_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_query),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_ai),
            CommandHandler("start", cancel_ai),
        ],
        per_message=False,
    )
    return [conv_handler]
