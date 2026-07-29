"""ICP screening sub-agent: assesses and scores companies against ICP.

Takes a list of candidate companies, runs ICP assessment and scoring
for each, then returns filtered and ranked results.
"""

from typing import Optional

from chains.icp_filter_chain import ICPAssessment, assess_icp
from chains.scoring_chain import CompanyScore, score_company
from models.company import CompanyCreate
from models.score import ScoreWeights


class ICPAgent:
    """Sub-agent focused on ICP screening and scoring."""

    @staticmethod
    async def assess_companies(
        companies: list[CompanyCreate],
        user_requirement: str,
        target_industry: str,
        target_region: str,
        weights: Optional[ScoreWeights] = None,
    ) -> list[dict]:
        """Assess and score multiple companies against ICP.

        Runs ICP assessment and scoring in parallel for all companies.
        Returns list sorted by score descending, each with:
            company, icp_assessment, score, overall_recommendation
        """
        tasks = []
        for company in companies:
            tasks.append(
                _assess_and_score_one(
                    company=company,
                    user_requirement=user_requirement,
                    target_industry=target_industry,
                    target_region=target_region,
                    weights=weights,
                )
            )

        from asyncio import gather
        results = await gather(*tasks, return_exceptions=True)

        valid = []
        for r in results:
            if isinstance(r, Exception):
                continue
            valid.append(r)

        valid.sort(key=lambda x: x["score"].total_score, reverse=True)
        return valid

    @staticmethod
    def filter_qualified(
        assessments: list[dict],
        min_score: int = 50,
    ) -> list[dict]:
        """Filter assessments to only qualified leads."""
        return [
            a for a in assessments
            if a["score"].total_score >= min_score
            and a["icp"].is_match
        ]

    @staticmethod
    def format_summary(assessment: dict) -> str:
        """Format a single assessment as a readable string."""
        company = assessment["company"]
        icp = assessment["icp"]
        score = assessment["score"]

        lines = [
            f"【{company.name}】评分: {score.total_score}/100",
            f"  行业匹配: {score.icp_criteria.industry_match} | "
            f"规模匹配: {score.icp_criteria.size_match} | "
            f"需求匹配: {score.icp_criteria.demand_match} | "
            f"地区优先级: {score.icp_criteria.region_priority}",
            f"  ICP判定: {'✅ 匹配' if icp.is_match else '❌ 不匹配'}",
            f"  推荐: {score.recommendation}",
            f"  理由: {icp.match_reason}",
        ]
        return "\n".join(lines)


async def _assess_and_score_one(
    company: CompanyCreate,
    user_requirement: str,
    target_industry: str,
    target_region: str,
    weights: Optional[ScoreWeights] = None,
) -> dict:
    """Run ICP assessment + scoring for a single company."""
    icp_result = await assess_icp(
        company_name=company.name,
        company_description=company.description or "",
        user_requirement=user_requirement,
        target_industry=target_industry,
        target_region=target_region,
        company_industry=company.industry,
        technology_focus=company.technology_focus,
        employee_count=company.employee_count,
        company_region=company.region,
    )

    score_result = await score_company(
        company_name=company.name,
        company_description=company.description or "",
        user_requirement=user_requirement,
        industry=company.industry or "",
        region=company.region or "",
        target_industry=target_industry,
        target_region=target_region,
        employee_count=company.employee_count,
        technology_focus=company.technology_focus,
        weights=weights,
    )
    score_result.company_id = company.id or 0

    return {
        "company": company,
        "icp": icp_result,
        "score": score_result,
    }
