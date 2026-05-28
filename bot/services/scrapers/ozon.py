import logging
import re
import json
from typing import List

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ozon.ru"
SEARCH_URL = "https://www.ozon.ru/api/entrypoint-api.bx/page/json/v2"


class OzonScraper(BaseScraper):
    MARKETPLACE_KEY = "ozon"
    MARKETPLACE_NAME = "Ozon"
    MARKETPLACE_EMOJI = "🟣"
    CURRENCY = "RUB"

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept": "application/json",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                "Referer": "https://www.ozon.ru/",
                "Origin": "https://www.ozon.ru",
                "x-o3-app-name": "ozonsite",
                "x-o3-app-version": "2.1.0",
            }
        )

    async def search(self, query: str) -> List[ProductResult]:
        try:
            params = {
                "url": f"/search/?text={query}&layout_container=categorySearchMegapagination&layout_page_index=1"
            }
            data = await self._get(SEARCH_URL, params=params)
            if not isinstance(data, dict):
                return await self._search_fallback(query)

            results = []
            catalog_data = data.get("catalog", {}) or {}
            items = (
                catalog_data.get("products", [])
                or data.get("searchResultsV2", {}).get("items", [])
                or []
            )

            for item in items[:10]:
                try:
                    name = item.get("name") or item.get("title") or "Unknown"
                    price_data = item.get("price") or {}
                    if isinstance(price_data, dict):
                        price_str = price_data.get("price", "0")
                        price = float(re.sub(r"[^\d.]", "", str(price_str)) or "0")
                    else:
                        price = float(re.sub(r"[^\d.]", "", str(price_data)) or "0")

                    if price <= 0:
                        continue

                    product_id = item.get("id") or item.get("skuId", "")
                    url = f"{BASE_URL}/product/{product_id}/" if product_id else BASE_URL

                    image_url = None
                    images = item.get("images", []) or []
                    if images and isinstance(images, list):
                        image_url = images[0] if isinstance(images[0], str) else None

                    results.append(self._make_result(name, price, url, image_url))
                except Exception as e:
                    logger.debug(f"Ozon: error parsing item: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"Ozon search error: {e}")
            return []

    async def _search_fallback(self, query: str) -> List[ProductResult]:
        try:
            url = f"{BASE_URL}/search/"
            params = {"text": query, "from_global": "true"}
            soup = await self._get_soup(url, params=params)
            if not soup:
                return []

            results = []
            script_tags = soup.find_all("script", type="application/json")
            for script in script_tags:
                try:
                    script_data = json.loads(script.string or "{}")
                    products = self._extract_products_from_json(script_data)
                    if products:
                        results.extend(products)
                        break
                except Exception:
                    continue

            if not results:
                cards = soup.select("[class*='product'], [class*='tile'], [class*='item']")
                for card in cards[:10]:
                    try:
                        name_el = card.select_one("h3, h2, [class*='title'], [class*='name']")
                        price_el = card.select_one("[class*='price']")
                        if not name_el or not price_el:
                            continue
                        name = name_el.get_text(strip=True)
                        price_text = re.sub(r"[^\d]", "", price_el.get_text(strip=True))
                        if name and price_text:
                            price = float(price_text)
                            link_el = card.select_one("a[href]")
                            product_url = BASE_URL
                            if link_el:
                                href = link_el.get("href", "")
                                product_url = href if href.startswith("http") else BASE_URL + href
                            results.append(self._make_result(name, price, product_url))
                    except Exception:
                        continue

            return results[:10]
        except Exception as e:
            logger.error(f"Ozon fallback search error: {e}")
            return []

    def _extract_products_from_json(self, data: dict, depth: int = 0) -> List[ProductResult]:
        if depth > 5:
            return []
        results = []
        if isinstance(data, dict):
            if "name" in data and "price" in data:
                try:
                    name = data["name"]
                    price_raw = data["price"]
                    price = float(re.sub(r"[^\d.]", "", str(price_raw)) or "0")
                    if name and price > 0:
                        url = data.get("url", BASE_URL)
                        if not url.startswith("http"):
                            url = BASE_URL + url
                        results.append(self._make_result(name, price, url))
                except Exception:
                    pass
            for v in data.values():
                if isinstance(v, (dict, list)):
                    results.extend(self._extract_products_from_json(v, depth + 1))
        elif isinstance(data, list):
            for item in data:
                results.extend(self._extract_products_from_json(item, depth + 1))
        return results
