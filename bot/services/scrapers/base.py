import logging
import re
from dataclasses import dataclass
from typing import Optional, List, Union
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=60)


@dataclass
class ProductResult:
    name: str
    price: float
    currency: str
    url: str
    marketplace: str
    marketplace_emoji: str
    image_url: Optional[str] = None
    is_available: bool = True
    id: Optional[int] = None

    def formatted_price(self) -> str:
        if self.currency == "UZS":
            return f"{self.price:,.0f} so'm".replace(",", " ")
        elif self.currency == "RUB":
            return f"₽ {self.price:,.0f}".replace(",", " ")
        return f"{self.price:,.0f} {self.currency}"


class BaseScraper:
    MARKETPLACE_KEY: str = ""
    MARKETPLACE_NAME: str = ""
    MARKETPLACE_EMOJI: str = ""
    CURRENCY: str = "UZS"

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "uz-UZ,uz;q=0.9,ru;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
        }

    async def search(self, query: str) -> List[ProductResult]:
        raise NotImplementedError

    def _build_url(self, target_url: str, scraperapi_key: str, render: bool = True) -> str:
        """Wrap URL with ScraperAPI proxy if key is provided."""
        if scraperapi_key:
            render_param = "&render=true" if render else ""
            return f"http://api.scraperapi.com?api_key={scraperapi_key}{render_param}&url={quote(target_url, safe='')}"
        return target_url

    async def _get(
        self,
        url: str,
        params: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
        scraperapi_key: str = "",
        render: bool = True,
    ) -> Optional[Union[dict, str]]:
        from bot.config import SCRAPERAPI_KEY
        key = scraperapi_key or SCRAPERAPI_KEY

        headers = {**self.headers}
        if extra_headers:
            headers.update(extra_headers)

        # Build full URL with params for ScraperAPI wrapping
        if key and params:
            import urllib.parse
            full_url = url + ("?" if "?" not in url else "&") + urllib.parse.urlencode(params)
            request_url = self._build_url(full_url, key, render=render)
            request_params = None
        elif key:
            request_url = self._build_url(url, key, render=render)
            request_params = None
        else:
            request_url = url
            request_params = params

        try:
            async with aiohttp.ClientSession(headers=headers, timeout=DEFAULT_TIMEOUT) as session:
                async with session.get(request_url, params=request_params) as response:
                    if response.status != 200:
                        logger.warning(
                            f"{self.MARKETPLACE_KEY}: HTTP {response.status} for {url}"
                        )
                        return None
                    content_type = response.content_type or ""
                    if "json" in content_type:
                        return await response.json(content_type=None)
                    return await response.text()
        except aiohttp.ClientError as e:
            logger.warning(f"{self.MARKETPLACE_KEY}: request error: {e}")
            return None
        except Exception as e:
            logger.error(f"{self.MARKETPLACE_KEY}: unexpected error: {e}")
            return None

    async def _get_soup(
        self,
        url: str,
        params: Optional[dict] = None,
        render: bool = True,
    ) -> Optional[BeautifulSoup]:
        html = await self._get(url, params=params, render=render)
        if isinstance(html, str):
            return BeautifulSoup(html, "lxml")
        return None

    def _parse_price(self, text: str) -> float:
        """Extract a numeric price from a text string."""
        nums = re.findall(r'[\d\s]+', text)
        for n in nums:
            cleaned = n.replace(' ', '').replace('\xa0', '')
            if cleaned.isdigit() and int(cleaned) > 100:
                return float(cleaned)
        return 0.0

    def format_price(self, price: float, currency: Optional[str] = None) -> str:
        cur = currency or self.CURRENCY
        if cur == "UZS":
            return f"{price:,.0f} so'm".replace(",", " ")
        elif cur == "RUB":
            return f"₽ {price:,.0f}".replace(",", " ")
        return f"{price:,.0f} {cur}"

    def _make_result(
        self,
        name: str,
        price: float,
        url: str,
        image_url: Optional[str] = None,
        is_available: bool = True,
        currency: Optional[str] = None,
    ) -> ProductResult:
        return ProductResult(
            name=name,
            price=price,
            currency=currency or self.CURRENCY,
            url=url,
            image_url=image_url,
            marketplace=self.MARKETPLACE_NAME,
            marketplace_emoji=self.MARKETPLACE_EMOJI,
            is_available=is_available,
        )
