"""Self-reflection chain (自我反思 / Self-Critique).

After key pipeline nodes, this chain reviews the output for quality,
accuracy, and completeness. Provides a critique score and actionable
improvement suggestions.

Used in:
  - After ICP screening: "Are these assessments accurate?"
  - After email generation: "Are these emails effective?"
  - After company research: "Is the data reliable?"
"""

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Output model
# ──────────────────────────────────────────────


class ReflectionResult(BaseModel):
    """Result of a self-reflection / critique pass."""
    quality_score: int = Field(ge=1, le=10, description="Overall quality score (1-10)")
    critique: str = Field(description="Constructive critique of the output")
    strengths: list[str] = Field(description="What was done well")
    weaknesses: list[str] = Field(description="What could be improved")
    specific_suggestions: list[str] = Field(
        description="Actionable suggestions for improvement"
    )
    should_revise: bool = Field(
        description="Whether this output should be regenerated"
    )
    revised_prompt_hint: str = Field(
        default="",
        description="Hint for how to prompt the revision",
    )


# ──────────────────────────────────────────────
# Reflection variants
# ──────────────────────────────────────────────

_REFLECTION_SYSTEM_PROMPT = """You are a quality assurance reviewer for an AI-powered B2B \
lead generation system. Your job is to critically review the output of each pipeline stage \
and provide honest, constructive feedback.

**Review Principles:**
- Be critical but constructive — identify specific issues, not vague concerns
- Check for accuracy, completeness, and relevance
- Flag any claims that seem exaggerated or unsupported
- Consider the B2B industrial sales context
- If quality is high (score >= 8/10), still note minor improvements
- If quality is low (score < 6/10), recommend regeneration with specific guidance

**Scoring Rubric:**
- 9-10: Excellent — accurate, complete, well-targeted
- 7-8: Good — minor issues, usable as-is
- 5-6: Acceptable — has issues but can be fixed with edits
- 3-4: Poor — significant problems, should revise
- 1-2: Unacceptable — must regenerate"""

_REFLECTION_ICP_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _REFLECTION_SYSTEM_PROMPT),
    (
        "human",
        "**Stage:** ICP Screening & Scoring\n"
        "**Target Industry:** {target_industry}\n"
        "**Target Region:** {target_region}\n"
        "**User Requirement:** {user_requirement}\n\n"
        "**Output to Review:**\n{output_to_review}\n\n"
        "Critique this ICP screening output. Consider:\n"
        "1. Are the assessments well-reasoned?\n"
        "2. Is there sufficient evidence for each match/non-match?\n"
        "3. Are the scores consistent with the rubric?\n"
        "4. Are any high-value companies potentially missed?\n\n"
        "{format_instructions}",
    ),
])

_REFLECTION_EMAIL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _REFLECTION_SYSTEM_PROMPT),
    (
        "human",
        "**Stage:** Email Outreach Generation\n"
        "**Target Company:** {company_name}\n"
        "**Company Industry:** {company_industry}\n"
        "**User Requirement:** {user_requirement}\n\n"
        "**Output to Review:**\n{output_to_review}\n\n"
        "Critique this email sequence. Consider:\n"
        "1. Is the tone appropriate for B2B industrial sales?\n"
        "2. Is the value proposition clear and specific?\n"
        "3. Are the CTAs effective and varied across the sequence?\n"
        "4. Is the personalization sufficient?\n"
        "5. Are there any spelling, grammar, or tone issues?\n\n"
        "{format_instructions}",
    ),
])

_REFLECTION_RESEARCH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _REFLECTION_SYSTEM_PROMPT),
    (
        "human",
        "**Stage:** Company Research & Data Collection\n"
        "**Target Company:** {company_name}\n\n"
        "**Output to Review:**\n{output_to_review}\n\n"
        "Critique this research output. Consider:\n"
        "1. Is the company description accurate and informative?\n"
        "2. Are the technology focus areas relevant?\n"
        "3. Is the data complete enough for sales outreach?\n"
        "4. Are there any red flags about data reliability?\n\n"
        "{format_instructions}",
    ),
])


# ──────────────────────────────────────────────
# Reflection chain builds
# ──────────────────────────────────────────────


def _get_llm() -> BaseChatModel:
    from llm_utils import get_llm as build_llm
    return build_llm(temperature=0.2)


_PARSER = PydanticOutputParser(pydantic_object=ReflectionResult)


def build_icp_reflection_chain() -> RunnableSerializable:
    """Build a self-reflection chain for ICP screening output."""
    return _REFLECTION_ICP_PROMPT | _get_llm() | _PARSER


def build_email_reflection_chain() -> RunnableSerializable:
    """Build a self-reflection chain for email generation output."""
    return _REFLECTION_EMAIL_PROMPT | _get_llm() | _PARSER


def build_research_reflection_chain() -> RunnableSerializable:
    """Build a self-reflection chain for company research output."""
    return _REFLECTION_RESEARCH_PROMPT | _get_llm() | _PARSER


# ──────────────────────────────────────────────
# Convenience functions
# ──────────────────────────────────────────────


async def reflect_on_icp(
    output_to_review: str,
    target_industry: str = "",
    target_region: str = "",
    user_requirement: str = "",
) -> ReflectionResult:
    """Run self-reflection on ICP screening output."""
    chain = build_icp_reflection_chain()
    return await chain.ainvoke({
        "output_to_review": output_to_review[:4000],
        "target_industry": target_industry or "Not specified",
        "target_region": target_region or "Not specified",
        "user_requirement": user_requirement or "Not specified",
        "format_instructions": _PARSER.get_format_instructions(),
    })


async def reflect_on_emails(
    output_to_review: str,
    company_name: str,
    company_industry: str = "",
    user_requirement: str = "",
) -> ReflectionResult:
    """Run self-reflection on email generation output."""
    chain = build_email_reflection_chain()
    return await chain.ainvoke({
        "output_to_review": output_to_review[:4000],
        "company_name": company_name,
        "company_industry": company_industry or "Not specified",
        "user_requirement": user_requirement or "Not specified",
        "format_instructions": _PARSER.get_format_instructions(),
    })


async def reflect_on_research(
    output_to_review: str,
    company_name: str,
) -> ReflectionResult:
    """Run self-reflection on company research output."""
    chain = build_research_reflection_chain()
    return await chain.ainvoke({
        "output_to_review": output_to_review[:4000],
        "company_name": company_name,
        "format_instructions": _PARSER.get_format_instructions(),
    })
