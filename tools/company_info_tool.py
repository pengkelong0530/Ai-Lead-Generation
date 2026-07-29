"""Company information extraction tool.

Takes a company website URL or name, scrapes available pages,
and uses an LLM to extract structured company information.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from config import config
from models.company import CompanyCreate
from tools.scrape_tool import WebScraper

# ──────────────────────────────────────────────
# LLM-powered extraction chain
# ──────────────────────────────────────────────


def _get_llm() -> BaseChatModel:
    """Get configured LLM instance."""
    return ChatOpenAI(
        model=config.llm.model,
        temperature=config.llm.temperature,
        api_key=config.llm.openai_api_key,
    )


# Parser that validates output matches CompanyCreate schema
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

_EXTRACTION_CHAIN = _EXTRACTION_PROMPT | _get_llm() | _COMPANY_PARSER


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
    # Scrape the website
    homepage = await WebScraper.scrape(website_url)
    about_page = await WebScraper.scrape(f"{website_url.rstrip('/')}/about")

    # Combine content from both pages
    combined_content = f"=== Homepage ===\n{homepage.text_content}\n\n"
    if about_page.success:
        combined_content += f"=== About Page ===\n{about_page.text_content}"

    try:
        company = await _EXTRACTION_CHAIN.ainvoke({
            "company_name": company_name,
            "website_url": website_url,
            "web_content": combined_content[:8000],
            "format_instructions": _COMPANY_PARSER.get_format_instructions(),
        })
        return company.model_dump_json(ensure_ascii=False, indent=2)
    except Exception as e:
        # Fallback: return basic info without LLM
        result = CompanyCreate(
            name=company_name,
            website=website_url,
            description=homepage.meta_description or homepage.text_content[:500],
        )
        return result.model_dump_json(ensure_ascii=False, indent=2)
