"""Pydantic models for scoring and agent reasoning."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ICPCriteria(BaseModel):
    """Ideal Customer Profile criteria used for scoring."""
    industry_match: int = Field(ge=0, le=100, description="Industry relevance score")
    size_match: int = Field(ge=0, le=100, description="Company size relevance score")
    demand_match: int = Field(ge=0, le=100, description="Technology/demand relevance score")
    region_priority: int = Field(ge=0, le=100, description="Region priority score")


class CompanyScore(BaseModel):
    """Company ICP matching score."""
    company_id: int
    company_name: str
    icp_criteria: ICPCriteria
    total_score: int = Field(ge=0, le=100, description="Weighted total score")
    reasoning: str = Field(description="Why this score was assigned")
    recommendation: str = Field(description="Develop / Follow-up / Skip")


class ScoreWeights(BaseModel):
    """Configurable weights for scoring formula."""
    industry_weight: float = Field(default=0.40, ge=0, le=1)
    size_weight: float = Field(default=0.25, ge=0, le=1)
    demand_weight: float = Field(default=0.25, ge=0, le=1)
    region_weight: float = Field(default=0.10, ge=0, le=1)


class AgentReasoning(BaseModel):
    """Record of agent decision-making for transparency (Q4)."""
    session_id: str
    node: str = Field(description="Pipeline node name")
    input_text: str = Field(description="Input to this node")
    output_text: str = Field(description="Output from this node")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in output")
    reasoning: str = Field(description="Free-text reasoning / explanation")


class AgentReasoningRecord(AgentReasoning):
    """Agent reasoning record with database fields."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
