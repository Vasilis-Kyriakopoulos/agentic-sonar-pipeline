"""
ui.py — Streamlit Dashboard for the Agentic SonarQube Fix Pipeline.

Connects to the FastAPI backend (api.py) to:
  1. Fetch issues from SonarQube
  2. Launch pipeline runs
  3. Monitor progress in real time
  4. View analytics and history
"""

import time
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Agentic SonarQube Pipeline",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* Global font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Header gradient */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 2rem; font-weight: 700; }
    .main-header p { color: rgba(255,255,255,0.85); margin: 0.5rem 0 0 0; font-size: 1.05rem; }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
        text-align: center;
    }
    .metric-card .value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #667eea;
    }
    .metric-card .label {
        font-size: 0.85rem;
        color: #8892b0;
        margin-top: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Issue table styling */
    .issue-row {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
    }

    /* Status badges */
    .badge { padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.8rem; font-weight: 600; display: inline-block; }
    .badge-pass { background: rgba(16,185,129,0.15); color: #10b981; }
    .badge-fail { background: rgba(239,68,68,0.15); color: #ef4444; }
    .badge-retry { background: rgba(245,158,11,0.15); color: #f59e0b; }
    .badge-progress { background: rgba(59,130,246,0.15); color: #3b82f6; }
    .badge-verified { background: rgba(16,185,129,0.25); color: #059669; border: 1px solid rgba(16,185,129,0.3); }
    .badge-unverified { background: rgba(239,68,68,0.25); color: #dc2626; border: 1px solid rgba(239,68,68,0.3); }

    /* Verification card */
    .verify-card {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
        margin: 1rem 0;
    }
    .verify-card h4 { color: #e2e8f0; margin: 0 0 0.5rem 0; }
    .verify-card p { color: #94a3b8; margin: 0.25rem 0; }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a2e 100%);
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper — talk to the FastAPI backend
# ---------------------------------------------------------------------------

def api_get(path: str, **kwargs):
    """GET request to the FastAPI backend."""
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to the API. Is the FastAPI server running?")
        st.info(f"Expected at: `{API_BASE}`")
        st.code("uvicorn api:app --host 0.0.0.0 --port 8000", language="bash")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None


def api_post(path: str, json_body: dict, timeout: int = 300):
    """POST request to the FastAPI backend."""
    try:
        resp = requests.post(f"{API_BASE}{path}", json=json_body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        st.error("⚠️ The operation timed out. The backend is taking too long.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("⚠️ Cannot connect to the API. Is the FastAPI server running?")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None


# ---------------------------------------------------------------------------
# Sidebar — Navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🔧 Navigation")
    page = st.radio(
        "Go to",
        ["🏠 Dashboard", "🚀 Run Pipeline", "📋 Issues", "📊 Analytics"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(
        "<div style='text-align:center; color:#8892b0; font-size:0.8rem;'>"
        "Agentic SonarQube Pipeline<br/>v1.0.0"
        "</div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Dashboard
# ═══════════════════════════════════════════════════════════════════════════

if page == "🏠 Dashboard":
    # Header
    st.markdown(
        '<div class="main-header">'
        '<h1>🔧 Agentic SonarQube Pipeline</h1>'
        '<p>Multi-agent system for automated code quality fixes</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Analytics summary
    analytics = api_get("/analytics")
    if analytics:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value">{analytics["total_issues"]}</div>'
                f'<div class="label">Total Issues</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value" style="color:#10b981">{analytics["fixed"]}</div>'
                f'<div class="label">Fixed</div></div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value" style="color:#ef4444">{analytics["failed"]}</div>'
                f'<div class="label">Failed</div></div>',
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value" style="color:#667eea">{analytics["success_rate_pct"]}%</div>'
                f'<div class="label">Success Rate</div></div>',
                unsafe_allow_html=True,
            )

        # Verification metrics row
        v1, v2, v3 = st.columns(3)
        with v1:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value" style="color:#059669">{analytics.get("verified", 0)}</div>'
                f'<div class="label">Verified Fixes ✅</div></div>',
                unsafe_allow_html=True,
            )
        with v2:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value" style="color:#dc2626">{analytics.get("verification_failed", 0)}</div>'
                f'<div class="label">Verification Failed ⚠️</div></div>',
                unsafe_allow_html=True,
            )
        with v3:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="value" style="color:#8892b0">{analytics.get("pending_verification", 0)}</div>'
                f'<div class="label">Pending Verification</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # Cost & usage
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("💰 Cost Summary")
            st.metric("Total Tokens Used", f"{analytics['total_tokens']:,}")
            st.metric("Total API Cost", f"${analytics['total_cost_usd']:.4f}")
            st.metric("Avg Attempts/Run", analytics["avg_attempts"])

        with col_b:
            st.subheader("🤖 Cost by Agent")
            if analytics.get("cost_by_agent"):
                for agent, cost in sorted(analytics["cost_by_agent"].items()):
                    pct = (cost / analytics["total_cost_usd"] * 100) if analytics["total_cost_usd"] > 0 else 0
                    st.markdown(f"**{agent}** — ${cost:.4f} ({pct:.1f}%)")
                    st.progress(min(pct / 100, 1.0))
            else:
                st.info("No cost data yet — run the pipeline first.")

    # Recent runs
    st.markdown("---")
    st.subheader("📜 Recent Pipeline Runs")
    runs = api_get("/runs?limit=10")
    if runs:
        for run in runs:
            verdict = run.get("verdict", "UNKNOWN")
            badge_cls = {"SUCCESS": "badge-pass", "FAIL": "badge-fail", "IN_PROGRESS": "badge-progress"}.get(verdict, "badge-retry")

            # Verification badge
            verified = run.get("verified")
            if verified is True:
                verify_badge = ' <span class="badge badge-verified">VERIFIED</span>'
            elif verified is False:
                verify_badge = ' <span class="badge badge-unverified">UNVERIFIED</span>'
            else:
                verify_badge = ""

            st.markdown(
                f'<div class="issue-row">'
                f'<span class="badge {badge_cls}">{verdict}</span>{verify_badge} '
                f'<strong>Run #{run["id"]}</strong> — Issue: <code>{run["issue_key"][:12]}…</code> '
                f'— Attempts: {run["attempts"]} '
                f'— {run.get("started_at", "")[:19]}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No pipeline runs yet.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Run Pipeline
# ═══════════════════════════════════════════════════════════════════════════

elif page == "🚀 Run Pipeline":
    st.markdown(
        '<div class="main-header">'
        '<h1>🚀 Run Pipeline</h1>'
        '<p>Fix SonarQube issues automatically with AI agents</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- Step 1: Configure ---
    st.subheader("1️⃣ Configure")

    repo_mode = st.radio("Repository source", ["Git URL (clone)", "Local path (already cloned)"], horizontal=True)

    if repo_mode == "Git URL (clone)":
        repo_url = st.text_input("Git Repository URL", placeholder="https://github.com/user/repo.git")
        repo_path = None
    else:
        repo_url = None
        repo_path = st.text_input("Local repository path", placeholder="/app/repos/my-project")

    project_key = st.text_input("SonarQube Project Key", placeholder="my-project")

    # --- Step 1.5: Trigger SonarQube Scan (Optional but recommended) ---
    can_scan = project_key and (repo_url or repo_path)
    if st.button("⚡ Clone & Run SonarQube Scan", type="secondary", disabled=not can_scan, use_container_width=True):
        scan_payload = {
            "project_key": project_key,
        }
        if repo_url:
            scan_payload["repo_url"] = repo_url
        elif repo_path:
            scan_payload["repo_path"] = repo_path

        with st.spinner("Cloning repository (if needed) and running SonarQube scan..."):
            res = api_post("/scan", scan_payload)
            if res and res.get("status") == "SUCCESS":
                st.success(f"✅ {res['message']}")
                # Immediately fetch issues and update session state
                st.session_state["fetched_issues"] = []
                data = api_get(f"/issues/{project_key}")
                if data:
                    st.session_state["fetched_issues"] = data.get("issues", [])
                    st.toast("Fetched new issues successfully!", icon="📡")

    # --- Step 2: Preview issues ---
    st.subheader("2️⃣ Preview Issues")

    if project_key:
        if st.button("🔍 Fetch Issues from SonarQube", type="secondary"):
            with st.spinner("Fetching issues..."):
                data = api_get(f"/issues/{project_key}")
                if data:
                    st.session_state["fetched_issues"] = data.get("issues", [])
                    st.success(f"Found **{data['total']}** issue(s)")

        if "fetched_issues" in st.session_state and st.session_state["fetched_issues"]:
            issues = st.session_state["fetched_issues"]

            # Issue table
            issue_options = {}
            for i, issue in enumerate(issues):
                file_path = issue.get("component", "").split(":")[-1]
                label = f"{issue.get('rule', '')} — {file_path}:{issue.get('line', '?')} — {issue.get('message', '')[:60]}"
                issue_options[label] = issue["key"]

            selected_labels = st.multiselect(
                "Select issues to fix (leave empty for all)",
                options=list(issue_options.keys()),
            )

            # Store selected keys
            if selected_labels:
                st.session_state["selected_keys"] = [issue_options[lbl] for lbl in selected_labels]
            else:
                st.session_state["selected_keys"] = ["all"]
    else:
        st.info("Enter a SonarQube project key to fetch issues.")

    # --- Step 3: Launch ---
    st.subheader("3️⃣ Launch Pipeline")

    can_launch = project_key and (repo_url or repo_path)

    if st.button("🚀 Start Pipeline", type="primary", disabled=not can_launch):
        payload = {
            "project_key": project_key,
            "issue_keys": st.session_state.get("selected_keys", ["all"]),
        }
        if repo_url:
            payload["repo_url"] = repo_url
        elif repo_path:
            payload["repo_path"] = repo_path

        with st.spinner("Starting pipeline..."):
            result = api_post("/pipeline/run", payload)

        if result:
            session_id = result["session_id"]
            st.success(f"✅ Pipeline started! Session: `{session_id}`")
            st.session_state["active_session"] = session_id

    # --- Step 4: Live progress ---
    if "active_session" in st.session_state:
        st.subheader("4️⃣ Live Progress")
        session_id = st.session_state["active_session"]

        progress_placeholder = st.empty()
        results_placeholder = st.empty()

        if st.button("🔄 Refresh Status"):
            pass  # Just triggers a rerun

        status = api_get(f"/pipeline/status/{session_id}")
        if status:
            s = status["status"]
            processed = status["processed"]
            total = status["total_issues"]

            if s == "IN_PROGRESS":
                progress_placeholder.progress(
                    processed / total if total > 0 else 0,
                    text=f"Processing issue {processed}/{total}..."
                )
                # Auto-refresh every 5 seconds
                time.sleep(5)
                st.rerun()
            elif s == "VERIFYING":
                progress_placeholder.progress(
                    1.0,
                    text="🔍 Running verification scan..."
                )
                time.sleep(5)
                st.rerun()
            elif s == "COMPLETED":
                progress_placeholder.progress(1.0, text="✅ Pipeline completed!")
            elif s == "FAILED":
                progress_placeholder.error("❌ Pipeline failed")

            # Show results
            if status.get("results"):
                results_placeholder.markdown("### Results")
                for entry in status["results"]:
                    if "error" in entry:
                        st.error(f"Error: {entry['error']}")
                        continue

                    issue = entry.get("issue", {})
                    result = entry.get("result", {})
                    verdict = result.get("status", "UNKNOWN")
                    score = result.get("evaluation", {}).get("overall_score", "-")
                    attempts = result.get("attempt", "-")
                    file_path = issue.get("component", "").split(":")[-1]

                    icon = "✅" if verdict == "SUCCESS" else "❌"
                    badge_cls = "badge-pass" if verdict == "SUCCESS" else "badge-fail"

                    st.markdown(
                        f'<div class="issue-row">'
                        f'{icon} <span class="badge {badge_cls}">{verdict}</span> '
                        f'<strong>{issue.get("rule", "")}</strong> '
                        f'in <code>{file_path}</code> '
                        f'— Score: <strong>{score}</strong> '
                        f'— Attempts: {attempts}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # Show reasoning if available
                    reasoning = result.get("evaluation", {}).get("reasoning", "")
                    if reasoning:
                        with st.expander(f"Evaluator reasoning — {issue.get('rule', '')}"):
                            st.markdown(reasoning)

            # --- Step 5: Verification Results ---
            verification = status.get("verification")
            if verification:
                st.markdown("### 🔍 Verification Results")

                v_status = verification.get("status", "UNKNOWN")
                if v_status == "SUCCESS":
                    st.success(verification.get("message", "All fixes verified!"))
                elif v_status == "PARTIAL":
                    st.warning(verification.get("message", "Some fixes could not be verified."))
                elif v_status == "FAILED":
                    st.error(verification.get("message", "Verification failed."))

                vc1, vc2, vc3 = st.columns(3)
                vc1.metric("Verified ✅", len(verification.get("verified", [])))
                vc2.metric("Still Open ⚠️", len(verification.get("still_open", [])))
                vc3.metric("New Issues", verification.get("new_issues", 0))

                # Show details in expander
                if verification.get("verified"):
                    with st.expander("Verified issue keys"):
                        for k in verification["verified"]:
                            st.markdown(f"- `{k}` ✅")
                if verification.get("still_open"):
                    with st.expander("Still open issue keys"):
                        for k in verification["still_open"]:
                            st.markdown(f"- `{k}` ⚠️")

            elif s == "COMPLETED":
                # Offer manual verification if auto-verify didn't run
                st.markdown("---")
                st.subheader("🔍 Verification")
                st.info("No automatic verification was run (no successful fixes or verification skipped).")

                # Build manual verify payload from session results
                fixed_keys_from_session = [
                    entry.get("issue", {}).get("key")
                    for entry in status.get("results", [])
                    if entry.get("result", {}).get("status") == "SUCCESS"
                    and entry.get("issue", {}).get("key")
                ]

                if fixed_keys_from_session:
                    if st.button("🔍 Run Verification Scan", type="secondary", use_container_width=True):
                        verify_payload = {
                            "project_key": status["project_key"],
                            "issue_keys": fixed_keys_from_session,
                        }
                        # Use repo_path from the session store if available
                        if repo_path:
                            verify_payload["repo_path"] = repo_path
                        elif repo_url:
                            verify_payload["repo_url"] = repo_url

                        with st.spinner("Running verification scan (this may take up to 2 minutes)..."):
                            vr = api_post("/pipeline/verify", verify_payload)
                        if vr:
                            st.session_state["manual_verification"] = vr
                            st.rerun()

                # Show manual verification results if stored
                if "manual_verification" in st.session_state:
                    vr = st.session_state["manual_verification"]
                    v_status = vr.get("status", "UNKNOWN")
                    if v_status == "SUCCESS":
                        st.success(vr.get("message", ""))
                    elif v_status == "PARTIAL":
                        st.warning(vr.get("message", ""))
                    else:
                        st.error(vr.get("message", ""))

                    vc1, vc2, vc3 = st.columns(3)
                    vc1.metric("Verified ✅", len(vr.get("verified", [])))
                    vc2.metric("Still Open ⚠️", len(vr.get("still_open", [])))
                    vc3.metric("New Issues", vr.get("new_issues", 0))


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Issues
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📋 Issues":
    st.markdown(
        '<div class="main-header">'
        '<h1>📋 SonarQube Issues</h1>'
        '<p>Browse and inspect issues for any project</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    project_key = st.text_input("SonarQube Project Key", placeholder="my-project", key="issues_pk")

    if project_key and st.button("🔍 Fetch Issues", key="fetch_btn"):
        with st.spinner("Fetching..."):
            data = api_get(f"/issues/{project_key}")
        if data:
            issues = data.get("issues", [])
            st.success(f"Found **{len(issues)}** issue(s)")

            for issue in issues:
                file_path = issue.get("component", "").split(":")[-1]
                severity = issue.get("severity", "")
                sev_color = {
                    "BLOCKER": "#ef4444", "CRITICAL": "#f97316",
                    "MAJOR": "#f59e0b", "MINOR": "#3b82f6", "INFO": "#8892b0"
                }.get(severity, "#8892b0")

                with st.expander(f"**{issue.get('rule', '')}** — {file_path}:{issue.get('line', '?')} — {issue.get('message', '')[:80]}"):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Severity:** <span style='color:{sev_color}'>{severity}</span>", unsafe_allow_html=True)
                    c2.markdown(f"**Type:** {issue.get('type', '')}")
                    c3.markdown(f"**Status:** {issue.get('issueStatus', issue.get('status', ''))}")

                    st.markdown(f"**Component:** `{issue.get('component', '')}`")
                    st.markdown(f"**Message:** {issue.get('message', '')}")

                    tags = issue.get("tags", [])
                    if tags:
                        st.markdown("**Tags:** " + ", ".join(f"`{t}`" for t in tags))


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Analytics
# ═══════════════════════════════════════════════════════════════════════════

elif page == "📊 Analytics":
    st.markdown(
        '<div class="main-header">'
        '<h1>📊 Pipeline Analytics</h1>'
        '<p>Token usage, costs, and success rates</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    analytics = api_get("/analytics")
    if analytics:
        # Top metrics
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Issues", analytics["total_issues"])
        c2.metric("Fixed ✅", analytics["fixed"])
        c3.metric("Failed ❌", analytics["failed"])
        c4.metric("Open ⏳", analytics["open"])
        c5.metric("Success Rate", f"{analytics['success_rate_pct']}%")

        # Verification row
        v1, v2, v3 = st.columns(3)
        v1.metric("Verified ✅", analytics.get("verified", 0))
        v2.metric("Verification Failed ⚠️", analytics.get("verification_failed", 0))
        v3.metric("Pending Verification", analytics.get("pending_verification", 0))

        st.divider()

        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("📈 Pipeline Stats")
            st.metric("Total Pipeline Runs", analytics["total_runs"])
            st.metric("Avg Attempts per Run", analytics["avg_attempts"])

        with col_b:
            st.subheader("💰 Cost Breakdown")
            st.metric("Total Tokens", f"{analytics['total_tokens']:,}")
            st.metric("Total API Cost", f"${analytics['total_cost_usd']:.6f}")

        st.divider()

        st.subheader("🤖 Cost by Agent")
        if analytics.get("cost_by_agent"):
            for agent, cost in sorted(analytics["cost_by_agent"].items(), key=lambda x: x[1], reverse=True):
                pct = (cost / analytics["total_cost_usd"] * 100) if analytics["total_cost_usd"] > 0 else 0
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{agent}**")
                    st.progress(min(pct / 100, 1.0))
                with col2:
                    st.markdown(f"${cost:.6f} ({pct:.1f}%)")
        else:
            st.info("No cost data yet — run the pipeline first.")

        # Recent runs table
        st.divider()
        st.subheader("📜 All Pipeline Runs")
        runs = api_get("/runs?limit=50")
        if runs:
            import pandas as pd
            df = pd.DataFrame(runs)
            if not df.empty:
                df = df[["id", "issue_key", "verdict", "attempts", "verified", "started_at", "completed_at"]]
                df["verified"] = df["verified"].map({True: "✅", False: "❌", None: "—"})
                df.columns = ["Run ID", "Issue Key", "Verdict", "Attempts", "Verified", "Started", "Completed"]
                st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No pipeline runs yet.")
