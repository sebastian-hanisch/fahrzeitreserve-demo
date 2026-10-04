"""Plotly-Figuren der Fahrzeitreserve-Demo. Alle Achsen fest (fixedrange), damit Touch-Scrollen nicht am Chart hängen bleibt."""
from __future__ import annotations

import plotly.graph_objects as go

import rsv_constants as C
import rsv_results as R


def _lock(fig, height=360, **layout):
    fig.update_layout(height=height, margin=dict(l=50, r=20, t=40, b=55), font=dict(size=12),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0), **layout)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def method_keys(run: dict) -> list:
    """Verfahren der Anzeige: die drei Verfahren, bei Störungslagen zusätzlich das Optimum ohne Störungslagen."""
    return [k for k in ("prop", "risk", "saa", "saa_blind") if k in run["results"]]


def build_allocation_bars(run: dict) -> go.Figure:
    """Reserve (Zehntelminuten, gezeigt in Minuten) je Abschnitt und Verfahren; unter der Abschnittsnummer die planmäßige Fahrzeit und, wo es einen gibt, das Wort Engpass; das Fenster der Störungslage ist hinterlegt."""
    cfg = run["cfg"]
    n = cfg["n"]
    labels = [f"{k + 1}<br>{int(cfg['r'][k])} min" + ("<br>Engpass" if k in cfg["bott"] else "") for k in range(n)]
    fig = go.Figure()
    for key in method_keys(run):
        fig.add_trace(go.Bar(x=list(range(n)), y=[x / C.UNITS_PER_MIN for x in run["results"][key]["alloc"]], name=C.METHOD_LABELS[key], marker_color=C.METHOD_COLORS[key],
                             hovertemplate="Abschnitt %{customdata}: %{y:.1f} min Reserve<extra>" + C.METHOD_LABELS[key] + "</extra>", customdata=[k + 1 for k in range(n)]))
    if run.get("corr", "aus") != "aus":
        fig.add_vrect(x0=cfg["w0"] - 0.5, x1=cfg["w0"] + C.SHOCK_WINDOW - 0.5, fillcolor="#c0392b", opacity=0.08, line_width=0)
    fig.update_layout(barmode="group")
    fig.update_xaxes(tickvals=list(range(n)), ticktext=labels, title_text="Abschnitt und planmäßige Fahrzeit")
    fig.update_yaxes(title_text="Reserve (min)", rangemode="tozero")
    return _lock(fig, 400)


def build_delay_profile(run: dict) -> go.Figure:
    """Mittlere Verspätung am Ende jedes Abschnitts (alle Züge, frische Tage): wo sammelt sich Verspätung an, und wo nimmt die Reserve sie auf?"""
    n = run["cfg"]["n"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(1, n + 1)), y=run["results"]["none"]["profile"], mode="lines", name="ohne Reserve", line=dict(color="#bbb", dash="dot", width=2)))
    for key in method_keys(run):
        fig.add_trace(go.Scatter(x=list(range(1, n + 1)), y=run["results"][key]["profile"], mode="lines+markers", name=C.METHOD_LABELS[key], line=dict(color=C.METHOD_COLORS[key], width=2.5),
                                 hovertemplate="Abschnitt %{x}: %{y:.2f} min<extra>" + C.METHOD_LABELS[key] + "</extra>"))
    fig.update_xaxes(title_text="Abschnitt", dtick=1)
    fig.update_yaxes(title_text="mittlere Verspätung am Abschnittsende (min)", rangemode="tozero")
    return _lock(fig, 360)


def build_method_bars(run: dict) -> go.Figure:
    """Mittlere gewichtete Verspätung je Verfahren (frische Tage); über den Balken die Pünktlichkeit."""
    keys = ["none"] + method_keys(run)
    labels = {"none": "ohne Reserve", **C.METHOD_LABELS}
    colors = {"none": "#bbb", **C.METHOD_COLORS}
    fig = go.Figure(go.Bar(x=[labels[k] for k in keys], y=[run["results"][k]["delay"] for k in keys], marker_color=[colors[k] for k in keys],
                           text=[f"{100 * run['results'][k]['punct']:.0f} % pünktlich" for k in keys], textposition="outside",
                           hovertemplate="%{x}: %{y:.2f} min<extra></extra>"))
    top = max(run["results"][k]["delay"] for k in keys)
    fig.update_yaxes(title_text="mittlere Verspätung (min)", range=[0, 1.2 * top])
    return _lock(fig, 340, showlegend=False)


