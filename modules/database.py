"""Octa Project Risk Log — Database layer."""
import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timezone, date
from config import (FUNDED_STATUS, FUNDED_LIFECYCLE, RISK_MATRIX,
                    ACTION_STATUS_OPTS)
import json


@st.cache_resource
def _client() -> Client:
    return create_client(st.secrets["supabase"]["url"],
                         st.secrets["supabase"]["key"])

def db() -> Client:
    return _client()

def _now():
    return datetime.now(timezone.utc).isoformat()


def compute_risk_level(likelihood: str, severity: str) -> str:
    return RISK_MATRIX.get(
        (likelihood.lower(), severity.lower()), "medium"
    )


# ── Funded projects ───────────────────────────────────────────────────────────

def get_funded_projects(organisation: str = "", is_admin: bool = False) -> tuple:
    try:
        resp = db().table("proposals").select("*") \
                   .order("proposal_id", desc=True).execute()
        all_props = resp.data or []
    except Exception as e:
        return [], str(e)

    projects = [
        p for p in all_props
        if (p.get("status") or "")           in FUNDED_STATUS
        or (p.get("lifecycle_status") or "")  in FUNDED_LIFECYCLE
    ]
    return projects, None


def get_project(proposal_id: str) -> dict | None:
    try:
        r = db().table("proposals").select("*") \
                .eq("proposal_id", proposal_id).execute()
        return r.data[0] if r.data else None
    except Exception:
        return None


# ── Work packages ─────────────────────────────────────────────────────────────

def get_work_packages(proposal_id: str) -> list:
    try:
        return db().table("work_packages").select("*") \
                   .eq("proposal_id", proposal_id) \
                   .order("wp_number").execute().data or []
    except Exception:
        return []


# ── Partners ──────────────────────────────────────────────────────────────────

def get_project_partners(proposal_id: str) -> list:
    try:
        prop = get_project(proposal_id)
        if not prop:
            return []
        names = []
        coord = (prop.get("coordinator") or "").strip()
        if coord: names.append(coord)
        plist = prop.get("partners_list") or []
        if isinstance(plist, str):
            try:    plist = json.loads(plist)
            except: plist = [plist]
        names.extend([str(n).strip() for n in plist if n])
        if not names:
            return []
        all_p = db().table("partners").select(
            "id,full_name,short_name,country,partner_type"
        ).order("full_name").execute().data or []
        result = []; seen = set()
        for name in names:
            nl = name.lower()
            for p in all_p:
                if p["id"] in seen: continue
                fn = (p.get("full_name") or "").lower()
                sn = (p.get("short_name") or "").lower()
                if nl in fn or fn in nl or (sn and (nl in sn or sn in nl)):
                    result.append({**p, "is_coordinator": name==coord})
                    seen.add(p["id"]); break
        return result
    except Exception:
        return []


# ── Users ─────────────────────────────────────────────────────────────────────

def get_all_users() -> list:
    try:
        return db().table("octa_users").select(
            "id,username,first_name,last_name,organisation"
        ).eq("status","approved").order("first_name").execute().data or []
    except Exception:
        return []


# ── Risks ─────────────────────────────────────────────────────────────────────

def get_risks(proposal_id: str) -> list:
    try:
        return db().table("risks").select("*") \
                   .eq("proposal_id", proposal_id) \
                   .order("risk_number").execute().data or []
    except Exception:
        return []


def upsert_risk(data: dict) -> tuple:
    try:
        data["risk_level"] = compute_risk_level(
            data.get("likelihood","medium"),
            data.get("severity","medium")
        )
        data["updated_at"] = _now()
        if data.get("risk_id"):
            rid = data.pop("risk_id")
            db().table("risks").update(data).eq("risk_id", rid).execute()
            return True, rid
        r = db().table("risks").insert(data).execute()
        return True, r.data[0]["risk_id"] if r.data else None
    except Exception as e:
        return False, str(e)


def delete_risk(risk_id: int) -> bool:
    try:
        db().table("risks").delete().eq("risk_id", risk_id).execute()
        return True
    except Exception:
        return False


def get_risk_wps(risk_id: int) -> list:
    try:
        r = db().table("risk_work_packages").select("wp_id") \
                .eq("risk_id", risk_id).execute()
        return [row["wp_id"] for row in (r.data or [])]
    except Exception:
        return []


def set_risk_wps(risk_id: int, wp_ids: list) -> bool:
    try:
        db().table("risk_work_packages").delete().eq("risk_id", risk_id).execute()
        if wp_ids:
            db().table("risk_work_packages").insert(
                [{"risk_id": risk_id, "wp_id": w} for w in wp_ids]
            ).execute()
        return True
    except Exception:
        return False


# ── Risk reviews ──────────────────────────────────────────────────────────────

def get_risk_reviews(proposal_id: str, risk_id: int = None) -> list:
    try:
        q = db().table("risk_reviews").select("*") \
                .eq("proposal_id", proposal_id)
        if risk_id:
            q = q.eq("risk_id", risk_id)
        return q.order("reporting_period").execute().data or []
    except Exception:
        return []


def save_risk_review(data: dict) -> bool:
    try:
        data["risk_level"] = compute_risk_level(
            data.get("likelihood","medium"),
            data.get("severity","medium")
        )
        db().table("risk_reviews").upsert(
            data, on_conflict="risk_id,reporting_period"
        ).execute()
        return True
    except Exception:
        return False


# ── Risk actions ──────────────────────────────────────────────────────────────

def get_risk_actions(proposal_id: str, risk_id: int = None) -> list:
    try:
        q = db().table("risk_actions").select("*") \
                .eq("proposal_id", proposal_id)
        if risk_id:
            q = q.eq("risk_id", risk_id)
        return q.order("due_date").execute().data or []
    except Exception:
        return []


def upsert_risk_action(data: dict) -> tuple:
    try:
        data["updated_at"] = _now()
        if data.get("id"):
            aid = data.pop("id")
            db().table("risk_actions").update(data).eq("id", aid).execute()
            return True, aid
        r = db().table("risk_actions").insert(data).execute()
        return True, r.data[0]["id"] if r.data else None
    except Exception as e:
        return False, str(e)


def delete_risk_action(action_id: int) -> bool:
    try:
        db().table("risk_actions").delete().eq("id", action_id).execute()
        return True
    except Exception:
        return False


# ── Dashboard stats ───────────────────────────────────────────────────────────

def get_risk_stats(risks: list, actions: list) -> dict:
    today = date.today().isoformat()
    level_order = {"critical":0,"high":1,"medium":2,"low":3}
    return {
        "total":       len(risks),
        "open":        sum(1 for r in risks if r.get("status") == "open"),
        "critical":    sum(1 for r in risks if r.get("risk_level") == "critical"),
        "high":        sum(1 for r in risks if r.get("risk_level") == "high"),
        "mitigated":   sum(1 for r in risks if r.get("status") == "mitigated"),
        "materialized":sum(1 for r in risks if r.get("materialized")),
        "actions_open":sum(1 for a in actions
                          if a.get("status") in ("planned","in_progress")),
        "actions_overdue":sum(1 for a in actions
                             if a.get("due_date","") < today
                             and a.get("status") not in ("completed","cancelled")),
        "top_risks":   sorted(
            [r for r in risks if r.get("status") not in ("closed","mitigated")],
            key=lambda r: (level_order.get(r.get("risk_level","low"),3),
                           r.get("risk_number",""))
        )[:5],
    }
