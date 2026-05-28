import logging
import re
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://mediapark.uz"
SEARCH_URL = "https://mediapark.uz/search"


class MediaparkScraper(BaseScraper):
    MARKETPLACE_KEY = "mediapark"
    MARKETPLACE_NAME = "Mediapark"
    MARKETPLACE_EMOJI = "🟢"
    CURRENCY = "UZS"

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://mediapark.uz/",
            }
        )

    async def search(self, query: str) -> List[ProductResult]:
        try:
            params = {"q": query}
            soup = await self._get_soup(SEARCH_URL, params=params)
            if not soup:
                return []

            results = []
            product_cards = soup.select(
                ".product-card, .product-item, .catalog-item, "
                "[class*='product-card'], [class*='product_item'], "
                "[class*='catalog-item']"
            )

            if not product_cards:
                product_cards = soup.select("div[class*='product']")[:20]

            for card in product_cards[:10]:
                try:
                    name_el = card.select_one(
                        "h3, h2, .product-name, .product-title, "
                        "[class*='name'], [class*='title']"
                    )
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    price_el = card.select_one(
                        ".price, .product-price, [class*='price']"
                    )
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
                    logger.debug(f"Mediapark: error parsing card: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"Mediapark search error: {e}")
            return []
