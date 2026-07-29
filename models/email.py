"""Pydantic models for email sequences."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EmailStatus(str, Enum):
    pending = "待发送"
    sent = "已发送"
    replied = "已回复"
    bounced = "退回"


class EmailBase(BaseModel):
    """Email sequence fields."""
    company_id: int = Field(description="Target company ID")
    sequence_no: int = Field(ge=1, le=7, description="Email number in sequence (1, 2, 3, ...)")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content")
    scheduled_day: int = Field(ge=1, description="Day to send (1 = immediate, 3 = day 3, etc.)")


class EmailSequenceCreate(EmailBase):
    """Used when creating a new email sequence record."""
    status: EmailStatus = EmailStatus.pending


class EmailSequence(EmailBase):
    """Full email model with database fields."""
    id: int
    status: EmailStatus
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmailSequenceBundle(BaseModel):
    """A complete multi-email outreach bundle for one company."""
    company_name: str
    company_id: int
    emails: list[EmailSequence]
    total: int
