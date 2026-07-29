"""Company information extraction tool.

Takes a company website URL or name, scrapes available pages,
and uses an LLM to extract structured company information.
"""

from typing import Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from llm_utils import get_llm
from models.company import CompanyCreate
from tools.scrape_tool import WebScraper

# ──────────────────────────────────────────────
# LLM-powered extraction chain (lazy-init)
# ──────────────────────────────────────────────


_COMPANY_PARSER = PydanticOutputParser(pydantic_object=CompanyCreate)

_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a business research assistant. Extract structured company "
        "information from the provided web content.\n\n"
        "Only include information that is explicitly stated in the content. "
        "If a field is not found, leave it as null.\n\n"
        "{format_instructions}",
    ),
    (
        "human",
        "Company name: {company_name}\n"
        "Website: {website_url}\n\n"
        "Web content:\n{web_content}\n\n"
        "Extract structured company information:",
    ),
])


def _get_chain():
    """Build extraction chain lazily so LLM config is ready at call time."""
    return _EXTRACTION_PROMPT | get_llm() | _COMPANY_PARSER


# ──────────────────────────────────────────────
# Tool implementation
# ──────────────────────────────────────────────


@tool
async def extract_company_info(company_name: str, website_url: str) -> str:
    """Extract structured company information from a website.

    Scrapes the company website and uses AI to extract fields like
    industry, description, employee count, revenue, and tech focus.

    Args:
        company_name: name of the company
        website_url: full URL of the company website

    Returns:
        JSON string with structured company information.
    """
    homepage = await WebScraper.scrape(website_url)
    about_page = await WebScraper.scrape(f"{website_url.rstrip('/')}/about")

    combined_content = f"=== Homepage ===\n{homepage.text_content}\n\n"
    if about_page.success:
        combined_content += f"=== About Page ===\n{about_page.text_content}"

    try:
        chain = _get_chain()
        company = await chain.ainvoke({
            "company_name": company_name,
            "website_url": website_url,
            "web_content": combined_content[:8000],
            "format_instructions": _COMPANY_PARSER.get_format_instructions(),
        })
        return company.model_dump_json(ensure_ascii=False, indent=2)
    except Exception as e:
        result = CompanyCreate(
            name=company_name,
            website=website_url,
            description=homepage.meta_description or homepage.text_content[:500],
        )
        return result.model_dump_json(ensure_ascii=False, indent=2)
