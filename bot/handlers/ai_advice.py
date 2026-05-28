import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import get_back_keyboard

logger = logging.getLogger(__name__)
router = Router()


class AIStates(StatesGroup):
    waiting_query = State()


def get_texts(language: str) -> dict:
    from locales.uz import TEXTS as UZ
    from locales.ru import TEXTS as RU
    return UZ if language == "uz" else RU


@router.callback_query(F.data == "menu:ai")
async def cb_ai_menu(callback: CallbackQuery, state: FSMContext, user_language: str = "uz", **kwargs):
    t = get_texts(user_language)
    await state.set_state(AIStates.waiting_query)
    await callback.message.edit_text(
        t["ai_prompt"],
        reply_markup=get_back_keyboard(user_language, "menu:main"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AIStates.waiting_query)
async def handle_ai_query(message: Message, state: FSMContext, user_language: str = "uz", **kwargs):
    query = message.text.strip()
    if not query:
        return

    t = get_texts(user_language)
    thinking_msg = await message.answer(t["ai_thinking"], parse_mode="HTML")

    try:
        from bot.config import ANTHROPIC_API_KEY
        from bot.services.ai_advisor import AIAdvisor

        advisor = AIAdvisor(ANTHROPIC_API_KEY)
        response = await advisor.get_advice(query, user_language)

        await thinking_msg.delete()
        await message.answer(
            response,
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"AI advice handler error: {e}")
        await thinking_msg.delete()
        await message.answer(
            t.get("ai_error", "❌ Xatolik yuz berdi."),
            reply_markup=get_back_keyboard(user_language, "menu:main"),
            parse_mode="HTML",
        )
    finally:
        await state.clear()
