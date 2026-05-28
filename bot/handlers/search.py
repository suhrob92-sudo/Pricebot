import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import get_back_keyboard
from bot.services.price_comparator import PriceComparator

logger = logging.getLogger(__name__)
router = Router()
comparator = PriceComparator()


class SearchStates(StatesGroup):
    waiting_query = State()


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


@router.callback_query(F.data == "menu:search")
async def cb_search_menu(callback: CallbackQuery, state: FSMContext, user_language: str = "uz", **kwargs):
    t = get_texts(user_language)
    await state.set_state(SearchStates.waiting_query)
    await callback.message.edit_text(
        t["search_prompt"],
        reply_markup=get_back_keyboard(user_language, "menu:main"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SearchStates.waiting_query)
async def handle_search_query(message: Message, state: FSMContext, db, user_language: str = "uz", **kwargs):
    query = message.text.strip()
    if not query or len(query) < 2:
        t = get_texts(user_language)
        await message.answer(t.get("error_general", "❌ Xatolik"), parse_mode="HTML")
        return

    t = get_texts(user_language)
    searching_msg = await message.answer(t["searching"], parse_mode="HTML")

    try:
        search_data = await comparator.search_all(query)
        results = search_data.get("results", [])
        total = search_data.get("total", 0)

        await db.save_search(message.from_user.id, query, total)

        await searching_msg.delete()

        if not results:
            await message.answer(
                t["no_results"].format(query=query),
                reply_markup=get_back_keyboard(user_language, "menu:main"),
                parse_mode="HTML",
            )
            await state.clear()
            return

        text = comparator.format_results_text(search_data, user_language)

        saved_ids = []
        for r in results:
            pid = await db.save_product(
                name=r.name,
                marketplace=r.marketplace,
                url=r.url,
                image_url=r.image_url,
                price=r.price,
                currency=r.currency,
            )
            r.id = pid
            saved_ids.append(pid)

        await state.update_data(last_results=saved_ids, last_query=query)

        from bot.keyboards.inline_kb import get_results_navigation_keyboard
        kb = get_results_navigation_keyboard(
            [{"id": r.id, "name": r.name} for r in results if r.id],
            user_language, 0, query
        )

        await message.answer(text, reply_markup=kb, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Search handler error: {e}")
        await searching_msg.delete()
        t = get_texts(user_language)
        await message.answer(
            t.get("error_general", "❌ Xatolik yuz berdi."),
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )
    finally:
        await state.clear()


@router.callback_query(F.data.startswith("product:view:"))
async def cb_product_view(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    product_id = int(callback.data.split(":")[2])
    product = await db.get_product(product_id)

    if not product:
        await callback.answer("❌ Mahsulot topilmadi", show_alert=True)
        return

    from bot.utils.formatter import format_price, get_marketplace_emoji
    from bot.keyboards.inline_kb import get_product_actions_keyboard

    t = get_texts(user_language)
    price_str = format_price(product["current_price"], product.get("currency", "UZS"))
    emoji = get_marketplace_emoji(product["marketplace"])

    text = (
        f"{emoji} <b>{product['name']}</b>\n\n"
        f"📍 {product['marketplace']}\n"
        f"💰 <b>{price_str}</b>\n"
    )
    if product.get("url"):
        text += f"🔗 <a href='{product['url']}'>Ko'rish</a>"

    await callback.message.answer(
        text,
        reply_markup=get_product_actions_keyboard(product_id, user_language),
        parse_mode="HTML",
    )
    await callback.answer()
