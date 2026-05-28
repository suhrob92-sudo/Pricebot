import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.keyboards.main_menu import get_back_keyboard
from bot.services.deals_service import DealsService

logger = logging.getLogger(__name__)
router = Router()
deals_service = DealsService()


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


@router.callback_query(F.data == "menu:deals")
async def cb_deals_menu(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    t = get_texts(user_language)

    await callback.message.edit_text(
        t.get("deals_header", "🔥 <b>Bugungi TOP chegirmalar</b>\n\n") + "⏳ Yuklanmoqda...",
        parse_mode="HTML",
    )

    try:
        deals = await deals_service.get_top_deals(db, limit=10)
        text = deals_service.format_deals_post(deals, user_language)

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(
            InlineKeyboardButton(
                text=t.get("btn_back", "◀️ Orqaga"),
                callback_data="menu:main",
            )
        )

        await callback.message.edit_text(
            text,
            reply_markup=kb_builder.as_markup(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Deals handler error: {e}")
        await callback.message.edit_text(
            t.get("no_deals", "😔 Bugun chegirmalar topilmadi."),
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data == "admin:post_deals")
async def cb_post_deals_to_channel(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    from bot.config import ADMIN_IDS
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return

    try:
        await deals_service.send_daily_deals(callback.bot, db)
        await callback.answer("✅ Kanalga yuborildi!", show_alert=True)
    except Exception as e:
        logger.error(f"Post deals error: {e}")
        await callback.answer("❌ Xatolik yuz berdi", show_alert=True)
