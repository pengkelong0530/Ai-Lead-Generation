"""Streamlit UI for AI Lead Generation Agent.

Provides an interactive chat interface with:
- Sidebar: session management, mode toggle, configuration
- Chat: user input with streaming agent responses
- Results: company table, scoring details, email previews (Q3)
- Reasoning: agent decision transparency (Q4)

Usage:
    streamlit run main.py
"""

import asyncio
import uuid
from typing import Any, Optional

import streamlit as st
import pandas as pd

from config import config

# Page config must be first Streamlit call
st.set_page_config(
    page_title="AI 海外获客 Agent",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ──────────────────────────────────────────────
# Session State Initialization
# ──────────────────────────────────────────────


def init_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "results" not in st.session_state:
        st.session_state.results = None
    if "demo_mode" not in st.session_state:
        st.session_state.demo_mode = config.app.demo_mode
    if "pipeline_running" not in st.session_state:
        st.session_state.pipeline_running = False


# ──────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────


def render_sidebar() -> None:
    """Render the sidebar controls."""
    with st.sidebar:
        st.title("🌍 AI 海外获客 Agent")
        st.markdown("---")

        # Mode toggle
        st.session_state.demo_mode = st.toggle(
            "🎯 Demo Mode",
            value=st.session_state.demo_mode,
            help="启用后将使用模拟数据，无需 API Key",
        )

        # Session info
        st.markdown("### 会话信息")
        st.code(st.session_state.session_id, language="text")

        st.markdown("---")

        # Clear chat button
        if st.button("🔄 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.results = None
            st.rerun()

        # About section
        st.markdown("---")
        st.markdown(
            """
            **关于本 Agent**

            基于 LangChain 构建的 AI 海外获客智能体，
            自动完成目标企业搜索 → ICP 筛选 →
            评分 → 信息采集 → 邮件生成 → 数据持久化。

            **已确认优化:**
            - ✅ Q1: 多平台搜索
            - ✅ Q2: 客户评分排序
            - ✅ Q3: 多轮邮件链
            - ✅ Q4: 推理过程透明
            - ✅ Q5: MySQL 持久化
            """
        )


# ──────────────────────────────────────────────
# Chat Area
# ──────────────────────────────────────────────


def render_chat() -> None:
    """Render the chat message area."""
    chat_container = st.container()

    with chat_container:
        # Display chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                # If this message has results data attached, display it
                if "results_data" in msg:
                    render_results_tables(msg["results_data"])

    # Chat input
    if not st.session_state.pipeline_running:
        user_input = st.chat_input(
            "输入需求，例如：我要开发德国刀具行业客户",
        )
        if user_input:
            handle_user_input(user_input)
    else:
        # Show a disabled input while pipeline is running
        st.chat_input("⏳ Agent 执行中，请稍候...", disabled=True)


# ──────────────────────────────────────────────
# Results Display
# ──────────────────────────────────────────────


def render_results_tables(results: dict[str, Any]) -> None:
    """Render results: company table, scores, emails, reasoning."""
    if not results:
        return

    tabs = st.tabs(["📋 客户列表", "📊 评分详情", "📧 邮件预览", "🧠 推理日志"])

    # Tab 1: Company table
    with tabs[0]:
        companies = results.get("companies", [])
        if companies:
            df = pd.DataFrame([
                {
                    "公司名称": c.get("name", ""),
                    "行业": c.get("industry", ""),
                    "地区": c.get("region", ""),
                    "网站": c.get("website", ""),
                    "评分": c.get("score", 0),
                    "来源": c.get("source", ""),
                }
                for c in companies
            ])
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "网站": st.column_config.LinkColumn("网站"),
                },
            )
        else:
            st.info("暂无客户数据")

    # Tab 2: Score details
    with tabs[1]:
        scores = results.get("scores", [])
        if scores:
            for s in scores:
                with st.expander(f"⭐ {s.get('company_name', '')} — {s.get('total_score', 0)}/100"):
                    st.markdown(f"**推荐操作:** {s.get('recommendation', '')}")
                    st.markdown(f"**推理过程:**\n{s.get('reasoning', '')}")
        else:
            st.info("暂无评分数据")

    # Tab 3: Email preview
    with tabs[2]:
        emails = results.get("emails", [])
        if emails:
            for email_bundle in emails:
                company_name = email_bundle.get("company_name", "Unknown")
                with st.expander(f"📧 {company_name} 邮件序列"):
                    for e in email_bundle.get("emails", []):
                        st.markdown(f"**邮件 {e.get('sequence_no')}** (Day {e.get('scheduled_day')})")
                        st.markdown(f"**主题:** {e.get('subject', '')}")
                        st.text_area(
                            "正文",
                            value=e.get("body", ""),
                            height=200,
                            key=f"email_{company_name}_{e.get('sequence_no')}",
                            disabled=True,
                        )
                        if e.get("writer_note"):
                            st.caption(f"💡 {e['writer_note']}")
                        st.divider()
        else:
            st.info("暂无邮件数据")

    # Tab 4: Reasoning logs
    with tabs[3]:
        logs = results.get("reasoning_logs", [])
        if logs:
            for log in logs:
                node_name = log.get("node", "unknown")
                confidence = log.get("confidence", "N/A")
                with st.expander(f"🧩 {node_name} (置信度: {confidence})"):
                    st.markdown(f"**输入:**\n{log.get('input_text', '')}")
                    st.markdown(f"**输出:**\n{log.get('output_text', '')}")
                    if log.get("reasoning"):
                        st.markdown(f"**推理:**\n{log['reasoning']}")
        else:
            st.info("暂无推理日志")


