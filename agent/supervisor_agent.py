"""Supervisor Agent: the main orchestrator for the AI lead generation workflow.

Manages the 6-node pipeline end-to-end:
  1. Requirement Understanding + Self-Assessment (Q4)
  2. Multi-Platform Enterprise Search (Q1)
  3. ICP Screening + Scoring + Self-Reflection (Q2, Phase 6)
  4. Information & Contact Collection + Self-Reflection
  5. Multi-Round Email Generation + Self-Reflection (Q3, Phase 6)
  6. Output & Persistence (Q5)

Uses LangGraph create_react_agent for tool-using steps and direct sub-agent
invocations for structured LLM tasks.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langgraph.prebuilt import create_react_agent

from agent.icp_agent import ICPAgent
from agent.email_agent import EmailAgent
from agent.research_agent import ResearchAgent
from chains.reflection_chain import (
    reflect_on_icp,
    reflect_on_emails,
    ReflectionResult,
)
from config import config
from db import get_db
from llm_utils import get_llm
from memory.progress_callback import ProgressCallback
from models.company import CompanyCreate, CompanyStatus
from models.score import AgentReasoning
from tools import ALL_TOOLS


# ──────────────────────────────────────────────
# Prompt templates
# ──────────────────────────────────────────────

SUPERVISOR_SYSTEM_PROMPT = """You are an AI Lead Generation Specialist for a PVD/CVD vacuum \
coating equipment manufacturer. Your job is to help the sales team find and develop overseas \
industrial customers.

**Your Capabilities:**
You have access to web search, web scraping, and company research tools.
You operate in a structured pipeline with the following stages:

1. **Understand Requirement** — Parse the user's request to identify target industry, region, products
2. **Search Companies** — Find target companies matching the requirement
3. **Screen & Score** — Filter companies by ICP and score them
4. **Collect Details** — Get website info and contact details
5. **Generate Outreach** — Create email sequences
6. **Output Results** — Summarize and save

