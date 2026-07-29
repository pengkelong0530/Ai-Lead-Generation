"""Multi-round email sequence generation chain (Q3).

Generates a sequence of follow-up emails for a target company:
  - Email 1 (Day 1): Introduction + value proposition
  - Email 2 (Day 3): Case study / social proof
  - Email 3 (Day 7): Meeting invitation + CTA

Each email is tailored to the company's profile and the PVD/CVD coating
equipment value proposition.
"""

from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel, Field

from models.email import EmailSequenceCreate, EmailStatus

# ──────────────────────────────────────────────
# Output model
# ──────────────────────────────────────────────


class SingleEmail(BaseModel):
    """One email in the sequence."""
    sequence_no: int = Field(description="Position in sequence (1, 2, 3)")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content (plain text)")
    writer_note: str = Field(description="Explanation of why this email is written this way (Q4)")


class EmailSequenceBundle(BaseModel):
    """Complete multi-email outreach sequence for one company."""
    company_name: str = Field(description="Target company name")
    target_contact_name: str = Field(default="", description="Recipient name if known")
    sequence: list[SingleEmail] = Field(description="Ordered list of emails")
    total_emails: int = 3


# ──────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────

_EMAIL_SYSTEM_PROMPT = """You are a senior B2B business development writer specializing in \
industrial manufacturing equipment sales. Write professional, compelling cold outreach \
emails for a company selling PVD/CVD vacuum coating equipment.

**Our Company Profile:**
We manufacture advanced PVD (Physical Vapor Deposition) and CVD (Chemical Vapor Deposition) \
vacuum coating equipment. Our systems help industrial manufacturers:
- Extend tool/die/mold lifespan by 3-5x through wear-resistant coatings
- Improve product quality and consistency
- Reduce production downtime and replacement costs
- Achieve precision coating for medical devices and automotive components

**Email Writing Guidelines:**
- Professional, concise, value-focused tone
- Personalize based on the target company's industry and profile
- No generic fluff or exaggerated claims
- Clear call-to-action in each email
- Respectful of the recipient's time
- Write in natural English suitable for international business communication

**Sequence Strategy:**
- Email 1 (Day 1): Introduction — who we are, why we're reaching out, value hook
- Email 2 (Day 3): Social proof — specific case study or result from similar companies
- Email 3 (Day 7): Direct CTA — propose a brief call or demo, create urgency"""

_EMAIL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _EMAIL_SYSTEM_PROMPT),
    (
        "human",
        "**Target Company:** {company_name}\n"
        "**Industry:** {industry}\n"
        "**Region:** {region}\n"
        "**Company Profile:** {company_description}\n"
        "**Key Technology Focus:** {technology_focus}\n"
        "**Contact Name (if known):** {contact_name}\n"
        "**Contact Email:** {contact_email}\n\n"
        "**User Requirement Context:** {user_requirement}\n\n"
        "Generate a {num_emails}-email outreach sequence tailored to this company.\n"
        "Include a writer_note for each email explaining the strategy behind it.\n\n"
        "{format_instructions}",
    ),
])


# ──────────────────────────────────────────────
# Chain factory
# ──────────────────────────────────────────────


def _get_llm() -> BaseChatModel:
    from llm_utils import get_llm as build_llm
    return build_llm(temperature=0.4)


_EMAIL_PARSER = PydanticOutputParser(pydantic_object=EmailSequenceBundle)


def build_email_chain() -> RunnableSerializable:
    """Build the multi-email sequence generation chain.

    Returns a Runnable that accepts company profile fields
    and returns an EmailSequenceBundle.
    """
    chain: RunnableSerializable = _EMAIL_PROMPT | _get_llm() | _EMAIL_PARSER
    return chain


async def generate_email_sequence(
    company_name: str,
    company_description: str,
    user_requirement: str,
    industry: str = "",
    region: str = "",
    technology_focus: Optional[str] = None,
    contact_name: str = "",
    contact_email: str = "",
    num_emails: int = 3,
) -> EmailSequenceBundle:
    """Generate a multi-email outreach sequence for a target company.

    Returns an EmailSequenceBundle for review; call ``to_db_models``
    to convert to persistable EmailSequenceCreate models.
    """
    chain = build_email_chain()
    result: EmailSequenceBundle = await chain.ainvoke({
        "company_name": company_name,
        "industry": industry or "General manufacturing",
        "region": region or "International",
        "company_description": company_description or "No description available",
        "technology_focus": technology_focus or "Not specified",
        "contact_name": contact_name or "Potential Customer",
        "contact_email": contact_email or "",
        "user_requirement": user_requirement,
        "num_emails": num_emails,
        "format_instructions": _EMAIL_PARSER.get_format_instructions(),
    })
    return result


def bundle_to_db_models(
    bundle: EmailSequenceBundle,
    company_id: int,
) -> list[EmailSequenceCreate]:
    """Convert an EmailSequenceBundle to a list of EmailSequenceCreate models
    for persistence via MySQLManager.save_email_sequence().

    Standard schedule: Day 1, Day 3, Day 7.
    """
    schedule = {1: 1, 2: 3, 3: 7}
    models_list = []
    for email in bundle.sequence:
        models_list.append(
            EmailSequenceCreate(
                company_id=company_id,
                sequence_no=email.sequence_no,
                subject=email.subject,
                body=email.body,
                scheduled_day=schedule.get(email.sequence_no, email.sequence_no),
                status=EmailStatus.pending,
            )
        )
    return models_list
