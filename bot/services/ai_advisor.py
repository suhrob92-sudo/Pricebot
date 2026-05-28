import logging
import json
import aiohttp

logger = logging.getLogger(__name__)

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"


class AIAdvisor:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def get_advice(self, query: str, language: str = "uz") -> str:
        if not self.api_key:
            return self._fallback_advice(query, language)

        try:
            if language == "uz":
                system_prompt = (
                    "Sen O'zbekiston bozori uchun aqlli xarid maslahatchiisan. "
                    "Foydalanuvchi so'roviga ko'ra 3-5 ta mahsulot tavsiya qil. "
                    "Har bir tavsiyada: mahsulot nomi, narx diapazoni (so'mda), asosiy afzalliklari, "
                    "va qayerdan sotib olish mumkinligi (Uzum, Olcha, Texnomart) ko'rsatilsin. "
                    "Javob qisqa, Telegram HTML formatida bo'lsin (faqat <b>, <i> teglar)."
                )
                user_prompt = f"Menga bunday mahsulot tavsiya qil: {query}"
            else:
                system_prompt = (
                    "Ты умный помощник по покупкам для рынка Узбекистана. "
                    "По запросу пользователя порекомендуй 3-5 товаров. "
                    "Для каждой рекомендации: название, ценовой диапазон (в сумах), "
                    "преимущества, где купить (Uzum, Olcha, Texnomart). "
                    "Краткий ответ в Telegram HTML (только <b>, <i>)."
                )
                user_prompt = f"Порекомендуй мне: {query}"

            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    CLAUDE_API_URL,
                    headers=headers,
                    data=json.dumps(payload),
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["content"][0]["text"]
                    else:
                        logger.error(f"Claude API error {resp.status}")
                        return self._fallback_advice(query, language)

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
                f"📌 AI funksiyasi uchun ANTHROPIC_API_KEY kerak."
            )
        return (
            f"🤖 <b>AI советник</b>\n\n"
            f"По запросу «{query}»:\n\n"
            f"💡 Советы:\n"
            f"• Сравните цены на Uzum Market и Olcha.uz\n"
            f"• На Texnomart.uz часто бывают скидки\n"
            f"• Добавьте в отслеживание и ждите снижения цены\n\n"
            f"📌 Для AI нужен ANTHROPIC_API_KEY."
        )
