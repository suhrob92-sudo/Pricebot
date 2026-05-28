import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import get_back_keyboard

logger = logging.getLogger(__name__)
router = Router()


class TrackingStates(StatesGroup):
    waiting_target_price = State()


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


@router.callback_query(F.data == "menu:tracking")
async def cb_tracking_menu(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    t = get_texts(user_language)
    user_id = callback.from_user.id
    tracked = await db.get_user_tracked_products(user_id)

    if not tracked:
        await callback.message.edit_text(
            t["no_tracking"],
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    from bot.keyboards.inline_kb import get_tracking_list_keyboard
    from bot.utils.formatter import format_tracking_item

    text = t["tracking_list"]
    for item in tracked[:5]:
        text += format_tracking_item(item, user_language) + "\n\n"

    kb = get_tracking_list_keyboard(tracked, user_language, page=0)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("track:add:"))
async def cb_track_add(callback: CallbackQuery, db, user_language: str = "uz", state: FSMContext = None, **kwargs):
    product_id = int(callback.data.split(":")[2])
    t = get_texts(user_language)
    user_id = callback.from_user.id

    from bot.config import MAX_TRACKED_PRODUCTS
    tracked = await db.get_user_tracked_products(user_id)
    if len(tracked) >= MAX_TRACKED_PRODUCTS:
        await callback.answer(
            t["track_limit"].format(limit=MAX_TRACKED_PRODUCTS),
            show_alert=True,
        )
        return

    success = await db.add_tracked_product(user_id, product_id, target_price=None)
    if success:
        await callback.answer(t["track_added"], show_alert=True)
    else:
        await callback.answer(t.get("already_tracking", "ℹ️ Allaqachon kuzatilmoqda"), show_alert=True)


@router.callback_query(F.data.startswith("track:remove:"))
async def cb_track_remove(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    tracking_id = int(callback.data.split(":")[2])
    t = get_texts(user_language)
    user_id = callback.from_user.id

    await db.remove_tracked_product(tracking_id, user_id)
    await callback.answer(t.get("tracking_removed", "✅ O'chirildi"), show_alert=True)

    tracked = await db.get_user_tracked_products(user_id)
    if not tracked:
        await callback.message.edit_text(
            t["no_tracking"],
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )
        return

    from bot.keyboards.inline_kb import get_tracking_list_keyboard
    from bot.utils.formatter import format_tracking_item

    text = t["tracking_list"]
    for item in tracked[:5]:
        text += format_tracking_item(item, user_language) + "\n\n"

    kb = get_tracking_list_keyboard(tracked, user_language, page=0)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("track:page:"))
async def cb_track_page(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    page = int(callback.data.split(":")[2])
    t = get_texts(user_language)
    user_id = callback.from_user.id

    tracked = await db.get_user_tracked_products(user_id)
    if not tracked:
        await callback.answer()
        return

    from bot.keyboards.inline_kb import get_tracking_list_keyboard
    from bot.utils.formatter import format_tracking_item

    start = page * 5
    text = t["tracking_list"]
    for item in tracked[start:start + 5]:
        text += format_tracking_item(item, user_language) + "\n\n"

    kb = get_tracking_list_keyboard(tracked, user_language, page=page)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()
