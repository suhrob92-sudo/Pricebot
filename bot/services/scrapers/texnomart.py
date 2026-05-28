import logging
from typing import List
from urllib.parse import quote

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://texnomart.uz"
SEARCH_URL = "https://texnomart.uz/search"


class TexnomartScraper(BaseScraper):
    MARKETPLACE_KEY = "texnomart"
    MARKETPLACE_NAME = "Texnomart"
    MARKETPLACE_EMOJI = "🔵"
    CURRENCY = "UZS"

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://texnomart.uz/",
            }
        )

    async def search(self, query: str) -> List[ProductResult]:
        url = f"{SEARCH_URL}?query={quote(query)}"
        try:
            html = await self._get(url, render=True)
            if not isinstance(html, str):
                logger.warning("Texnomart: no HTML returned")
                return []

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            results = []

            # Try multiple selectors to find product cards
            cards = (
                soup.select('.product-card')
                or soup.select('.product-item')
                or soup.select('[class*="product-card"]')
                or soup.select('[class*="product_card"]')
                or soup.select('[class*="productCard"]')
                or soup.select('[class*="catalog-item"]')
                or soup.select('[class*="product"]')[:20]
            )

            logger.info(f"Texnomart: found {len(cards)} product cards")

            for card in cards[:10]:
                try:
                    name_el = (
                        card.select_one('[class*="title"]')
                        or card.select_one('[class*="name"]')
                        or card.select_one('h3')
                        or card.select_one('h2')
                    )
                    if not name_el:
                        continue
                    name = name_el.get_text(strip=True)
                    if not name or len(name) < 3:
                        continue

                    price_el = (
                        card.select_one('[class*="price"]')
                        or card.select_one('[class*="Price"]')
                        or card.select_one('[class*="cost"]')
                    )
                    if not price_el:
                        continue
                    price_text = price_el.get_text(strip=True)
                    price = self._parse_price(price_text)
                    if price <= 0:
                        continue

                    link_el = card.select_one('a[href]')
                    if link_el:
                        href = link_el.get('href', '')
                        product_url = href if href.startswith('http') else BASE_URL + href
                    else:
                        product_url = BASE_URL

                    img_el = card.select_one('img')
                    image_url = None
                    if img_el:
                        image_url = img_el.get('data-src') or img_el.get('src')
                        if image_url and not image_url.startswith('http'):
                            image_url = BASE_URL + image_url

                    results.append(self._make_result(name, price, product_url, image_url))
                except Exception as e:
                    logger.debug(f"Texnomart: error parsing card: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"Texnomart search error: {e}")
            return []
