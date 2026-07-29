"""Customer scoring chain (Q2).

Calculates a weighted ICP matching score (0-100) for each company.
Uses LLM to evaluate each dimension, then applies configurable weights.

Scoring formula:
  total = industry_match * 0.40 + size_match * 0.25 +
          demand_match * 0.25 + region_priority * 0.10
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel, Field

from models.score import CompanyScore, ICPCriteria, ScoreWeights

# ──────────────────────────────────────────────
# Output model
# ──────────────────────────────────────────────


class ScoringInput(BaseModel):
    """Input to the scoring chain."""
    company_name: str
    company_description: str
    industry: str
    region: str
    employee_count: Optional[str] = None
    technology_focus: Optional[str] = None
    user_requirement: str
    target_industry: str
    target_region: str


# ──────────────────────────────────────────────
# Prompt template
# ──────────────────────────────────────────────

_SCORING_SYSTEM_PROMPT = """You are a B2B lead scoring analyst. Your job is to evaluate \
how well a company matches an Ideal Customer Profile (ICP) for PVD/CVD vacuum coating equipment.

Score each dimension from 0-100 using the rubric below:

**1. Industry Match (weight 40%)**
- 90-100: Primary target (tooling, mold/die, automotive parts, medical devices)
- 70-89: Adjacent industry with known coating needs
- 40-69: General manufacturing, possible need
- 0-39: Unrelated industry, unlikely need

**2. Company Size Match (weight 25%)**
- 90-100: Large enterprise (500+ employees) — production-scale buying power
- 70-89: Medium enterprise (100-499) — likely has coating operations
- 40-69: Small manufacturer (20-99) — may outsource coating
- 0-39: Very small (<20) — unlikely to purchase coating equipment

**3. Technology/Demand Match (weight 25%)**
- 90-100: Explicit mention of PVD/CVD/coating/vacuum/ surface treatment
- 70-89: Related processes (heat treatment, plating, finishing)
- 40-69: General manufacturing with possible surface treatment
- 0-39: No relevant technology indicators

**4. Region Priority (weight 10%)**
- 90-100: Primary target region (specified by user)
- 70-89: Industrial region in target country
- 40-69: Industrial region in nearby country
- 0-39: Non-target or remote region

Output the score for each dimension plus the weighted total, detailed reasoning, \
and a clear recommendation."""

_SCORING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SCORING_SYSTEM_PROMPT),
    (
        "human",
        "**Company:** {company_name}\n"
        "**Industry:** {industry}\n"
        "**Region:** {region}\n"
        "**Description:** {company_description}\n"
        "**Employees:** {employee_count}\n"
        "**Technology focus:** {technology_focus}\n\n"
        "**User Requirement:** {user_requirement}\n"
        "**Target Industry:** {target_industry}\n"
        "**Target Region:** {target_region}\n\n"
        "Evaluate each scoring dimension and provide the weighted total.\n\n"
        "{format_instructions}",
    ),
])


# ──────────────────────────────────────────────
# Internal scoring model for LLM output
# ──────────────────────────────────────────────


class _RawScores(BaseModel):
    """Raw dimension scores from LLM before weighting."""
    industry_match_score: int = Field(ge=0, le=100, description="Industry match score")
    size_match_score: int = Field(ge=0, le=100, description="Company size match score")
    demand_match_score: int = Field(ge=0, le=100, description="Technology/demand match score")
    region_priority_score: int = Field(ge=0, le=100, description="Region priority score")
    industry_reasoning: str = Field(description="Reasoning for industry score")
    size_reasoning: str = Field(description="Reasoning for size score")
    demand_reasoning: str = Field(description="Reasoning for demand score")
    region_reasoning: str = Field(description="Reasoning for region score")
    recommendation: str = Field(description="Develop / Follow-up / Skip")


# ──────────────────────────────────────────────
# Scoring chain
# ──────────────────────────────────────────────


def _get_llm() -> BaseChatModel:
    from llm_utils import get_llm as build_llm
    return build_llm()


def _compute_weighted_score(
    raw: _RawScores, weights: Optional[ScoreWeights] = None
) -> int:
    """Apply weighted formula to raw dimension scores."""
    w = weights or ScoreWeights()
    total = (
        raw.industry_match_score * w.industry_weight
        + raw.size_match_score * w.size_weight
        + raw.demand_match_score * w.demand_weight
        + raw.region_priority_score * w.region_weight
    )
    return round(total)


def build_scoring_chain() -> RunnableSerializable:
    """Build the lead scoring chain.

    Returns a Runnable that accepts ScoringInput fields
    and returns a CompanyScore.
    """
    parser = PydanticOutputParser(pydantic_object=_RawScores)

    chain: RunnableSerializable = _SCORING_PROMPT | _get_llm() | parser
    return chain


async def score_company(
    company_name: str,
    company_description: str,
    user_requirement: str,
    industry: str = "",
    region: str = "",
    target_industry: str = "",
    target_region: str = "",
    employee_count: Optional[str] = None,
    technology_focus: Optional[str] = None,
    weights: Optional[ScoreWeights] = None,
) -> CompanyScore:
    """Convenience function: score a single company and return weighted result."""
    chain = build_scoring_chain()

    raw: _RawScores = await chain.ainvoke({
        "company_name": company_name,
        "industry": industry or "Unknown",
        "region": region or "Unknown",
        "company_description": company_description or "No description available",
        "employee_count": employee_count or "Not specified",
        "technology_focus": technology_focus or "Not specified",
        "user_requirement": user_requirement,
        "target_industry": target_industry or "Not specified",
        "target_region": target_region or "Not specified",
        "format_instructions": PydanticOutputParser(
            pydantic_object=_RawScores
        ).get_format_instructions(),
    })

    total = _compute_weighted_score(raw, weights)
    criteria = ICPCriteria(
        industry_match=raw.industry_match_score,
        size_match=raw.size_match_score,
        demand_match=raw.demand_match_score,
        region_priority=raw.region_priority_score,
    )

    reasoning_parts = [
        f"Industry ({raw.industry_match_score}/100): {raw.industry_reasoning}",
        f"Size ({raw.size_match_score}/100): {raw.size_reasoning}",
        f"Demand ({raw.demand_match_score}/100): {raw.demand_reasoning}",
        f"Region ({raw.region_priority_score}/100): {raw.region_reasoning}",
    ]

    return CompanyScore(
        company_id=0,  # Assigned when saved to DB
        company_name=company_name,
        icp_criteria=criteria,
        total_score=total,
        reasoning="\n".join(reasoning_parts),
        recommendation=raw.recommendation,
    )
