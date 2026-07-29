"""Demo mode: provides mock implementations when live APIs are unavailable.

Switches between live (API) and demo (mock) mode based on configuration.
Allows seamless demonstration during interviews without network dependencies.
"""

from typing import Any, Optional

from config import config

from . import mock_data


class DemoMode:
    """Manages demo mode state and provides mock data access."""

    def __init__(self, enabled: Optional[bool] = None) -> None:
        self.enabled = enabled if enabled is not None else config.app.demo_mode

    def is_active(self) -> bool:
        return self.enabled

    @staticmethod
    def _detect_region(user_input: str) -> str:
        """Simple region detection from user input."""
        text = user_input.lower()
        if "germany" in text or "german" in text or "德国" in text:
            return "Germany"
        if "usa" in text or "united states" in text or "american" in text or "美国" in text:
            return "USA"
        if "japan" in text or "japanese" in text or "日本" in text:
            return "Japan"
        if "china" in text or "chinese" in text or "中国" in text:
            return "China"
        return ""

    def get_companies(self, region: str = "") -> list[dict[str, Any]]:
        """Get mock companies for demo display, optionally filtered by region."""
        # Build comprehensive list: first add high-scoring companies, then low-scoring
        all_companies = mock_data.SAMPLE_COMPANIES + mock_data.SAMPLE_COMPANIES_USA + mock_data.SAMPLE_COMPANIES_LOW_SCORE
        if region:
            all_companies = [c for c in all_companies if c.region and region.lower() in c.region.lower()]
        return [c.model_dump() for c in all_companies]

    def get_qualified_companies(self, region: str = "") -> list[dict[str, Any]]:
        """Get only qualified mock companies, filtered by region."""
        companies = mock_data.SAMPLE_COMPANIES + mock_data.SAMPLE_COMPANIES_USA
        if region:
            companies = [c for c in companies if c.region and region.lower() in c.region.lower()]
        return [c.model_dump() for c in companies]

    def get_summary_report(self, region: str = "") -> str:
        """Generate a demo summary report."""
        qualified = mock_data.SAMPLE_COMPANIES + mock_data.SAMPLE_COMPANIES_USA
        if region:
            qualified = [c for c in qualified if c.region and region.lower() in c.region.lower()]
        all_search = mock_data.SAMPLE_COMPANIES + mock_data.SAMPLE_COMPANIES_USA + mock_data.SAMPLE_COMPANIES_LOW_SCORE
        if region:
            all_search = [c for c in all_search if c.region and region.lower() in c.region.lower()]

        target_industry = "Cutting Tools"
        target_region = region or "Global"
        lines = [
            "=" * 60,
            "📊 AI 海外获客 Agent — 演示执行报告",
            "=" * 60,
            f"需求: {getattr(self, '_last_input', '我要开发{region}刀具行业客户')}",
            f"目标行业: {target_industry}",
            f"目标地区: {target_region}",
            "模式: 🎯 Demo Mode (模拟数据)\n",
            f"搜索候选企业: {len(all_search)} 家",
            f"ICP 筛选合格: {len(qualified)} 家\n",
            "--- 合格客户列表 (按评分排序) ---",
        ]

        for i, company in enumerate(mock_data.SAMPLE_COMPANIES, 1):
            score = mock_data.SAMPLE_SCORES.get(company.name)
            score_str = f"评分: {score.total_score}/100" if score else "评分: N/A"
            lines.append(
                f"{i}. {company.name} | {score_str} | {company.website}"
            )

        lines.append("=" * 60)
        return "\n".join(lines)

    def get_email_preview(self, company_name: str = "Walter AG") -> str:
        """Get mock email preview for a company."""
        emails = mock_data.SAMPLE_EMAILS.get(company_name, [])
        if not emails:
            return f"暂无 {company_name} 的邮件数据"

        lines = [f"📧 {company_name} 邮件序列 ({len(emails)} 封)\n"]
        for email in emails:
            lines.append(f"--- 邮件 {email.sequence_no} (Day {email.scheduled_day}) ---")
            lines.append(f"主题: {email.subject}")
            lines.append(f"正文:\n{email.body}\n")

        return "\n".join(lines)

    def get_reasoning_logs(self) -> list[dict[str, Any]]:
        """Get mock reasoning logs."""
        return [r.model_dump() for r in mock_data.SAMPLE_REASONING_LOGS]
