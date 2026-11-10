"""Inicio: dashboard ejecutivo. Todo se lee del libro; lo que no existe se marca como no disponible."""
import pandas as pd
import streamlit as st

from core.modules import extract_module
from ui import plots, theme
from core.textnorm import norm


def _sheet(wb, name):
    return wb.sheet(name)


def _value_below(sheet, label):
    """Busca el primer valor no vacío debajo de una etiqueta, sin depender de métodos del lector."""
    if sheet is None:
        return None
    target = norm(label)
    for r in sorted(sheet.grid):
        for c in sorted(sheet.grid[r]):
            value = sheet.grid[r][c]
            if isinstance(value, str) and target in norm(value):
                candidate = sheet.grid.get(r + 1, {}).get(c)
                if candidate is not None:
                    return candidate
    return None


def _value_right_of(sheet, label):
    """Busca el primer valor no vacío a la derecha de una etiqueta."""
    if sheet is None:
        return None
    target = norm(label)
    for r in sorted(sheet.grid):
        for c in sorted(sheet.grid[r]):
            value = sheet.grid[r][c]
            if isinstance(value, str) and target in norm(value):
                for next_col in sorted(k for k in sheet.grid.get(r, {}) if k > c):
                    return sheet.grid[r][next_col]
    return None


def render(wb, schema):
    theme.page_header("Exportaciones Mirsa E.I.R.L.",
                      "Resumen ejecutivo del proyecto: problemas, objetivos, resultados e impacto económico.")
    emp = _sheet(wb, "Empresa")
    mision = _value_below(emp, "MISIÓN") if emp else None
    rubro = _value_below(emp, "Rubro e industria") if emp else None
    st.markdown('<div class="card"><h4>Descripción</h4>'
                f'{(rubro or mision or "Sin descripción en la hoja Empresa.")}</div>', unsafe_allow_html=True)

    o2 = extract_module(wb, "obj2", schema)
    o3 = extract_module(wb, "obj3", schema)
    o5 = extract_module(wb, "obj5", schema)
    ts = _sheet(wb, "Tabla Resumen")
    total = _value_right_of(ts, "TOTAL") if ts else None
    k2 = {k["name"]: k["value"] for k in o2["kpis"]}
    base3 = o3["tables"].get("ira_base", {}).get("df")
    ira_as = ira_to = None
    if base3 is not None and len(base3):
        ira_as = base3.iloc[0, 1]
        ira_to = base3.iloc[0, 2]

    def pct(v):
        return f"{v:.1%}" if isinstance(v, (int, float)) else "No disponible"

    theme.kpi_row([
        ("Impacto económico total", f"S/ {total:,.0f}" if isinstance(total, (int, float)) else "No disponible",
         "Suma de Tabla Resumen (P2, P3, P4)", "coral"),
        ("Reducción del ciclo de picking", pct(k2.get("Reducción del tiempo de ciclo")), "Objetivo 2 · slotting", "verde"),
        ("Exactitud de inventario (IRA)", f"{pct(ira_as)} → {pct(ira_to)}", "Objetivo 3 · AS IS → TO BE", "celeste"),
        ("Vejez de inventario", str(next((k["value"] for k in o5["kpis"] if "Vejez" in k["name"]), "No disponible")),
         "Objetivo 5 · AS IS → TO BE (simulado)", ""),
    ])

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### Antes y después")
        rows = []
        f = o2["tables"].get("ciclo_fases", {}).get("df")
        if f is not None and len(f):
            tot = f[f.iloc[:, 0].astype(str).str.lower().str.contains("total")]
            if len(tot):
                rows.append({"Indicador": "Ciclo de picking (min)", "Antes": tot.iloc[0]["Antes (min)"],
                             "Después": tot.iloc[0]["Después (min)"]})
        if ira_as is not None:
            rows.append({"Indicador": "Exactitud de inventario (IRA)", "Antes": ira_as, "Después": ira_to})
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption("Cada indicador viene de su propio objetivo; no se mezclan unidades.")
        else:
            theme.no_data("Antes y después")
    with right:
        st.markdown("#### Impacto económico por problema")
        imp = None
        if ts:
            res = wb.read_table(ts, "Impacto económico anual (S/)")
            if res:
                imp = res[0]
        if imp is not None and len(imp):
            pcol = imp.columns[0]
            vcol = next((c for c in imp.columns if "Impacto" in str(c)), imp.columns[-1])
            d = imp[imp[pcol].astype(str).str.upper().str.strip() != "TOTAL"].copy()
            d["Problema"] = d[pcol].astype(str).str.split("—").str[0].str.strip()
            d[vcol] = pd.to_numeric(d[vcol], errors="coerce")
            st.plotly_chart(plots.bars(d, "Problema", [vcol], title="Impacto anual (S/)"), use_container_width=True)
        else:
            theme.no_data("Tabla Resumen")

    st.markdown("#### Estado de los objetivos")
    rows = []
    for mod_id, label in [("obj2", "Objetivo 2 · Slotting"), ("obj3", "Objetivo 3 · Conteo cíclico"),
                          ("obj4", "Objetivo 4 · MRP"), ("obj5", "Objetivo 5 · Lote por lote"),
                          ("minmax", "Modelo Min-Max")]:
        d = extract_module(wb, mod_id, schema)
        rows.append({"Objetivo": label,
                     "Hoja": schema["modules"][mod_id]["sheet"].strip(),
                     "Lectura": "Completa" if not d["warnings"] else f"{len(d['warnings'])} aviso(s)"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Obj. 4 y Min-Max usan datos simulados según el propio libro; se indica en cada módulo.")
