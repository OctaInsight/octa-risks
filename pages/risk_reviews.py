"""Octa Project Risk Log — Periodic Risk Reviews."""
import streamlit as st
from datetime import date

from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, DARK)
from modules.database import (get_project, get_risks, get_risk_reviews,
                               save_risk_review, compute_risk_level)
from modules.charts import chart_risk_trend, fig_to_html
from config import (DARK as D, LIKELIHOOD_OPTS, SEVERITY_OPTS,
                    RISK_STATUS_OPTS, LEVEL_COLORS, RISK_STATUS_COLORS)

st.set_page_config(page_title="Risk Reviews — Octa", page_icon="🔄",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_project_id","")
if not sel_pid: st.switch_page("app.py"); st.stop()

proj    = get_project(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Periodic Risk Reviews",
            f"{acronym} — Record how each risk has evolved over reporting periods", "🔄")
if st.button("← Dashboard"): st.switch_page("app.py")

muted   = D["muted"]; acc = D["accent"]
user_id = st.session_state.get("user_id")
risks   = get_risks(sel_pid)
reviews = get_risk_reviews(sel_pid)

if not risks:
    st.info("Add risks in the **Risk Register** first."); st.stop()

# ── Trend chart ───────────────────────────────────────────────────────────────
if reviews:
    section_label("📈 Risk Level Trend")
    fig = chart_risk_trend(reviews, f"{acronym} — Risk Level Evolution by Period")
    st.plotly_chart(fig, use_container_width=True)
    if st.button("📥 Export Trend Chart", key="exp_trend"):
        st.download_button("⬇ Download HTML",
                           fig_to_html(fig).encode(),
                           f"{acronym}_risk_trend.html","text/html", key="dl_trend")

# ── Record new review ─────────────────────────────────────────────────────────
section_label("📝 Record Period Review")
st.markdown(
    f"<p style='color:{muted};font-size:0.84rem'>"
    f"At each reporting period, review every active risk and update its likelihood, "
    f"severity and status. This creates a snapshot that feeds the trend chart.</p>",
    unsafe_allow_html=True)

period = st.number_input("Reporting Period to Review", min_value=1,
                          max_value=20, value=len(set(r["reporting_period"] for r in reviews))+1,
                          key="review_period")

active_risks = [r for r in risks if r.get("status") not in ("closed",)]

if not active_risks:
    st.success("All risks are closed. Nothing to review.")
else:
    with st.form("bulk_review_form"):
        st.markdown(
            f"<strong style='color:{D["text"]}'>Reviewing {len(active_risks)} active risks "
            f"for Period {period}</strong>", unsafe_allow_html=True)

        review_data = []
        for r in active_risks:
            rid    = r["risk_id"]
            rnum   = r.get("risk_number","")
            rtitle = r.get("risk_title","")
            cur_like  = r.get("likelihood","medium")
            cur_sev   = r.get("severity","medium")
            cur_status= r.get("status","open")
            cur_level = r.get("risk_level","medium")
            lc = LEVEL_COLORS.get(cur_level, D["muted"])

            st.markdown(
                f"<div style='background:{D["bg2"]};border-left:4px solid {lc};"
                f"border-radius:8px;padding:0.6rem 0.9rem;margin-bottom:0.3rem'>"
                f"<strong style='color:{D["text"]}'>{rnum}: {rtitle}</strong></div>",
                unsafe_allow_html=True)

            rvc1,rvc2,rvc3,rvc4 = st.columns(4)
            with rvc1:
                new_like = st.selectbox("Likelihood",
                    LIKELIHOOD_OPTS,
                    index=LIKELIHOOD_OPTS.index(cur_like) if cur_like in LIKELIHOOD_OPTS else 1,
                    format_func=str.title, key=f"rvl_{rid}")
            with rvc2:
                new_sev = st.selectbox("Severity",
                    SEVERITY_OPTS,
                    index=SEVERITY_OPTS.index(cur_sev) if cur_sev in SEVERITY_OPTS else 1,
                    format_func=str.title, key=f"rvs_{rid}")
            with rvc3:
                preview_lv = compute_risk_level(new_like, new_sev)
                plc = LEVEL_COLORS.get(preview_lv, D["muted"])
                st.markdown(
                    f"<div style='margin-top:1.6rem;background:{plc}22;border:1px solid {plc}44;"
                    f"border-radius:8px;padding:0.4rem;text-align:center'>"
                    f"<strong style='color:{plc}'>{preview_lv.title()}</strong></div>",
                    unsafe_allow_html=True)
            with rvc4:
                new_st = st.selectbox("Status",
                    RISK_STATUS_OPTS,
                    index=RISK_STATUS_OPTS.index(cur_status) if cur_status in RISK_STATUS_OPTS else 0,
                    format_func=str.title, key=f"rvst_{rid}")

            new_notes = st.text_input("Review notes",
                key=f"rvnotes_{rid}", placeholder="What changed? Any new information?")
            st.markdown("---")

            review_data.append({
                "risk_id":         rid,
                "proposal_id":     sel_pid,
                "reporting_period":period,
                "review_date":     date.today().isoformat(),
                "reviewer_id":     user_id,
                "likelihood":      new_like,
                "severity":        new_sev,
                "status":          new_st,
                "review_notes":    new_notes.strip(),
            })

        if st.form_submit_button("💾 Save All Reviews", type="primary", use_container_width=True):
            saved = 0
            for rv in review_data:
                if save_risk_review(rv): saved += 1
            st.success(f"✅ Saved {saved} / {len(review_data)} reviews for Period {period}!")
            st.rerun()

# ── Review history ────────────────────────────────────────────────────────────
if reviews:
    section_label(f"📋 Review History ({len(reviews)} records)")
    risk_map = {r["risk_id"]: r for r in risks}
    periods  = sorted(set(rv["reporting_period"] for rv in reviews), reverse=True)

    for p in periods:
        p_reviews = [rv for rv in reviews if rv["reporting_period"] == p]
        with st.expander(f"Period {p} — {len(p_reviews)} risks reviewed", expanded=(p==periods[0])):
            for rv in p_reviews:
                r_obj  = risk_map.get(rv["risk_id"],{})
                rnum   = r_obj.get("risk_number","")
                rtitle = r_obj.get("risk_title","")
                level  = rv.get("risk_level","medium")
                status = rv.get("status","open")
                lc     = LEVEL_COLORS.get(level, D["muted"])
                sc     = RISK_STATUS_COLORS.get(status, D["muted"])
                bg2=D["bg2"]; border=D["border"]; txt=D["text"]
                st.markdown(
                    f"<div style='background:{bg2};border:1px solid {border};"
                    f"border-left:4px solid {lc};border-radius:8px;"
                    f"padding:0.5rem 0.9rem;margin-bottom:0.3rem;font-size:0.83rem'>"
                    f"<span style='color:{txt};font-weight:600'>{rnum}: {rtitle}</span>"
                    f"<span style='background:{lc}22;color:{lc};margin-left:0.5rem;"
                    f"padding:1px 8px;border-radius:8px;font-size:0.72rem'>{level.title()}</span>"
                    f"<span style='background:{sc}22;color:{sc};margin-left:0.3rem;"
                    f"padding:1px 8px;border-radius:8px;font-size:0.72rem'>{status.title()}</span>"
                    f"<span style='color:{muted};margin-left:0.5rem'>"
                    f"L:{rv.get('likelihood','').title()} × S:{rv.get('severity','').title()}</span>"
                    + (f"<br><span style='color:{muted}'>{rv.get('review_notes','')}</span>"
                       if rv.get("review_notes") else "")
                    + "</div>", unsafe_allow_html=True)
