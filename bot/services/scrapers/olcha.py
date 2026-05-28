import logging
import re
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://olcha.uz"
SEARCH_URL = "https://olcha.uz/search/{query}"


class OlchaScraper(BaseScraper):
    MARKETPLACE_KEY = "olcha"
    MARKETPLACE_NAME = "Olcha.uz"
    MARKETPLACE_EMOJI = "🔴"
    CURRENCY = "UZS"

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://olcha.uz/",
            }
        )

    async def search(self, query: str) -> List[ProductResult]:
        url = SEARCH_URL.format(query=quote(query))
        try:
            soup = await self._get_soup(url)
            if not soup:
                return []

            results = []
            product_cards = soup.select(".product-card, .product-item, article.product")
            if not product_cards:
                product_cards = soup.select("[class*='product']")[:20]

            for card in product_cards[:10]:
                try:
                    name_el = card.select_one(
                        ".product-card__name, .product-name, h3, h2, [class*='name']"
                    )
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    price_el = card.select_one(
                        ".product-card__price, .price, [class*='price']"
                    )
                    if not price_el:
                        continue
                    price_text = price_el.get_text(strip=True)
                    price_clean = re.sub(r"[^\d]", "", price_text)
                    if not price_clean:
                        continue
                    price = float(price_clean)
                    if price <= 0:
                        continue

                    link_el = card.select_one("a[href]")
                    if link_el:
                        href = link_el.get("href", "")
                        product_url = href if href.startswith("http") else BASE_URL + href
                    else:
                        product_url = BASE_URL

                    img_el = card.select_one("img")
                    image_url = None
                    if img_el:
                        image_url = img_el.get("data-src") or img_el.get("src")
                        if image_url and not image_url.startswith("http"):
                            image_url = BASE_URL + image_url

                    results.append(self._make_result(name, price, product_url, image_url))
                except Exception as e:
                    logger.debug(f"Olcha: error parsing card: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"Olcha search error: {e}")
            return []
