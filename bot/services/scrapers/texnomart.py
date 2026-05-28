import logging
import re
from typing import List
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://texnomart.uz"

# Try multiple search URL patterns since the site returned 404 before
SEARCH_URLS = [
    f"{BASE_URL}/search?q={{q}}",
    f"{BASE_URL}/search?query={{q}}",
    f"{BASE_URL}/ru/search?q={{q}}",
]


class TexnomartScraper(BaseScraper):
    MARKETPLACE_KEY = "texnomart"
    MARKETPLACE_NAME = "Texnomart"
    MARKETPLACE_EMOJI = "🔵"
    CURRENCY = "UZS"

    def __init__(self):
        super().__init__()
        self.headers.update({
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
        })

    async def search(self, query: str) -> List[ProductResult]:
        from bot.config import SCRAPERAPI_KEY
        encoded = quote(query)

        for url_pattern in SEARCH_URLS:
            url = url_pattern.format(q=encoded)
            try:
                html = await self._fetch_html(url, SCRAPERAPI_KEY)
                if not html:
                    continue
                results = self._parse_html(html, url)
                if results:
                    return results
            except Exception as e:
                logger.debug(f"Texnomart URL {url}: {e}")
                continue

        return []

    async def _fetch_html(self, url: str, scraperapi_key: str) -> str | None:
        from urllib.parse import quote as q
        if scraperapi_key:
            proxy = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={q(url, safe='')}"
        else:
            proxy = url
        try:
            timeout = aiohttp.ClientTimeout(total=25)
            async with aiohttp.ClientSession(headers=self.headers, timeout=timeout) as session:
                async with session.get(proxy) as resp:
                    if resp.status not in (200, 206):
                        logger.warning(f"Texnomart: HTTP {resp.status} for {url}")
                        return None
                    return await resp.text(errors="replace")
        except Exception as e:
            logger.debug(f"Texnomart fetch error: {e}")
            return None

    def _parse_html(self, html: str, base_url: str) -> List[ProductResult]:
        soup = BeautifulSoup(html, "lxml")
        results = []

        # Texnomart selectors — try most specific first
        selectors = [
            "div.product-item",
            "div.item-product",
            "div.catalog-item",
            "div.product-card",
            "li.product-item",
            "article.product",
            "[class*='product-item']",
            "[class*='catalog-item']",
            "[class*='product-card']",
        ]
        cards = []
        for sel in selectors:
            found = soup.select(sel)
            if found:
                cards = found[:10]
                break

        if not cards:
            cards = soup.select("article")[:10]

        for card in cards:
            try:
                name_el = card.select_one(
                    "h2, h3, [class*='title'], [class*='name'], "
                    "[itemprop='name'], a[title]"
                )
                price_el = card.select_one(
                    "[class*='price']:not([class*='old']):not([class*='was']), "
                    "[itemprop='price'], [class*='cost']"
                )
                if not name_el:
                    continue
                name = (name_el.get("title") or name_el.get_text(strip=True)).strip()
                if len(name) < 3:
                    continue
                price = 0.0
                if price_el:
                    price_text = price_el.get("content") or price_el.get_text(strip=True)
                    price = self._parse_price(price_text)
                if price <= 0:
                    # try to find any number > 1000 in the card text
                    nums = re.findall(r'\d[\d\s]{3,}', card.get_text())
                    for n in nums:
                        v = int(re.sub(r'\s', '', n))
                        if v > 1000:
                            price = float(v)
                            break
                if price <= 0:
                    continue
                link_el = card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else BASE_URL + href
                image_el = card.select_one("img[src], img[data-src]")
                img = None
                if image_el:
                    img = image_el.get("src") or image_el.get("data-src")
                    if img and not img.startswith("http"):
                        img = BASE_URL + img
                results.append(self._make_result(name, price, product_url, img))
            except Exception:
                continue

        if not results:
            logger.debug(f"Texnomart: no cards matched. Page size={len(html)} bytes")

        return results
