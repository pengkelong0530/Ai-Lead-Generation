"""Web scraping tool with Playwright + BeautifulSoup.

Handles dynamic pages (JS-rendered) gracefully via Playwright,
with a fallback to static requests via httpx + BeautifulSoup.
Extracts structured content from common page types:
  - About page: company description, history, team
  - Product page: product lines, technology focus
  - Contact page: email, phone, address
"""

import asyncio
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ──────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────


class ScrapedPage(BaseModel):
    """Structured representation of a scraped web page."""
    url: str = Field(description="Source URL")
    title: str = Field(default="", description="Page title")
    text_content: str = Field(default="", description="Cleaned visible text")
    meta_description: str = Field(default="", description="Meta description content")
    links: list[str] = Field(default_factory=list, description="All links found on page")
    emails: list[str] = Field(default_factory=list, description="Email addresses found")
    phones: list[str] = Field(default_factory=list, description="Phone numbers found")
    success: bool = True
    error: Optional[str] = None


# ──────────────────────────────────────────────
# Scraper implementation
# ──────────────────────────────────────────────


class WebScraper:
    """Web scraper with static + dynamic rendering support."""

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    PHONE_RE = re.compile(
        r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,9}"
    )

    @staticmethod
    async def _fetch_static(url: str, timeout: int = 15) -> Optional[str]:
        """Fetch page content via static HTTP request."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8,ja;q=0.7",
        }
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return resp.text
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                return None

    @staticmethod
    async def _fetch_dynamic(url: str, timeout: int = 30) -> Optional[str]:
        """Fetch page content via Playwright (JS-rendered pages)."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                await page.wait_for_timeout(2000)  # Allow JS to finish
                content = await page.content()
                await browser.close()
                return content
        except Exception:
            return None

    @classmethod
    def _parse_html(cls, html: str, url: str) -> ScrapedPage:
        """Parse HTML content into structured data."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_tag.get("content", "") if isinstance(meta_tag, Tag) else ""

        # Extract clean text
        text_content = soup.get_text(separator="\n", strip=True)
        text_content = re.sub(r"\n{3,}", "\n\n", text_content)

        # Extract links
        links: list[str] = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("http"):
                links.append(href)

        # Extract emails and phones from text
        emails = list(set(cls.EMAIL_RE.findall(text_content)))
        phones = list(set(cls.PHONE_RE.findall(text_content)))
        # Filter obvious non-phone matches
        phones = [p for p in phones if len(p) >= 6]

        return ScrapedPage(
            url=url,
            title=title,
            text_content=text_content[:10000],  # Cap at 10k chars
            meta_description=meta_desc,
            links=links,
            emails=emails,
            phones=phones,
        )

    @classmethod
    async def scrape(cls, url: str, dynamic: bool = False) -> ScrapedPage:
        """Scrape a URL. Try static first, fall back to dynamic if requested."""
        html = await cls._fetch_static(url)

        if html is None and dynamic:
            html = await cls._fetch_dynamic(url)

        if html is None:
            return ScrapedPage(url=url, success=False, error="Failed to fetch URL")

        return cls._parse_html(html, url)


# ──────────────────────────────────────────────
# LangChain Tool wrappers
# ──────────────────────────────────────────────


@tool
async def scrape_website(url: str) -> str:
    """Scrape and extract structured content from a company website.

    Use this to get company descriptions, product info, and contact details
    from a company's official website or any other URL.

    Args:
        url: full URL to scrape (including https://)

    Returns:
        JSON string with title, text content, links, emails, and phones found.
    """
    page = await WebScraper.scrape(url)
    return page.model_dump_json(ensure_ascii=False, indent=2)


@tool
async def scrape_company_about(website_url: str) -> str:
    """Scrape a company's About or About Us page for company description.

    Args:
        website_url: base company website URL

    Returns:
        JSON string with company description and extracted info.
    """
    # Common about page paths
    about_paths = [
        website_url.rstrip("/"),
        f"{website_url.rstrip('/')}/about",
        f"{website_url.rstrip('/')}/about-us",
        f"{website_url.rstrip('/')}/company",
        f"{website_url.rstrip('/')}/company/about",
    ]

    pages = await asyncio.gather(
        *[WebScraper.scrape(p) for p in about_paths],
        return_exceptions=True,
    )

    best: Optional[ScrapedPage] = None
    best_length = 0
    for p in pages:
        if isinstance(p, ScrapedPage) and p.success:
            length = len(p.text_content)
            if length > best_length and "about" in p.text_content[:500].lower():
                best_length = length
                best = p

    if best is None:
        # Fall back to homepage
        best = await WebScraper.scrape(website_url)

    return best.model_dump_json(ensure_ascii=False, indent=2) if best else ScrapedPage(
        url=website_url, success=False, error="No about page found"
    ).model_dump_json(ensure_ascii=False, indent=2)
