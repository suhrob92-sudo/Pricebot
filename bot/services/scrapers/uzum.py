import json
import logging
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://uzum.uz"


class UzumScraper(BaseScraper):
    MARKETPLACE_KEY = "uzum"
    MARKETPLACE_NAME = "Uzum Market"
    MARKETPLACE_EMOJI = "🟠"
    CURRENCY = "UZS"

    async def search(self, query: str) -> List[ProductResult]:
        url = f"{BASE_URL}/search?keyword={quote(query)}"
        try:
            html = await self._get(url, render=False)
            if not isinstance(html, str):
                return []
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            script = soup.find("script", {"id": "__NEXT_DATA__"})
            if script and script.string:
                try:
                    data = json.loads(script.string)
                    results = self._find_products(data)
                    if results:
                        return results
                except Exception as e:
                    logger.debug(f"Uzum __NEXT_DATA__ error: {e}")
            logger.warning("Uzum: no products found")
            return []
        except Exception as e:
            logger.error(f"Uzum error: {e}")
            return []

    def _find_products(self, node, depth=0) -> List[ProductResult]:
        if depth > 10:
            return []
        results = []
        if isinstance(node, dict):
            for key in ("products", "productList", "items", "goods", "catalog"):
                val = node.get(key)
                if isinstance(val, list) and len(val) > 0:
                    for item in val[:10]:
                        r = self._parse_item(item)
                        if r:
                            results.append(r)
                    if results:
                        return results
                elif isinstance(val, dict):
                    sub = val.get("products") or val.get("items") or []
                    for item in sub[:10]:
                        r = self._parse_item(item)
                        if r:
                            results.append(r)
                    if results:
                        return results
            for v in node.values():
                if isinstance(v, (dict, list)):
                    r = self._find_products(v, depth + 1)
                    if r:
                        return r
        elif isinstance(node, list):
            for item in node[:10]:
                r = self._parse_item(item)
                if r:
                    results.append(r)
            if results:
                return results
        return []

    def _parse_item(self, item) -> ProductResult | None:
        if not isinstance(item, dict):
            return None
        try:
            name = (item.get("title") or item.get("name") or "").strip()
            if len(name) < 3:
                return None
            price = 0.0
            for key in ("minSellPrice", "price", "sellPrice", "cost"):
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
            url = f"{BASE_URL}/product/{pid}" if pid else BASE_URL
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
