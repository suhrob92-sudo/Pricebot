import json
import logging
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://mediapark.uz"


class MediaparkScraper(BaseScraper):
    MARKETPLACE_KEY = "mediapark"
    MARKETPLACE_NAME = "Mediapark"
    MARKETPLACE_EMOJI = "🟢"
    CURRENCY = "UZS"

    async def search(self, query: str) -> List[ProductResult]:
        url = f"{BASE_URL}/search?q={quote(query)}"
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
                    logger.debug(f"Mediapark __NEXT_DATA__ error: {e}")
            # HTML fallback
            results = []
            cards = (soup.select(".product-card") or
                     soup.select("[class*='product']") or
                     soup.select("article"))[:20]
            for card in cards[:10]:
                name_el = card.select_one("[class*='name'], [class*='title'], h3, h2")
                price_el = card.select_one("[class*='price'], [class*='cost']")
                if not name_el or not price_el:
                    continue
                name = name_el.get_text(strip=True)
                price = self._parse_price(price_el.get_text(strip=True))
                if len(name) < 3 or price <= 0:
                    continue
                link_el = card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else BASE_URL + href
                results.append(self._make_result(name, price, product_url))
            return results
        except Exception as e:
            logger.error(f"Mediapark error: {e}")
            return []

    def _find_products(self, node, depth=0) -> List[ProductResult]:
        if depth > 10:
            return []
        if isinstance(node, dict):
            for key in ("products", "items", "data", "results", "goods"):
                val = node.get(key)
                if isinstance(val, list) and val:
                    results = [r for item in val[:10] if (r := self._parse_item(item))]
                    if results:
                        return results
            for v in node.values():
                if isinstance(v, (dict, list)):
                    r = self._find_products(v, depth + 1)
                    if r:
                        return r
        elif isinstance(node, list):
            results = [r for item in node[:10] if (r := self._parse_item(item))]
            if results:
                return results
        return []

    def _parse_item(self, item) -> ProductResult | None:
        if not isinstance(item, dict):
            return None
        try:
            name = (item.get("name") or item.get("title") or "").strip()
            if len(name) < 3:
                return None
            price = 0.0
            for key in ("price", "sell_price", "current_price", "cost"):
                raw = item.get(key)
                if raw is None:
                    continue
                if isinstance(raw, dict):
                    raw = raw.get("amount") or raw.get("value") or 0
                try:
                    val = float(str(raw).replace(" ", "").replace(",", "."))
                    if val > 0:
                        price = val
                        break
                except (TypeError, ValueError):
                    continue
            if price <= 0:
                return None
            slug = item.get("slug") or item.get("id") or ""
            url = f"{BASE_URL}/product/{slug}" if slug else BASE_URL
            image_url = item.get("image") or item.get("photo") or None
            if isinstance(image_url, dict):
                image_url = image_url.get("url") or image_url.get("src")
            return self._make_result(name, price, url, image_url)
        except Exception:
            return None