**Rules:**
- Be transparent about your reasoning at each step (Q4).
- Ask for confirmation before proceeding to the next major stage.
- When searching, use multiple search queries to maximize coverage (Q1).
- When evaluating companies, explain why they match or don't match the ICP.
- Always output structured data when possible.
- Track which companies have been contacted and their status (Q5).
- Keep a running summary of all companies found and their development status."""


# ──────────────────────────────────────────────
# Supervisor Agent
# ──────────────────────────────────────────────


class SupervisorAgent:
    """Main orchestrator for the lead generation pipeline."""

    def __init__(
        self,
        db: Any = None,
        llm: Optional[BaseChatModel] = None,
        callbacks: Optional[list[ProgressCallback]] = None,
    ) -> None:
        self.llm = llm or get_llm()
        self.db = db
        self.callbacks = callbacks or []
        self._agent: Any = None
        self._session_id: Optional[str] = None
        self._current_requirement: str = ""
        self._parsed_requirement: dict[str, str] = {}
        self._found_companies: list[CompanyCreate] = []
        self._qualified_companies: list[dict] = []
        self._reflection_results: list[dict[str, Any]] = []

    # ── Initialization ────────────────────────────

    def _init_db(self) -> Any:
        """Initialize database via factory (MySQL or SQLite)."""
        if self.db is None:
            self.db = get_db()
            self.db.connect()
        return self.db

    def _build_agent(self) -> Any:
        """Build the agent using LangGraph create_react_agent."""
        from langchain_core.messages import SystemMessage

        agent = create_react_agent(
            model=self.llm,
            tools=ALL_TOOLS,
            system_message=SUPERVISOR_SYSTEM_PROMPT,
        )
        return agent

    def _get_session_id(self) -> str:
        if self._session_id is None:
            self._session_id = f"session_{uuid.uuid4().hex[:12]}"
        return self._session_id

    # ── Callback Notifications (Phase 6) ───────────

    def _notify(self, method: str, **kwargs: Any) -> None:
        """Notify all registered callbacks of an event."""
        for cb in self.callbacks:
            getattr(cb, method)(**kwargs)

    # ── Self-Reflection (Phase 6) ───────────────────

    async def _reflect_on_stage(
        self,
        stage: str,
        output_summary: str,
        reflection_coro: Any,
        **kwargs: Any,
    ) -> Optional[ReflectionResult]:
        """Run self-reflection on a pipeline stage output and log results."""
        try:
            result = await reflection_coro(
                output_to_review=output_summary,
                **kwargs,
            )

            self._reflection_results.append({
                "stage": stage,
                "score": result.quality_score,
                "should_revise": result.should_revise,
                "critique": result.critique,
                "suggestions": result.specific_suggestions,
            })

            self._log_reasoning(
                node=f"reflection_{stage}",
                input_text=output_summary[:500],
                output_text=(
                    f"Score: {result.quality_score}/10 | Revise: {result.should_revise}\n"
                    f"Critique: {result.critique}\n"
                    f"Suggestions: {'; '.join(result.specific_suggestions)}"
                ),
                confidence=result.quality_score / 10.0,
                reasoning=f"Self-reflection on {stage} stage: {result.critique[:300]}",
            )

            return result
        except Exception as e:
            print(f"[Supervisor] Reflection failed for {stage}: {e}")
            return None

    # ── Reasoning Logging (Q4) ─────────────────────

    def _log_reasoning(
        self,
        node: str,
        input_text: str,
        output_text: str,
        confidence: Optional[float] = None,
        reasoning: str = "",
    ) -> None:
        """Log agent reasoning step to MySQL (Q4)."""
        if self.db is None:
            return
        try:
            record = AgentReasoning(
                session_id=self._get_session_id(),
                node=node,
                input_text=input_text[:2000],
                output_text=output_text[:2000],
                confidence=confidence,
                reasoning=reasoning[:2000],
            )
            self.db.save_reasoning_log(record)
        except Exception as e:
            print(f"[Supervisor] Failed to log reasoning: {e}")

    # ── Pipeline Nodes ─────────────────────────────

    async def node_understand_requirement(
        self, user_input: str
    ) -> dict[str, str]:
        """Node 1: Parse and understand user requirement with self-assessment."""
        self._current_requirement = user_input

        parsed = ResearchAgent._parse_requirement(user_input)

        reasoning = (
            f"Parsed user input: '{user_input}'\n"
            f"Detected region: {parsed.get('region', 'Not specified')}\n"
            f"Detected industry: {parsed.get('industry', 'Not specified')}\n"
            f"Confidence: {'High' if parsed['region'] and parsed['industry'] else 'Medium'}"
        )
        confidence = 0.9 if parsed["region"] and parsed["industry"] else 0.6

        self._log_reasoning(
            node="understand_requirement",
            input_text=user_input,
            output_text=json.dumps(parsed, ensure_ascii=False),
            confidence=confidence,
            reasoning=reasoning,
        )

        self._parsed_requirement = parsed
        return parsed

    async def node_search_companies(self) -> list[CompanyCreate]:
        """Node 2: Search for target companies across multiple platforms (Q1)."""
        user_input = self._current_requirement

        results, parsed = await ResearchAgent.search_target_companies(
            user_input=user_input,
            max_results=15,
        )

        companies: list[CompanyCreate] = []
        for r in results:
            company = CompanyCreate(
                name=r.title.split(" - ")[0].split(" | ")[0].strip()[:255],
                region=parsed.get("region", ""),
                industry=parsed.get("industry", ""),
                website=r.url,
                description=r.snippet,
                source=r.source,
                confidence=r.confidence,
                session_id=self._get_session_id(),
            )
            companies.append(company)

        self._found_companies = companies

        self._log_reasoning(
            node="search_companies",
            input_text=user_input,
            output_text=f"Found {len(companies)} companies from {len(results)} search results",
            confidence=0.8,
            reasoning=(
                f"Searched with queries targeting {parsed.get('industry', 'N/A')} "
                f"in {parsed.get('region', 'N/A')}. "
                f"Sources: {', '.join(set(r.source for r in results))}"
            ),
        )

        return companies

    async def node_screen_and_score(
        self,
        min_score: int = 50,
    ) -> list[dict]:
        """Node 3: ICP screening + scoring for all found companies (Q2).
        Also runs self-reflection on the screening quality (Phase 6).
        """
        if not self._found_companies:
            return []

        self._notify("on_step_start", step_name="ICP Screening & Scoring")

        parsed = self._parsed_requirement
        assessments = await ICPAgent.assess_companies(
            companies=self._found_companies,
            user_requirement=self._current_requirement,
            target_industry=parsed.get("industry", ""),
            target_region=parsed.get("region", ""),
        )

        qualified = ICPAgent.filter_qualified(assessments, min_score=min_score)
        self._qualified_companies = qualified

        # Log summary
        summary_parts = []
        for a in qualified:
            company = a["company"]
            score = a["score"]
            icp = a["icp"]
            summary_parts.append(
                f"{company.name}: score={score.total_score}, match={icp.is_match}"
            )

        output_text = (
            f"Qualified: {len(qualified)}/{len(assessments)} companies\n"
            + "\n".join(summary_parts)
        )

        self._log_reasoning(
            node="screen_and_score",
            input_text=f"Screening {len(assessments)} companies, min_score={min_score}",
            output_text=output_text,
            confidence=0.85,
            reasoning=f"Weights applied: industry*40%, size*25%, demand*25%, region*10%",
        )

        # Self-reflection on ICP screening quality (Phase 6)
        await self._reflect_on_stage(
            stage="icp_screening",
            output_summary=output_text,
            reflection_coro=reflect_on_icp,
            target_industry=parsed.get("industry", ""),
            target_region=parsed.get("region", ""),
            user_requirement=self._current_requirement,
        )

        self._notify("on_step_complete", step_name="ICP Screening & Scoring")
        return qualified

    async def node_collect_details(
        self,
    ) -> list[dict]:
        """Node 4: Collect website info and contact details for qualified companies."""
        self._notify("on_step_start", step_name="Company Research & Data Collection")

        enriched = []
        for assessment in self._qualified_companies:
            company = assessment["company"]

            # Research the company website
            researched = await ResearchAgent.research_company(
                company_name=company.name,
                website_url=company.website,
            )
            if researched:
                company.description = researched.description or company.description
                company.industry = researched.industry or company.industry
                company.employee_count = researched.employee_count
                company.technology_focus = researched.technology_focus

            enriched.append(assessment)

        self._log_reasoning(
            node="collect_details",
            input_text=f"Collecting details for {len(self._qualified_companies)} companies",
            output_text=f"Enriched {len(enriched)} company profiles",
            confidence=0.75,
            reasoning="Scraped company websites and extracted structured information",
        )

        self._notify("on_step_complete", step_name="Company Research & Data Collection")
        return enriched

    async def node_generate_emails(
        self,
    ) -> list[dict]:
        """Node 5: Generate multi-round email sequences for qualified companies (Q3).
        Also runs self-reflection on email quality (Phase 6).
        """
        self._notify("on_step_start", step_name="Email Outreach Generation")

        email_results = []
        for assessment in self._qualified_companies:
            company = assessment["company"]
            try:
                bundle = await EmailAgent.create_outreach(
                    company=company,
                    user_requirement=self._current_requirement,
                )
                email_results.append({
                    "company": company,
                    "bundle": bundle,
                })
                self._notify("on_message", msg=f"Emails generated for {company.name}")
            except Exception as e:
                print(f"[Supervisor] Email gen failed for {company.name}: {e}")
                self._notify("on_step_error", step_name=f"Email gen: {company.name}", error=str(e))

        output_text = f"Generated {len(email_results)} email bundles"

        self._log_reasoning(
            node="generate_emails",
            input_text=f"Generating email sequences for {len(self._qualified_companies)} companies",
            output_text=output_text,
            confidence=0.8,
            reasoning="Generated 3-email sequences: introduction / case study / CTA",
        )

        # Self-reflection on email quality (Phase 6)
        if email_results:
            first_bundle = email_results[0]["bundle"]
            email_summary = (
                f"Generated {len(email_results)} sequences for companies: "
                + ", ".join(r["company"].name for r in email_results)
            )
            await self._reflect_on_stage(
                stage="email_generation",
                output_summary=email_summary,
                reflection_coro=reflect_on_emails,
                company_name=email_results[0]["company"].name,
                company_industry=email_results[0]["company"].industry or "",
                user_requirement=self._current_requirement,
            )

        self._notify("on_step_complete", step_name="Email Outreach Generation")
        return email_results

    async def node_output_results(
        self,
    ) -> str:
        """Node 6: Persist all results to MySQL and generate summary (Q5)."""
        db = self._init_db()
        session_id = self._get_session_id()

        # Save session
        db.create_session(session_id, self._current_requirement)

        saved_count = 0
        for assessment in self._qualified_companies:
            company = assessment["company"]
            company.session_id = session_id

            try:
                # Check for duplicates
                existing = db.get_company_by_name(company.name)
                if existing:
                    company_id = existing.id
                else:
                    company_id = db.save_company(company)

                saved_count += 1

                # Save score
                score = assessment["score"]
                if company_id:
                    db.update_company_status(company_id, CompanyStatus.pending)

            except Exception as e:
                print(f"[Supervisor] DB save error for {company.name}: {e}")

        db.complete_session(session_id)

        summary = self._generate_summary()
        return summary

    def _generate_summary(self) -> str:
        """Generate a human-readable summary of results with reflection."""
        parsed = self._parsed_requirement
        lines = [
            "=" * 60,
            "📊 AI 海外获客 Agent — 执行报告",
            "=" * 60,
            f"需求: {self._current_requirement}",
            f"目标行业: {parsed.get('industry', '未指定')}",
            f"目标地区: {parsed.get('region', '未指定')}",
            f"Session ID: {self._get_session_id()}",
            "",
            f"搜索候选企业: {len(self._found_companies)} 家",
            f"ICP 筛选合格: {len(self._qualified_companies)} 家",
            "",
            "--- 合格客户列表 ---",
        ]

        for i, a in enumerate(self._qualified_companies, 1):
            company = a["company"]
            score = a["score"]
            icp = a["icp"]
            lines.append(
                f"{i}. {company.name} | 评分: {score.total_score}/100 | "
                f"网站: {company.website or 'N/A'} | "
                f"{'✅' if icp.is_match else '❌'} 匹配"
            )

        # Phase 6: Self-reflection summary
        if self._reflection_results:
            lines.extend(["", "--- 自我反思摘要 (Phase 6) ---"])
            for ref in self._reflection_results:
                score_str = f"{'⭐' * (ref['score'] // 2)}{'☆' * (5 - ref['score'] // 2)}"
                lines.append(
                    f"  [{ref['stage']}] {score_str} {ref['score']}/10 "
                    f"{'🔄 建议修订' if ref['should_revise'] else '✅ 质量达标'}"
                )
                if ref["suggestions"]:
                    for s in ref["suggestions"][:2]:
                        lines.append(f"    ↳ {s}")

        lines.append("=" * 60)
        return "\n".join(lines)

    # ── Full Pipeline ──────────────────────────────

    async def run_pipeline(
        self,
        user_input: str,
        min_score: int = 50,
        auto_confirm: bool = False,
    ) -> str:
        """Execute the full 6-node lead generation pipeline.

        Args:
            user_input: natural language request (e.g. "开发德国刀具客户")
            min_score: minimum ICP score threshold (default 50)
            auto_confirm: if True, skip human-in-the-loop pauses

        Returns:
            Final summary report string.
        """
        report_lines = []
        step = 0

        def progress(msg: str) -> None:
            step_num = step + 1
            report_lines.append(f"\n[{step_num}/6] {msg}")

        # Node 1
        step = 1
        progress("理解需求...")
        self._notify("on_step_start", step_name="需求理解", detail=user_input)
        parsed = await self.node_understand_requirement(user_input)
        report_lines.append(
            f"  地区: {parsed.get('region', '未识别')}, "
            f"行业: {parsed.get('industry', '未识别')}"
        )
        self._notify("on_step_complete", step_name="需求理解")

        # Node 2
        step = 2
        progress("搜索目标企业 (Q1 多平台并行搜索)...")
        self._notify("on_step_start", step_name="企业搜索")
        companies = await self.node_search_companies()
        report_lines.append(f"  找到 {len(companies)} 家候选企业")
        self._notify("on_step_complete", step_name="企业搜索", result=f"{len(companies)} candidates")

        if not companies:
            report_lines.append("  ⚠️ 未找到匹配企业，请调整搜索条件")
            return "\n".join(report_lines)

        # Node 3
        step = 3
        progress("ICP 筛选与评分 (Q2)...")
        qualified = await self.node_screen_and_score(min_score=min_score)
        report_lines.append(
            f"  合格: {len(qualified)}/{len(companies)} 家 "
            f"(阈值: {min_score}/100)"
        )

        if not qualified:
            report_lines.append("  ⚠️ 无企业通过 ICP 筛选，建议降低评分阈值")
            all_assessments = self._qualified_companies or []
            if all_assessments:
                report_lines.append("  最高评分:")
                for a in all_assessments[:3]:
                    report_lines.append(
                        f"    - {a['company'].name}: {a['score'].total_score}/100"
                    )
            return "\n".join(report_lines)

        # Node 4
        step = 4
        progress("收集企业详细信息与联系方式...")
        await self.node_collect_details()
        report_lines.append(f"  已完成 {len(qualified)} 家企业的信息采集")

        # Node 5
        step = 5
        progress("生成多轮跟进邮件 (Q3)...")
        email_results = await self.node_generate_emails()
        report_lines.append(f"  已生成 {len(email_results)} 个邮件序列")

        # Node 6
        step = 6
        progress("保存结果到数据库并输出汇总 (Q5)...")
        summary = await self.node_output_results()
        report_lines.append("  数据已持久化 ✅")

        report_lines.append("\n" + summary)
        return "\n".join(report_lines)

    # ── Interactive Chat ───────────────────────────

    def get_chat_agent(self) -> Any:
        """Get a conversational agent with database memory for interactive use.

        Returns a callable that accepts {"input": str} and
        configuration {"configurable": {"session_id": "xxx"}}.
        """
        from langchain_core.messages import HumanMessage

        agent = self._build_agent()

        def chat_fn(inputs: dict) -> dict:
            session_id = inputs.get("configurable", {}).get("session_id", "default")
            user_input = inputs.get("input", "")
            result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
            return {"output": result["messages"][-1].content}

        return chat_fn