# ──────────────────────────────────────────────
# Handle User Input
# ──────────────────────────────────────────────


def build_results_package(
    companies: list,
    scores: list,
    emails: list,
    logs: list,
) -> dict[str, Any]:
    """Build a structured results package for display."""
    return {
        "companies": [c if isinstance(c, dict) else c.model_dump()
                      for c in companies],
        "scores": [s if isinstance(s, dict) else s.model_dump()
                   for s in scores],
        "emails": emails,
        "reasoning_logs": [l if isinstance(l, dict) else l.model_dump()
                           for l in logs],
    }


def handle_user_input(user_input: str) -> None:
    """Process user input and run the pipeline.

    In demo mode, uses mock data. In live mode, runs the full agent pipeline.
    """
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    if st.session_state.demo_mode:
        handle_demo_input(user_input)
    else:
        # Launch async pipeline
        asyncio.run(handle_live_pipeline(user_input))


def handle_demo_input(user_input: str) -> None:
    """Handle input in demo mode — instant mock response."""
    from demo.demo_mode import DemoMode
    from demo import mock_data as demo_mock
    from models.score import AgentReasoning

    demo = DemoMode(enabled=True)

    # Build response incrementally for better UX
    response_parts = []
    results_data = {}

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()

        # Node 1
        response_parts.append("✅ **[1/6] 理解需求**")
        response_parts.append("  地区: Germany | 行业: Cutting Tools\n")
        msg_placeholder.markdown("\n".join(response_parts))

        # Node 2
        response_parts.append("✅ **[2/6] 搜索目标企业 (Q1 多平台)**")
        companies = demo.get_qualified_companies()
        response_parts.append(f"  找到 {len(companies)} 家候选企业\n")
        msg_placeholder.markdown("\n".join(response_parts))

        # Node 3
        response_parts.append("✅ **[3/6] ICP 筛选与评分 (Q2)**")
        response_parts.append("  合格: 5 家候选企业 (阈值: 50/100)\n")
        msg_placeholder.markdown("\n".join(response_parts))

        # Node 4
        response_parts.append("✅ **[4/6] 收集详细信息与联系方式**")
        response_parts.append("  已完成 5 家企业的信息采集\n")
        msg_placeholder.markdown("\n".join(response_parts))

        # Node 5
        response_parts.append("✅ **[5/6] 生成多轮跟进邮件 (Q3)**")
        response_parts.append("  已生成 5 个邮件序列 (每个序列 3 封)\n")
        msg_placeholder.markdown("\n".join(response_parts))

        # Node 6
        response_parts.append("✅ **[6/6] 保存结果到数据库 (Q5)**")
        response_parts.append("  数据已持久化 ✅\n")
        msg_placeholder.markdown("\n".join(response_parts))

        # Summary
        response_parts.append(demo.get_summary_report())
        msg_placeholder.markdown("\n".join(response_parts))

        # Build results data for tabs
        from demo.mock_data import SAMPLE_SCORES, SAMPLE_EMAILS
        results_data = build_results_package(
            companies=companies,
            scores=list(SAMPLE_SCORES.values()),
            emails=[{
                "company_name": "Walter AG",
                "emails": [
                    e.model_dump()
                    for e in SAMPLE_EMAILS.get("Walter AG", [])
                ],
            }],
            logs=demo.get_reasoning_logs(),
        )

        # Render result tables
        render_results_tables(results_data)

    # Save to session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": "\n".join(response_parts),
        "results_data": results_data,
    })


async def handle_live_pipeline(user_input: str) -> None:
    """Handle input in live mode — runs actual agent pipeline."""
    from agent.supervisor_agent import SupervisorAgent

    st.session_state.pipeline_running = True

    response_parts = []
    results_data = {}

    try:
        with st.chat_message("assistant"):
            msg_placeholder = st.empty()
            msg_placeholder.markdown("⏳ Agent 启动中...")

            agent = SupervisorAgent()
            result = await agent.run_pipeline(
                user_input=user_input,
                auto_confirm=True,
            )

            response_parts.append(result)

            # Collect results from agent state
            results_data = build_results_package(
                companies=agent._found_companies,
                scores=[a["score"] for a in agent._qualified_companies],
                emails=[{
                    "company_name": a["company"].name,
                    "emails": [],  # Could be populated from email agent results
                } for a in agent._qualified_companies],
                logs=[],  # Could query from DB
            )

            msg_placeholder.markdown(result)
            render_results_tables(results_data)

    except Exception as e:
        error_msg = f"❌ 执行出错: {str(e)}"
        response_parts.append(error_msg)

        with st.chat_message("assistant"):
            st.error(error_msg)

    finally:
        st.session_state.pipeline_running = False

    st.session_state.messages.append({
        "role": "assistant",
        "content": "\n".join(response_parts),
        "results_data": results_data,
    })


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────


def main() -> None:
    """Main Streamlit app entry point."""
    init_session_state()
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()
