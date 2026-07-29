"""ICP (Ideal Customer Profile) filtering chain.

Evaluates a candidate company against user-defined ICP criteria using LLM
reasoning. Determines whether the company is a target customer and why.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel, Field

from config import config


# ──────────────────────────────────────────────
# Output model
# ──────────────────────────────────────────────


class ICPAssessment(BaseModel):
    """ICP assessment result for a single company."""
    company_name: str = Field(description="Company name being assessed")
    is_match: bool = Field(description="Whether the company matches the ICP")
    match_reason: str = Field(description="Summary of why it matches or not")
    industry_relevance: str = Field(description="Industry alignment assessment")
    size_fit: str = Field(description="Company size / scale assessment")
    demand_indicators: str = Field(description="Evidence of need for PVD/CVD coating")
    region_note: str = Field(description="Region-specific considerations")
    concerns: str = Field(description="Potential concerns or mismatches")


class ICPFilterResult(BaseModel):
    """Aggregated ICP filter result."""
    total_candidates: int = Field(description="Number of companies assessed")
    matched: list[ICPAssessment] = Field(default_factory=list)
    not_matched: list[ICPAssessment] = Field(default_factory=list)


# ──────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────

_ICP_SYSTEM_PROMPT = """You are an expert B2B sales qualification analyst specializing in \
industrial manufacturing and PVD/CVD coating equipment.

Your task is to evaluate whether a company fits the Ideal Customer Profile (ICP) for \
a vacuum coating equipment manufacturer.

**Our ICP Definition:**
- **Target Industry**: Industrial manufacturers requiring surface coating (PVD/CVD)
- **Typical Segments**: Cutting tools, molds/dies, automotive parts, medical devices, decorative hardware
- **Need Indicator**: Companies that manufacture products where wear resistance, hardness, or decorative coating is critical
- **Geography**: Global, with focus on manufacturing-heavy regions
- **Size Range**: Medium to large enterprises with production-scale coating needs

Evaluate each company carefully. Consider their business description, products, and industry.
Be conservative - only classify as "match" if there is reasonable evidence of potential need."""

_ICP_ASSESSMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _ICP_SYSTEM_PROMPT),
    (
        "human",
        "**User Requirement Context:**\n"
        "{user_requirement}\n\n"
        "**Target Industry:** {target_industry}\n"
        "**Target Region:** {target_region}\n\n"
        "**Company to evaluate:**\n"
        "- Name: {company_name}\n"
        "- Industry: {company_industry}\n"
        "- Description: {company_description}\n"
        "- Technology focus: {technology_focus}\n"
        "- Employee count: {employee_count}\n"
        "- Region: {company_region}\n\n"
        "Assess this company against the ICP.\n\n"
        "{format_instructions}",
    ),
])


# ──────────────────────────────────────────────
# Chain factory
# ──────────────────────────────────────────────


def _get_llm() -> BaseChatModel:
    from llm_utils import get_llm as build_llm
    return build_llm()


def build_icp_filter_chain() -> RunnableSerializable:
    """Build the ICP assessment chain.

    Returns a Runnable that accepts:
        user_requirement, target_industry, target_region,
        company_name, company_industry, company_description,
        technology_focus, employee_count, company_region

    And returns an ICPAssessment.
    """
    parser = PydanticOutputParser(pydantic_object=ICPAssessment)

    chain: RunnableSerializable = _ICP_ASSESSMENT_PROMPT | _get_llm() | parser
    return chain


async def assess_icp(
    company_name: str,
    company_description: str,
    user_requirement: str,
    target_industry: str = "",
    target_region: str = "",
    company_industry: Optional[str] = None,
    technology_focus: Optional[str] = None,
    employee_count: Optional[str] = None,
    company_region: Optional[str] = None,
) -> ICPAssessment:
    """Convenience function: assess a single company's ICP fit."""
    chain = build_icp_filter_chain()
    result = await chain.ainvoke({
        "user_requirement": user_requirement,
        "target_industry": target_industry,
        "target_region": target_region,
        "company_name": company_name,
        "company_industry": company_industry or "Unknown",
        "company_description": company_description or "No description available",
        "technology_focus": technology_focus or "Not specified",
        "employee_count": employee_count or "Not specified",
        "company_region": company_region or "Not specified",
        "format_instructions": PydanticOutputParser(
            pydantic_object=ICPAssessment
        ).get_format_instructions(),
    })
    return result
