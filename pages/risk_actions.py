"""Octa Project Risk Log — Mitigation Actions."""
import streamlit as st
from datetime import date

from modules.auth import require_auth
from modules.sso import auto_login_from_url
from modules.ui_helpers import (inject_css, sidebar_nav, page_header,
                                 section_label, kpi_card, DARK)
from modules.database import (get_project, get_risks, get_risk_actions,
                               upsert_risk_action, delete_risk_action,
                               get_project_partners)
from modules.charts import chart_action_status, fig_to_html
from config import (DARK as D, ACTION_TYPES, ACTION_STATUS_OPTS,
                    ACTION_STATUS_COLORS, LEVEL_COLORS)

st.set_page_config(page_title="Risk Actions — Octa", page_icon="🛡️",
                   layout="wide", initial_sidebar_state="expanded")
inject_css(); auto_login_from_url(); require_auth(); sidebar_nav()

sel_pid = st.session_state.get("selected_project_id","")
if not sel_pid: st.switch_page("app.py"); st.stop()

proj    = get_project(sel_pid)
acronym = proj.get("acronym","") or sel_pid
page_header("Mitigation Actions",
            f"{acronym} — Track concrete actions to prevent and reduce risks", "🛡️")
if st.button("← Dashboard"): st.switch_page("app.py")

muted = D["muted"]; acc = D["accent"]
user_id = st.session_state.get("user_id")

risks    = get_risks(sel_pid)
actions  = get_risk_actions(sel_pid)
partners = get_project_partners(sel_pid)
today    = date.today().isoformat()

risk_opts    = {f"{r['risk_number']}: {r.get('risk_title','')[:40]}": r["risk_id"] for r in risks}
partner_opts = {"— Not assigned —": None} | {
    f"{p.get('short_name','') or p.get('full_name','')[:20]}": p["id"]
    for p in partners
}

# ── KPI row ───────────────────────────────────────────────────────────────────
section_label("📊 Actions Summary")
k1,k2,k3,k4,k5 = st.columns(5)
kpi_card(k1,"Total",      len(actions),  acc)
kpi_card(k2,"Planned",    sum(1 for a in actions if a.get("status")=="planned"),    D["muted"])
kpi_card(k3,"In Progress",sum(1 for a in actions if a.get("status")=="in_progress"),D["warning"])
kpi_card(k4,"Completed",  sum(1 for a in actions if a.get("status")=="completed"),  D["success"])
kpi_card(k5,"Overdue",    sum(1 for a in actions if a.get("due_date","")< today
                              and a.get("status") not in ("completed","cancelled")),
         D["danger"])

if actions:
    cc1, _ = st.columns([1,2])
    with cc1:
        fig = chart_action_status(actions)
        st.plotly_chart(fig, use_container_width=True)

# ── Add new action ────────────────────────────────────────────────────────────
section_label("➕ Add Mitigation Action")
with st.expander("New Action Form", expanded=not actions):
    with st.form("add_action_form", clear_on_submit=True):
        at1, at2 = st.columns([2,3])
        with at1:
            risk_sel   = st.selectbox("Linked Risk *", list(risk_opts.keys()))
            risk_id_sel= risk_opts[risk_sel]
            type_labels= [t[1] for t in ACTION_TYPES]
            type_sel   = st.selectbox("Action Type", type_labels)
            a_type     = [t[0] for t in ACTION_TYPES][type_labels.index(type_sel)]
        with at2:
            a_title = st.text_input("Action Title *", placeholder="e.g. Weekly monitoring call with partner")
            a_desc  = st.text_area("Description", height=60, placeholder="What exactly needs to be done?")

        ac1,ac2,ac3 = st.columns(3)
        with ac1:
            resp_sel = st.selectbox("Responsible Partner", list(partner_opts.keys()))
            resp_id  = partner_opts[resp_sel]
        with ac2:
            a_person = st.text_input("Responsible Person", placeholder="Name or role")
        with ac3:
            a_period = st.number_input("Period", min_value=1, max_value=20, value=1)

        ad1,ad2 = st.columns(2)
        with ad1:
            a_due    = st.date_input("Due Date", value=date.today())
        with ad2:
            a_status = st.selectbox("Status", ACTION_STATUS_OPTS, format_func=str.title)

        if st.form_submit_button("➕ Add Action", type="primary", use_container_width=True):
            if not a_title.strip():
                st.error("❌ Action title required.")
            else:
                ok, aid = upsert_risk_action({
                    "risk_id":             risk_id_sel,
                    "proposal_id":         sel_pid,
                    "action_title":        a_title.strip(),
                    "action_description":  a_desc.strip(),
                    "action_type":         a_type,
                    "responsible_partner_id": resp_id,
                    "responsible_person":  a_person.strip(),
                    "due_date":            a_due.isoformat(),
                    "status":              a_status,
                    "reporting_period":    a_period,
                    "created_by":          user_id,
                })
                if ok: st.success("✅ Action added!"); st.rerun()
                else:  st.error(f"❌ {aid}")

# ── Action list ───────────────────────────────────────────────────────────────
section_label(f"📋 All Actions ({len(actions)})")
ACTION_TYPE_LABELS = dict(ACTION_TYPES)

