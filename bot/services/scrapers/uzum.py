import json
import logging
from typing import List
from urllib.parse import quote

import aiohttp

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://uzum.uz"
API_URL = "https://api.uzum.uz/api/main/search/product"


class UzumScraper(BaseScraper):
    MARKETPLACE_KEY = "uzum"
    MARKETPLACE_NAME = "Uzum Market"
    MARKETPLACE_EMOJI = "🟠"
    CURRENCY = "UZS"

    async def search(self, query: str) -> List[ProductResult]:
        # Uzum is a SPA — scraping HTML gives bot-detection page.
        # Use their internal search API directly (no ScraperAPI needed).
        params = {
            "keyword": query,
            "size": "20",
            "page": "0",
            "sortField": "RELEVANCE",
            "sortDirection": "DESC",
            "showAdultContent": "FALSE",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
            "Origin": "https://uzum.uz",
            "Referer": "https://uzum.uz/",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(API_URL, params=params) as resp:
                    if resp.status != 200:
                        logger.warning(f"Uzum API: HTTP {resp.status}")
                        return []
                    data = await resp.json(content_type=None)

            products = (
                data.get("payload", {}).get("products")
                or data.get("products")
                or data.get("data", {}).get("products")
                or []
            )
            if not products and isinstance(data, dict):
                products = self._deep_find_list(data, ("products", "items", "goods"))

            results = []
            for item in products[:10]:
                r = self._parse_item(item)
                if r:
                    results.append(r)
            return results
        except Exception as e:
            logger.error(f"Uzum error: {e}")
            return []

    def _deep_find_list(self, node, keys, depth=0):
        if depth > 8 or not isinstance(node, dict):
            return []
        for k in keys:
            v = node.get(k)
            if isinstance(v, list) and v:
                return v
        for v in node.values():
            if isinstance(v, dict):
                r = self._deep_find_list(v, keys, depth + 1)
                if r:
                    return r
        return []

    def _parse_item(self, item) -> ProductResult | None:
        if not isinstance(item, dict):
            return None
        try:
            name = (item.get("title") or item.get("name") or "").strip()
            if len(name) < 3:
                return None
            price = 0.0
            for key in ("minSellPrice", "price", "sellPrice", "cost", "minPrice"):
                raw = item.get(key)
                if raw is None:
                    continue
                if isinstance(raw, dict):
                    raw = raw.get("amount") or raw.get("value") or 0
                try:
                    val = float(raw)
                    if val > 10_000_000:
                        val /= 100
                    if val > 0:
                        price = val
                        break
                except (TypeError, ValueError):
                    continue
            if price <= 0:
                return None
            pid = item.get("id") or item.get("productId") or ""
            slug = item.get("slug") or ""
            url = f"{BASE_URL}/product/{slug}-{pid}" if slug else (
                f"{BASE_URL}/product/{pid}" if pid else BASE_URL
            )
            photos = item.get("photos") or item.get("images") or []
            image_url = None
            if photos:
                first = photos[0]
                if isinstance(first, dict):
                    image_url = first.get("photoUrl") or first.get("url")
                elif isinstance(first, str):
                    image_url = first
            return self._make_result(name, price, url, image_url)
        except Exception:
            return None
