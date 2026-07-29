"""Multi-platform search tool for target company discovery (Q1).

Supports concurrent search across multiple sources:
  - Tavily (primary, AI-optimized web search)
  - Bing Web Search API (fallback)
  - Google Custom Search (fallback)
  - Direct web scraping for region-specific sources (IHK, etc.)
"""

import asyncio
import json
from typing import Any, Optional

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from config import config


# ──────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────


class SearchResult(BaseModel):
    """A single search result entry."""
    title: str = Field(description="Page title")
    url: str = Field(description="Page URL")
    snippet: str = Field(description="Brief description / snippet")
    source: str = Field(description="Search engine source: tavily / bing / google / direct")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Estimated relevance")


class SearchResponse(BaseModel):
    """Aggregated search response."""
    query: str = Field(description="Original search query")
    results: list[SearchResult] = Field(default_factory=list)
    total_found: int = 0


# ──────────────────────────────────────────────
# Tool implementation
# ──────────────────────────────────────────────


class SearchTools:
    """Search tools with multi-engine fallback and parallel execution."""

    @staticmethod
    async def _search_tavily(query: str, max_results: int = 10) -> list[dict]:
        """Search via Tavily API (primary)."""
        api_key = config.search.api_key
        if not api_key:
            return []

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("results", [])
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                print(f"[SearchTools] Tavily error: {e}")
                return []

    @staticmethod
    async def _search_bing(query: str, max_results: int = 10) -> list[dict]:
        """Search via Bing Web Search API (fallback)."""
        api_key = config.search.bing_api_key  # type: ignore[attr-defined]
        if not api_key:
            return []

        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {"q": query, "count": max_results, "mkt": "en-US"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("webPages", {}).get("value", [])
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                print(f"[SearchTools] Bing error: {e}")
                return []

    @staticmethod
    async def _search_google(query: str, max_results: int = 10) -> list[dict]:
        """Search via Google Custom Search API (fallback)."""
        api_key = config.search.google_api_key  # type: ignore[attr-defined]
        cx = config.search.google_cx  # type: ignore[attr-defined]
        if not api_key or not cx:
            return []

        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": api_key, "cx": cx, "q": query, "num": min(max_results, 10)}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("items", [])
            except (httpx.HTTPError, json.JSONDecodeError) as e:
                print(f"[SearchTools] Google error: {e}")
                return []

    # ── Public API ────────────────────────────────────────

    @classmethod
    async def search(cls, query: str, max_results: int = 10) -> SearchResponse:
        """Execute search across available engines, return merged results.

        Engines run concurrently (Tavily primary, others as fallback).
        Results are merged and deduplicated by URL.
        """
        # Run all available engines in parallel
        tasks = []
        tasks.append(cls._search_tavily(query, max_results))

        # Add fallback engines if configured
        if config.search.bing_api_key:
            tasks.append(cls._search_bing(query, max_results))
        if config.search.google_api_key and config.search.google_cx:
            tasks.append(cls._search_google(query, max_results))

        if not tasks:
            return SearchResponse(query=query, results=[], total_found=0)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Merge and deduplicate
        seen_urls: set[str] = set()
        merged: list[SearchResult] = []

        engine_names = ["tavily", "bing", "google"]
        for engine_idx, engine_results in enumerate(results):
            if isinstance(engine_results, Exception):
                continue
            source_name = engine_names[engine_idx] if engine_idx < len(engine_names) else "unknown"

            for item in engine_results:
                url = item.get("url", "") or item.get("link", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                merged.append(SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("content", "") or item.get("snippet", ""),
                    source=source_name,
                    confidence=0.9 if source_name == "tavily" else 0.7,
                ))

        return SearchResponse(query=query, results=merged[:max_results], total_found=len(merged))

    @classmethod
    async def search_multi(
        cls, queries: list[str], max_results_per_query: int = 5
    ) -> list[SearchResponse]:
        """Execute multiple search queries concurrently."""
        tasks = [cls.search(q, max_results_per_query) for q in queries]
        return await asyncio.gather(*tasks)


# ──────────────────────────────────────────────
# LangChain Tool wrappers
# ──────────────────────────────────────────────


@tool
async def search_companies(query: str, max_results: int = 10) -> str:
    """Search for companies matching a description.

    Use this when you need to find companies by industry, region, or product type.
    Example queries: 'German tooling manufacturers', 'Japanese automotive parts suppliers'.

    Args:
        query: natural language search query describing target companies
        max_results: maximum results to return (default 10)

    Returns:
        JSON string with company name, URL, and description for each result.
    """
    response = await SearchTools.search(query, max_results)
    return response.model_dump_json(ensure_ascii=False, indent=2)


@tool
async def search_company_contacts(company_name: str) -> str:
    """Search for contact information of a specific company.

    Use this when you need to find email, phone, or LinkedIn for a known company.

    Args:
        company_name: the full company name to search for

    Returns:
        JSON string with contact details found.
    """
    queries = [
        f"{company_name} official website",
        f"{company_name} email contact",
        f"{company_name} LinkedIn",
    ]
    responses = await SearchTools.search_multi(queries, max_results_per_query=3)
    merged = SearchResponse(query=company_name, results=[], total_found=0)
    for resp in responses:
        for r in resp.results:
            if r.url not in {x.url for x in merged.results}:
                merged.results.append(r)
                merged.total_found += 1
    return merged.model_dump_json(ensure_ascii=False, indent=2)
