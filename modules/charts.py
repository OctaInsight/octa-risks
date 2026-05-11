"""Octa Project Risk Log — Charts."""
import plotly.graph_objects as go

D = {
    "bg":"#0f1421","bg2":"#1a2235","bg3":"#232f45",
    "text":"#e2e8f0","muted":"#8899b0","accent":"#00BCD4",
    "accent2":"#FF6B35","success":"#6fcf97","warning":"#f6cc52",
    "danger":"#fc8181","border":"rgba(255,255,255,0.09)",
}
LEVEL_COLORS = {
    "critical":"#fc8181","high":"#FF6B35","medium":"#f6cc52","low":"#6fcf97"
}


def _layout(fig, title="", height=380):
    fig.update_layout(
        title=dict(text=title, font=dict(color=D["text"],size=13)) if title else None,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height, margin=dict(l=10,r=10,t=100 if title else 20,b=50),
        font=dict(color=D["text"],size=11),
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color=D["text"],size=10),
                    orientation="h",yanchor="bottom",y=1.08,xanchor="left",x=0),
        xaxis=dict(gridcolor="rgba(255,255,255,0.06)",color=D["text"]),
        yaxis=dict(gridcolor="rgba(255,255,255,0.06)",color=D["text"]),
    )
    return fig


def fig_to_html(fig, title=""):
    if title: fig.update_layout(title=dict(text=title))
    return fig.to_html(full_html=True, include_plotlyjs=True,
                       config={"responsive":True,"scrollZoom":True})


# ── 1. Risk Matrix heatmap (3×3 grid) ────────────────────────────────────────
def chart_risk_matrix(risks: list, title="Risk Matrix") -> go.Figure:
    """
    3×3 grid: Likelihood (rows) × Severity (cols).
    Cells coloured by risk level. Number = count of risks in each cell.
    """
    opts  = ["high","medium","low"]
    grid  = {(l,s):[] for l in opts for s in opts}

    for r in risks:
        l = (r.get("likelihood") or "medium").lower()
        s = (r.get("severity")   or "medium").lower()
        if l in opts and s in opts:
            grid[(l,s)].append(r.get("risk_number",""))

    # Build heatmap data
    z_colors = {"critical":3,"high":2,"medium":1,"low":0}
    MATRIX_LEVEL = {
        ("high","high"):"critical",("high","medium"):"high",("high","low"):"medium",
        ("medium","high"):"high",("medium","medium"):"medium",("medium","low"):"low",
        ("low","high"):"medium",("low","medium"):"low",("low","low"):"low",
    }
    CELL_COLORS = {"critical":"rgba(252,129,129,0.7)","high":"rgba(255,107,53,0.7)",
                   "medium":"rgba(246,204,82,0.7)","low":"rgba(111,207,151,0.7)"}

    fig = go.Figure()

    for li, lik in enumerate(opts):
        for si, sev in enumerate(opts):
            level = MATRIX_LEVEL[(lik,sev)]
            risks_here = grid[(lik,sev)]
            count = len(risks_here)
            label = str(count) if count > 0 else ""
            hover = f"<b>{lik.title()} × {sev.title()}</b><br>"
            hover += f"Risk Level: <b>{level.title()}</b><br>"
            if risks_here:
                hover += "Risks: " + ", ".join(risks_here[:8])
                if len(risks_here) > 8: hover += f" +{len(risks_here)-8}"

            fig.add_trace(go.Scatter(
                x=[si], y=[li],
                mode="markers+text",
                marker=dict(symbol="square", size=80,
                            color=CELL_COLORS[level],
                            line=dict(color=D["bg"],width=2)),
                text=[label],
                textfont=dict(size=22, color="white"),
                hovertext=hover, hoverinfo="text",
                name=level, showlegend=False,
            ))

    fig.update_layout(
        xaxis=dict(ticktext=["High","Medium","Low"], tickvals=[0,1,2],
                   title="Severity", gridcolor="rgba(0,0,0,0)",
                   color=D["text"]),
        yaxis=dict(ticktext=["High","Medium","Low"], tickvals=[0,1,2],
                   title="Likelihood", gridcolor="rgba(0,0,0,0)",
                   color=D["text"], autorange="reversed"),
        height=340, margin=dict(l=80,r=20,t=80 if title else 20,b=60),
    )
    # Add legend patches as scatter
    for level, color in CELL_COLORS.items():
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(symbol="square",size=12,color=color),
            name=level.title(), showlegend=True
        ))
    return _layout(fig, title, 360)


