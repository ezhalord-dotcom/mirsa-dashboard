"""Dashboards por objetivo. Todo sale de los datos extraídos del Excel (config/schema.yaml)."""
import pandas as pd
import streamlit as st

from ui import theme

from core.modules import extract_module
from ui import plots


def _pct(v):
    return f"{v:.1%}" if isinstance(v, (int, float)) else "—"


def _num(v, fmt="{:,.2f}"):
    return fmt.format(v) if isinstance(v, (int, float)) else "—"


def _style_semaforo(df: pd.DataFrame):
    colors = {"VERDE": "#C6EFCE", "AMARILLO": "#FFEB9C", "ROJO": "#FFC7CE"}
    cols = [c for c in df.columns if "Semáforo" in str(c)]
    return df.style.map(lambda v: f"background-color: {colors.get(v, '')}", subset=cols)


def _kpi_row(items: list[tuple[str, str]]):
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.metric(label, value)


def _warnings(data: dict):
    if data["warnings"]:
        with st.expander(f"Avisos de lectura ({len(data['warnings'])})"):
            for w in data["warnings"]:
                st.warning(w)


def _col(df, token: str):
    """Columna por nombre parcial (no por posición)."""
    for c in df.columns:
        if token.lower() in str(c).lower():
            return c
    return None


def _umbrales(wb, schema):
    """Umbrales de semáforo leídos del Excel (Objetivo 2)."""
    u = extract_module(wb, "obj2", schema).get("umbrales", {})
    return u.get("verde"), u.get("amarillo")


def _kpi_by_name(data: dict, contains: str):
    for k in data["kpis"]:
        if contains.lower() in k["name"].lower():
            return k["value"]
    return None


def render_obj3(wb, schema):
    data = extract_module(wb, "obj3", schema)
    st.header(data["title"])
    _warnings(data)
    base = data["tables"].get("ira_base", {}).get("df")
    ira_as = ira_to = ira_ref = None
    if base is not None and len(base):
        ira_as = base.iloc[0][_col(base, "AS IS")]
        ira_to = base.iloc[0][_col(base, "TO BE")]
        ira_ref = base.iloc[0][_col(base, "Referencia")]
    _kpi_row([
        ("IRA AS IS (antes)", _pct(ira_as)),
        ("IRA TO BE (ciclo 3)", _pct(ira_to)),
        ("Estándar (literatura)", _pct(ira_ref)),
        ("Ahorro anual", "S/ " + _num(_kpi_by_name(data, "ahorro"), "{:,.0f}")),
    ])

    tab1, tab2, tab3, tab4 = st.tabs(["Exactitud (IRA)", "Diagnóstico (Pareto)", "Semaforización", "Economía"])

    with tab1:
        m = data["tables"].get("ira_mensual", {}).get("df")
        if m is not None and len(m):
            m = m.copy()
            m["IRA"] = pd.to_numeric(m["IRA"], errors="coerce")
            ref_col = _col(m, "Referencia")
            fig = plots.bars(m, "Mes", ["IRA"], title="IRA mensual AS IS (registros correctos / verificados)",
                             ref=float(m[ref_col].iloc[0]) if ref_col else None, yfmt=".0%")
            theme.chart(fig, use_container_width=True)
            st.dataframe(m, use_container_width=True, hide_index=True)
        c = data["tables"].get("ciclos", {}).get("df")
        if c is not None and len(c):
            c = c.copy()
            c["IRA"] = pd.to_numeric(c["IRA"], errors="coerce")
            fig = plots.bars(c, "Ciclo", ["IRA"], title="IRA por ciclo del piloto (TO BE)",
                             ref=float(ira_ref) if isinstance(ira_ref, (int, float)) else None, yfmt=".0%")
            theme.chart(fig, use_container_width=True)
            st.dataframe(c, use_container_width=True, hide_index=True)
            n_col = _col(c, "SKU contados")
            if n_col is not None:
                lo, hi = int(c[n_col].min()), int(c[n_col].max())
                st.caption(f"Muestra pequeña: {lo} a {hi} conteos por ciclo. Un SKU mueve el IRA unos {100 / hi:.1f} puntos.")

    with tab2:
        p = data["tables"].get("pareto", {}).get("df")
        if p is not None and len(p):
            cat = _col(p, "Causa de la diferencia") or p.columns[1]
            cnt = _col(p, "N°")
            cum = _col(p, "acumulado")
            if cnt is not None and cum is not None:
                total = int(pd.to_numeric(p[cnt], errors="coerce").sum())
                theme.chart(plots.pareto(p, cat, cnt, cum,
                                             title=f"Pareto de causas de diferencias ({total} registros)"),
                                use_container_width=True)
            st.dataframe(p, use_container_width=True, hide_index=True)
        pct = _kpi_by_name(data, "alcance")
        st.metric("Alcance de la herramienta (% de diferencias que ataca)", _pct(pct))

    with tab3:
        s = data["tables"].get("semaforo", {}).get("df")
        if s is not None and len(s):
            st.dataframe(_style_semaforo(s), use_container_width=True, hide_index=True)
            v, a = _umbrales(wb, schema)
            if v is not None and a is not None:
                st.caption(f"Semáforo = cumplimiento del estándar: verde ≥ {v:.0%}, amarillo ≥ {a:.0%}, "
                           f"rojo < {a:.0%} (umbrales leídos de Objetivo 2, mismo método).")
            else:
                st.caption("Semáforo = cumplimiento del estándar (umbrales no encontrados en Objetivo 2).")
        pesos = data["tables"].get("ahp_pesos", {}).get("df")
        if pesos is not None and len(pesos):
            st.subheader("Matriz AHP (selección de herramienta)")
            st.dataframe(pesos, use_container_width=True, hide_index=True)

    with tab4:
        econ = [(k["name"], k["value"]) for k in data["kpis"]]
        cols = st.columns(3)
        for i, (name, val) in enumerate(econ):
            fmt = "{:,.2f}" if "Relación" in name or "meses" in name else "{:,.0f}"
            txt = _pct(val) if "%" in name else _num(val, fmt)
            cols[i % 3].metric(name, txt)


