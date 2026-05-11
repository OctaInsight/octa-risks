"""Octa Project Risk Log — Configuration."""

APP_NAME    = "Project Risk Log"
APP_ICON    = "🛡️"
APP_VERSION = "1.0.0"

DARK = {
    "bg":      "#0f1421",
    "bg2":     "#1a2235",
    "bg3":     "#232f45",
    "border":  "rgba(255,255,255,0.09)",
    "text":    "#e2e8f0",
    "muted":   "#8899b0",
    "accent":  "#00BCD4",
    "accent2": "#FF6B35",
    "sidebar": "#1B2A4A",
    "success": "#6fcf97",
    "warning": "#f6cc52",
    "danger":  "#fc8181",
}

# Risk level colours and icons
LEVEL_COLORS = {
    "critical": "#fc8181",
    "high":     "#FF6B35",
    "medium":   "#f6cc52",
    "low":      "#6fcf97",
}
LEVEL_ICONS = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🟢",
}

# Risk matrix: (likelihood, severity) → level
RISK_MATRIX = {
    ("high",   "high"):   "critical",
    ("high",   "medium"): "high",
    ("high",   "low"):    "medium",
    ("medium", "high"):   "high",
    ("medium", "medium"): "medium",
    ("medium", "low"):    "low",
    ("low",    "high"):   "medium",
    ("low",    "medium"): "low",
    ("low",    "low"):    "low",
}

LIKELIHOOD_OPTS = ["high", "medium", "low"]
SEVERITY_OPTS   = ["high", "medium", "low"]

RISK_STATUS_OPTS = ["open", "mitigated", "accepted", "monitoring", "closed"]
RISK_STATUS_COLORS = {
    "open":       "#fc8181",
    "mitigated":  "#6fcf97",
    "accepted":   "#f6cc52",
    "monitoring": "#00BCD4",
    "closed":     "#8899b0",
}

RISK_CATEGORIES = [
    ("technical",      "⚙️ Technical"),
    ("financial",      "💶 Financial"),
    ("management",     "🏢 Management / Organisational"),
    ("legal",          "⚖️ Legal / Compliance"),
    ("ethical",        "🧭 Ethical"),
    ("external",       "🌐 External / Political"),
    ("communication",  "📢 Dissemination / Communication"),
]
CAT_LABELS = dict(RISK_CATEGORIES)

ESCALATION_OPTS = [
    ("internal",  "🔒 Internal only"),
    ("partner",   "🤝 Report to partners"),
    ("funder",    "📋 Report to funder"),
]
ESC_LABELS = dict(ESCALATION_OPTS)

ACTION_TYPES = [
    ("mitigation",   "🛡️ Mitigation"),
    ("contingency",  "🔄 Contingency"),
    ("monitoring",   "👁 Monitoring"),
    ("communication","📢 Communication"),
]
ACTION_STATUS_OPTS    = ["planned","in_progress","completed","overdue","cancelled"]
ACTION_STATUS_COLORS  = {
    "planned":     "#8899b0",
    "in_progress": "#f6cc52",
    "completed":   "#6fcf97",
    "overdue":     "#fc8181",
    "cancelled":   "#4a4a6a",
}

FUNDED_STATUS    = {"Funded", "Ended"}
FUNDED_LIFECYCLE = {"funded_project", "ongoing_project", "ended_project"}
