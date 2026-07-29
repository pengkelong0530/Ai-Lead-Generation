"""Mock data for offline demo mode.

Provides pre-built sample data so the agent can be demonstrated
without live API calls during interviews or testing.
"""

from models.company import CompanyCreate, CompanyStatus
from models.contact import ContactCreate
from models.email import EmailSequenceCreate, EmailStatus
from models.score import AgentReasoning, CompanyScore, ICPCriteria


# ──────────────────────────────────────────────
# Sample Companies
# ──────────────────────────────────────────────

SAMPLE_COMPANIES = [
    CompanyCreate(
        name="Walter AG",
        industry="Cutting Tools",
        region="Germany",
        website="https://www.walter-tools.com",
        description="Leading German manufacturer of precision cutting tools for metalworking, "
                    "including indexable inserts, solid carbide tools, and tooling systems. "
                    "A global leader in turning, milling, drilling, and threading.",
        employee_count="1000-5000",
        technology_focus="PVD coating for cutting tools, wear-resistant coatings",
        score=92,
        source="tavily",
        confidence=0.95,
        status=CompanyStatus.pending,
    ),
    CompanyCreate(
        name="Gühring KG",
        industry="Cutting Tools",
        region="Germany",
        website="https://www.guehring.de",
        description="One of the world's leading manufacturers of precision tools for "
                    "metal cutting. Specializes in drilling, milling, and threading tools "
                    "with advanced coating technologies.",
        employee_count="1000-5000",
        technology_focus="Tool coating, CVD/PVD processes, wear protection",
        score=90,
        source="tavily",
        confidence=0.92,
        status=CompanyStatus.pending,
    ),
    CompanyCreate(
        name="MAPAL Dr. Kress KG",
        industry="Cutting Tools",
        region="Germany",
        website="https://www.mapal.com",
        description="German precision tool manufacturer specializing in reaming, drilling, "
                    "and milling tools for the automotive and mechanical engineering industries. "
                    "Offers PVD-coated tool solutions.",
        employee_count="500-1000",
        technology_focus="Precision tools, PVD coating, diamond tools",
        score=88,
        source="tavily",
        confidence=0.90,
        status=CompanyStatus.pending,
    ),
    CompanyCreate(
        name="EMUGE-Werk Richard Glimpel KG",
        industry="Cutting Tools",
        region="Germany",
        website="https://www.emuge.com",
        description="Manufacturer of taps, thread cutters, and milling tools. Provides "
                    "coated tool solutions for improved performance and tool life.",
        employee_count="500-1000",
        technology_focus="Thread cutting tools, PVD coating",
        score=85,
        source="bing",
        confidence=0.85,
        status=CompanyStatus.pending,
    ),
    CompanyCreate(
        name="Kennametal Inc.",
        industry="Cutting Tools",
        region="Germany/Global",
        website="https://www.kennametal.com",
        description="Global leader in metal cutting tools, tooling systems, and wear-resistant "
                    "solutions. Extensive PVD/CVD coating capabilities for tooling applications.",
        employee_count="10000+",
        technology_focus="PVD/CVD coating, wear materials, metal cutting",
        score=82,
        source="tavily",
        confidence=0.88,
        status=CompanyStatus.pending,
    ),
]

SAMPLE_COMPANIES_LOW_SCORE = [
    CompanyCreate(
        name="Bosch GmbH",
        industry="Automotive Parts",
        region="Germany",
        website="https://www.bosch.com",
        description="Global technology company specializing in automotive components, "
                    "industrial technology, and consumer goods. Operates extensive manufacturing "
                    "with potential PVD coating needs for automotive parts.",
        employee_count="100000+",
        technology_focus="Automotive manufacturing, surface treatment",
        score=65,
        source="tavily",
        confidence=0.70,
        status=CompanyStatus.pending,
    ),
    CompanyCreate(
        name="Siemens AG",
        industry="Industrial Manufacturing",
        region="Germany",
        website="https://www.siemens.com",
        description="Global technology conglomerate focused on industry, infrastructure, "
                    "transport, and healthcare. Limited direct coating equipment need.",
        employee_count="100000+",
        technology_focus="Industrial automation, digitalization",
        score=35,
        source="tavily",
        confidence=0.60,
        status=CompanyStatus.pending,
    ),
]

# ──────────────────────────────────────────────
# Sample Contacts
# ──────────────────────────────────────────────

SAMPLE_CONTACTS: dict[str, list[ContactCreate]] = {
    "Walter AG": [
        ContactCreate(
            company_id=0,
            email="info@walter-tools.com",
            contact_page_url="https://www.walter-tools.com/en/company/contact",
            verified=False,
        ),
        ContactCreate(
            company_id=0,
            email="sales@walter-tools.com",
            contact_page_url="https://www.walter-tools.com/en/company/contact",
            verified=False,
        ),
    ],
    "Gühring KG": [
        ContactCreate(
            company_id=0,
            email="info@guehring.de",
            contact_page_url="https://www.guehring.de/en/contact",
            linkedin_url="https://www.linkedin.com/company/guehring",
            verified=False,
        ),
    ],
}

# ──────────────────────────────────────────────
# Sample Scores
# ──────────────────────────────────────────────

