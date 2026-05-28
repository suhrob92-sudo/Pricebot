from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu(language: str = "uz") -> InlineKeyboardMarkup:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if language == "uz" else RU

    keyboard = [
        [
            InlineKeyboardButton(t["btn_search"], callback_data="menu:search"),
            InlineKeyboardButton(t["btn_track"], callback_data="menu:tracking"),
        ],
        [
            InlineKeyboardButton(t["btn_wishlist"], callback_data="menu:wishlist"),
            InlineKeyboardButton(t["btn_ai"], callback_data="menu:ai"),
        ],
        [
            InlineKeyboardButton(t["btn_deals"], callback_data="menu:deals"),
            InlineKeyboardButton(t["btn_settings"], callback_data="menu:settings"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang:uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
    ]]
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard(language: str = "uz") -> InlineKeyboardMarkup:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if language == "uz" else RU

    keyboard = [
        [InlineKeyboardButton(t["btn_language"], callback_data="settings:language")],
        [InlineKeyboardButton(t["btn_back"], callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(language: str = "uz", callback_data: str = "menu:main") -> InlineKeyboardMarkup:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if language == "uz" else RU

    keyboard = [[InlineKeyboardButton(t["btn_back"], callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistika", callback_data="admin:stats"),
            InlineKeyboardButton("📢 Xabar yuborish", callback_data="admin:broadcast"),
        ],
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin:users")],
        [InlineKeyboardButton("◀️ Orqaga", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(keyboard)
