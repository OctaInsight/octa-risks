"""Octa Project Risk Log — Dashboard."""
import streamlit as st
from modules.auth import require_auth
from modules.sso import auto_login_from_url, set_token_in_url, get_token_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, kpi_card, level_badge,
                                 status_badge, DARK)
from modules.database import (get_funded_projects, get_project, get_work_packages,
                               get_risks, get_risk_actions, get_risk_reviews,
                               get_risk_stats)
from modules.charts import (chart_risk_matrix, chart_risk_levels,
                             chart_risk_status, chart_risk_by_category,
                             chart_action_status, fig_to_html)
from config import DARK as D, LEVEL_COLORS, RISK_STATUS_COLORS

st.set_page_config(page_title="Project Risk Log — Octa",
                   page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth()
token = st.session_state.get("sso_token","") or get_token_from_url()
if token: set_token_in_url(token)
sidebar_nav()

org      = st.session_state.get("organisation","")
is_admin = st.session_state.get("role") == "admin"
muted    = D["muted"]; acc = D["accent"]

page_header("Project Risk Log",
            "Identify, assess, monitor and mitigate risks across funded projects",
            "🛡️")

# ── Project selector ──────────────────────────────────────────────────────────
projects, err = get_funded_projects(org, is_admin)
if err:
    st.error(f"❌ Database error: {err}"); st.stop()
if not projects:
    st.warning("No funded projects found. Set a proposal to **Funded** in the Proposal Tracker.")
    st.stop()

proj_opts = {
    f"{p.get('acronym','').strip() or p['proposal_id']} — {p.get('proposal_title','')[:40]}": p["proposal_id"]
    for p in projects
}
cur_pid   = st.session_state.get("selected_project_id","")
cur_label = next((l for l,v in proj_opts.items() if v==cur_pid), None)
def_idx   = list(proj_opts.keys()).index(cur_label) if cur_label else 0

sel_label = st.selectbox("Select Project", list(proj_opts.keys()),
                          index=def_idx, key="risk_proj")
sel_pid   = proj_opts[sel_label]
if sel_pid != cur_pid:
    st.session_state["selected_project_id"] = sel_pid; st.rerun()

proj    = get_project(sel_pid)
acronym = proj.get("acronym","") or sel_pid
risks   = get_risks(sel_pid)
actions = get_risk_actions(sel_pid)
reviews = get_risk_reviews(sel_pid)
stats   = get_risk_stats(risks, actions)

# ── KPI row ───────────────────────────────────────────────────────────────────
section_label("📊 Risk Overview")
k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
kpi_card(k1,"Total Risks",       stats["total"],            acc)
kpi_card(k2,"Open",              stats["open"],             D["danger"] if stats["open"] else D["success"])
kpi_card(k3,"Critical",          stats["critical"],         D["danger"] if stats["critical"] else D["success"])
kpi_card(k4,"High",              stats["high"],             D["accent2"]if stats["high"]    else D["success"])
kpi_card(k5,"Mitigated",         stats["mitigated"],        D["success"])
kpi_card(k6,"Materialized",      stats["materialized"],     D["danger"] if stats["materialized"] else D["success"])
kpi_card(k7,"Actions Overdue",   stats["actions_overdue"],  D["danger"] if stats["actions_overdue"] else D["success"])

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts row ────────────────────────────────────────────────────────────────
section_label("📈 Risk Analysis")
cc1, cc2, cc3 = st.columns(3)

with cc1:
    fig1 = chart_risk_matrix(risks, "Risk Matrix")
    st.plotly_chart(fig1, use_container_width=True)
    if st.button("📥 Export", key="exp_matrix"):
        st.download_button("⬇ Download HTML",
                           fig_to_html(fig1,"Risk Matrix").encode(),
                           f"{acronym}_risk_matrix.html","text/html", key="dl_matrix")

with cc2:
    fig2 = chart_risk_levels(risks, "Risks by Level")
    st.plotly_chart(fig2, use_container_width=True)
    if st.button("📥 Export", key="exp_levels"):
        st.download_button("⬇ Download HTML",
                           fig_to_html(fig2,"Risk Levels").encode(),
                           f"{acronym}_risk_levels.html","text/html", key="dl_levels")

with cc3:
    fig3 = chart_risk_status(risks, "Risks by Status")
    st.plotly_chart(fig3, use_container_width=True)
    if st.button("📥 Export", key="exp_status"):
        st.download_button("⬇ Download HTML",
                           fig_to_html(fig3,"Risk Status").encode(),
                           f"{acronym}_risk_status.html","text/html", key="dl_status")

cc4, cc5 = st.columns(2)
with cc4:
    fig4 = chart_risk_by_category(risks, "Risks by Category")
    st.plotly_chart(fig4, use_container_width=True)
    if st.button("📥 Export", key="exp_cat"):
        st.download_button("⬇ Download HTML",
                           fig_to_html(fig4,"Risks by Category").encode(),
                           f"{acronym}_risk_categories.html","text/html", key="dl_cat")

with cc5:
    if actions:
        fig5 = chart_action_status(actions, "Mitigation Actions by Status")
        st.plotly_chart(fig5, use_container_width=True)
    else:
        bg2=D["bg2"]; border=D["border"]
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};border-radius:10px;"
            f"padding:2rem;text-align:center;color:{muted}'>"
            f"Add mitigation actions on the <strong>Actions</strong> page to see this chart.</div>",
            unsafe_allow_html=True)

