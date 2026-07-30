"""Streamlit UI for AI Lead Generation Agent.

Clean dashboard-style UI matching demo.html visual design,
backed by the real agent pipeline.
"""

import asyncio
import uuid

import streamlit as st
import pandas as pd
from config import config

st.set_page_config(page_title="AI 海外获客 Agent", page_icon="A", layout="centered", initial_sidebar_state="expanded")


def main() -> None:
    """Main entry point for the Streamlit UI."""
    # ── CSS ──
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    *{font-family:'Inter',sans-serif}
    .block-container{padding-top:3rem!important;max-width:1000px!important}
    .header-row{display:flex;align-items:center;justify-content:space-between;padding:1.2rem 0 1rem;border-bottom:1px solid #e8ecf0;margin-bottom:1.5rem}
    .header-left{display:flex;align-items:center;gap:14px}
    .logo-box{width:40px;height:40px;border-radius:10px;background:#1a3a7a;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:18px}
    .header-title{font-size:18px;font-weight:600;letter-spacing:-.01em}
    .header-sub{font-size:12px;color:#5e6673}
    .pipeline-row{display:flex;align-items:center;gap:4px;margin-bottom:1.5rem;overflow-x:auto;padding:8px 0}
    .pipe-node{display:flex;flex-direction:column;align-items:center;flex-shrink:0;width:100px}
    .pipe-circle{width:36px;height:36px;border-radius:50%;background:#e8ecf0;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600;color:#929aab;transition:all .4s}
    .pipe-circle.done{background:#1a7a3a;color:#fff}
    .pipe-label{font-size:11px;color:#929aab;margin-top:6px;text-align:center;line-height:1.3;max-width:85px}
    .pipe-label.done{color:#1a7a3a;font-weight:600}
    .pipe-connector{flex-shrink:0;width:24px;height:2px;background:#e8ecf0;margin-top:17px}
    .pipe-connector.done{background:#1a7a3a}
    .stats-row{display:flex;justify-content:space-around;padding:1rem 0;margin-top:1.5rem;background:#fff;border:1px solid #e8ecf0;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
    .stat-item{text-align:center}
    .stat-num{font-size:20px;font-weight:700;color:#1a3a7a}
    .stat-lbl{font-size:11px;color:#5e6673;margin-top:2px}
    .score-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
    @media(max-width:768px){.score-grid{grid-template-columns:1fr}}
    .score-card{border:1px solid #e8ecf0;border-radius:8px;padding:16px;background:#fff}
    .score-card h4{font-size:14px;font-weight:600;margin-bottom:8px}
    .score-row{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:13px;color:#5e6673}
    .s-label{width:80px;flex-shrink:0;font-size:12px}
    .s-bar{flex:1;height:6px;background:#e8ecf0;border-radius:3px;overflow:hidden}
    .s-bar-fill{height:100%;border-radius:3px;background:#1a3a7a}
    .s-val{width:28px;text-align:right;font-weight:600;font-size:12px;color:#1a1d23}
    .score-total{text-align:center;margin-top:10px;font-size:22px;font-weight:700;color:#1a3a7a}
    [data-testid="stSidebarContent"] > div:first-child {padding-top:0!important;margin-top:-0.5rem!important}
    </style>
    """, unsafe_allow_html=True)

    # ── State ──
    for k, v in {"sid": f"streamlit_{uuid.uuid4().hex[:8]}", "demo": config.app.demo_mode, "running": False, "results": None}.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Sidebar ──
    with st.sidebar:
        st.markdown('<div style="font-size:18px;font-weight:600">AI 海外获客 Agent</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:12px;color:#5e6673;margin-bottom:12px">基于 LangChain 的智能获客系统</div>', unsafe_allow_html=True)
        st.divider()
        st.session_state.demo = st.toggle("Demo 模式", value=st.session_state.demo)
        st.divider()
        st.markdown("**关于本 Agent**  \n基于 LangChain + LangGraph 构建，自动完成搜索、ICP 筛选、评分、邮件生成全流程。")
        if st.session_state.results:
            st.divider()
            if st.button("清空结果", use_container_width=True):
                st.session_state.results = None
                st.rerun()

    # ── Header ──
    mode_tag = " · Demo 模式" if st.session_state.demo else ""
    st.markdown(f'<div class="header-row"><div class="header-left"><div class="logo-box">A</div><div><div class="header-title">AI 海外获客 Agent</div><div class="header-sub">基于 LangChain 的智能获客{mode_tag}</div></div></div></div>', unsafe_allow_html=True)

    # ── Input ──
    col1, col2 = st.columns([4, 1])
    with col1:
        inp = st.text_input("需求", value="我要开发德国刀具行业客户", label_visibility="collapsed", disabled=st.session_state.running, key="inp")
    with col2:
        go = st.button("开始执行", type="primary", use_container_width=True, disabled=st.session_state.running)

    # ── Pipeline ──
    done = 6 if st.session_state.results else 0
    labels = ["理解需求", "搜索企业", "ICP筛选", "信息采集", "生成邮件", "结果输出"]
    parts = []
    for i, lbl in enumerate(labels):
        n = i + 1
        cls = "done" if n <= done else ""
        parts.append(f'<div class="pipe-node"><div class="pipe-circle {cls}">{n}</div><div class="pipe-label {cls}">{lbl}</div></div>')
        if i < len(labels) - 1:
            c_cls = "done" if n <= done else ""
            parts.append(f'<div class="pipe-connector {c_cls}"></div>')
    st.markdown(f'<div class="pipeline-row">{"".join(parts)}</div>', unsafe_allow_html=True)

    # ── Results ──
    if st.session_state.results:
        r = st.session_state.results
        comps = r.get("companies", []); scores = r.get("scores", []); emails = r.get("emails", [])
        st.markdown(f'<div class="stats-row"><div class="stat-item"><div class="stat-num">{len(comps)}</div><div class="stat-lbl">客户数</div></div><div class="stat-item"><div class="stat-num">{len(scores)}</div><div class="stat-lbl">评分详情</div></div><div class="stat-item"><div class="stat-num">{len(emails)}</div><div class="stat-lbl">邮件序列</div></div><div class="stat-item"><div class="stat-num">✅</div><div class="stat-lbl">已完成</div></div></div>', unsafe_allow_html=True)
        tab1, tab2, tab3, tab4 = st.tabs(["客户列表", "评分详情", "邮件预览", "推理日志"])
        with tab1:
            if comps:
                st.dataframe(
                    pd.DataFrame([{
                        "公司名称": c.get("name",""),
                        "行业": c.get("industry",""),
                        "地区": c.get("region",""),
                        "匹配度": c.get("score",0),
                        "网站": c.get("website","") or "",
                    } for c in comps]),
                    use_container_width=True, hide_index=True,
                    column_config={"网站": st.column_config.LinkColumn("网站")},
                )
        with tab2:
            if scores:
                cols = st.columns(2)
                for i, s in enumerate(scores):
                    with cols[i % 2]:
                        nm = s.get("company_name", s.get("name", ""))
                        dims = s.get("dims", s.get("icp_criteria", {})); tot = s.get("total_score", s.get("total", 0))
                        if isinstance(dims, dict):
                            dims = [{"l":"行业匹配","v":dims.get("industry_match",0)},{"l":"规模匹配","v":dims.get("size_match",0)},{"l":"需求匹配","v":dims.get("demand_match",0)},{"l":"地区优先级","v":dims.get("region_priority",0)}]
                        h = f'<div class="score-card"><h4>{nm}</h4>'
                        for d in dims: h += f'<div class="score-row"><span class="s-label">{d["l"]}</span><div class="s-bar"><div class="s-bar-fill" style="width:{d["v"]}%"></div></div><span class="s-val">{d["v"]}</span></div>'
                        h += f'<div class="score-total">{tot}<span style="font-size:12px;color:#5e6673;font-weight:400">/100</span></div></div>'
                        st.markdown(h, unsafe_allow_html=True)
        with tab3:
            for em in emails:
                with st.expander(em.get("company_name", "")):
                    for e in em.get("emails", []):
                        st.markdown(f"**Day {e.get('scheduled_day', e.get('day',''))}** - {e.get('subject','')}")
                        st.caption(e.get("body","")[:300] + ("..." if len(e.get("body",""))>300 else ""))
                        st.divider()
        with tab4:
            for l in r.get("logs", []):
                nd=l.get("node","");cf=l.get("confidence",l.get("conf",""));tx=l.get("text",l.get("output_text",""));rs=l.get("reason",l.get("reasoning",""))
                st.markdown(f'<div style="padding:10px 0;border-bottom:1px solid #e8ecf0"><div style="display:flex;justify-content:space-between;font-size:12px"><span style="font-weight:600;color:#1a3a7a">{nd}</span><span style="color:#929aab">{cf}</span></div><div style="font-size:12px;color:#5e6673;margin-top:4px">{tx}</div><div style="margin-top:6px;padding:8px 10px;background:#f0f4fb;border-radius:6px;font-size:12px;color:#5e6673">{rs}</div></div>', unsafe_allow_html=True)
    elif not st.session_state.running:
        st.markdown('<div class="stats-row"><div class="stat-item"><div class="stat-num">-</div><div class="stat-lbl">客户数</div></div><div class="stat-item"><div class="stat-num">-</div><div class="stat-lbl">评分详情</div></div><div class="stat-item"><div class="stat-num">-</div><div class="stat-lbl">邮件序列</div></div><div class="stat-item"><div class="stat-num">-</div><div class="stat-lbl">状态</div></div></div>', unsafe_allow_html=True)

    # ── Execute ──
    if go:
        st.session_state.running = True
        st.session_state.results = None
        with st.spinner("Agent 执行中..."):
            if st.session_state.demo:
                from demo.demo_mode import DemoMode
                from demo.mock_data import SAMPLE_SCORES, SAMPLE_EMAILS
                demo = DemoMode(enabled=True)
                demo._last_input = inp
                region = demo._detect_region(inp)
                st.session_state.results = {
                    "companies": demo.get_qualified_companies(region=region),
                    "scores": [s.model_dump() for s in SAMPLE_SCORES.values()],
                    "emails": [{"company_name": "Walter AG", "emails": [e.model_dump() for e in SAMPLE_EMAILS.get("Walter AG", [])]}],
                    "logs": demo.get_reasoning_logs(),
                }
            else:
                import threading
                results_holder = []
                def run_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        from agent.supervisor_agent import SupervisorAgent
                        agent = SupervisorAgent()
                        loop.run_until_complete(agent.run_pipeline(user_input=inp, auto_confirm=True))
                        results_holder.append({
                            "companies": [c.model_dump() for c in agent._found_companies],
                            "scores": [a["score"].model_dump() for a in agent._qualified_companies],
                            "emails": [],
                            "logs": [],
                        })
                    finally:
                        loop.close()
                thread = threading.Thread(target=run_async)
                thread.start()
                thread.join()
                st.session_state.results = results_holder[0] if results_holder else None
        st.session_state.running = False
        st.rerun()


if __name__ == "__main__":
    main()
