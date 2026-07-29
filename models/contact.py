"""Pydantic models for contact information."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContactBase(BaseModel):
    """Contact information fields."""
    company_id: int = Field(description="Associated company ID")
    email: Optional[str] = Field(None, description="Contact email address")
    phone: Optional[str] = Field(None, description="Phone number")
    contact_page_url: Optional[str] = Field(None, description="URL of the contact page")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn company/profile URL")
    verified: bool = Field(default=False, description="Whether contact info has been verified")


class ContactCreate(ContactBase):
    """Used when creating a new contact record."""
    pass


class Contact(ContactBase):
    """Full contact model with database fields."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
