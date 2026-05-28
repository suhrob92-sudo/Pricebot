import json
import logging
from typing import List
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://uzum.uz"

# Known working API endpoints to try in order
API_CANDIDATES = [
    "https://api.uzum.uz/api/v2/main/search",
    "https://api.uzum.uz/api/main/search/product",
    "https://api.uzum.uz/api/v1/product/list",
]


class UzumScraper(BaseScraper):
    MARKETPLACE_KEY = "uzum"
    MARKETPLACE_NAME = "Uzum Market"
    MARKETPLACE_EMOJI = "🟠"
    CURRENCY = "UZS"

    _api_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
        "Origin": "https://uzum.uz",
        "Referer": "https://uzum.uz/",
    }

    async def search(self, query: str) -> List[ProductResult]:
        # Try direct REST API first (fast, no credits used)
        for api_url in API_CANDIDATES:
            results = await self._try_api(api_url, query)
            if results:
                return results

        # Fall back: ScraperAPI render=True (handles SPA/bot-protection)
        from bot.config import SCRAPERAPI_KEY
        if SCRAPERAPI_KEY:
            results = await self._search_rendered(query, SCRAPERAPI_KEY)
            if results:
                return results

        return []

    async def _try_api(self, api_url: str, query: str) -> List[ProductResult]:
        params = {
            "keyword": query,
            "size": "20",
            "page": "0",
            "sortField": "RELEVANCE",
            "sortDirection": "DESC",
            "showAdultContent": "FALSE",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(headers=self._api_headers, timeout=timeout) as s:
                async with s.get(api_url, params=params) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json(content_type=None)
            return self._extract_products(data)
        except Exception as e:
            logger.debug(f"Uzum API {api_url}: {e}")
            return []

    async def _search_rendered(self, query: str, key: str) -> List[ProductResult]:
        url = f"{BASE_URL}/search?keyword={quote(query)}"
        proxy = f"http://api.scraperapi.com?api_key={key}&render=true&url={quote(url, safe='')}"
        try:
            timeout = aiohttp.ClientTimeout(total=90)
            async with aiohttp.ClientSession(timeout=timeout) as s:
                async with s.get(proxy) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text(errors="replace")
            soup = BeautifulSoup(html, "lxml")
            # Try __NEXT_DATA__
            script = soup.find("script", {"id": "__NEXT_DATA__"})
            if script and script.string:
                try:
                    data = json.loads(script.string)
                    results = self._extract_products(data)
                    if results:
                        return results
                except Exception:
                    pass
            return self._parse_cards(soup)
        except Exception as e:
            logger.error(f"Uzum render error: {e}")
            return []

    def _extract_products(self, data) -> List[ProductResult]:
        products = self._deep_find(data, ("products", "productList", "items", "goods", "catalog"))
        results = []
        for item in products[:10]:
            r = self._parse_item(item)
            if r:
                results.append(r)
        return results

    def _deep_find(self, node, keys, depth=0):
        if depth > 10 or not isinstance(node, dict):
            return []
        for k in keys:
            v = node.get(k)
            if isinstance(v, list) and v:
                return v
            if isinstance(v, dict):
                inner = self._deep_find(v, keys, depth + 1)
                if inner:
                    return inner
        for v in node.values():
            if isinstance(v, dict):
                r = self._deep_find(v, keys, depth + 1)
                if r:
                    return r
        return []

    def _parse_cards(self, soup: BeautifulSoup) -> List[ProductResult]:
        results = []
        for sel in ("[class*='product-card']", "[class*='product-item']",
                    "[class*='catalog-item']", "article"):
            cards = soup.select(sel)[:10]
            if cards:
                for card in cards:
                    name_el = card.select_one("h2,h3,[class*='title'],[class*='name']")
                    price_el = card.select_one("[class*='price'],[class*='cost'],[class*='sum']")
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if len(name) < 3:
                        continue
                    price = self._parse_price(price_el.get_text(strip=True)) if price_el else 0
                    if price <= 0:
                        continue
                    link = card.select_one("a[href]")
                    href = link.get("href", "") if link else ""
                    url = href if href.startswith("http") else BASE_URL + href
                    results.append(self._make_result(name, price, url))
                if results:
                    break
        return results

    def _parse_item(self, item) -> ProductResult | None:
        if not isinstance(item, dict):
            return None
        try:
            name = (item.get("title") or item.get("name") or "").strip()
            if len(name) < 3:
                return None
            price = 0.0
            for key in ("minSellPrice", "sellPrice", "price", "cost", "minPrice"):
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
            img = None
            if photos:
                first = photos[0]
                img = (first.get("photoUrl") or first.get("url")) if isinstance(first, dict) else (
                    first if isinstance(first, str) else None
                )
            return self._make_result(name, price, url, img)
        except Exception:
            return None
