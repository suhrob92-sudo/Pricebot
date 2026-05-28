import json
import logging
import re
from typing import List
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

from bot.services.scrapers.base import BaseScraper, ProductResult

logger = logging.getLogger(__name__)

BASE_URL = "https://texnomart.uz"

SEARCH_URLS = [
    f"{BASE_URL}/search?q={{q}}",
    f"{BASE_URL}/search?query={{q}}",
    f"{BASE_URL}/catalogsearch/result/?q={{q}}",
]


class TexnomartScraper(BaseScraper):
    MARKETPLACE_KEY = "texnomart"
    MARKETPLACE_NAME = "Texnomart"
    MARKETPLACE_EMOJI = "🔵"
    CURRENCY = "UZS"

    async def search(self, query: str) -> List[ProductResult]:
        from bot.config import SCRAPERAPI_KEY
        if not SCRAPERAPI_KEY:
            return []

        encoded = quote(query)
        for url_pattern in SEARCH_URLS:
            url = url_pattern.format(q=encoded)
            # render=True: Texnomart is a SPA (shows loading-spinner with render=False)
            proxy = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&render=true&url={quote(url, safe='')}"
            try:
                timeout = aiohttp.ClientTimeout(total=90)
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,*/*",
                    "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8",
                }
                async with aiohttp.ClientSession(headers=headers, timeout=timeout) as s:
                    async with s.get(proxy) as resp:
                        if resp.status == 404:
                            continue
                        if resp.status != 200:
                            logger.warning(f"Texnomart {url}: HTTP {resp.status}")
                            continue
                        html = await resp.text(errors="replace")
            except Exception as e:
                logger.debug(f"Texnomart {url}: {e}")
                continue

            soup = BeautifulSoup(html, "lxml")

            # Try __NEXT_DATA__
            script = soup.find("script", {"id": "__NEXT_DATA__"})
            if script and script.string:
                try:
                    data = json.loads(script.string)
                    results = self._find_products_json(data)
                    if results:
                        return results
                except Exception:
                    pass

            results = self._parse_cards(soup)
            if results:
                return results

        return []

    def _find_products_json(self, node, depth=0) -> List[ProductResult]:
        if depth > 10:
            return []
        if isinstance(node, dict):
            for key in ("products", "items", "data", "results", "catalog", "goods"):
                val = node.get(key)
                if isinstance(val, list) and val:
                    results = [r for item in val[:10] if (r := self._parse_item(item))]
                    if results:
                        return results
            for v in node.values():
                if isinstance(v, (dict, list)):
                    r = self._find_products_json(v, depth + 1)
                    if r:
                        return r
        return []

    def _parse_cards(self, soup: BeautifulSoup) -> List[ProductResult]:
        results = []
        selectors = [
            "div.product-item", "div.item-product", "div.catalog-item",
            "div.product-card", "li.product-item",
            "[class*='product-item']", "[class*='catalog-item']",
            "[class*='product-card']", "article",
        ]
        cards = []
        for sel in selectors:
            found = soup.select(sel)
            if found:
                cards = found[:10]
                break

        for card in cards:
            try:
                name_el = card.select_one(
                    "h2,h3,[class*='title'],[class*='name'],[itemprop='name'],a[title]"
                )
                price_el = card.select_one(
                    "[class*='price']:not([class*='old']):not([class*='was']),"
                    "[itemprop='price'],[class*='cost']"
                )
                if not name_el:
                    continue
                name = (name_el.get("title") or name_el.get_text(strip=True)).strip()
                if len(name) < 3:
                    continue
                price = 0.0
                if price_el:
                    price = self._parse_price(price_el.get("content") or price_el.get_text(strip=True))
                if price <= 0:
                    for n in re.findall(r'\d[\d\s]{3,}', card.get_text()):
                        v = int(re.sub(r'\s', '', n))
                        if v > 1000:
                            price = float(v)
                            break
                if price <= 0:
                    continue
                link_el = card.select_one("a[href]")
                href = link_el.get("href", "") if link_el else ""
                product_url = href if href.startswith("http") else BASE_URL + href
                image_el = card.select_one("img[src],img[data-src]")
                img = None
                if image_el:
                    img = image_el.get("src") or image_el.get("data-src")
                    if img and not img.startswith("http"):
                        img = BASE_URL + img
                results.append(self._make_result(name, price, product_url, img))
            except Exception:
                continue
        return results

    def _parse_item(self, item) -> ProductResult | None:
        if not isinstance(item, dict):
            return None
        try:
            name = (item.get("name") or item.get("title") or item.get("product_name") or "").strip()
            if len(name) < 3:
                return None
            price = 0.0
            for key in ("price", "sell_price", "current_price", "cost", "minPrice"):
                raw = item.get(key)
                if raw is None:
                    continue
                if isinstance(raw, dict):
                    raw = raw.get("amount") or raw.get("value") or 0
                try:
                    val = float(str(raw).replace(" ", "").replace(",", "."))
                    if val > 0:
                        price = val
                        break
                except (TypeError, ValueError):
                    continue
            if price <= 0:
                return None
            slug = item.get("slug") or item.get("id") or ""
            url = f"{BASE_URL}/product/{slug}" if slug else BASE_URL
            img = item.get("image") or item.get("photo") or item.get("thumbnail") or None
            if isinstance(img, dict):
                img = img.get("url") or img.get("src")
            return self._make_result(name, price, url, img)
        except Exception:
            return None
