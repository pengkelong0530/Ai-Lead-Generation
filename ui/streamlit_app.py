"""Streamlit UI for AI Lead Generation Agent — demo.html style.

Embeds the polished demo.html as the main interface.
"""

import uuid
from pathlib import Path

import streamlit as st

from config import config

st.set_page_config(
    page_title="AI 海外获客 Agent",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Sidebar ──────────────────────────────────

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <style>
            .sidebar-title{font-size:18px;font-weight:600;margin-bottom:4px}
            .sidebar-sub{font-size:12px;color:#5e6673;margin-bottom:16px}
            </style>
            <div class="sidebar-title">AI 海外获客 Agent</div>
            <div class="sidebar-sub">基于 LangChain 的智能获客演示系统</div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        st.session_state.demo_mode = st.toggle(
            "Demo Mode",
            value=st.session_state.get("demo_mode", config.app.demo_mode),
            help="启用模拟数据，无需 API Key",
        )

        if st.button("重新运行", use_container_width=True, type="primary"):
            st.rerun()

        st.divider()
        st.markdown(
            """
            **关于本 Agent**

            基于 LangChain + LangGraph 构建，
            自动完成搜索 → ICP 筛选 → 评分 →
            信息采集 → 邮件生成 → 数据持久化。

            **优化项:**
            - Q1: 多平台搜索
            - Q2: 客户评分排序
            - Q3: 多轮邮件链
            - Q4: 推理过程透明
            - Q5: SQLite/MySQL 持久化
            """
        )


# ── Main ─────────────────────────────────────

def main() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"

    render_sidebar()

    # Read and embed demo.html
    demo_path = Path(__file__).resolve().parent.parent / "demo.html"
    if not demo_path.exists():
        st.error("demo.html not found")
        return

    html_content = demo_path.read_text(encoding="utf-8")

    st.components.v1.html(html_content, height=950, scrolling=True)


if __name__ == "__main__":
    main()
