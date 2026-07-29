"""Pydantic models for company/enterprise information."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class CompanyStatus(str, Enum):
    pending = "待开发"
    following = "跟进中"
    converted = "已转化"
    invalid = "无效"


class CompanyBase(BaseModel):
    """Core company information fields."""
    name: str = Field(description="Company name")
    industry: Optional[str] = Field(None, description="Industry category")
    region: Optional[str] = Field(None, description="Geographic region / country")
    website: Optional[str] = Field(None, description="Company website URL")
    description: Optional[str] = Field(None, description="Company business description")
    employee_count: Optional[str] = Field(None, description="Employee count range")
    revenue_estimate: Optional[str] = Field(None, description="Estimated revenue")
    technology_focus: Optional[str] = Field(None, description="Key technology / process focus")


class CompanyCreate(CompanyBase):
    """Used when creating a new company record."""
    score: int = Field(default=0, ge=0, le=100, description="ICP matching score (0-100)")
    source: Optional[str] = Field(None, description="Search source (Google/Bing/IHK/etc.)")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence of data accuracy")
    status: CompanyStatus = CompanyStatus.pending
    session_id: Optional[str] = Field(None, description="Session ID that created this record")


class Company(CompanyCreate):
    """Full company model with database fields."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyList(BaseModel):
    """Wrapper for paginated company list results."""
    companies: list[Company]
    total: int
    page: int = 1
    page_size: int = 20
