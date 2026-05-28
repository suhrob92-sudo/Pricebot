import asyncio
import logging
from typing import Dict, List, Optional, Any

from bot.services.scrapers.base import ProductResult
from bot.services.scrapers.uzum import UzumScraper
from bot.services.scrapers.olcha import OlchaScraper
from bot.services.scrapers.texnomart import TexnomartScraper
from bot.services.scrapers.mediapark import MediaparkScraper
from bot.services.scrapers.ozon import OzonScraper
from bot.services.scrapers.wildberries import WildberriesScraper

logger = logging.getLogger(__name__)

UZS_TO_RUB_RATE = 0.0085


class PriceComparator:
    def __init__(self):
        self.scrapers = [
            UzumScraper(),
            OlchaScraper(),
            TexnomartScraper(),
            MediaparkScraper(),
            OzonScraper(),
            WildberriesScraper(),
        ]

    async def search_all(self, query: str) -> Dict[str, Any]:
        tasks = [self._safe_search(scraper, query) for scraper in self.scrapers]
        all_results_nested = await asyncio.gather(*tasks, return_exceptions=False)

        all_results: List[ProductResult] = []
        for results in all_results_nested:
            if results:
                all_results.extend(results)

        if not all_results:
            return {"results": [], "cheapest": None, "total": 0}

        sorted_results = sorted(all_results, key=lambda r: self._normalize_price(r))
        cheapest = sorted_results[0] if sorted_results else None

        return {
            "results": sorted_results,
            "cheapest": cheapest,
            "total": len(sorted_results),
        }

    async def _safe_search(self, scraper, query: str) -> List[ProductResult]:
        try:
            results = await asyncio.wait_for(scraper.search(query), timeout=12.0)
            return results or []
        except asyncio.TimeoutError:
            logger.warning(f"{scraper.MARKETPLACE_KEY}: search timed out")
            return []
        except Exception as e:
            logger.error(f"{scraper.MARKETPLACE_KEY}: search failed: {e}")
            return []

    def _normalize_price(self, result: ProductResult) -> float:
        if result.currency == "RUB":
            return result.price / UZS_TO_RUB_RATE
        return result.price

    def get_cheapest(self, results: List[ProductResult]) -> Optional[ProductResult]:
        if not results:
            return None
        return min(results, key=lambda r: self._normalize_price(r))

    def format_results_text(self, results: Dict[str, Any], query: str, language: str = "uz") -> str:
        from locales.uz import TEXTS as UZ
        from locales.ru import TEXTS as RU
        t = UZ if language == "uz" else RU

        if not results.get("results"):
            return t["no_results"].format(query=query)

        text = t["results_header"].format(query=query)
        items = results["results"][:8]

        for i, product in enumerate(items, 1):
            price_str = product.formatted_price()
            name = product.name[:60]
            text += (
                f"{i}. {product.marketplace_emoji} <b>{name}</b>\n"
                f"   💰 {price_str}\n"
                f"   🔗 <a href='{product.url}'>{product.marketplace}</a>\n\n"
            )

        if results.get("cheapest"):
            cheapest = results["cheapest"]
            text += t["cheapest"].format(
                marketplace=cheapest.marketplace,
                price=cheapest.formatted_price(),
            )

        return text

    async def save_results_to_db(
        self, results: List[ProductResult], db
    ) -> List[Dict[str, Any]]:
        saved = []
        for product in results:
            try:
                product_id = await db.save_product(
                    name=product.name,
                    marketplace=product.marketplace,
                    url=product.url,
                    image_url=product.image_url,
                    price=product.price,
                    currency=product.currency,
                )
                product.id = product_id
                saved.append(
                    {
                        "id": product_id,
                        "name": product.name,
                        "marketplace": product.marketplace,
                        "marketplace_emoji": product.marketplace_emoji,
                        "price": product.price,
                        "currency": product.currency,
                        "url": product.url,
                        "image_url": product.image_url,
                        "formatted_price": product.formatted_price(),
                    }
                )
            except Exception as e:
                logger.error(f"Error saving product to DB: {e}")
        return saved
