from typing import List, Dict, Any
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

ITEMS_PER_PAGE = 5


def get_text(key: str, language: str) -> str:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    t = UZ if language == "uz" else RU
    return t.get(key, key)


def get_search_results_keyboard(
    products: List[Dict[str, Any]], user_language: str = "uz"
) -> InlineKeyboardMarkup:
    rows = []
    for i, product in enumerate(products[:10]):
        product_id = product.get("id", i)
        name = product.get("name", "Unknown")[:30]
        marketplace = product.get("marketplace", "")
        rows.append([InlineKeyboardButton(
            f"📦 {name} ({marketplace})",
            callback_data=f"product:view:{product_id}",
        )])
    rows.append([InlineKeyboardButton(
        get_text("btn_back", user_language), callback_data="menu:main"
    )])
    return InlineKeyboardMarkup(rows)


def get_product_actions_keyboard(
    product_id: int, language: str = "uz"
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(get_text("btn_add_track", language), callback_data=f"track:add:{product_id}"),
            InlineKeyboardButton(get_text("btn_add_wish", language), callback_data=f"wish:add:{product_id}"),
        ],
        [InlineKeyboardButton(get_text("btn_history", language), callback_data=f"history:show:{product_id}")],
        [InlineKeyboardButton(get_text("btn_back", language), callback_data="menu:search")],
    ]
    return InlineKeyboardMarkup(rows)


def get_tracking_list_keyboard(
    tracked_items: List[Dict[str, Any]], language: str = "uz", page: int = 0
) -> InlineKeyboardMarkup:
    rows = []
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = tracked_items[start:end]

    for item in page_items:
        tracking_id = item.get("tracking_id", 0)
        name = item.get("name", "Unknown")[:25]
        rows.append([InlineKeyboardButton(
            f"🗑 {name}",
            callback_data=f"track:remove:{tracking_id}",
        )])

    nav_buttons = []
    total_pages = (len(tracked_items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            get_text("btn_prev", language),
            callback_data=f"track:page:{page - 1}",
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            get_text("btn_next", language),
            callback_data=f"track:page:{page + 1}",
        ))
    if nav_buttons:
        rows.append(nav_buttons)

    rows.append([InlineKeyboardButton(get_text("btn_back", language), callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def get_wishlist_keyboard(
    items: List[Dict[str, Any]], language: str = "uz", page: int = 0
) -> InlineKeyboardMarkup:
    rows = []
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = items[start:end]

    for item in page_items:
        wish_id = item.get("id", 0)
        name = item.get("product_name", "Unknown")[:25]
        rows.append([InlineKeyboardButton(
            f"🗑 {name}",
            callback_data=f"wish:remove:{wish_id}",
        )])

    nav_buttons = []
    total_pages = (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            get_text("btn_prev", language),
            callback_data=f"wish:page:{page - 1}",
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            get_text("btn_next", language),
            callback_data=f"wish:page:{page + 1}",
        ))
    if nav_buttons:
        rows.append(nav_buttons)

    rows.append([InlineKeyboardButton(get_text("btn_back", language), callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def get_deals_keyboard(
    deals: List[Dict[str, Any]], language: str = "uz"
) -> InlineKeyboardMarkup:
    rows = []
    for deal in deals[:5]:
        product_id = deal.get("id", 0)
        name = deal.get("name", "Unknown")[:25]
        discount = deal.get("discount", 0)
        rows.append([InlineKeyboardButton(
            f"🔥 {name} (-{discount}%)",
            callback_data=f"product:view:{product_id}",
        )])
    rows.append([InlineKeyboardButton(get_text("btn_back", language), callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def get_results_navigation_keyboard(
    results: List[Dict[str, Any]],
    language: str = "uz",
    page: int = 0,
    query: str = "",
) -> InlineKeyboardMarkup:
    rows = []
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_items = results[start:end]

    for item in page_items:
        product_id = item.get("id", 0)
        name = item.get("name", "Unknown")[:28]
        rows.append([InlineKeyboardButton(
            f"📦 {name}",
            callback_data=f"product:view:{product_id}",
        )])

    nav_buttons = []
    total_pages = (len(results) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            get_text("btn_prev", language),
            callback_data=f"search:page:{page - 1}",
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            get_text("btn_next", language),
            callback_data=f"search:page:{page + 1}",
        ))
    if nav_buttons:
        rows.append(nav_buttons)

    rows.append([InlineKeyboardButton(get_text("btn_back", language), callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)