def build_budget_curve(rows: list) -> go.Figure:
    """Messreihe: wie viel Prozent weniger Verspätung als die Praxisregel das Optimum erreicht, je Budget (Mittel ± Standardfehler)."""
    pts = sorted(((r["B_pct"], r) for r in rows), key=lambda t: t[0])
    fig = go.Figure(go.Scatter(x=[p for p, _ in pts], y=[r["gain_saa"] for _, r in pts], mode="lines+markers", line=dict(color=C.METHOD_COLORS["saa"], width=3),
                               error_y=dict(type="data", array=[r["gain_saa_se"] for _, r in pts], visible=True),
                               hovertemplate="%{x} % Budget: %{y:.1f} % weniger Verspätung<extra></extra>"))
    fig.update_xaxes(title_text="Reservebudget (% der Fahrzeit)", dtick=1)
    fig.update_yaxes(title_text="Optimum senkt gegenüber der Praxisregel um (%)", rangemode="tozero")
    return _lock(fig, 340, showlegend=False)


def build_variant_bars(rows: list) -> go.Figure:
    """Messreihe: Verspätung der Praxisregel und der risikoproportionalen Regel über dem Optimum (%), je Variante."""
    fig = go.Figure()
    names = [r["name"] for r in rows]
    for key in ("prop", "risk"):
        fig.add_trace(go.Bar(x=names, y=[r[f"over_{key}"] for r in rows], name=C.METHOD_LABELS[key], marker_color=C.METHOD_COLORS[key],
                             error_y=dict(type="data", array=[r[f"over_{key}_se"] for r in rows], visible=True)))
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="Verspätung über dem Optimum (%)", rangemode="tozero")
    return _lock(fig, 400)


def build_mean_allocation(res: dict, variant: str) -> go.Figure:
    """Messreihe: mittlerer Anteil des Budgets je Abschnittsposition über alle Strecken (der Buckel des Optimums)."""
    fig = go.Figure()
    for key in ("prop", "risk", "saa"):
        share = R.mean_allocation(res, variant, key)
        fig.add_trace(go.Scatter(x=list(range(1, len(share) + 1)), y=[100 * s for s in share], mode="lines+markers", name=C.METHOD_LABELS[key],
                                 line=dict(color=C.METHOD_COLORS[key], width=3 if key == "saa" else 2)))
    fig.update_xaxes(title_text="Abschnittsposition", dtick=1)
    fig.update_yaxes(title_text="Anteil am Budget (%)", rangemode="tozero")
    return _lock(fig, 340)


def build_data_curve(rows: list) -> go.Figure:
    """Messreihe: Vorsprung des Optimums (frische Tage) und Optimismus (Planungstage gegen frische Tage) je Zahl der Planungsszenarien."""
    pts = sorted(((r["data"], r) for r in rows), key=lambda t: t[0])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[p for p, _ in pts], y=[r["gain_saa"] for _, r in pts], mode="lines+markers", name="Optimum senkt gegenüber der Praxisregel um (%)",
                             line=dict(color=C.METHOD_COLORS["saa"], width=3), error_y=dict(type="data", array=[r["gain_saa_se"] for _, r in pts], visible=True)))
    fig.add_trace(go.Scatter(x=[p for p, _ in pts], y=[-r["optimism"] for _, r in pts], mode="lines+markers", name="Selbsttäuschung: Planung besser als Wirklichkeit (%)",
                             line=dict(color="#c0392b", width=2.5, dash="dot"), error_y=dict(type="data", array=[r["optimism_se"] for _, r in pts], visible=True)))
    fig.update_xaxes(title_text="Planungsszenarien (beobachtete Tage)", type="log", tickvals=[p for p, _ in pts], ticktext=[str(p) for p, _ in pts])
    fig.update_yaxes(title_text="%", rangemode="tozero")
    return _lock(fig, 360)