SAMPLE_SCORES: dict[str, CompanyScore] = {
    "Walter AG": CompanyScore(
        company_id=1,
        company_name="Walter AG",
        icp_criteria=ICPCriteria(
            industry_match=95,
            size_match=90,
            demand_match=95,
            region_priority=90,
        ),
        total_score=92,
        reasoning=(
            "Industry (95/100): Primary target - cutting tool manufacturer with explicit "
            "PVD coating needs\n"
            "Size (90/100): Large enterprise with production-scale requirements\n"
            "Demand (95/100): Clear demand for PVD/CVD coating for cutting tools\n"
            "Region (90/100): Germany is primary target region"
        ),
        recommendation="Develop",
    ),
    "Gühring KG": CompanyScore(
        company_id=2,
        company_name="Gühring KG",
        icp_criteria=ICPCriteria(
            industry_match=95,
            size_match=90,
            demand_match=90,
            region_priority=90,
        ),
        total_score=90,
        reasoning=(
            "Industry (95/100): Primary target - precision tool manufacturer\n"
            "Size (90/100): Large enterprise\n"
            "Demand (90/100): Known CVD/PVD coating usage in tool production\n"
            "Region (90/100): Germany"
        ),
        recommendation="Develop",
    ),
}

# ──────────────────────────────────────────────
# Sample Email Sequences
# ──────────────────────────────────────────────

SAMPLE_EMAILS: dict[str, list[EmailSequenceCreate]] = {
    "Walter AG": [
        EmailSequenceCreate(
            company_id=1,
            sequence_no=1,
            subject="Enhancing Walter AG's Cutting Tool Performance with Advanced PVD Coatings",
            body=(
                "Dear Walter AG Team,\n\n"
                "I hope this message finds you well. I'm reaching out from [Our Company], "
                "a specialized manufacturer of advanced PVD/CVD vacuum coating equipment.\n\n"
                "Given Walter AG's position as a global leader in precision cutting tools, "
                "we believe our latest generation of PVD coating systems could significantly "
                "enhance the performance and lifespan of your tooling products.\n\n"
                "Our coating technology has been shown to:\n"
                "- Extend tool life by 3-5x through advanced wear-resistant coatings\n"
                "- Improve cutting performance and surface finish quality\n"
                "- Reduce production downtime through more durable tooling\n\n"
                "I would welcome the opportunity to discuss how our coating solutions "
                "could support your manufacturing excellence.\n\n"
                "Best regards,\n[Your Name]"
            ),
            scheduled_day=1,
            status=EmailStatus.pending,
        ),
        EmailSequenceCreate(
            company_id=1,
            sequence_no=2,
            subject="Case Study: How [Similar Company] Improved Tool Life by 4x",
            body=(
                "Dear Walter AG Team,\n\n"
                "Following up on my previous email, I wanted to share a relevant success "
                "story from our work with a leading European cutting tool manufacturer.\n\n"
                "After implementing our PVD coating system, they achieved:\n"
                "- 4x improvement in tool lifespan\n"
                "- 22% increase in cutting speed capability\n"
                "- Significant reduction in tool change downtime\n\n"
                "The key differentiator was our advanced multi-layer coating technology, "
                "which provides superior adhesion and wear resistance compared to "
                "standard single-layer coatings.\n\n"
                "Would you be open to a 15-minute technical discussion to explore "
                "whether this could deliver similar results for Walter AG?\n\n"
                "Best regards,\n[Your Name]"
            ),
            scheduled_day=3,
            status=EmailStatus.pending,
        ),
        EmailSequenceCreate(
            company_id=1,
            sequence_no=3,
            subject="Quick question about Walter AG's coating requirements",
            body=(
                "Dear Walter AG Team,\n\n"
                "I've been researching Walter AG's impressive range of cutting tools, "
                "and I'm curious about your current approach to PVD coating.\n\n"
                "Are you currently managing coating in-house, or working with external "
                "coating partners? In either case, our systems are designed to integrate "
                "seamlessly into existing production workflows.\n\n"
                "I'll be at the upcoming EMO Hannover exhibition - would this be a good "
                "opportunity to briefly connect and learn more about your requirements?\n\n"
                "Looking forward to hearing from you.\n\n"
                "Best regards,\n[Your Name]"
            ),
            scheduled_day=7,
            status=EmailStatus.pending,
        ),
    ],
}

# ──────────────────────────────────────────────
# Sample Reasoning Logs (Q4)
# ──────────────────────────────────────────────

SAMPLE_REASONING_LOGS = [
    AgentReasoning(
        session_id="demo_session",
        node="understand_requirement",
        input_text="我要开发德国刀具行业客户",
        output_text=(
            '{"region": "Germany", "industry": "Cutting Tools", '
            '"product": "PVD CVD coating equipment"}'
        ),
        confidence=0.92,
        reasoning=(
            "Parsed user input. Detected: region=Germany (keyword: 德国), "
            "industry=Cutting Tools (keyword: 刀具). "
            "High confidence due to clear industry and region indicators."
        ),
    ),
    AgentReasoning(
        session_id="demo_session",
        node="search_companies",
        input_text="Searching for German cutting tool manufacturers",
        output_text="Found 5 companies from search results across 2 sources",
        confidence=0.88,
        reasoning=(
            "Searched with queries: 'Germany cutting tools manufacturers', "
            "'Germany刀具行业公司'. "
            "Sources: tavily, bing. "
            "Walter AG and Gühring KG appear to be strong candidates."
        ),
    ),
]
