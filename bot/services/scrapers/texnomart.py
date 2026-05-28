import logging
import re
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://texnomart.uz"
SEARCH_API_URL = "https://texnomart.uz/api/v1/catalog/search"
SEARCH_HTML_URL = "https://texnomart.uz/search"


class TexnomartScraper(BaseScraper):
    MARKETPLACE_KEY = "texnomart"
    MARKETPLACE_NAME = "Texnomart"
    MARKETPLACE_EMOJI = "🔵"
    CURRENCY = "UZS"

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept": "application/json, text/html, */*",
                "Referer": "https://texnomart.uz/",
                "Origin": "https://texnomart.uz",
            }
        )

    async def search(self, query: str) -> List[ProductResult]:
        results = await self._search_api(query)
        if not results:
            results = await self._search_html(query)
        return results

    async def _search_api(self, query: str) -> List[ProductResult]:
        try:
            params = {"query": query, "page": 1, "limit": 10}
            data = await self._get(SEARCH_API_URL, params=params)
            if not isinstance(data, dict):
                return []

            items = (
                data.get("data", {}).get("products", [])
                or data.get("products", [])
                or data.get("items", [])
                or []
            )
            results = []
            for item in items[:10]:
                try:
                    name = item.get("name") or item.get("title") or "Unknown"
                    price = float(item.get("price") or item.get("sell_price") or 0)
                    if price <= 0:
                        continue
                    slug = item.get("slug") or item.get("id") or ""
                    url = f"{BASE_URL}/product/{slug}" if slug else BASE_URL
                    image_url = item.get("image") or item.get("photo") or item.get("img")
                    if image_url and not image_url.startswith("http"):
                        image_url = BASE_URL + image_url
                    results.append(self._make_result(name, price, url, image_url))
                except Exception as e:
                    logger.debug(f"Texnomart API: error parsing item: {e}")
                    continue
            return results
        except Exception as e:
            logger.error(f"Texnomart API search error: {e}")
            return []

    async def _search_html(self, query: str) -> List[ProductResult]:
        try:
            params = {"q": query}
            soup = await self._get_soup(SEARCH_HTML_URL, params=params)
            if not soup:
                return []

            results = []
            product_cards = soup.select(
                ".product-card, .product-item, [class*='product-card'], [class*='product_card']"
            )
            for card in product_cards[:10]:
                try:
                    name_el = card.select_one(
                        "h3, h2, .product-name, .name, [class*='title'], [class*='name']"
                    )
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    price_el = card.select_one(".price, [class*='price']")
                    if not price_el:
                        continue
                    price_text = re.sub(r"[^\d]", "", price_el.get_text(strip=True))
                    if not price_text:
                        continue
                    price = float(price_text)
                    if price <= 0:
                        continue

                    link_el = card.select_one("a[href]")
                    url = BASE_URL
                    if link_el:
                        href = link_el.get("href", "")
                        url = href if href.startswith("http") else BASE_URL + href

                    img_el = card.select_one("img")
                    image_url = None
                    if img_el:
                        image_url = img_el.get("data-src") or img_el.get("src")
                        if image_url and not image_url.startswith("http"):
                            image_url = BASE_URL + image_url

                    results.append(self._make_result(name, price, url, image_url))
                except Exception as e:
                    logger.debug(f"Texnomart HTML: error parsing card: {e}")
                    continue
            return results
        except Exception as e:
            logger.error(f"Texnomart HTML search error: {e}")
            return []
