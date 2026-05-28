import logging
from typing import List
from urllib.parse import quote

import aiohttp

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v5/search"
PRODUCT_BASE = "https://www.wildberries.ru/catalog"


class WildberriesScraper(BaseScraper):
    MARKETPLACE_KEY = "wildberries"
    MARKETPLACE_NAME = "Wildberries"
    MARKETPLACE_EMOJI = "🩷"
    CURRENCY = "RUB"

    async def search(self, query: str) -> List[ProductResult]:
        from bot.config import SCRAPERAPI_KEY
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
        wb_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Origin": "https://www.wildberries.ru",
            "Referer": "https://www.wildberries.ru/",
        }

        # Build query string manually to preserve WB-specific params
        import urllib.parse
        qs = urllib.parse.urlencode(params)
        full_url = f"{SEARCH_URL}?{qs}"

        # Use ScraperAPI premium to bypass WB rate limiting (429)
        # premium=true uses residential IPs — costs 10 credits but bypasses blocks
        if SCRAPERAPI_KEY:
            request_url = (
                f"http://api.scraperapi.com"
                f"?api_key={SCRAPERAPI_KEY}"
                f"&premium=true"
                f"&url={quote(full_url, safe='')}"
            )
            req_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
        else:
            request_url = full_url
            req_headers = wb_headers

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(headers=req_headers, timeout=timeout) as session:
                async with session.get(request_url) as resp:
                    if resp.status != 200:
                        logger.warning(f"WB: HTTP {resp.status}")
                        return []
                    data = await resp.json(content_type=None)

            products = (
                data.get("data", {}).get("products", [])
                or data.get("catalog", {}).get("products", [])
                or []
            )
            results = []
            for item in products[:10]:
                try:
                    name = item.get("name") or "Unknown"
                    price = 0.0
                    for size in (item.get("sizes") or []):
                        p = size.get("price") or {}
                        total = p.get("total") or p.get("product") or 0
                        if total:
                            price = float(total) / 100
                            break
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
                    results.append(self._make_result(name, price, url, self._wb_image(pid)))
                except Exception as e:
                    logger.debug(f"WB item: {e}")
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
