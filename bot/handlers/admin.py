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
        except asyncio.TimeoutError:
            status = "⏱ Timeout (45s)"
        except Exception as e:
            status = f"❌ {str(e)[:40]}"
        lines.append(f"{scraper.MARKETPLACE_EMOJI} {scraper.MARKETPLACE_NAME}: {status}")

    await msg.edit_text("\n".join(lines), parse_mode="HTML")


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
        CallbackQueryHandler(cb_admin_stats, pattern=r"^admin:stats$"),
        CallbackQueryHandler(cb_admin_users, pattern=r"^admin:users$"),
        broadcast_conv,
    ]
