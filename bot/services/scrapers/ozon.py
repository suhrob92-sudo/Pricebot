import json
import logging
import re
from typing import List
from urllib.parse import quote

import aiohttp

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ozon.ru"


class OzonScraper(BaseScraper):
    MARKETPLACE_KEY = "ozon"
    MARKETPLACE_NAME = "Ozon"
    MARKETPLACE_EMOJI = "🟣"
    CURRENCY = "RUB"

    async def search(self, query: str) -> List[ProductResult]:
        from bot.config import SCRAPERAPI_KEY

        # Strategy 1: ScraperAPI with render=True (JS-rendered page)
        # Ozon is a heavy SPA so we need render=True
        if SCRAPERAPI_KEY:
            result = await self._search_rendered(query, SCRAPERAPI_KEY)
            if result:
                return result

        # Strategy 2: Try Ozon's internal search API directly
        result = await self._search_api(query)
        if result:
            return result

        return []

    async def _search_rendered(self, query: str, key: str) -> List[ProductResult]:
        url = f"{BASE_URL}/search/?text={quote(query)}&from_global=true"
        proxy = f"http://api.scraperapi.com?api_key={key}&render=true&premium=true&url={quote(url, safe='')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,*/*",
            "Accept-Language": "ru-RU,ru;q=0.9",
        }
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.get(proxy) as resp:
                    if resp.status != 200:
                        logger.warning(f"Ozon render: HTTP {resp.status}")
                        return []
                    raw = await resp.text(errors="replace")

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "lxml")

            # Try JSON-LD
            for script in soup.find_all("script", type="application/ld+json"):
                r = self._try_jsonld(script.string or "")
                if r:
                    return r

            # Try window state / embedded JSON
            for script in soup.find_all("script"):
                text = script.string or ""
                if len(text) < 500:
                    continue
                if '"price"' not in text and '"finalPrice"' not in text:
                    continue
                results = self._extract_json_products(text)
                if results:
                    return results

            return []
        except Exception as e:
            logger.error(f"Ozon render error: {e}")
            return []

    async def _search_api(self, query: str) -> List[ProductResult]:
        """Try Ozon's internal search API (no auth needed for basic search)."""
        url = "https://api.ozon.ru/composer-api.bx/_action/textSearch"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-o3-app-name": "ozonsite",
            "x-o3-lang": "ru",
        }
        payload = {
            "text": query,
            "from": "search",
            "page": 1,
            "layout_page_index": 2,
        }
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json(content_type=None)
            return self._parse_ozon_api(data)
        except Exception as e:
            logger.debug(f"Ozon API: {e}")
            return []

    def _parse_ozon_api(self, data) -> List[ProductResult]:
        results = []
        try:
            items = (
                data.get("searchResultsV2", {}).get("items")
                or data.get("items")
                or data.get("catalog", {}).get("items")
                or []
            )
            for item in items[:10]:
                try:
                    name = item.get("title") or item.get("name") or ""
                    if len(name) < 3:
                        continue
                    price = 0.0
                    price_raw = (item.get("price") or item.get("finalPrice")
                                 or item.get("cardPrice") or 0)
                    if isinstance(price_raw, dict):
                        price_raw = price_raw.get("amount") or price_raw.get("value") or 0
                    price_str = re.sub(r"[^\d.]", "", str(price_raw))
                    if price_str:
                        price = float(price_str)
                    if price <= 0:
                        continue
                    pid = item.get("id") or item.get("sku") or ""
                    item_url = item.get("url") or f"{BASE_URL}/product/{pid}/"
                    if not item_url.startswith("http"):
                        item_url = BASE_URL + item_url
                    img = item.get("image") or item.get("imageUrl") or None
                    results.append(self._make_result(name, price, item_url, img))
                except Exception:
                    continue
        except Exception:
            pass
        return results

    def _try_jsonld(self, text: str) -> List[ProductResult]:
        try:
            data = json.loads(text)
            items = data if isinstance(data, list) else [data]
            results = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get("name", "")
                if not name or len(name) < 3:
                    continue
                offers = item.get("offers") or {}
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                price_raw = offers.get("price") or item.get("price") or 0
                price_str = re.sub(r"[^\d.]", "", str(price_raw))
                if not price_str:
                    continue
                price = float(price_str)
                if price <= 0:
                    continue
                url = item.get("url") or BASE_URL
                if not url.startswith("http"):
                    url = BASE_URL + url
                img = item.get("image")
                if isinstance(img, list):
                    img = img[0] if img else None
                results.append(self._make_result(name, price, url, img))
            return results
        except Exception:
            return []

    def _extract_json_products(self, text: str) -> List[ProductResult]:
        results = []
        for match in re.finditer(r'\{[^{}]{30,}"name"[^{}]*"price"[^{}]*\}', text):
            try:
                obj = json.loads(match.group())
                name = obj.get("name", "")
                if len(name) < 3:
                    continue
                price_raw = obj.get("price") or obj.get("finalPrice") or 0
                price_str = re.sub(r"[^\d.]", "", str(price_raw))
                if not price_str:
                    continue
                price = float(price_str)
                if price <= 0:
                    continue
                pid = obj.get("id") or obj.get("sku") or ""
                url = f"{BASE_URL}/product/{pid}/" if pid else BASE_URL
                results.append(self._make_result(name, price, url))
                if len(results) >= 5:
                    break
            except Exception:
                continue
        return results
