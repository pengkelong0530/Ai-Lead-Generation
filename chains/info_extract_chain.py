"""Information refinement chain.

Takes raw scraped web content and extracts structured,
cleaned company information. Complementary to the search/scrape tools —
this chain is used when you need deeper, more accurate extraction
from already-collected content.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import config
from models.company import CompanyCreate


class ExtractionResult(BaseModel):
    """Refined extraction from raw web content."""
    company_name: str = Field(description="Full legal company name")
    industry: str = Field(description="Primary industry classification")
    description: str = Field(description="Clean 2-3 sentence business description")
    products_services: list[str] = Field(description="Key products or services offered")
    technology_focus: Optional[str] = Field(None, description="Relevant technologies used")
    employee_estimate: Optional[str] = Field(None, description="Estimated employee count range")
    revenue_estimate: Optional[str] = Field(None, description="Estimated revenue range")
    headquarters: Optional[str] = Field(None, description="HQ location")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence in extraction")


_EXTRACT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a business information extraction specialist. Extract structured "
        "company information from the provided web content. Be precise: only include "
        "information explicitly stated or strongly implied in the content.\n\n"
        "{format_instructions}",
    ),
    (
        "human",
        "**Source URL:** {source_url}\n"
        "**Company name:** {company_name}\n\n"
        "**Web Content:**\n{web_content}\n\n"
        "Extract structured company information:",
    ),
])


def _get_llm() -> BaseChatModel:
    return ChatOpenAI(
        model=config.llm.model,
        temperature=config.llm.temperature,
        api_key=config.llm.openai_api_key,
    )


_EXTRACT_PARSER = PydanticOutputParser(pydantic_object=ExtractionResult)


def build_extraction_chain() -> RunnableSerializable:
    chain: RunnableSerializable = _EXTRACT_PROMPT | _get_llm() | _EXTRACT_PARSER
    return chain


async def extract_company_details(
    company_name: str,
    web_content: str,
    source_url: str = "",
) -> ExtractionResult:
    """Extract structured company details from raw web content."""
    chain = build_extraction_chain()
    result: ExtractionResult = await chain.ainvoke({
        "company_name": company_name,
        "web_content": web_content[:8000],
        "source_url": source_url or "Unknown",
        "format_instructions": _EXTRACT_PARSER.get_format_instructions(),
    })
    return result


def extraction_to_company_create(
    extraction: ExtractionResult,
    source: str = "",
    session_id: Optional[str] = None,
) -> CompanyCreate:
    """Convert an ExtractionResult to a CompanyCreate model for DB persistence."""
    return CompanyCreate(
        name=extraction.company_name,
        industry=extraction.industry,
        region=extraction.headquarters,
        description=extraction.description,
        employee_count=extraction.employee_estimate,
        revenue_estimate=extraction.revenue_estimate,
        technology_focus=extraction.technology_focus,
        source=source,
        confidence=extraction.confidence,
        session_id=session_id,
    )
