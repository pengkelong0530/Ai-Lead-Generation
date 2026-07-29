"""Email sub-agent: generates multi-round outreach email sequences (Q3)."""

from typing import Optional

from chains.email_chain import (
    EmailSequenceBundle,
    bundle_to_db_models,
    generate_email_sequence,
)
from models.company import CompanyCreate
from models.email import EmailSequenceCreate


class EmailAgent:
    """Sub-agent focused on email outreach sequence generation."""

    @staticmethod
    async def create_outreach(
        company: CompanyCreate,
        user_requirement: str,
        contact_name: str = "",
        contact_email: str = "",
        num_emails: int = 3,
    ) -> EmailSequenceBundle:
        """Generate a complete email outreach sequence for a company."""
        bundle = await generate_email_sequence(
            company_name=company.name,
            company_description=company.description or "",
            user_requirement=user_requirement,
            industry=company.industry or "",
            region=company.region or "",
            technology_focus=company.technology_focus,
            contact_name=contact_name,
            contact_email=contact_email,
            num_emails=num_emails,
        )
        return bundle

    @staticmethod
    def to_db_models(
        bundle: EmailSequenceBundle,
        company_id: int,
    ) -> list[EmailSequenceCreate]:
        """Convert bundle to persistable models."""
        return bundle_to_db_models(bundle, company_id)

    @staticmethod
    def format_email_preview(
        bundle: EmailSequenceBundle,
        company_name: str,
    ) -> str:
        """Format the email bundle as a readable preview string."""
        lines = [f"📧 {company_name} 邮件序列 ({bundle.total_emails} 封)\n"]
        for email in bundle.sequence:
            lines.append(f"--- 邮件 {email.sequence_no} ---")
            lines.append(f"主题: {email.subject}")
            lines.append(f"正文:\n{email.body}\n")
            lines.append(f"[策略说明] {email.writer_note}\n")
        return "\n".join(lines)
