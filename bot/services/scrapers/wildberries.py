import logging
import re
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

SEARCH_API_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"
PRODUCT_BASE_URL = "https://www.wildberries.ru/catalog"
IMAGE_BASE_URL = "https://images.wbstatic.net/c246x328/new"


class WildberriesScraper(BaseScraper):
    MARKETPLACE_KEY = "wildberries"
    MARKETPLACE_NAME = "Wildberries"
    MARKETPLACE_EMOJI = "🩷"
    CURRENCY = "RUB"

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept": "application/json",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                "Origin": "https://www.wildberries.ru",
                "Referer": "https://www.wildberries.ru/",
            }
        )

    async def search(self, query: str) -> List[ProductResult]:
        params = {
            "query": query,
            "resultset": "catalog",
            "limit": "10",
            "sort": "popular",
            "page": "1",
            "appType": "1",
            "curr": "rub",
            "lang": "ru",
            "locale": "ru",
            "spp": "0",
        }
        try:
            data = await self._get(SEARCH_API_URL, params=params)
            if not isinstance(data, dict):
                return []

            products = (
                data.get("data", {}).get("products", [])
                or data.get("catalog", {}).get("products", [])
                or []
            )

            results = []
            for item in products[:10]:
                try:
                    name = item.get("name") or "Unknown"
                    sizes = item.get("sizes", []) or []
                    price = 0.0
                    for size in sizes:
                        price_data = size.get("price", {}) or {}
                        if isinstance(price_data, dict):
                            total = price_data.get("total") or price_data.get("product", 0)
                            if total:
                                price = float(total) / 100
                                break
                    if price <= 0:
                        sale_price = item.get("salePriceU") or item.get("priceU", 0)
                        price = float(sale_price) / 100 if sale_price else 0
                    if price <= 0:
                        continue

                    product_id = item.get("id", "")
                    url = f"{PRODUCT_BASE_URL}/{product_id}/detail.aspx" if product_id else "https://www.wildberries.ru"

                    image_url = self._get_image_url(product_id)

                    results.append(self._make_result(name, price, url, image_url))
                except Exception as e:
                    logger.debug(f"WB: error parsing item: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"Wildberries search error: {e}")
            return []

    def _get_image_url(self, product_id) -> str:
        try:
            pid = int(product_id)
            vol = pid // 100000
            part = pid // 1000
            return f"https://basket-{vol % 13 + 1:02d}.wbbasket.ru/vol{vol}/part{part}/{pid}/images/c246x328/1.webp"
        except Exception:
            return ""
