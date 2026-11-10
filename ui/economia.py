"""Evaluación económica: solo muestra cifras que existen en el libro."""
import streamlit as st

from core.modules import extract_module
from ui import generic, plots, theme


def render(wb, schema):
    theme.page_header("Evaluación económica", "Inversiones, costos, beneficios y ahorros según el libro.")
    flujo = wb.sheet("Flujo Caja")
    if flujo is None or not flujo.grid:
        st.markdown("#### Flujo de caja")
        theme.no_data("Flujo de caja (hoja «Flujo Caja»)")
    else:
        generic.render_sheet(wb, flujo, title="Flujo de caja")

    st.markdown("#### Indicadores económicos por objetivo")
    o3 = extract_module(wb, "obj3", schema)
    o5 = extract_module(wb, "obj5", schema)
    kp = [(k["name"], k["value"]) for k in o3["kpis"]]
    if kp:
        cols = st.columns(3)
        for i, (name, val) in enumerate(kp):
            if isinstance(val, (int, float)):
                txt = f"{val:,.2f}" if ("Relación" in name or "meses" in name) else f"{val:,.0f}"
                if "%" in name:
                    txt = f"{val:.1%}"
            else:
                txt = "No disponible"
            cols[i % 3].markdown(theme.kpi_html(name, txt, "Objetivo 3 · DesarrolloOBJ3"), unsafe_allow_html=True)
    for k in o5["kpis"]:
        if "económico" in k["name"] or "beneficio" in k["name"]:
            theme.kpi_row([(k["name"], str(k["value"]), "Objetivo 5 · simulado según el libro", "celeste")])

    ts = wb.sheet("Tabla Resumen")
    if ts:
        res = wb.read_table(ts, "Impacto económico anual (S/)")
        if res:
            import pandas as pd
            df = res[0]
            theme.show_table(df, "impacto_economico", title="Impacto económico anual por problema (Tabla Resumen)")
