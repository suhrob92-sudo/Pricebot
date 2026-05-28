from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu(language: str = "uz") -> InlineKeyboardMarkup:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if language == "uz" else RU

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t["btn_search"], callback_data="menu:search"),
        InlineKeyboardButton(text=t["btn_track"], callback_data="menu:tracking"),
    )
    builder.row(
        InlineKeyboardButton(text=t["btn_wishlist"], callback_data="menu:wishlist"),
        InlineKeyboardButton(text=t["btn_ai"], callback_data="menu:ai"),
    )
    builder.row(
        InlineKeyboardButton(text=t["btn_deals"], callback_data="menu:deals"),
        InlineKeyboardButton(text=t["btn_settings"], callback_data="menu:settings"),
    )
    return builder.as_markup()


def get_language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
    )
    return builder.as_markup()


def get_settings_keyboard(language: str = "uz") -> InlineKeyboardMarkup:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if language == "uz" else RU

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t["btn_language"], callback_data="settings:language"),
    )
    builder.row(
        InlineKeyboardButton(text=t["btn_back"], callback_data="menu:main"),
    )
    return builder.as_markup()


def get_back_keyboard(language: str = "uz", callback_data: str = "menu:main") -> InlineKeyboardMarkup:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if language == "uz" else RU

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t["btn_back"], callback_data=callback_data),
    )
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats"),
        InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin:broadcast"),
    )
    builder.row(
        InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin:users"),
    )
    builder.row(
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="menu:main"),
    )
    return builder.as_markup()
