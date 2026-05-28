import logging
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v5/search"
PRODUCT_BASE = "https://www.wildberries.ru/catalog"


class WildberriesScraper(BaseScraper):
    MARKETPLACE_KEY = "wildberries"
    MARKETPLACE_NAME = "Wildberries"
    MARKETPLACE_EMOJI = "🩷"
    CURRENCY = "RUB"

    def __init__(self):
        super().__init__()
        self.headers.update({
            "Accept": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Origin": "https://www.wildberries.ru",
            "Referer": "https://www.wildberries.ru/",
        })

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
            "spp": "27",
        }
        try:
            data = await self._get(SEARCH_URL, params=params, render=False)
            if not isinstance(data, dict):
                logger.warning("WB: non-dict response")
                return []
            products = (data.get("data", {}).get("products", []) or
                        data.get("catalog", {}).get("products", []) or [])
            results = []
            for item in products[:10]:
                try:
                    name = item.get("name") or "Unknown"
                    price = 0.0
                    # Try sizes first
                    for size in (item.get("sizes") or []):
                        p = size.get("price") or {}
                        total = p.get("total") or p.get("product") or 0
                        if total:
                            price = float(total) / 100
                            break
                    # Fallback prices
                    if price <= 0:
                        for key in ("salePriceU", "priceU", "sale_price_u"):
                            raw = item.get(key)
                            if raw:
                                price = float(raw) / 100
                                break
                    if price <= 0:
                        continue
                    pid = item.get("id", "")
                    url = f"{PRODUCT_BASE}/{pid}/detail.aspx" if pid else "https://www.wildberries.ru"
                    image_url = self._wb_image(pid)
                    results.append(self._make_result(name, price, url, image_url))
                except Exception as e:
                    logger.debug(f"WB item parse error: {e}")
                    continue
            return results
        except Exception as e:
            logger.error(f"WB error: {e}")
            return []

    def _wb_image(self, pid) -> str:
        try:
            pid = int(pid)
            vol = pid // 100000
            part = pid // 1000
            n = (vol % 13) + 1
            return f"https://basket-{n:02d}.wbbasket.ru/vol{vol}/part{part}/{pid}/images/c246x328/1.webp"
        except Exception:
            return ""
