import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AIAdvisor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if not self._client and self.api_key:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
        return self._client

    async def get_advice(self, query: str, language: str = "uz") -> str:
        client = self._get_client()
        if not client:
            return self._fallback_advice(query, language)

        try:
            if language == "uz":
                system_prompt = (
                    "Sen O'zbekiston bozori uchun aqlli xarid maslahatchiisan. "
                    "Foydalanuvchi so'roviga ko'ra 3-5 ta mahsulot tavsiya qil. "
                    "Har bir tavsiyada: mahsulot nomi, narx diapazoni (so'mda), asosiy afzalliklari, "
                    "va qayerdan sotib olish mumkinligi (Uzum, Olcha, Texnomart va h.k.) ko'rsatilsin. "
                    "Javob qisqa, aniq va Telegram HTML formatida bo'lsin (faqat <b>, <i>, <a> teglar). "
                    "Har bir tavsiyani alohida paragrafda ber."
                )
                user_prompt = f"Menga bunday mahsulot tavsiya qil: {query}"
            else:
                system_prompt = (
                    "Ты умный помощник по покупкам для рынка Узбекистана. "
                    "По запросу пользователя порекомендуй 3-5 товаров. "
                    "Для каждой рекомендации укажи: название товара, ценовой диапазон (в сумах), "
                    "основные преимущества, и где можно купить (Uzum, Olcha, Texnomart и т.д.). "
                    "Ответ должен быть кратким, четким и в формате Telegram HTML (только теги <b>, <i>). "
                    "Каждую рекомендацию давай в отдельном абзаце."
                )
                user_prompt = f"Порекомендуй мне: {query}"

            message = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text

        except Exception as e:
            logger.error(f"AI advisor error: {e}")
            return self._fallback_advice(query, language)

    def _fallback_advice(self, query: str, language: str) -> str:
        if language == "uz":
            return (
                f"🤖 <b>AI maslahat</b>\n\n"
                f"«{query}» so'rovi bo'yicha:\n\n"
                f"💡 Tavsiyalarim:\n"
                f"• Uzum Market va Olcha.uz da narxlarni solishtiring\n"
                f"• Texnomart.uz da ko'pincha chegirmalar bor\n"
                f"• Narx kuzatuviga qo'shing — tushishini kuting\n\n"
                f"📌 AI funksiyasi ishlashi uchun ANTHROPIC_API_KEY kerak."
            )
        return (
            f"🤖 <b>AI советник</b>\n\n"
            f"По запросу «{query}»:\n\n"
            f"💡 Советы:\n"
            f"• Сравните цены на Uzum Market и Olcha.uz\n"
            f"• На Texnomart.uz часто бывают скидки\n"
            f"• Добавьте в отслеживание и ждите снижения цены\n\n"
            f"📌 Для работы AI нужен ANTHROPIC_API_KEY."
        )
