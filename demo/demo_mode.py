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

    def get_companies(self) -> list[dict[str, Any]]:
        """Get mock companies for demo display."""
        companies = mock_data.SAMPLE_COMPANIES + mock_data.SAMPLE_COMPANIES_LOW_SCORE
        return [c.model_dump() for c in companies]

    def get_qualified_companies(self) -> list[dict[str, Any]]:
        """Get only qualified mock companies."""
        return [
            c.model_dump() for c in mock_data.SAMPLE_COMPANIES
        ]

    def get_summary_report(self) -> str:
        """Generate a demo summary report."""
        lines = [
            "=" * 60,
            "📊 AI 海外获客 Agent — 演示执行报告",
            "=" * 60,
            "需求: 我要开发德国刀具行业客户",
            "目标行业: Cutting Tools",
            "目标地区: Germany",
            "模式: 🎯 Demo Mode (模拟数据)\n",
            f"搜索候选企业: {len(mock_data.SAMPLE_COMPANIES + mock_data.SAMPLE_COMPANIES_LOW_SCORE)} 家",
            f"ICP 筛选合格: {len(mock_data.SAMPLE_COMPANIES)} 家\n",
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
