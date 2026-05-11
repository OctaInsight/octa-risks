"""Octa Project Risk Log — Risk Register."""
import streamlit as st
from datetime import date

from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, level_badge, status_badge, DARK)
from modules.database import (get_project, get_work_packages,
                               get_project_partners, get_risks,
                               upsert_risk, delete_risk,
                               get_risk_wps, set_risk_wps, compute_risk_level)
from modules.charts import chart_risk_matrix, fig_to_html
from config import (DARK as D, RISK_CATEGORIES, CAT_LABELS, LEVEL_COLORS,
                    RISK_STATUS_OPTS, RISK_STATUS_COLORS,
                    LIKELIHOOD_OPTS, SEVERITY_OPTS, ESCALATION_OPTS, ESC_LABELS)

st.set_page_config(page_title="Risk Register — Octa", page_icon="📋",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_project_id","")
if not sel_pid: st.switch_page("app.py"); st.stop()

proj    = get_project(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Risk Register", f"{acronym} — Add, update and monitor all project risks", "📋")
if st.button("← Dashboard"): st.switch_page("app.py")

muted = D["muted"]; acc = D["accent"]

wps      = get_work_packages(sel_pid)
partners = get_project_partners(sel_pid)
risks    = get_risks(sel_pid)

wp_opts = {f"{w['wp_number']}: {w.get('wp_title','')[:35]}": w["wp_id"] for w in wps}
partner_opts = {
    f"{p.get('short_name','') or p.get('full_name','')[:20]} — {p.get('full_name','')[:30]}": p["id"]
    for p in partners
}

# ── Add new risk ──────────────────────────────────────────────────────────────
section_label("➕ Add New Risk")
with st.expander("New Risk Form", expanded=not risks):
    with st.form("add_risk_form", clear_on_submit=True):
        rc1, rc2, rc3 = st.columns([1,4,2])
        with rc1: r_num   = st.text_input("Risk ID *", placeholder="R1")
        with rc2: r_title = st.text_input("Risk Title *", placeholder="e.g. Key partner withdrawal")
        with rc3:
            cat_keys   = [c[0] for c in RISK_CATEGORIES]
            cat_labels = [c[1] for c in RISK_CATEGORIES]
            cat_sel    = st.selectbox("Category *", cat_labels)
            r_cat      = cat_keys[cat_labels.index(cat_sel)]

        r_desc = st.text_area("Risk Description", height=70,
                               placeholder="Describe the risk in detail…")

        ra1,ra2,ra3,ra4 = st.columns(4)
        with ra1:
            r_like = st.selectbox("Likelihood *", LIKELIHOOD_OPTS,
                                   index=1, format_func=str.title)
        with ra2:
            r_sev  = st.selectbox("Severity *",   SEVERITY_OPTS,
                                   index=1, format_func=str.title)
        with ra3:
            preview_lv = compute_risk_level(r_like, r_sev)
            lc = LEVEL_COLORS.get(preview_lv, D["muted"])
            st.markdown(
                f"<div style='margin-top:1.6rem;background:{lc}22;border:1px solid {lc}44;"
                f"border-radius:8px;padding:0.5rem;text-align:center'>"
                f"<strong style='color:{lc}'>⚡ {preview_lv.title()}</strong></div>",
                unsafe_allow_html=True)
        with ra4:
            esc_labels = [e[1] for e in ESCALATION_OPTS]
            esc_sel    = st.selectbox("Escalation", esc_labels)
            r_esc      = [e[0] for e in ESCALATION_OPTS][esc_labels.index(esc_sel)]

        r_mit  = st.text_area("Mitigation Strategy *", height=80,
                               placeholder="How will this risk be prevented or reduced?")
        r_cont = st.text_area("Contingency Plan", height=60,
                               placeholder="Fallback plan if mitigation fails…")

        rb1,rb2,rb3 = st.columns(3)
        with rb1:
            r_wps = st.multiselect("Related WPs", list(wp_opts.keys()), key="add_rwps")
        with rb2:
            resp_opts = {"— Not assigned —": None} | partner_opts
            r_resp    = st.selectbox("Responsible Partner", list(resp_opts.keys()))
            r_resp_id = resp_opts[r_resp]
        with rb3:
            r_person  = st.text_input("Responsible Person", placeholder="Name or role")

        rsc1,rsc2 = st.columns(2)
        with rsc1:
            r_status = st.selectbox("Status", RISK_STATUS_OPTS, format_func=str.title)
        with rsc2:
            r_period = st.number_input("Reporting Period", min_value=1, max_value=20, value=1)

        if st.form_submit_button("⚠️ Add Risk", type="primary", use_container_width=True):
            if not r_num.strip() or not r_title.strip():
                st.error("❌ Risk ID and Title required.")
            elif not r_mit.strip():
                st.error("❌ Mitigation Strategy required.")
            else:
                ok, rid = upsert_risk({
                    "proposal_id":          sel_pid,
                    "risk_number":          r_num.strip().upper(),
                    "risk_title":           r_title.strip(),
                    "risk_description":     r_desc.strip(),
                    "risk_category":        r_cat,
                    "likelihood":           r_like,
                    "severity":             r_sev,
                    "mitigation_strategy":  r_mit.strip(),
                    "contingency_plan":     r_cont.strip(),
                    "responsible_partner_id": r_resp_id,
                    "responsible_person":   r_person.strip(),
                    "status":               r_status,
                    "escalation_level":     r_esc,
                    "reporting_period":     r_period,
                    "identified_date":      date.today().isoformat(),
                })
                if ok and rid:
                    set_risk_wps(rid, [wp_opts[l] for l in r_wps])
                    st.success("✅ Risk added!"); st.rerun()
                else:
                    st.error(f"❌ {rid}")

# ── Risk register ─────────────────────────────────────────────────────────────
level_order = {"critical":0,"high":1,"medium":2,"low":3}
risks_sorted = sorted(risks, key=lambda r: (
    level_order.get(r.get("risk_level","medium"),2),
    r.get("risk_number","")
))

# Filter tabs
all_count  = len(risks)
open_count = sum(1 for r in risks if r.get("status") not in ("closed","mitigated"))
tabs = st.tabs([
    f"🔴 Active ({open_count})",
    f"✅ Closed / Mitigated ({all_count - open_count})",
    f"📋 All ({all_count})",
])

def _render_risks(risk_list, tab_key="t"):
    if not risk_list:
        st.info("No risks in this category.")
        return

    for r in risk_list:
        rid    = r["risk_id"]
        rnum   = r.get("risk_number","")
        rtitle = r.get("risk_title","")
        level  = r.get("risk_level","medium")
        like   = r.get("likelihood","medium")
        sev    = r.get("severity","medium")
        status = r.get("status","open")
        cat    = r.get("risk_category","technical")
        esc    = r.get("escalation_level","internal")
        lc     = LEVEL_COLORS.get(level, D["muted"])
        sc     = RISK_STATUS_COLORS.get(status, D["muted"])
        linked = get_risk_wps(rid)
        wp_labels = [w.get("wp_number","") for w in wps if w["wp_id"] in linked]
        materialized = r.get("materialized", False)

        with st.expander(
            f"{'⚡' if level in ('critical','high') else '⚠️'} "
            f"{rnum}: {rtitle}  ·  {level.title()}  ·  {status.title()}"
            + ("  💥 MATERIALIZED" if materialized else ""),
            expanded=(level in ("critical","high") and status == "open")
        ):
            ec1, ec2 = st.columns([3,2])
            with ec1:
                txt = D["text"]
                # Badges row
                st.markdown(
                    f"<div style='display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.5rem'>"
                    f"{level_badge(level)} {status_badge(status)}"
                    f"<span style='background:{D["bg3"]};color:{muted};padding:2px 8px;"
                    f"border-radius:10px;font-size:0.73rem'>{CAT_LABELS.get(cat,cat)}</span>"
                    f"<span style='background:{D["bg3"]};color:{muted};padding:2px 8px;"
                    f"border-radius:10px;font-size:0.73rem'>{ESC_LABELS.get(esc,esc)}</span>"
                    f"</div>", unsafe_allow_html=True)

                if r.get("risk_description"):
                    st.markdown(f"<p style='color:{muted};font-size:0.84rem'>{r['risk_description']}</p>",
                                unsafe_allow_html=True)

                # Mitigation
                if r.get("mitigation_strategy"):
                    suc=D["success"]
                    st.markdown(
                        f"<div style='background:{suc}11;border-left:3px solid {suc};"
                        f"border-radius:8px;padding:0.5rem 0.8rem;margin:0.3rem 0'>"
                        f"<div style='font-size:0.7rem;color:{suc};font-weight:600;margin-bottom:0.2rem'>"
                        f"🛡️ MITIGATION</div>"
                        f"<span style='color:{txt};font-size:0.84rem'>{r['mitigation_strategy']}</span>"
                        f"</div>", unsafe_allow_html=True)

                # Contingency
                if r.get("contingency_plan"):
                    warn=D["warning"]
                    st.markdown(
                        f"<div style='background:{warn}11;border-left:3px solid {warn};"
                        f"border-radius:8px;padding:0.4rem 0.7rem;margin:0.3rem 0;"
                        f"font-size:0.82rem;color:{warn}'>🔄 Contingency: {r['contingency_plan']}</div>",
                        unsafe_allow_html=True)

                # Meta
                meta = []
                if wp_labels: meta.append(f"📦 WPs: {', '.join(wp_labels)}")
                if r.get("responsible_person"): meta.append(f"👤 {r['responsible_person']}")
                if r.get("identified_date"):    meta.append(f"📅 Identified: {r['identified_date'][:10]}")
                if meta:
                    st.markdown(
                        f"<div style='color:{muted};font-size:0.78rem;margin-top:0.3rem'>"
                        + "  ·  ".join(meta) + "</div>", unsafe_allow_html=True)

                # Materialization
                if materialized:
                    danger=D["danger"]
                    st.markdown(
                        f"<div style='background:{danger}11;border-left:3px solid {danger};"
                        f"border-radius:8px;padding:0.5rem 0.8rem;margin-top:0.3rem'>"
                        f"<div style='color:{danger};font-weight:600;font-size:0.8rem'>💥 RISK MATERIALIZED</div>"
                        + (f"<div style='color:{txt};font-size:0.82rem'>{r.get('actual_impact','')}</div>"
                           if r.get("actual_impact") else "")
                        + f"</div>", unsafe_allow_html=True)

            with ec2:
                with st.form(f"edit_risk_{rid}_{tab_key}"):
                    er1,er2 = st.columns([1,3])
                    with er1: e_rnum   = st.text_input("ID", value=rnum)
                    with er2: e_rtitle = st.text_input("Title", value=rtitle)
                    e_rdesc = st.text_area("Description", value=r.get("risk_description",""), height=55)

                    erl1,erl2 = st.columns(2)
                    with erl1:
                        e_like = st.selectbox("Likelihood", LIKELIHOOD_OPTS,
                            index=LIKELIHOOD_OPTS.index(like) if like in LIKELIHOOD_OPTS else 1,
                            format_func=str.title, key=f"elike_{rid}_{tab_key}")
                    with erl2:
                        e_sev = st.selectbox("Severity", SEVERITY_OPTS,
                            index=SEVERITY_OPTS.index(sev) if sev in SEVERITY_OPTS else 1,
                            format_func=str.title, key=f"esev_{rid}_{tab_key}")

                    e_mit  = st.text_area("Mitigation", value=r.get("mitigation_strategy",""), height=55, key=f"emit_{rid}_{tab_key}")
                    e_cont = st.text_area("Contingency", value=r.get("contingency_plan",""), height=40, key=f"econt_{rid}_{tab_key}")

                    e_wps = st.multiselect("Related WPs", list(wp_opts.keys()),
                        default=[l for l,v in wp_opts.items() if v in linked],
                        key=f"ewps_{rid}_{tab_key}")

                    e_status = st.selectbox("Status", RISK_STATUS_OPTS,
                        index=RISK_STATUS_OPTS.index(status) if status in RISK_STATUS_OPTS else 0,
                        format_func=str.title, key=f"estat_{rid}_{tab_key}")

                    cat_labels2 = [c[1] for c in RISK_CATEGORIES]
                    cur_cat_idx = [c[0] for c in RISK_CATEGORIES].index(cat) if cat in [c[0] for c in RISK_CATEGORIES] else 0
                    e_cat_sel   = st.selectbox("Category", cat_labels2, index=cur_cat_idx, key=f"ecat_{rid}_{tab_key}")
                    e_cat       = [c[0] for c in RISK_CATEGORIES][cat_labels2.index(e_cat_sel)]

                    e_mat = st.checkbox("Risk materialized", value=bool(materialized), key=f"emat_{rid}_{tab_key}")
                    e_impact = ""
                    if e_mat:
                        e_impact = st.text_area("Actual Impact", value=r.get("actual_impact",""), height=50, key=f"eimp_{rid}_{tab_key}")

                    e_person = st.text_input("Responsible Person", value=r.get("responsible_person",""), key=f"eperson_{rid}_{tab_key}")

                    sc1,sc2 = st.columns(2)
                    with sc1:
                        if st.form_submit_button("💾 Save", type="primary", use_container_width=True):
                            ok2,_ = upsert_risk({
                                "risk_id":          rid,
                                "proposal_id":      sel_pid,
                                "risk_number":      e_rnum.strip().upper(),
                                "risk_title":       e_rtitle.strip(),
                                "risk_description": e_rdesc.strip(),
                                "risk_category":    e_cat,
                                "likelihood":       e_like,
                                "severity":         e_sev,
                                "mitigation_strategy": e_mit.strip(),
                                "contingency_plan": e_cont.strip(),
                                "status":           e_status,
                                "materialized":     e_mat,
                                "actual_impact":    e_impact.strip() if e_mat else "",
                                "responsible_person": e_person.strip(),
                                "last_reviewed_date": date.today().isoformat(),
                            })
                            if ok2:
                                set_risk_wps(rid, [wp_opts[l] for l in e_wps])
                                st.success("✅ Saved!"); st.rerun()
                    with sc2:
                        if st.form_submit_button("🗑 Delete", use_container_width=True):
                            delete_risk(rid); st.rerun()

with tabs[0]:
    _render_risks([r for r in risks_sorted if r.get("status") not in ("closed","mitigated")], "active")
with tabs[1]:
    _render_risks([r for r in risks_sorted if r.get("status") in ("closed","mitigated")], "closed")
with tabs[2]:
    _render_risks(risks_sorted, "all")
