"""
Language/user helper utilities for python-telegram-bot v21.

In PTB v21 there is no middleware system like aiogram.
Instead, handlers retrieve the user language directly from the DB
using the helper function below.
"""
import logging

logger = logging.getLogger(__name__)


async def get_user_lang(db, telegram_id: int) -> str:
    """Return the stored language for a user, defaulting to 'uz'."""
    try:
        user = await db.get_user(telegram_id)
        return user["language"] if user and user.get("language") else "uz"
    except Exception as e:
        logger.error(f"get_user_lang error for {telegram_id}: {e}")
        return "uz"


async def ensure_user(db, telegram_user) -> dict:
    """Get-or-create DB record for a Telegram user and return it."""
    try:
        return await db.get_or_create_user(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            full_name=telegram_user.full_name,
        )
    except Exception as e:
        logger.error(f"ensure_user error for {telegram_user.id}: {e}")
        return {}
