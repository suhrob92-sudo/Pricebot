import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.config import ADMIN_IDS
from bot.keyboards.main_menu import get_admin_keyboard, get_back_keyboard

logger = logging.getLogger(__name__)
router = Router()


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_ban_id = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message, db, user_language: str = "uz", **kwargs):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Bu buyruq faqat adminlar uchun.")
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
    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery, db, **kwargs):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return

    stats = await db.get_admin_stats()
    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🔔 Kuzatuvlar: <b>{stats['active_trackings']}</b>\n"
        f"🔍 Bugun qidiruvlar: <b>{stats['today_searches']}</b>\n"
        f"🚫 Bloklangan: <b>{stats['banned_users']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast_prompt(callback: CallbackQuery, state: FSMContext, **kwargs):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_broadcast)
    await callback.message.answer(
        "📢 <b>Xabar yuborish</b>\n\nBarcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n/cancel — bekor qilish",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_broadcast)
async def handle_broadcast(message: Message, state: FSMContext, db, **kwargs):
    if not is_admin(message.from_user.id):
        return

    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi.")
        return

    users = await db.get_all_users()
    sent = 0
    failed = 0

    status_msg = await message.answer(f"⏳ Yuborilmoqda... 0/{len(users)}")

    for i, user in enumerate(users):
        if user.get("is_banned"):
            continue
        try:
            await message.bot.send_message(
                user["telegram_id"],
                message.text,
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

    await state.clear()
    await status_msg.edit_text(
        f"✅ Xabar yuborildi!\n\n"
        f"📤 Muvaffaqiyatli: <b>{sent}</b>\n"
        f"❌ Xatolik: <b>{failed}</b>",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:users")
async def cb_admin_users(callback: CallbackQuery, db, **kwargs):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Ruxsat yo'q", show_alert=True)
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

    await callback.message.edit_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("ban"))
async def cmd_ban(message: Message, db, **kwargs):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Foydalanish: /ban <user_id>")
        return

    try:
        target_id = int(parts[1])
        await db.ban_user(target_id)
        await message.answer(f"🚫 Foydalanuvchi {target_id} bloklandi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID format.")


@router.message(Command("unban"))
async def cmd_unban(message: Message, db, **kwargs):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Foydalanish: /unban <user_id>")
        return

    try:
        target_id = int(parts[1])
        await db.unban_user(target_id)
        await message.answer(f"✅ Foydalanuvchi {target_id} blokdan chiqarildi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID format.")
