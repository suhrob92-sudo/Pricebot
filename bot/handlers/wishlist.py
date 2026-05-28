import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.config import MAX_WISHLIST_ITEMS
from bot.keyboards.main_menu import get_back_keyboard
from bot.keyboards.inline_kb import get_wishlist_keyboard

logger = logging.getLogger(__name__)
router = Router()


class WishlistStates(StatesGroup):
    waiting_product_name = State()


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


@router.callback_query(F.data == "menu:wishlist")
async def cb_wishlist_menu(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    t = get_texts(user_language)
    user_id = callback.from_user.id
    items = await db.get_user_wishlist(user_id)

    if not items:
        await callback.message.edit_text(
            t["no_wishlist"],
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    header = t.get("wishlist_header", "📋 <b>Mening ro'yxatim</b>\n\n")
    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"{i}. 📦 <b>{item['product_name']}</b>")

    text = header + "\n".join(lines)
    text += f"\n\n📊 {len(items)}/{MAX_WISHLIST_ITEMS}"

    add_label = "➕ Qo'shish" if user_language == "uz" else "➕ Добавить"
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb_builder = InlineKeyboardBuilder()
    for item in items[:8]:
        kb_builder.row(
            InlineKeyboardButton(
                text=f"🗑 {item['product_name'][:25]}",
                callback_data=f"wish:remove:{item['id']}",
            )
        )
    kb_builder.row(
        InlineKeyboardButton(text=add_label, callback_data="wish:add_new"),
        InlineKeyboardButton(text=t.get("btn_back", "◀️ Orqaga"), callback_data="menu:main"),
    )

    await callback.message.edit_text(text, reply_markup=kb_builder.as_markup(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "wish:add_new")
async def cb_wishlist_add_new(callback: CallbackQuery, state: FSMContext, user_language: str = "uz", **kwargs):
    t = get_texts(user_language)
    await state.set_state(WishlistStates.waiting_product_name)
    await callback.message.answer(
        t["wishlist_prompt"],
        reply_markup=get_back_keyboard(user_language, "menu:wishlist"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("wish:add:"))
async def cb_add_to_wishlist(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    product_id = int(callback.data.split(":")[2])
    t = get_texts(user_language)
    user_id = callback.from_user.id

    product = await db.get_product(product_id)
    if not product:
        await callback.answer("❌ Mahsulot topilmadi", show_alert=True)
        return

    success = await db.add_to_wishlist(user_id, product["name"])
    if success:
        await callback.answer(t["wishlist_added"].format(name=product["name"][:30]), show_alert=True)
    else:
        await callback.answer(t.get("wishlist_limit", "⚠️ Ro'yxat to'ldi"), show_alert=True)


@router.message(WishlistStates.waiting_product_name)
async def handle_wishlist_input(message: Message, state: FSMContext, db, user_language: str = "uz", **kwargs):
    product_name = message.text.strip()
    t = get_texts(user_language)
    user_id = message.from_user.id

    if not product_name or len(product_name) < 2:
        await message.answer(t.get("error_general", "❌ Xatolik"), parse_mode="HTML")
        return

    success = await db.add_to_wishlist(user_id, product_name)

    if success:
        await message.answer(
            t["wishlist_added"].format(name=product_name),
            reply_markup=get_back_keyboard(user_language, "menu:wishlist"),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            t.get("wishlist_limit", "⚠️ Ro'yxat to'ldi."),
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )

    await state.clear()


@router.callback_query(F.data.startswith("wish:remove:"))
async def cb_remove_from_wishlist(callback: CallbackQuery, db, user_language: str = "uz", **kwargs):
    wish_id = int(callback.data.split(":")[2])
    t = get_texts(user_language)
    user_id = callback.from_user.id

    await db.remove_from_wishlist(wish_id, user_id)
    await callback.answer(t.get("wishlist_removed", "✅ O'chirildi"), show_alert=True)

    items = await db.get_user_wishlist(user_id)
    if not items:
        await callback.message.edit_text(
            t["no_wishlist"],
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )
    else:
        header = t.get("wishlist_header", "📋 <b>Mening ro'yxatim</b>\n\n")
        lines = [f"{i}. 📦 <b>{item['product_name']}</b>" for i, item in enumerate(items, 1)]
        text = header + "\n".join(lines)

        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb_builder = InlineKeyboardBuilder()
        for item in items[:8]:
            kb_builder.row(
                InlineKeyboardButton(
                    text=f"🗑 {item['product_name'][:25]}",
                    callback_data=f"wish:remove:{item['id']}",
                )
            )
        add_label = "➕ Qo'shish" if user_language == "uz" else "➕ Добавить"
        kb_builder.row(
            InlineKeyboardButton(text=add_label, callback_data="wish:add_new"),
            InlineKeyboardButton(text=t.get("btn_back", "◀️"), callback_data="menu:main"),
        )
        await callback.message.edit_text(text, reply_markup=kb_builder.as_markup(), parse_mode="HTML")
