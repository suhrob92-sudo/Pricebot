import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger(__name__)


class LanguageMiddleware(BaseMiddleware):
    def __init__(self, db):
        self.db = db
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        telegram_user = None

        if isinstance(event, Message):
            telegram_user = event.from_user
        elif isinstance(event, CallbackQuery):
            telegram_user = event.from_user

        if telegram_user:
            try:
                db_user = await self.db.get_or_create_user(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    full_name=telegram_user.full_name,
                )
                user = db_user

                if db_user.get("is_banned"):
                    from locales.uz import TEXTS as UZ
                    from locales.ru import TEXTS as RU
                    lang = db_user.get("language", "uz")
                    t = UZ if lang == "uz" else RU
                    if isinstance(event, Message):
                        await event.answer(t["banned_message"])
                    elif isinstance(event, CallbackQuery):
                        await event.answer(t["banned_message"], show_alert=True)
                    return

                data["user_language"] = db_user.get("language", "uz")
                data["db_user"] = db_user
            except Exception as e:
                logger.error(f"Middleware error for user {telegram_user.id}: {e}")
                data["user_language"] = "uz"
                data["db_user"] = None
        else:
            data["user_language"] = "uz"
            data["db_user"] = None

        data["db"] = self.db
        return await handler(event, data)