# ── 2. Risk level donut ───────────────────────────────────────────────────────
def chart_risk_levels(risks: list, title="Risks by Level") -> go.Figure:
    counts = {}
    for r in risks:
        lv = r.get("risk_level","medium")
        counts[lv] = counts.get(lv,0) + 1
    if not counts: return go.Figure()
    order  = ["critical","high","medium","low"]
    labels = [l for l in order if l in counts]
    values = [counts[l] for l in labels]
    colors = [LEVEL_COLORS.get(l,D["muted"]) for l in labels]
    fig = go.Figure(go.Pie(
        labels=[l.title() for l in labels], values=values, hole=0.6,
        marker=dict(colors=colors, line=dict(color=D["bg"],width=2)),
        textfont=dict(color=D["text"]),
    ))
    return _layout(fig, title, 320)


# ── 3. Risk status bar ────────────────────────────────────────────────────────
def chart_risk_status(risks: list, title="Risks by Status") -> go.Figure:
    STATUS_COLORS = {
        "open":"#fc8181","mitigated":"#6fcf97",
        "accepted":"#f6cc52","monitoring":"#00BCD4","closed":"#8899b0"
    }
    counts = {}
    for r in risks:
        s = r.get("status","open")
        counts[s] = counts.get(s,0) + 1
    if not counts: return go.Figure()
    labels = list(counts.keys())
    values = list(counts.values())
    colors = [STATUS_COLORS.get(l,D["muted"]) for l in labels]
    fig = go.Figure(go.Bar(
        x=[l.replace("_"," ").title() for l in labels], y=values,
        marker_color=colors, marker_line_width=0,
        text=values, textposition="outside",
        textfont=dict(color=D["text"]),
        hovertemplate="%{x}: %{y} risks<extra></extra>",
    ))
    fig.update_layout(yaxis_title="Count")
    return _layout(fig, title, 320)


# ── 4. Risk by category ───────────────────────────────────────────────────────
def chart_risk_by_category(risks: list, title="Risks by Category") -> go.Figure:
    from config import CAT_LABELS
    counts = {}
    for r in risks:
        cat = r.get("risk_category","technical")
        counts[cat] = counts.get(cat,0) + 1
    if not counts: return go.Figure()
    cats   = sorted(counts.keys())
    labels = [CAT_LABELS.get(c,c) for c in cats]
    values = [counts[c] for c in cats]
    colors = [D["accent"],D["success"],D["warning"],D["accent2"],
              D["danger"],"#9b59b6","#3498db"]
    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker_color=colors[:len(cats)],
        marker_line_width=0,
        text=values, textposition="outside",
        textfont=dict(color=D["text"]),
        hovertemplate="%{x}: %{y} risks<extra></extra>",
    ))
    fig.update_layout(yaxis_title="Count", xaxis_tickangle=-20)
    return _layout(fig, title, 360)


# ── 5. Risk trend over reporting periods ──────────────────────────────────────
def chart_risk_trend(reviews: list, title="Risk Level Trend Over Time") -> go.Figure:
    """
    Shows how risk levels changed across reporting periods.
    Uses review snapshots — one line per risk level.
    """
    if not reviews: return go.Figure()

    from collections import defaultdict
    period_counts = defaultdict(lambda: {"critical":0,"high":0,"medium":0,"low":0})
    for rv in reviews:
        p  = rv.get("reporting_period",1)
        lv = rv.get("risk_level","medium")
        period_counts[p][lv] += 1

    periods = sorted(period_counts.keys())
    fig = go.Figure()
    for level, color in [("critical",LEVEL_COLORS["critical"]),
                          ("high",LEVEL_COLORS["high"]),
                          ("medium",LEVEL_COLORS["medium"]),
                          ("low",LEVEL_COLORS["low"])]:
        y_vals = [period_counts[p][level] for p in periods]
        if any(y_vals):
            fig.add_trace(go.Scatter(
                x=periods, y=y_vals, mode="lines+markers",
                name=level.title(),
                line=dict(color=color,width=2),
                marker=dict(size=7,color=color),
                hovertemplate=f"Period %{{x}}<br>{level.title()}: %{{y}} risks<extra></extra>",
            ))
    fig.update_layout(xaxis_title="Reporting Period", yaxis_title="Number of Risks")
    return _layout(fig, title, 340)


# ── 6. Action status bar ──────────────────────────────────────────────────────
def chart_action_status(actions: list, title="Mitigation Actions by Status") -> go.Figure:
    ACTION_COLORS = {
        "planned":"#8899b0","in_progress":"#f6cc52",
        "completed":"#6fcf97","overdue":"#fc8181","cancelled":"#4a4a6a"
    }
    counts = {}
    for a in actions:
        s = a.get("status","planned")
        counts[s] = counts.get(s,0) + 1
    if not counts: return go.Figure()
    labels = list(counts.keys())
    values = list(counts.values())
    colors = [ACTION_COLORS.get(l,D["muted"]) for l in labels]
    fig = go.Figure(go.Pie(
        labels=[l.replace("_"," ").title() for l in labels],
        values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color=D["bg"],width=2)),
        textfont=dict(color=D["text"]),
    ))
    return _layout(fig, title, 300)
