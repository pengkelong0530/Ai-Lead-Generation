"""Research sub-agent: searches and collects company information.

Takes user requirements, searches for target companies across multiple platforms,
scrapes their websites, and extracts structured data.
"""

from typing import Optional

from models.company import CompanyCreate
from tools.search_tool import SearchTools, SearchResult
from tools.scrape_tool import WebScraper
from chains.info_extract_chain import extract_company_details, extraction_to_company_create


class ResearchAgent:
    """Sub-agent focused on company research and data collection."""

    @staticmethod
    def _build_search_queries(
        industry: str,
        region: str,
        product: str = "",
    ) -> list[str]:
        """Build targeted search queries based on user requirements."""
        base_queries = [
            f"{region} {industry} manufacturers",
            f"{region} {industry} companies list",
            f"{region} {industry} industry directory",
        ]
        if product:
            base_queries.append(f"{region} {industry} {product}")
            base_queries.append(f"{region} {industry} surface coating")
            base_queries.append(f"{region} PVD coating {industry}")
        return base_queries

    @staticmethod
    def _parse_requirement(user_input: str) -> dict[str, str]:
        """Simple rule-based parsing of user requirement.

        In production, this would use an LLM; for now we use keyword extraction
        to keep the supervisor prompt lean. The extracted fields serve as
        starting context for the chains which do full LLM-based understanding.
        """
        result = {
            "raw": user_input,
            "industry": "",
            "region": "",
            "product": "PVD CVD coating equipment",
        }

        user_lower = user_input.lower()

        # Region extraction (English + Chinese keywords)
        region_keywords = {
            "germany": "Germany", "german": "Germany", "德国": "Germany",
            "japan": "Japan", "japanese": "Japan", "日本": "Japan",
            "china": "China", "chinese": "China", "中国": "China",
            "usa": "USA", "united states": "USA", "american": "USA", "美国": "USA",
            "korea": "South Korea", "south korea": "South Korea", "韩国": "South Korea",
            "taiwan": "Taiwan", "台湾": "Taiwan",
            "india": "India", "印度": "India",
            "italy": "Italy", "意大利": "Italy",
            "france": "France", "法国": "France",
            "uk": "UK", "united kingdom": "UK", "英国": "UK",
            "europe": "Europe", "european": "Europe", "欧洲": "Europe",
        }
        for kw, region in region_keywords.items():
            if kw in user_lower:
                result["region"] = region
                break

        # Industry extraction
        industry_keywords = {
            "tool": "Cutting Tools",
            "刀具": "Cutting Tools",
            "mold": "Mold & Die",
            "模具": "Mold & Die",
            "automotive": "Automotive Parts",
            "汽车": "Automotive Parts",
            "medical": "Medical Devices",
            "医疗器械": "Medical Devices",
            "aerospace": "Aerospace Components",
            "电子": "Electronics",
            "electronics": "Electronics",
            "hardware": "Hardware & Decorative",
        }
        for kw, ind in industry_keywords.items():
            if kw in user_lower:
                result["industry"] = ind
                break

        return result

    @classmethod
    async def search_target_companies(
        cls,
        user_input: str,
        max_results: int = 15,
    ) -> tuple[list[SearchResult], dict[str, str]]:
        """Search for target companies based on user requirements.

        Returns:
            (list of SearchResult, parsed requirement dict)
        """
        parsed = cls._parse_requirement(user_input)
        queries = cls._build_search_queries(
            industry=parsed["industry"],
            region=parsed["region"],
            product=parsed["product"],
        )

        all_results: list[SearchResult] = []
        seen_urls: set[str] = set()

        responses = await SearchTools.search_multi(queries, max_results_per_query=5)
        for resp in responses:
            for r in resp.results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_results.append(r)

        # Sort by confidence, return top N
        all_results.sort(key=lambda x: x.confidence, reverse=True)
        return all_results[:max_results], parsed

    @classmethod
    async def research_company(
        cls,
        company_name: str,
        website_url: Optional[str] = None,
    ) -> Optional[CompanyCreate]:
        """Research a single company: scrape website + extract structured info.

        Returns a CompanyCreate model ready for DB storage.
        """
        # Scrape website
        url = website_url or ""
        if not url:
            # Search for the company website
            search_resp = await SearchTools.search(f"{company_name} official website", 3)
            for r in search_resp.results:
                if "wikipedia" not in r.url:
                    url = r.url
                    break

        if url:
            page = await WebScraper.scrape(url)
            if page.success:
                extraction = await extract_company_details(
                    company_name=company_name,
                    web_content=page.text_content,
                    source_url=url,
                )
                return extraction_to_company_create(
                    extraction=extraction,
                    source="web_research",
                )

        # Minimal fallback
        return CompanyCreate(name=company_name)