# Sort: overdue first, then by due date
actions_sorted = sorted(actions, key=lambda a: (
    0 if (a.get("due_date","")< today and a.get("status") not in ("completed","cancelled")) else 1,
    a.get("due_date","9999")
))

# Group by linked risk
risk_map = {r["risk_id"]: r for r in risks}
by_risk: dict = {}
for a in actions_sorted:
    rid  = a.get("risk_id")
    risk = risk_map.get(rid,{})
    rkey = f"{risk.get('risk_number','')}: {risk.get('risk_title','')[:40]}"
    if rkey not in by_risk: by_risk[rkey] = []
    by_risk[rkey].append(a)

for risk_label, risk_actions in by_risk.items():
    risk_obj  = risk_map.get(risk_actions[0]["risk_id"],{})
    risk_level= risk_obj.get("risk_level","medium")
    lc = LEVEL_COLORS.get(risk_level, D["muted"])
    bg2=D["bg2"]; border=D["border"]; txt=D["text"]
    st.markdown(
        f"<div style='font-size:0.82rem;font-weight:700;color:{lc};"
        f"margin:0.8rem 0 0.3rem'>⚠️ {risk_label}</div>",
        unsafe_allow_html=True)

    for a in risk_actions:
        aid    = a["id"]
        astatus= a.get("status","planned")
        adue   = a.get("due_date","")
        is_ov  = adue and adue < today and astatus not in ("completed","cancelled")
        sc     = ACTION_STATUS_COLORS.get(astatus, D["muted"])
        prog   = int(a.get("progress_pct",0) or 0)
        atype  = ACTION_TYPE_LABELS.get(a.get("action_type","mitigation"),"")

        with st.expander(
            f"{atype}  {a.get('action_title','')}  ·  {astatus.replace('_',' ').title()}"
            + ("  ⚠️ OVERDUE" if is_ov else ""),
            expanded=is_ov
        ):
            ac1, ac2 = st.columns([3,2])
            with ac1:
                st.markdown(
                    f"<div style='background:{bg2};border-left:4px solid {sc};"
                    f"border-radius:8px;padding:0.8rem 1rem'>"
                    f"<span style='background:{sc}22;color:{sc};padding:2px 9px;"
                    f"border-radius:10px;font-size:0.75rem;font-weight:600'>"
                    f"{astatus.replace('_',' ').title()}</span>"
                    + (f"<br><p style='color:{muted};font-size:0.83rem;margin:0.3rem 0'>{a.get('action_description','')}</p>"
                       if a.get("action_description") else "")
                    + f"<div style='color:{muted};font-size:0.78rem;margin-top:0.3rem'>"
                    f"📅 Due: <strong style='color:{D["danger"] if is_ov else txt}'>{adue}</strong>"
                    + (f" · 👤 {a.get('responsible_person','')}" if a.get("responsible_person") else "")
                    + (f" · Period {a.get('reporting_period',1)}" )
                    + f"</div></div>", unsafe_allow_html=True)
                if prog:
                    st.progress(prog/100, text=f"Progress: {prog}%")
                if a.get("outcome_notes"):
                    suc=D["success"]
                    st.markdown(
                        f"<div style='background:{suc}11;border-left:3px solid {suc};"
                        f"border-radius:6px;padding:0.3rem 0.7rem;font-size:0.8rem;color:{suc}'>"
                        f"📝 {a['outcome_notes']}</div>", unsafe_allow_html=True)

            with ac2:
                with st.form(f"edit_action_{aid}"):
                    e_atitle  = st.text_input("Title", value=a.get("action_title",""))
                    e_astatus = st.selectbox("Status", ACTION_STATUS_OPTS,
                        index=ACTION_STATUS_OPTS.index(astatus) if astatus in ACTION_STATUS_OPTS else 0,
                        format_func=str.title, key=f"eas_{aid}")
                    e_prog = st.slider("Progress %",0,100,prog,5,key=f"eaprog_{aid}")
                    e_due  = st.date_input("Due Date",
                        value=date.fromisoformat(adue) if adue else date.today(),
                        key=f"eadue_{aid}")
                    e_notes= st.text_area("Outcome Notes",
                        value=a.get("outcome_notes",""), height=60, key=f"ean_{aid}")
                    e_person2 = st.text_input("Responsible Person",
                        value=a.get("responsible_person",""), key=f"eaper_{aid}")

                    fa1,fa2 = st.columns(2)
                    with fa1:
                        if st.form_submit_button("💾 Save", type="primary", use_container_width=True):
                            ok2,_ = upsert_risk_action({
                                "id":                  aid,
                                "risk_id":             a["risk_id"],
                                "proposal_id":         sel_pid,
                                "action_title":        e_atitle.strip(),
                                "status":              e_astatus,
                                "progress_pct":        e_prog,
                                "due_date":            e_due.isoformat(),
                                "outcome_notes":       e_notes.strip(),
                                "responsible_person":  e_person2.strip(),
                                "completion_date":     date.today().isoformat() if e_astatus=="completed" else None,
                            })
                            if ok2: st.success("✅ Saved!"); st.rerun()
                    with fa2:
                        if st.form_submit_button("🗑 Delete", use_container_width=True):
                            delete_risk_action(aid); st.rerun()