# ── Top risks ─────────────────────────────────────────────────────────────────
if stats["top_risks"]:
    section_label(f"🔴 Top Active Risks ({len(stats['top_risks'])} shown)")
    for r in stats["top_risks"]:
        level   = r.get("risk_level","medium")
        lc      = LEVEL_COLORS.get(level, D["muted"])
        status  = r.get("status","open")
        sc      = RISK_STATUS_COLORS.get(status, D["muted"])
        bg2=D["bg2"]; border=D["border"]; txt=D["text"]
        st.markdown(
            f"<div style='background:{bg2};border:1px solid {border};"
            f"border-left:5px solid {lc};border-radius:10px;"
            f"padding:0.8rem 1.1rem;margin-bottom:0.5rem'>"
            f"<div style='display:flex;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.3rem'>"
            f"{level_badge(level)} {status_badge(status)}"
            f"<span style='color:{muted};font-size:0.78rem'>{r.get('risk_number','')}</span>"
            f"</div>"
            f"<strong style='color:{txt}'>{r.get('risk_title','')}</strong>"
            + (f"<br><span style='color:{muted};font-size:0.82rem'>{r.get('risk_description','')[:120]}…</span>"
               if r.get('risk_description') else "")
            + (f"<br><span style='color:{D["success"]};font-size:0.8rem'>🛡️ {r.get('mitigation_strategy','')[:100]}</span>"
               if r.get('mitigation_strategy') else "")
            + "</div>", unsafe_allow_html=True)

# ── Quick nav ─────────────────────────────────────────────────────────────────
section_label("🔗 Quick Access")
qc1,qc2,qc3,qc4 = st.columns(4)
for col, icon, label, page in [
    (qc1,"📋","Risk Register",  "pages/risk_register.py"),
    (qc2,"🛡️","Actions",       "pages/risk_actions.py"),
    (qc3,"🔄","Reviews",        "pages/risk_reviews.py"),
    (qc4,"📥","Export Report",  "pages/reports.py"),
]:
    col.markdown(
        f"<div style='background:{D["bg2"]};border:1px solid {D["border"]};"
        f"border-radius:10px;padding:0.7rem;text-align:center'>"
        f"<div style='font-size:1.5rem'>{icon}</div>"
        f"<div style='font-size:0.78rem;color:{D["text"]}'>{label}</div></div>",
        unsafe_allow_html=True)
    if col.button("Open", key=f"qrisk_{label}", use_container_width=True):
        st.switch_page(page)