def render_obj2(wb, schema):
    data = extract_module(wb, "obj2", schema)
    st.header(data["title"])
    _warnings(data)
    k = {x["name"]: x["value"] for x in data["kpis"]}
    _kpi_row([
        ("Reducción del ciclo", _pct(k.get("Reducción del tiempo de ciclo"))),
        ("Brecha cerrada del ciclo", _pct(k.get("Brecha cerrada del ciclo"))),
    ])
    tab1, tab2, tab3 = st.tabs(["Ciclo por fase", "Tiempo estándar", "Semaforización"])
    with tab1:
        f = data["tables"].get("ciclo_fases", {}).get("df")
        if f is not None and len(f):
            fases = f[f["Fase"].astype(str).str.lower() != "ciclo total"]
            theme.chart(plots.bars(fases, "Fase", ["Antes (min)", "Después (min)"],
                                       title="Tiempo de ciclo por fase (min)"), use_container_width=True)
            st.dataframe(f, use_container_width=True, hide_index=True)
    with tab2:
        e = data["tables"].get("tiempo_estandar", {}).get("df")
        if e is not None and len(e):
            fases = e[e.iloc[:, 0].astype(str).str.lower() != "ciclo total"]
            theme.chart(plots.bars(fases, fases.columns[0], list(fases.columns[1:3]),
                                       title="Tiempo estándar por fase (min)"), use_container_width=True)
            st.dataframe(e, use_container_width=True, hide_index=True)
    with tab3:
        s = data["tables"].get("semaforo", {}).get("df")
        if s is not None and len(s):
            st.dataframe(_style_semaforo(s), use_container_width=True, hide_index=True)
            st.caption("Cumplimiento = meta / actual (menor es mejor) o actual / meta (mayor es mejor), tope 100 %.")


MODULE_RENDERERS = {"obj2": render_obj2, "obj3": render_obj3}
