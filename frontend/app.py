import streamlit as st
import requests
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="QueryLens — SQL Optimizer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=DM+Sans:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
code, .stCode, textarea { font-family: 'JetBrains Mono', monospace !important; }

.metric-card {
    background: white;
    border: 1px solid #e8ecf2;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
}

.score-pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
}

.pill-green { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.pill-amber { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
.pill-red   { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.pill-blue  { background: #eff4ff; color: #2563eb; border: 1px solid #bfcffd; }

.issue-critical { background: #fef2f2; border-left: 3px solid #dc2626; padding: 8px 12px; border-radius: 0 6px 6px 0; margin-bottom: 6px; }
.issue-warning  { background: #fffbeb; border-left: 3px solid #d97706; padding: 8px 12px; border-radius: 0 6px 6px 0; margin-bottom: 6px; }
.issue-info     { background: #eff4ff; border-left: 3px solid #2563eb; padding: 8px 12px; border-radius: 0 6px 6px 0; margin-bottom: 6px; }

.suggestion-box { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; }
.dba-box        { background: #eff4ff; border-left: 3px solid #2563eb; padding: 8px 12px; border-radius: 0 6px 6px 0; margin-bottom: 6px; }

.stButton > button {
    background: #2563eb !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ QueryLens")
    st.markdown("*SQL Optimization Platform*")
    st.divider()

    page = st.radio("Navigation", [
        "🏠 Dashboard",
        "🔬 Query Analyzer",
        "⇄ Comparison",
        "📄 Reports",
        "⏱ History",
        "⚙ Settings",
    ])

    st.divider()
    st.markdown("**Database Engine**")
    db_type = st.selectbox("", ["postgresql", "mysql"], label_visibility="collapsed")

    st.divider()
    st.markdown("**Analysis Options**")
    run_benchmark = st.checkbox("Run Benchmark (10x)", value=False)
    gen_pdf = st.checkbox("Generate PDF Report", value=False)

    st.divider()
    st.caption("QueryLens v1.0 · Built with FastAPI + Streamlit")


# ── Helper functions ───────────────────────────────────────────────────────────
def score_color(score):
    if score >= 80: return "🟢"
    if score >= 60: return "🟡"
    return "🔴"

def score_label(score):
    if score >= 90: return "Highly Optimized"
    if score >= 75: return "Well Optimized"
    if score >= 60: return "Moderate"
    if score >= 40: return "Poor"
    return "Critical"

def safety_emoji(status):
    return {"SAFE": "✅", "WARNING": "⚠️", "NOT SAFE": "❌"}.get(status, "❓")

def call_api(endpoint, payload):
    try:
        r = requests.post(f"{API_URL}/{endpoint}", json=payload, timeout=30)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Cannot connect to backend. Make sure the FastAPI server is running at " + API_URL
    except Exception as e:
        return None, str(e)

def get_history_api(limit=20):
    try:
        r = requests.get(f"{API_URL}/history?limit={limit}", timeout=10)
        return r.json()
    except:
        return []


SAMPLE_QUERIES = {
    "SELECT * — Multiple JOINs": """SELECT * 
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN products p ON o.product_id = p.id
WHERE o.status = 'pending'
ORDER BY o.created_at DESC;""",

    "Correlated Subquery (N+1)": """SELECT u.user_id, u.email,
  (SELECT COUNT(*) FROM orders o WHERE o.user_id = u.user_id) AS cnt,
  (SELECT SUM(total) FROM orders o WHERE o.user_id = u.user_id) AS spent
FROM users u
WHERE u.status = 'active';""",

    "Function on Indexed Column": """SELECT order_id, total_amount
FROM orders
WHERE YEAR(created_at) = 2024
  AND MONTH(created_at) = 6;""",

    "Cartesian JOIN": """SELECT p.name, c.category_name, s.qty
FROM products p, categories c, stock s
WHERE p.price > 100;""",

    "Good — Optimized Query": """SELECT u.user_id, u.email, COUNT(o.order_id) AS orders
FROM users u
INNER JOIN orders o ON u.user_id = o.user_id
WHERE o.created_at BETWEEN '2024-01-01' AND '2024-12-31'
  AND o.status = 'completed'
GROUP BY u.user_id, u.email
ORDER BY orders DESC
LIMIT 50;"""
}


# ══════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.title("Dashboard")
    st.caption("Your SQL performance overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Queries Analyzed", "247", "+12%")
    col2.metric("Avg Performance Score", "81", "+8 pts")
    col3.metric("Slow Queries Flagged", "19", "-4")
    col4.metric("Reports Generated", "12", "+3")

    st.divider()

    col_l, col_r = st.columns([2, 1])

    with col_l:
        st.subheader("Query Volume & Avg Score (Last 7 Days)")
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Queries", x=days,
                             y=[28, 42, 35, 61, 47, 53, 38],
                             marker_color="#2563eb", opacity=0.7))
        fig.add_trace(go.Scatter(name="Avg Score", x=days,
                                 y=[64, 71, 68, 79, 76, 83, 81],
                                 mode="lines+markers", line=dict(color="#16a34a", width=2),
                                 yaxis="y2"))
        fig.update_layout(
            height=280, margin=dict(l=0,r=0,t=10,b=0),
            yaxis2=dict(overlaying="y", side="right", title="Score"),
            legend=dict(orientation="h", y=-0.2),
            plot_bgcolor="white", paper_bgcolor="white"
        )
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#f1f3f7")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Issue Distribution")
        fig2 = px.pie(
            names=["SELECT *", "Missing Index", "Bad JOIN", "Subquery", "No LIMIT"],
            values=[34, 28, 19, 12, 7],
            color_discrete_sequence=["#dc2626","#d97706","#7c3aed","#2563eb","#16a34a"],
            hole=0.6
        )
        fig2.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                           paper_bgcolor="white", showlegend=True,
                           legend=dict(font=dict(size=11)))
        fig2.update_traces(textinfo="none")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Score Breakdown by Category")
    categories = ["Index Usage", "JOIN Quality", "WHERE Clause", "Subqueries", "Column Selection"]
    scores_val = [78, 65, 85, 42, 70]
    fig3 = go.Figure(go.Bar(
        x=scores_val, y=categories, orientation="h",
        marker_color=["#16a34a" if s>=70 else "#d97706" if s>=50 else "#dc2626" for s in scores_val],
        text=[f"{s}/100" for s in scores_val], textposition="outside"
    ))
    fig3.update_layout(height=220, margin=dict(l=0,r=60,t=10,b=0),
                       plot_bgcolor="white", paper_bgcolor="white",
                       xaxis=dict(range=[0,110], showgrid=True, gridcolor="#f1f3f7"))
    st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# PAGE: QUERY ANALYZER
# ══════════════════════════════════════════════════════════════════
elif page == "🔬 Query Analyzer":
    st.title("Query Analyzer")
    st.caption("Paste your SQL and get AI-powered optimization insights")

    col_input, col_results = st.columns([1, 1])

    with col_input:
        st.subheader("SQL Input")

        preset_choice = st.selectbox("Load Sample Query", ["— choose —"] + list(SAMPLE_QUERIES.keys()))
        default_sql = SAMPLE_QUERIES.get(preset_choice, "SELECT * FROM orders WHERE status = 'pending';")

        sql_input = st.text_area("SQL Query", value=default_sql, height=260,
                                 placeholder="Paste your SQL query here...")

        if st.button("⚡ Analyze Query", use_container_width=True):
            if not sql_input.strip():
                st.error("Please enter a SQL query.")
            else:
                with st.spinner("Analyzing with AI..."):
                    result, err = call_api("analyze", {
                        "query": sql_input,
                        "db_type": db_type,
                        "run_benchmark": run_benchmark,
                        "generate_pdf": gen_pdf
                    })

                if err:
                    st.error(err)
                else:
                    st.session_state["last_result"] = result
                    st.success("Analysis complete!")

    with col_results:
        if "last_result" not in st.session_state:
            st.info("Results will appear here after analysis.")
        else:
            r = st.session_state["last_result"]
            score = r.get("score", 0)
            safety = r.get("safety", {})

            st.subheader("Analysis Results")

            m1, m2, m3 = st.columns(3)
            m1.metric("Performance Score", f"{score}/100", delta=score_label(score))
            m2.metric("Issues Found", len(r.get("issues", [])))
            m3.metric("Rows Scanned", r.get("rows_scanned", "N/A"))

            # Score gauge
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                domain={"x": [0,1], "y": [0,1]},
                gauge={
                    "axis": {"range": [0,100]},
                    "bar": {"color": "#16a34a" if score>=80 else "#d97706" if score>=60 else "#dc2626"},
                    "steps": [
                        {"range":[0,60], "color":"#fef2f2"},
                        {"range":[60,80], "color":"#fffbeb"},
                        {"range":[80,100], "color":"#f0fdf4"},
                    ]
                }
            ))
            fig_gauge.update_layout(height=200, margin=dict(l=20,r=20,t=20,b=0),
                                    paper_bgcolor="white")
            st.plotly_chart(fig_gauge, use_container_width=True)

            # Safety
            status = safety.get("status", "UNKNOWN")
            st.markdown(f"**Production Safety:** {safety_emoji(status)} `{status}`")
            st.caption(safety.get("summary", ""))

            # Issues
            issues = r.get("issues", [])
            if issues:
                st.subheader("Issues Detected")
                for issue in issues:
                    sev = issue.get("severity", "info")
                    icon = {"critical":"🔴","warning":"🟡","info":"🔵"}.get(sev,"•")
                    css = f"issue-{sev}"
                    st.markdown(
                        f'<div class="{css}">{icon} <strong>{issue.get("code","")}</strong> — {issue.get("description","")}</div>',
                        unsafe_allow_html=True
                    )

            # Tabs for more detail
            tab1, tab2, tab3, tab4 = st.tabs(["Optimized SQL", "Suggestions", "Exec Plan", "Safety Checks"])

            with tab1:
                st.code(r.get("optimized_sql", ""), language="sql")
                if gen_pdf and r.get("report_path"):
                    st.success(f"PDF saved: {r['report_path']}")

            with tab2:
                for s in r.get("suggestions", []):
                    st.markdown(
                        f'<div class="suggestion-box"><strong>✅ {s["title"]}</strong><br>{s["detail"]}</div>',
                        unsafe_allow_html=True
                    )

            with tab3:
                for step in r.get("exec_plan", []):
                    t = step.get("type","").upper()
                    badge = {"SCAN":"🔴","INDEX":"🟢","JOIN":"🔵","SORT":"🟡","FILTER":"🟣"}.get(t,"⚪")
                    st.markdown(f"{badge} **`{t}`** — {step.get('description','')}")

            with tab4:
                checks = safety.get("checks", [])
                for c in checks:
                    icon = "✅" if c.get("passed") else "❌"
                    st.markdown(f"{icon} **{c.get('check','')}** — {c.get('note','')}")


# ══════════════════════════════════════════════════════════════════
# PAGE: COMPARISON
# ══════════════════════════════════════════════════════════════════
elif page == "⇄ Comparison":
    st.title("Before vs After Comparison")
    st.caption("Run both queries and compare performance side-by-side")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**⛔ Original Query**")
        orig = st.text_area("", height=200, key="comp_orig",
                            value="SELECT *\nFROM orders o\nJOIN users u ON o.user_id = u.id\nWHERE o.status = 'pending';")
    with col_b:
        st.markdown("**✅ Optimized Query**")
        opt = st.text_area("", height=200, key="comp_opt",
                           value="SELECT o.order_id, u.email\nFROM orders o\nINNER JOIN users u ON o.user_id = u.user_id\nWHERE o.status = 'pending'\n  AND o.created_at >= NOW() - INTERVAL '30 days'\nLIMIT 100;")

    if st.button("⇄ Compare Queries", use_container_width=True):
        with st.spinner("Comparing..."):
            result, err = call_api("compare", {"original": orig, "optimized": opt, "db_type": db_type})

        if err:
            st.error(err)
        else:
            st.session_state["comp_result"] = result

    if "comp_result" in st.session_state:
        cr = st.session_state["comp_result"]
        before = cr.get("before", {})
        after = cr.get("after", {})
        bench = cr.get("benchmark", {})

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Score Delta", f"+{cr.get('improvement',{}).get('score_delta',0)} pts")
        c2.metric("Speedup", f"{bench.get('speedup_factor','N/A')}×")
        c3.metric("Time Reduction", f"{bench.get('time_reduction_pct',0)}%")

        if bench.get("original") and bench.get("optimized"):
            st.subheader("Benchmark — 10 Runs")
            runs = list(range(1, 11))
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Original", x=runs,
                                 y=bench["original"].get("all_runs", []),
                                 marker_color="rgba(220,38,38,0.6)"))
            fig.add_trace(go.Bar(name="Optimized", x=runs,
                                 y=bench["optimized"].get("all_runs", []),
                                 marker_color="rgba(22,163,74,0.6)"))
            fig.update_layout(height=280, barmode="group", margin=dict(l=0,r=0,t=10,b=0),
                               plot_bgcolor="white", paper_bgcolor="white",
                               yaxis_title="Time (ms)")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Safety Validation")
        safety = cr.get("safety", {})
        st.markdown(f"**Status:** {safety_emoji(safety.get('status','?'))} `{safety.get('status','?')}`")
        for c in safety.get("checks", []):
            icon = "✅" if c.get("passed") else "❌"
            st.markdown(f"{icon} {c.get('check','')} — {c.get('note','')}")


# ══════════════════════════════════════════════════════════════════
# PAGE: REPORTS
# ══════════════════════════════════════════════════════════════════
elif page == "📄 Reports":
    st.title("Reports")
    st.caption("Auto-generated client-ready PDF reports")

    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports", "generated")
    os.makedirs(reports_dir, exist_ok=True)

    report_files = sorted(
        [f for f in os.listdir(reports_dir) if f.endswith(".pdf")],
        reverse=True
    )

    if not report_files:
        st.info("No reports generated yet. Run an analysis with 'Generate PDF Report' enabled.")
    else:
        for fname in report_files:
            fpath = os.path.join(reports_dir, fname)
            fsize = round(os.path.getsize(fpath) / 1024, 1)
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"📄 **{fname}** · {fsize} KB")
                st.caption(datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%B %d, %Y %H:%M"))
            with col2:
                with open(fpath, "rb") as f:
                    st.download_button("⬇ Download", f, file_name=fname,
                                       mime="application/pdf", key=fname)
            st.divider()

    st.subheader("Generate Report from Last Analysis")
    if "last_result" in st.session_state:
        if st.button("📄 Generate PDF Now"):
            from report_generator import generate_report
            path = generate_report(st.session_state["last_result"])
            st.success(f"Report saved: {path}")
            with open(path, "rb") as f:
                st.download_button("⬇ Download Report", f,
                                   file_name=os.path.basename(path),
                                   mime="application/pdf")
    else:
        st.info("Run an analysis first to generate a report.")


# ══════════════════════════════════════════════════════════════════
# PAGE: HISTORY
# ══════════════════════════════════════════════════════════════════
elif page == "⏱ History":
    st.title("Query History")
    st.caption("Audit log of all analyzed queries")

    data = get_history_api(50)

    if not data:
        st.info("No queries analyzed yet.")
    else:
        df = pd.DataFrame(data)
        df["score_label"] = df["score"].apply(score_label)

        score_filter = st.selectbox("Filter by Score",
                                     ["All", "Optimized (80+)", "Moderate (60-79)", "Poor (<60)"])
        if score_filter == "Optimized (80+)":
            df = df[df["score"] >= 80]
        elif score_filter == "Moderate (60-79)":
            df = df[(df["score"] >= 60) & (df["score"] < 80)]
        elif score_filter == "Poor (<60)":
            df = df[df["score"] < 60]

        st.dataframe(
            df[["timestamp","db_type","original_query","score","safety_status","issues_count"]],
            column_config={
                "timestamp": "Time",
                "db_type": "DB",
                "original_query": st.column_config.TextColumn("Query", max_chars=60),
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
                "safety_status": "Safety",
                "issues_count": "Issues",
            },
            use_container_width=True
        )

        csv = df.to_csv(index=False)
        st.download_button("⬇ Export CSV", csv, "query_history.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════
elif page == "⚙ Settings":
    st.title("Settings")

    st.subheader("Database Connections")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("PostgreSQL URL", type="password",
                      placeholder="postgresql://user:pass@host:5432/db")
    with col2:
        st.text_input("MySQL URL", type="password",
                      placeholder="mysql+pymysql://user:pass@host/db")

    if st.button("Test Connections"):
        try:
            r = requests.get(f"{API_URL}/", timeout=5)
            st.success("✅ Backend API is reachable")
        except:
            st.error("❌ Cannot reach backend API at " + API_URL)

    st.divider()
    st.subheader("Analysis Thresholds")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.number_input("Poor Score Threshold", value=60, min_value=1, max_value=100)
    with col2:
        st.number_input("Slow Query Threshold (ms)", value=1000, min_value=100)
    with col3:
        st.number_input("Max Rows Scanned Alert", value=10000, min_value=100)

    st.divider()
    st.subheader("Free Deployment Stack")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
| Component | Service | Cost |
|-----------|---------|------|
| Frontend  | Streamlit Cloud | Free |
| Backend   | Render.com | Free |
| PostgreSQL | Neon | Free |
| MySQL | PlanetScale | Free |
| SQLite History | Render disk | Free |
        """)
    with col2:
        st.code("""
# Deploy backend to Render
# 1. Push to GitHub
# 2. Connect Render to repo
# 3. Build: pip install -r requirements.txt
# 4. Start: uvicorn app:app --host 0.0.0.0 --port $PORT
# 5. Add env vars in Render dashboard

# Deploy frontend to Streamlit Cloud
# 1. Push frontend/ to GitHub
# 2. Go to share.streamlit.io
# 3. Select repo → frontend/app.py
# 4. Add secrets: API_URL = https://...
        """, language="bash")
