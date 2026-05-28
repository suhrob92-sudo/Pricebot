import logging
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.uzum.uz/api/main/search"


class UzumScraper(BaseScraper):
    MARKETPLACE_KEY = "uzum"
    MARKETPLACE_NAME = "Uzum Market"
    MARKETPLACE_EMOJI = "🟠"
    CURRENCY = "UZS"

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept": "application/json",
                "Origin": "https://uzum.uz",
                "Referer": "https://uzum.uz/",
            }
        )

    async def search(self, query: str) -> List[ProductResult]:
        params = {
            "categoryId": "0",
            "showAdultContent": "false",
            "keyword": query,
            "size": "10",
            "page": "0",
        }
        try:
            data = await self._get(SEARCH_URL, params=params)
            if not isinstance(data, dict):
                return []
            products = data.get("productList", {})
            if isinstance(products, dict):
                items = products.get("products", [])
            else:
                items = data.get("data", {}).get("products", [])
                if not items:
                    items = data.get("products", [])

            results = []
            for item in items[:10]:
                try:
                    name = item.get("title") or item.get("name") or "Unknown"
                    price_data = item.get("minSellPrice") or item.get("price") or 0
                    if isinstance(price_data, dict):
                        price = float(price_data.get("amount", 0)) / 100
                    else:
                        price = float(price_data) / 100 if price_data > 10000 else float(price_data)

                    product_id = item.get("id") or item.get("productId", "")
                    url = f"https://uzum.uz/product/{product_id}" if product_id else "https://uzum.uz"

                    photos = item.get("photos") or []
                    image_url = None
                    if photos and isinstance(photos, list):
                        first = photos[0]
                        if isinstance(first, dict):
                            image_url = first.get("photoUrl") or first.get("url")
                        else:
                            image_url = str(first)

                    if price > 0:
                        results.append(self._make_result(name, price, url, image_url))
                except Exception as e:
                    logger.debug(f"Uzum: error parsing item: {e}")
                    continue
            return results
        except Exception as e:
            logger.error(f"Uzum search error: {e}")
            return []
