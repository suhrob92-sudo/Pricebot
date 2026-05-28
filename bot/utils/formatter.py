from datetime import datetime
from typing import Optional


def format_price(price: float, currency: str = "UZS") -> str:
    if currency == "UZS":
        return f"{price:,.0f} so'm".replace(",", " ")
    elif currency == "RUB":
        return f"₽{price:,.0f}".replace(",", " ")
    elif currency == "USD":
        return f"${price:,.2f}"
    return f"{price:,.0f} {currency}"


def format_date(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return dt_str


def format_short_date(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return dt_str


def truncate(text: str, max_len: int = 50) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def calc_discount(old_price: float, new_price: float) -> float:
    if old_price <= 0:
        return 0.0
    return round((old_price - new_price) / old_price * 100, 1)


def format_search_result(item: dict, language: str = "uz") -> str:
    name = truncate(item.get("name", "N/A"), 60)
    marketplace = item.get("marketplace", "")
    emoji = item.get("marketplace_emoji", "🏪")
    price = item.get("current_price", 0)
    currency = item.get("currency", "UZS")
    url = item.get("url", "")

    price_str = format_price(price, currency)
    line = f"{emoji} <b>{name}</b>\n   💰 {price_str}"
    if url:
        line += f" — <a href='{url}'>Ko'rish</a>"
    return line


def format_tracking_item(item: dict, language: str = "uz") -> str:
    name = truncate(item.get("name", "N/A"), 50)
    marketplace = item.get("marketplace", "")
    price = item.get("current_price", 0)
    currency = item.get("currency", "UZS")
    target = item.get("target_price")
    added_at = item.get("added_at", "")

    price_str = format_price(price, currency)
    target_str = format_price(target, currency) if target else ("Har qanday tushishda" if language == "uz" else "Любое снижение")

    return (
        f"📦 <b>{name}</b>\n"
        f"   📍 {marketplace}\n"
        f"   💰 {price_str}\n"
        f"   🎯 {target_str}"
    )


def format_price_history_table(history: list, language: str = "uz") -> str:
    if not history:
        return ""
    lines = []
    for record in history[-10:]:
        date = format_short_date(record.get("recorded_at", ""))
        price = format_price(record.get("price", 0))
        lines.append(f"  📅 {date}: <b>{price}</b>")
    return "\n".join(lines)


def get_marketplace_emoji(marketplace: str) -> str:
    emojis = {
        "uzum": "🟠",
        "olcha": "🔴",
        "texnomart": "🔵",
        "mediapark": "🟢",
        "ozon": "🟣",
        "wildberries": "🩷",
    }
    return emojis.get(marketplace.lower(), "🏪")
