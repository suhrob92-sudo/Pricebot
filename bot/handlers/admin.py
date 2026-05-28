import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from bot.config import ADMIN_IDS
from bot.keyboards.main_menu import get_admin_keyboard, get_back_keyboard

logger = logging.getLogger(__name__)

BROADCAST_MSG = 1


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun.")
        return

    db = context.application.bot_data.get("db")
    if not db:
        await update.message.reply_text("❌ DB xatolik")
        return

    stats = await db.get_admin_stats()
    text = (
        f"👨‍💼 <b>Admin panel</b>\n\n"
        f"📊 Statistika:\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🔔 Kuzatuvlar: <b>{stats['active_trackings']}</b>\n"
        f"🔍 Bugun qidiruvlar: <b>{stats['today_searches']}</b>\n"
        f"🚫 Bloklangan: <b>{stats['banned_users']}</b>"
    )
    await update.message.reply_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")


async def cb_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("❌ Ruxsat yo'q", show_alert=True)
        return

    db = context.application.bot_data.get("db")
    if not db:
        await query.answer("❌ DB xatolik", show_alert=True)
        return

    stats = await db.get_admin_stats()
    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🔔 Kuzatuvlar: <b>{stats['active_trackings']}</b>\n"
        f"🔍 Bugun qidiruvlar: <b>{stats['today_searches']}</b>\n"
        f"🚫 Bloklangan: <b>{stats['banned_users']}</b>"
    )
    await query.edit_message_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")


async def cb_broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("❌ Ruxsat yo'q", show_alert=True)
        return ConversationHandler.END

    await query.message.reply_text(
        "📢 <b>Xabar yuborish</b>\n\nBarcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n/cancel — bekor qilish",
        parse_mode="HTML",
    )
    return BROADCAST_MSG


async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    db = context.application.bot_data.get("db")
    if not db:
        await update.message.reply_text("❌ DB xatolik")
        return ConversationHandler.END

    users = await db.get_all_users()
    sent = 0
    failed = 0

    status_msg = await update.message.reply_text(f"⏳ Yuborilmoqda... 0/{len(users)}")

    for i, user in enumerate(users):
        if user.get("is_banned"):
            continue
        try:
            await context.bot.send_message(
                user["telegram_id"],
                update.message.text,
                parse_mode="HTML",
            )
            sent += 1
        except Exception:
            failed += 1

        if (i + 1) % 20 == 0:
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... {i + 1}/{len(users)}")
            except Exception:
                pass

    try:
        await status_msg.edit_text(
            f"✅ Xabar yuborildi!\n\n"
            f"📤 Muvaffaqiyatli: <b>{sent}</b>\n"
            f"❌ Xatolik: <b>{failed}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


async def cb_admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.answer("❌ Ruxsat yo'q", show_alert=True)
        return

    db = context.application.bot_data.get("db")
    if not db:
        await query.answer("❌ DB xatolik", show_alert=True)
        return

    users = await db.get_all_users()
    lines = []
    for u in users[:20]:
        status = "🚫" if u.get("is_banned") else "✅"
        name = u.get("full_name") or u.get("username") or f"ID:{u['telegram_id']}"
        lines.append(f"{status} {name} — <code>{u['telegram_id']}</code>")

    text = f"👥 <b>Foydalanuvchilar</b> (jami: {len(users)}):\n\n" + "\n".join(lines)
    if len(users) > 20:
        text += f"\n\n... va yana {len(users) - 20} ta"

    await query.edit_message_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )


async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    db = context.application.bot_data.get("db")
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ Foydalanish: /ban <user_id>")
        return

    try:
        target_id = int(parts[1])
        if db:
            await db.ban_user(target_id)
        await update.message.reply_text(f"🚫 Foydalanuvchi {target_id} bloklandi.")
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri ID format.")


async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    db = context.application.bot_data.get("db")
    parts = update.message.text.split()
    if len(parts) < 2:
        await update.message.reply_text("❌ Foydalanish: /unban <user_id>")
        return

    try:
        target_id = int(parts[1])
        if db:
            await db.unban_user(target_id)
        await update.message.reply_text(f"✅ Foydalanuvchi {target_id} blokdan chiqarildi.")
    except ValueError:
        await update.message.reply_text("❌ Noto'g'ri ID format.")


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return

    from bot.config import SCRAPERAPI_KEY
    key_status = f"✅ Set ({SCRAPERAPI_KEY[:8]}...)" if SCRAPERAPI_KEY else "❌ Not set"
    msg = await update.message.reply_text(
        f"🔍 Scraperlar tekshirilmoqda...\n🔑 ScraperAPI: {key_status}",
        parse_mode="HTML",
    )

    from bot.services.price_comparator import PriceComparator
    import asyncio

    comp = PriceComparator()
    lines = [f"🔑 ScraperAPI: {key_status}\n"]

    for scraper in comp.scrapers:
        try:
            results = await asyncio.wait_for(scraper.search("iphone"), timeout=45)
            status = f"✅ {len(results)} natija"
            if results:
                status += f" | {results[0].name[:25]}... {results[0].price:,.0f}"
        except asyncio.TimeoutError:
            status = "⏱ Timeout (45s)"
        except Exception as e:
            status = f"❌ {str(e)[:40]}"
        lines.append(f"{scraper.MARKETPLACE_EMOJI} {scraper.MARKETPLACE_NAME}: {status}")

    await msg.edit_text("\n".join(lines), parse_mode="HTML")


