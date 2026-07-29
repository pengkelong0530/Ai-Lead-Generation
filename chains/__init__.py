"""LangChain chain implementations for AI Lead Generation Agent.

Each module exposes:
  - A ``build_*_chain()`` factory returning a RunnableSerializable
  - A convenience async function for direct invocation
  - Helper conversion functions where applicable
"""

from chains.icp_filter_chain import (
    assess_icp, build_icp_filter_chain, ICPAssessment, ICPFilterResult,
)
from chains.scoring_chain import build_scoring_chain, score_company, CompanyScore
from chains.email_chain import (
    build_email_chain,
    generate_email_sequence,
    bundle_to_db_models,
    EmailSequenceBundle,
)
from chains.info_extract_chain import (
    build_extraction_chain,
    extract_company_details,
    extraction_to_company_create,
    ExtractionResult,
)
from chains.reflection_chain import (
    build_icp_reflection_chain,
    build_email_reflection_chain,
    build_research_reflection_chain,
    reflect_on_icp,
    reflect_on_emails,
    reflect_on_research,
    ReflectionResult,
)

__all__ = [
    "assess_icp",
    "build_icp_filter_chain",
    "ICPAssessment",
    "ICPFilterResult",
    "build_scoring_chain",
    "score_company",
    "CompanyScore",
    "build_email_chain",
    "generate_email_sequence",
    "bundle_to_db_models",
    "EmailSequenceBundle",
    "build_extraction_chain",
    "extract_company_details",
    "extraction_to_company_create",
    "ExtractionResult",
    "build_icp_reflection_chain",
    "build_email_reflection_chain",
    "build_research_reflection_chain",
    "reflect_on_icp",
    "reflect_on_emails",
    "reflect_on_research",
    "ReflectionResult",
]
