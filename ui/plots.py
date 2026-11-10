"""Gráficos Plotly. Recibe datos ya resueltos (sin tocar Excel)."""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PALETTE = ["#1F4E78", "#2E86AB", "#F6AE2D", "#86BBD8", "#33658A", "#F26419", "#55DDE0"]
REF_COLOR = "#C0392B"


def bars(df, x, ys: list, title="", ref: float | None = None, yfmt=None, horizontal=False):
    fig = go.Figure()
    for i, y in enumerate(ys):
        if y not in df.columns:
            continue
        fig.add_bar(name=str(y), x=df[x] if not horizontal else df[y],
                    y=df[y] if not horizontal else df[x], marker_color=PALETTE[i % len(PALETTE)],
                    orientation="h" if horizontal else "v")
    if ref is not None:
        if horizontal:
            fig.add_vline(x=ref, line_dash="dash", line_color=REF_COLOR, annotation_text="Referencia")
        else:
            fig.add_hline(y=ref, line_dash="dash", line_color=REF_COLOR, annotation_text="Referencia")
    fig.update_layout(title=title, barmode="group", template="plotly_white", height=380,
                      margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.2))
    if yfmt and not horizontal:
        fig.update_yaxes(tickformat=yfmt)
    return fig


def pareto(df, cat_col, count_col, cum_col, title=""):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=df[cat_col], y=df[count_col], name="N° de casos", marker_color=PALETTE[0], secondary_y=False)
    fig.add_scatter(x=df[cat_col], y=df[cum_col], name="% acumulado", mode="lines+markers",
                    line=dict(color=PALETTE[2]), secondary_y=True)
    fig.update_yaxes(title_text="Casos", secondary_y=False)
    fig.update_yaxes(title_text="% acumulado", tickformat="0%", range=[0, 1.05], secondary_y=True)
    fig.update_layout(title=title, template="plotly_white", height=430,
                      margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.25))
    return fig


def from_chart_values(cv: dict):
    """Reconstruye un gráfico del libro (leído de su XML) como figura Plotly."""
    fig = go.Figure()
    for i, s in enumerate(cv["series"]):
        color = PALETTE[i % len(PALETTE)]
        cats = s["cats"] or list(range(1, len(s["vals"]) + 1))
        kind = s["kind"]
        if kind == "barChart":
            fig.add_bar(name=s["name"], x=cats, y=s["vals"], marker_color=color)
        elif kind == "horizontalBar":
            fig.add_bar(name=s["name"], x=s["vals"], y=cats, orientation="h", marker_color=color)
        elif kind == "lineChart":
            fig.add_scatter(name=s["name"], x=cats, y=s["vals"], mode="lines+markers", line=dict(color=color))
        elif kind == "areaChart":
            fig.add_scatter(name=s["name"], x=cats, y=s["vals"], fill="tozeroy", line=dict(color=color))
        elif kind == "scatterChart":
            fig.add_scatter(name=s["name"], x=cats, y=s["vals"], mode="markers", marker=dict(color=color))
        elif kind in ("pieChart", "doughnutChart"):
            fig = go.Figure(go.Pie(labels=cats, values=s["vals"], hole=0.4 if kind == "doughnutChart" else 0))
            break
    fig.update_layout(title=cv["title"] or "Gráfico del libro", template="plotly_white", height=380,
                      margin=dict(l=10, r=10, t=50, b=10))
    return fig


def lines(df, x, ys: list, title="", ref: float | None = None, yfmt=None):
    fig = go.Figure()
    for i, y in enumerate(ys):
        if y in df.columns:
            fig.add_scatter(name=str(y), x=df[x], y=df[y], mode="lines+markers",
                            line=dict(color=PALETTE[i % len(PALETTE)]))
    if ref is not None:
        fig.add_hline(y=ref, line_dash="dash", line_color=REF_COLOR, annotation_text="Referencia")
    fig.update_layout(title=title, template="plotly_white", height=380,
                      margin=dict(l=10, r=10, t=50, b=10), legend=dict(orientation="h", y=-0.2))
    if yfmt:
        fig.update_yaxes(tickformat=yfmt)
    return fig
