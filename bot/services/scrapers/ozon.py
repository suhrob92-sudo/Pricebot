import json
import logging
import re
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ozon.ru"


class OzonScraper(BaseScraper):
    MARKETPLACE_KEY = "ozon"
    MARKETPLACE_NAME = "Ozon"
    MARKETPLACE_EMOJI = "🟣"
    CURRENCY = "RUB"

    def __init__(self):
        super().__init__()
        self.headers.update({
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "ru-RU,ru;q=0.9",
        })

    async def search(self, query: str) -> List[ProductResult]:
        url = f"{BASE_URL}/search/?text={quote(query)}&from_global=true"
        try:
            html = await self._get(url, render=False)
            if not isinstance(html, str):
                return []
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")

            # Ozon embeds data in window.__NUXT__ or similar scripts
            for script in soup.find_all("script"):
                text = script.string or ""
                if '"price"' in text and '"name"' in text and len(text) > 1000:
                    # Try to extract JSON blocks
                    for match in re.finditer(r'\{[^{}]*"name"[^{}]*"price"[^{}]*\}', text):
                        try:
                            obj = json.loads(match.group())
                            name = obj.get("name", "")
                            price_raw = obj.get("price") or obj.get("finalPrice") or 0
                            price = float(re.sub(r"[^\d.]", "", str(price_raw)) or "0")
                            if len(name) > 3 and price > 0:
                                pid = obj.get("id") or obj.get("sku") or ""
                                product_url = f"{BASE_URL}/product/{pid}/" if pid else BASE_URL
                                return [self._make_result(name, price, product_url)]
                        except Exception:
                            continue

            # Try JSON-LD structured data
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "{}")
                    if isinstance(data, list):
                        for item in data:
                            r = self._parse_jsonld(item)
                            if r:
                                return [r]
                    else:
                        r = self._parse_jsonld(data)
                        if r:
                            return [r]
                except Exception:
                    continue

            return []
        except Exception as e:
            logger.error(f"Ozon error: {e}")
            return []

    def _parse_jsonld(self, item) -> ProductResult | None:
        if not isinstance(item, dict):
            return None
        try:
            name = item.get("name", "")
            if not name or len(name) < 3:
                return None
            offers = item.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price_raw = offers.get("price") or item.get("price") or 0
            price = float(re.sub(r"[^\d.]", "", str(price_raw)) or "0")
            if price <= 0:
                return None
            url = item.get("url") or BASE_URL
            if not url.startswith("http"):
                url = BASE_URL + url
            image = item.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            return self._make_result(name, price, url, image)
        except Exception:
            return None
