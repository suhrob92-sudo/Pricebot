import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.keyboards.main_menu import get_back_keyboard
from bot.utils.formatter import format_price_history_table, format_price

logger = logging.getLogger(__name__)
router = Router()


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


@router.callback_query(F.data.startswith("history:show:"))
async def cb_show_history(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    product_id = int(callback.data.split(":")[2])
    t = get_texts(user_language)

    product = await db.get_product(product_id)
    if not product:
        await callback.answer("❌ Mahsulot topilmadi", show_alert=True)
        return

    history = await db.get_price_history(product_id, days=90)

    if not history:
        await callback.message.answer(
            t.get("no_history", "📭 Narx tarixi mavjud emas."),
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    name = product["name"][:50]
    marketplace = product["marketplace"]
    current_price = format_price(product["current_price"], product.get("currency", "UZS"))

    history_table = format_price_history_table(history, user_language)

    if len(history) >= 2:
        oldest = history[0]["price"]
        newest = history[-1]["price"]
        if oldest > newest:
            trend = "📉 Narx tushdi" if user_language == "uz" else "📉 Цена снизилась"
        elif oldest < newest:
            trend = "📈 Narx ko'tarildi" if user_language == "uz" else "📈 Цена выросла"
        else:
            trend = "➡️ Narx o'zgarmadi" if user_language == "uz" else "➡️ Цена не изменилась"
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

    await callback.message.answer(
        text,
        reply_markup=get_back_keyboard(user_language, "menu:main"),
        parse_mode="HTML",
    )
    await callback.answer()
