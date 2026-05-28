import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import get_main_menu, get_language_keyboard, get_settings_keyboard

logger = logging.getLogger(__name__)
router = Router()


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


@router.message(CommandStart())
async def cmd_start(message: Message, db, user_language: str = "uz", state: FSMContext = None, **kwargs):
    if state:
        await state.clear()
    t = get_texts(user_language)
    name = message.from_user.full_name or message.from_user.username or "Foydalanuvchi"
    await message.answer(
        t["welcome"].format(name=name),
        reply_markup=get_main_menu(user_language),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def cmd_help(message: Message, user_language: str = "uz", **kwargs):
    t = get_texts(user_language)
    await message.answer(
        t.get("help_text", t["welcome"].format(name="")),
        reply_markup=get_main_menu(user_language),
        parse_mode="HTML",
    )


@router.message(Command("language"))
async def cmd_language(message: Message, **kwargs):
    await message.answer(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=get_language_keyboard(),
    )


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, user_language: str = "uz", state: FSMContext = None, **kwargs):
    if state:
        await state.clear()
    t = get_texts(user_language)
    await callback.message.edit_text(
        t["main_menu"],
        reply_markup=get_main_menu(user_language),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "menu:settings")
async def cb_settings(callback: CallbackQuery, user_language: str = "uz", **kwargs):
    t = get_texts(user_language)
    await callback.message.edit_text(
        t.get("settings_menu", "⚙️ Sozlamalar"),
        reply_markup=get_settings_keyboard(user_language),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "settings:language")
async def cb_change_language(callback: CallbackQuery, **kwargs):
    await callback.message.edit_text(
        "🌐 Tilni tanlang / Выберите язык:",
        reply_markup=get_language_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def cb_set_language(callback: CallbackQuery, db, **kwargs):
    lang = callback.data.split(":")[1]
    if lang not in ["uz", "ru"]:
        await callback.answer("❌ Noto'g'ri til")
        return

    await db.update_user_language(callback.from_user.id, lang)

    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if lang == "uz" else RU

    await callback.message.edit_text(
        t["language_set"],
        reply_markup=get_main_menu(lang),
        parse_mode="HTML",
    )
    await callback.answer()