async def cmd_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Deep diagnostic: raw HTTP check per site, updates message after each."""
    if not is_admin(update.effective_user.id):
        return

    import asyncio
    import json as _json
    import aiohttp
    from urllib.parse import quote as _quote
    from bot.config import SCRAPERAPI_KEY

    msg = await update.message.reply_text(
        f"🔬 Diagnostika boshlandi...\n🔑 ScraperAPI: {'✅' if SCRAPERAPI_KEY else '❌'}",
    )

    sites = [
        ("🟠 Uzum", "https://uzum.uz/search?keyword=iphone"),
        ("🔴 Olcha", "https://olcha.uz/search/iphone"),
        ("🔵 Texnomart", "https://texnomart.uz/search?query=iphone"),
        ("🟢 Mediapark", "https://mediapark.uz/search?q=iphone"),
        ("🩷 WB", "https://search.wb.ru/exactmatch/ru/common/v5/search?query=iphone&resultset=catalog&limit=5&sort=popular&page=1&appType=1&curr=rub&lang=ru&locale=ru&spp=27"),
        ("🟣 Ozon", "https://www.ozon.ru/search/?text=iphone&from_global=true"),
    ]

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    done: list[str] = []

    for name, url in sites:
        proxy_url = (
            f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={_quote(url, safe='')}"
            if SCRAPERAPI_KEY else url
        )
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(headers=req_headers) as session:
                async with session.get(proxy_url, timeout=timeout) as resp:
                    http_status = resp.status
                    # Read at most 200KB to avoid memory issues
                    raw_bytes = await resp.content.read(200 * 1024)
                    raw = raw_bytes.decode("utf-8", errors="replace")
                    size_kb = len(raw) // 1024

                    if "wb.ru" in url:
                        try:
                            d = _json.loads(raw)
                            prods = (d.get("data", {}).get("products") or
                                     d.get("catalog", {}).get("products") or [])
                            line = f"{name}: {http_status} | {size_kb}KB | {len(prods)} mahsulot"
                        except Exception:
                            line = f"{name}: {http_status} | {size_kb}KB | JSON xato"
                    elif "__NEXT_DATA__" in raw:
                        # Simple key extraction — no regex, just string split
                        start = raw.find('"pageProps":{') + len('"pageProps":')
                        if start > len('"pageProps":'):
                            chunk = raw[start:start + 300]
                            # grab first few key names
                            import re as _re
                            keys = _re.findall(r'"(\w+)":', chunk)[:6]
                            line = f"{name}: {http_status} | {size_kb}KB | NEXT✅ | keys={keys}"
                        else:
                            line = f"{name}: {http_status} | {size_kb}KB | NEXT✅ (no pageProps)"
                    else:
                        # Show page title or first 60 chars
                        t_start = raw.find("<title>")
                        t_end = raw.find("</title>")
                        title = raw[t_start + 7:t_end][:50] if t_start >= 0 else raw[:60]
                        line = f"{name}: {http_status} | {size_kb}KB | NO NEXT | {title}"
            done.append(line)
        except asyncio.TimeoutError:
            done.append(f"{name}: ⏱ Timeout 20s")
        except Exception as e:
            done.append(f"{name}: ❌ {str(e)[:50]}")

        try:
            await msg.edit_text(
                f"🔬 Diagnostika ({len(done)}/{len(sites)}):\n" + "\n".join(done)
            )
        except Exception:
            pass

    try:
        await msg.edit_text("🔬 Natija:\n" + "\n".join(done))
    except Exception:
        pass


def get_handlers():
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_broadcast_prompt, pattern=r"^admin:broadcast$")],
        states={
            BROADCAST_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_broadcast),
        ],
        per_message=False,
    )
    return [
        CommandHandler("admin", cmd_admin),
        CommandHandler("ban", cmd_ban),
        CommandHandler("unban", cmd_unban),
        CommandHandler("debug", cmd_debug),
        CommandHandler("diagnose", cmd_diagnose),
        CallbackQueryHandler(cb_admin_stats, pattern=r"^admin:stats$"),
        CallbackQueryHandler(cb_admin_users, pattern=r"^admin:users$"),
        broadcast_conv,
    ]
