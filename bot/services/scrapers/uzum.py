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

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://uzum.uz/",
            }
        )

    async def search(self, query: str) -> List[ProductResult]:
        url = f"{BASE_URL}/search?keyword={quote(query)}"
        try:
            html = await self._get(url, render=True)
            if not isinstance(html, str):
                logger.warning("Uzum: no HTML returned")
                return []

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            results = []

            # Try multiple selectors to find product cards
            cards = (
                soup.select('[data-product-id]')
                or soup.select('[class*="product-card"]')
                or soup.select('[class*="ProductCard"]')
                or soup.select('[class*="productCard"]')
                or soup.select('[class*="catalog-item"]')
                or soup.select('[class*="catalogItem"]')
                or soup.select('article')
            )

            logger.info(f"Uzum: found {len(cards)} product cards")

            for card in cards[:10]:
                try:
                    name_el = (
                        card.select_one('[class*="title"]')
                        or card.select_one('[class*="name"]')
                        or card.select_one('h2')
                        or card.select_one('h3')
                    )
                    price_el = (
                        card.select_one('[class*="price"]')
                        or card.select_one('[class*="Price"]')
                        or card.select_one('[class*="cost"]')
                    )
                    link_el = card.select_one('a[href]')

                    if not name_el or not price_el:
                        continue

                    name = name_el.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    price_text = price_el.get_text(strip=True)
                    price = self._parse_price(price_text)
                    if price <= 0:
                        continue

                    url_path = link_el.get('href', '') if link_el else ''
                    if url_path.startswith('/'):
                        full_url = f"{BASE_URL}{url_path}"
                    elif url_path.startswith('http'):
                        full_url = url_path
                    else:
                        full_url = BASE_URL

                    img_el = card.select_one('img')
                    image_url = None
                    if img_el:
                        image_url = img_el.get('data-src') or img_el.get('src')
                        if image_url and not image_url.startswith('http'):
                            image_url = BASE_URL + image_url

                    results.append(self._make_result(name, price, full_url, image_url))
                except Exception as e:
                    logger.debug(f"Uzum: error parsing card: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"Uzum search error: {e}")
            return []
