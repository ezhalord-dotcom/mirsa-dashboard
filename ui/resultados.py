"""Resultados generales: consolida lo que existe por objetivo, indicando la fuente de cada cifra."""
import pandas as pd
import streamlit as st

from core.modules import extract_module
from ui import generic, plots, theme


def render(wb, schema):
    theme.page_header("Resultados generales", "Antes y después por objetivo. Cada cifra indica su hoja de origen.")
    o2 = extract_module(wb, "obj2", schema)
    o3 = extract_module(wb, "obj3", schema)
    o5 = extract_module(wb, "obj5", schema)
    k2 = {k["name"]: k["value"] for k in o2["kpis"]}
    rows = []
    f = o2["tables"].get("ciclo_fases", {}).get("df")
    if f is not None:
        tot = f[f.iloc[:, 0].astype(str).str.lower().str.contains("total")]
        if len(tot):
            rows.append({"Objetivo": "Objetivo 2 · Ciclo de picking (min)", "Antes": tot.iloc[0]["Antes (min)"],
                         "Después": tot.iloc[0]["Después (min)"], "Fuente": "DesarrolloOBJ2"})
    base = o3["tables"].get("ira_base", {}).get("df")
    if base is not None and len(base):
        rows.append({"Objetivo": "Objetivo 3 · Exactitud de inventario (IRA)", "Antes": base.iloc[0, 1],
                     "Después": base.iloc[0, 2], "Fuente": "DesarrolloOBJ3"})
    for k in o5["kpis"]:
        if "Vejez" in k["name"]:
            rows.append({"Objetivo": "Objetivo 5 · Vejez de inventario (simulado)", "Antes": str(k["value"]),
                         "Después": "", "Fuente": "Desarrollo Obj. 5"})
    if rows:
        theme.show_table(pd.DataFrame(rows), "resultados_objetivos", title="Antes y después por objetivo")
        theme.notice("Las unidades son distintas entre objetivos. No se comparan entre sí.", "info")
    else:
        theme.no_data("Resultados por objetivo")

    st.markdown("#### Resumen de resultados del libro")
    s = wb.sheet("Resultados-Indicadores")
    if s is None:
        theme.no_data("Hoja Resultados-Indicadores")
        return
    has_values = any(isinstance(v, (int, float)) and v not in (0,) for r in s.grid.values() for c, v in r.items() if c >= 3)
    if has_values:
        generic.render_sheet(wb, s)
    else:
        theme.notice("La hoja Resultados-Indicadores está vacía en el libro: tiene los nombres de los indicadores "
                     "(IND.1 a IND.X) pero aún no tiene valores ni impactos. Cuando se llenen, aparecerán aquí.", "warn")
