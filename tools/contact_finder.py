"""Contact information discovery tool.

Multi-strategy contact finder:
  A. Scrape Contact/About page for listed emails and phones
  B. Search engine query "company_name email" or "company_name contact"
  C. Domain-based pattern guessing (info@, contact@, sales@)
"""

import asyncio
import re
from typing import Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from models.contact import ContactCreate
from tools.scrape_tool import WebScraper, ScrapedPage
from tools.search_tool import SearchTools, SearchResult

# ──────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────


class ContactDiscoveryResult(BaseModel):
    """Aggregated contact discovery result."""
    company_name: str
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    contact_page_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    sources: list[str] = Field(default_factory=list, description="Where each contact was found")


# ──────────────────────────────────────────────
# Contact finder
# ──────────────────────────────────────────────


class ContactFinder:
    """Multi-strategy contact information discovery."""

    COMMON_PATHS = [
        "/contact", "/contact-us", "/contactus",
        "/about", "/about-us",
        "/support", "/help",
        "/company", "/company/contact",
    ]

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

    @staticmethod
    def _guess_emails_from_domain(domain: str) -> list[str]:
        """Generate probable email addresses from domain."""
        prefixes = ["info", "contact", "sales", "support", "hello", "inquiry"]
        return [f"{p}@{domain}" for p in prefixes]

    @classmethod
    async def _check_common_pages(cls, base_url: str) -> list[ScrapedPage]:
        """Scrape common contact-related pages concurrently."""
        urls = [f"{base_url.rstrip('/')}{path}" for path in cls.COMMON_PATHS]
        tasks = [WebScraper.scrape(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, ScrapedPage) and r.success]

    @classmethod
    async def find_contacts(
        cls, company_name: str, website_url: Optional[str] = None
    ) -> ContactDiscoveryResult:
        """Discover contact information for a company using all available strategies."""
        result = ContactDiscoveryResult(company_name=company_name)
        seen_emails: set[str] = set()

        # ── Strategy A: Scrape common pages ────────────
        if website_url:
            pages = await cls._check_common_pages(website_url)

            for page in pages:
                for e in page.emails:
                    if e not in seen_emails:
                        seen_emails.add(e)
                        result.emails.append(e)
                        result.sources.append(f"Scraped: {page.url}")

                result.phones.extend(page.phones)

                # Track contact page URL
                if "contact" in page.url.lower():
                    result.contact_page_url = page.url

                # Check for LinkedIn
                for link in page.links:
                    if "linkedin.com/company/" in link.lower():
                        result.linkedin_url = link

        # ── Strategy B: Search engine ──────────────────
        search_query = f"{company_name} email contact"
        search_resp = await SearchTools.search(search_query, max_results=5)

        for sr in search_resp.results:
            found_emails = cls.EMAIL_RE.findall(sr.snippet)
            for e in found_emails:
                if e not in seen_emails:
                    seen_emails.add(e)
                    result.emails.append(e)
                    result.sources.append(f"Search: {sr.url}")

            if "linkedin.com/company/" in sr.url and not result.linkedin_url:
                result.linkedin_url = sr.url

        # ── Strategy C: Domain pattern guessing ────────
        if website_url:
            from urllib.parse import urlparse
            parsed = urlparse(website_url)
            domain = parsed.netloc or parsed.path
            domain = domain.replace("www.", "")

            guessed = cls._guess_emails_from_domain(domain)
            for e in guessed:
                if e not in seen_emails:
                    seen_emails.add(e)
                    result.emails.append(e)
                    result.sources.append(f"Domain guess: {domain}")

        # Deduplicate phones
        result.phones = list(set(result.phones))

        return result


# ──────────────────────────────────────────────
# LangChain Tool wrappers
# ──────────────────────────────────────────────


@tool
async def find_contact_info(company_name: str, website_url: str = "") -> str:
    """Find contact information for a company.

    Searches the company website and web for email addresses, phone numbers,
    and LinkedIn profile. Uses multiple discovery strategies.

    Args:
        company_name: name of the company to find contacts for
        website_url: optional company website URL (providing this improves results)

    Returns:
        JSON string with found emails, phones, and LinkedIn URL.
    """
    url = website_url or ""
    result = await ContactFinder.find_contacts(company_name, url)
    return result.model_dump_json(ensure_ascii=False, indent=2)
