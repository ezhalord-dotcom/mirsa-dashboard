"""
Dashboards analíticos de Objetivo 4 (MRP y abastecimiento) y Objetivo 5 (lote por lote).
Todo sale de la hoja del Excel (config/schema.yaml + core/mrp_blocks.py). No se recalcula nada
salvo lo que se indica explícitamente como cálculo del dashboard.
"""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from core.modules import extract_module
from core.mrp_blocks import parse_blocks
from core.textnorm import norm
from core.xlsx_reader import long_texts
from ui import dashboards, generic, plots, theme

CAVEAT_WORDS = ("simulad", "supuesto", "datos reales")


# ----------------------------------------------------------------- utilidades
def _c(df, token):
    """Columna por texto parcial."""
    for c in df.columns:
        if norm(token) in norm(c):
            return c
    return None


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def _row_series(df, token):
    """Fila de una tabla 'ancha' (etiquetas en la 1.ª columna, semanas en las demás)."""
    first = df.columns[0]
    hit = df[df[first].astype(str).map(norm).str.contains(norm(token), regex=False)]
    if not len(hit):
        return None
    r = hit.iloc[0]
    out = {}
    for c in df.columns[1:]:
        v = pd.to_numeric(pd.Series([r[c]]), errors="coerce").iloc[0]
        if pd.notna(v):
            out[c] = float(v)
    return out


def _used_header_rows(data):
    rows = set()
    for t in data["tables"].values():
        m = re.match(r"^[A-Z]+(\d+):", t["range"])
        if m:
            rows.add(int(m.group(1)))
    return rows


def _missing(what):
    theme.no_data(what)


def _caveats(wb, sheet):
    # Solo frases de verdad (no encabezados ni rótulos de tabla): al menos 6 espacios y 60 caracteres.
    notes = [t for t in long_texts(sheet, min_len=60)
             if any(w in t["text"][:90].lower() for w in CAVEAT_WORDS)
             and t["text"].count(" ") >= 6
             and not t["text"].lstrip(' "“&quot;').startswith(("Actúa como", "Genera"))]
    seen = set()
    for t in notes:
        if t["text"] in seen:
            continue
        seen.add(t["text"])
        theme.notice("Dato simulado o supuesto del libro: " + t["text"][:500], "warn")


def _texts_expander(wb, sheet):
    allt = long_texts(sheet, min_len=120)
    prompts = [t for t in allt if t["text"].lstrip(' "“&quot;').startswith(("Actúa como", "Genera"))]
    rest = [t for t in allt if t not in prompts]
    if rest:
        with st.expander(f"Textos del objetivo ({len(rest)})"):
            for t in rest:
                st.markdown(f'<div class="card">{t["text"]}</div>', unsafe_allow_html=True)
    if prompts:
        with st.expander(f"Instrucciones (prompts) usadas en el libro ({len(prompts)})"):
            for t in prompts:
                st.markdown(f'<div class="card">{t["text"]}</div>', unsafe_allow_html=True)


def _originals_tab(wb, sheet, data):
    used = _used_header_rows(data)
    extra = [t for t in generic_detect(wb, sheet) if t["row"] not in used]
    if extra:
        theme.notice(f"{len(extra)} tabla(s) no reconocida(s) por el esquema; se muestran aquí sin interpretar:", "warn")
        for t in extra:
            with st.expander(f"{t['title']} · {t['range']}"):
                st.dataframe(t["df"], use_container_width=True, hide_index=True)
    st.markdown("**Hoja completa (todas las tablas y cálculos, sin cambios):**")
    generic.render_sheet(wb, sheet)


def generic_detect(wb, sheet):  # tablas detectadas por encabezado, sin interpretar
    from core.xlsx_reader import detect_tables
    return detect_tables(wb, sheet)


def _kpi(data, token):
    for k in data["kpis"]:
        if norm(token) in norm(k["name"]):
            return k["value"]
    return None


def _fmt(v, pct=False):
    if isinstance(v, (int, float)):
        return f"{v:.1%}" if pct else f"{v:,.2f}"
    return "No disponible" if v is None else str(v)


# ----------------------------------------------------------------- Objetivo 4
def render_obj4(wb, schema):
    spec = schema["modules"]["obj4"]
    sheet = wb.sheet(spec["sheet"])
    data = extract_module(wb, "obj4", schema)
    theme.page_header(data["title"], "Selección de herramienta, planificación MRP, proveedores y resultados.")
    if sheet is None:
        _missing("Hoja Desarrollo Obj. 4")
        return
    _caveats(wb, sheet)
    T = data["tables"]
    markers = [tuple(m) for m in spec.get("mrp_markers", [])]
    blocks = parse_blocks(sheet, markers)
    firme = T.get("semanas_firme", {}).get("df")
    total_firme = None
    if firme is not None:
        r = _row_series(firme, "Pedidos en firme")
        total_firme = sum(r.values()) if r else None

    theme.kpi_row([
        ("Herramienta seleccionada", str(_kpi(data, "Herramienta") or "No disponible"), "Dato del libro · selección AHP", "celeste"),
        ("MAPE del pronóstico", _fmt(_kpi(data, "MAPE"), pct=True), "Dato del libro · error % medio", ""),
        ("Órdenes a tiempo (AS-IS)", _fmt(_kpi(data, "Indicador AS-IS"), pct=True), "Indicador AS-IS del libro", "coral"),
        ("Pedidos en firme (total)", f"{total_firme:,.0f}" if total_firme else "No disponible",
         "Suma de semanas del horizonte", "verde"),
    ])

    tabs = st.tabs(["Selección de herramienta", "Datos de planificación", "Pronóstico de demanda",
                    "Planificación MRP", "Proveedores", "Resultados", "Tablas originales"])

    # 1. Selección de herramienta (AHP)
    with tabs[0]:
        alt = T.get("ahp_alt", {}).get("df")
        if alt is not None:
            alt = alt.copy()
            p = _c(alt, "Prioridad")
            if p:
                alt[p] = _num(alt[p])
                st.plotly_chart(plots.bars(alt, alt.columns[0], [p], title="Prioridad de cada herramienta (AHP)"),
                                use_container_width=True)
            theme.show_table(alt, "obj4_ahp_alternativas", title="Comparación MRP vs ROP (AHP)")
        else:
            _missing("Comparación AHP")
        pesos = T.get("ahp_pesos", {}).get("df")
        if pesos is not None:
            pesos = pesos.copy()
            w = _c(pesos, "Peso")
            if w:
                pesos[w] = _num(pesos[w])
                st.plotly_chart(plots.bars(pesos, pesos.columns[0], [w], title="Ponderación de los criterios"),
                                use_container_width=True)
            theme.show_table(pesos, "obj4_ahp_pesos", title="Criterios y ponderaciones")
        theme.notice("Pesos y prioridades tomados del libro (AHP). No se recalculan en el dashboard.", "info")

    # 2. Datos de planificación
    with tabs[1]:
        bom = T.get("bom", {}).get("df")
        if bom is not None:
            theme.show_table(bom, "obj4_bom", title="Árbol de producto (BOM) y parámetros por ítem")
            sf = _c(bom, "SF")
            ta = _c(bom, "TA")
            if sf and ta:
                b = bom[[bom.columns[0], sf, ta]].copy()
                b[sf] = _num(b[sf])
                b[ta] = _num(b[ta])
                b = b[b[sf].notna()]
                st.plotly_chart(plots.bars(b, bom.columns[0], [sf], title="Stock físico al inicio por ítem (unidades del ítem)"),
                                use_container_width=True)
                st.caption("Tiempo de atención (TA) por ítem: " + ", ".join(
                    f"{r[bom.columns[0]]}: {r[ta]:g} sem" for _, r in b.iterrows() if pd.notna(r[ta])))
        else:
            _missing("BOM / parámetros por ítem")
        if firme is not None:
            theme.show_table(firme, "obj4_pedidos_firme", title="Pedidos en firme y factor de campaña por semana")
            r = _row_series(firme, "Pedidos en firme")
            if r:
                df = pd.DataFrame({"Semana": list(r.keys()), "Pedidos en firme": list(r.values())})
                st.plotly_chart(plots.bars(df, "Semana", ["Pedidos en firme"], title="Pedidos en firme por semana (unidades)"),
                                use_container_width=True)

    # 3. Pronóstico
    with tabs[2]:
        h = T.get("historia", {}).get("df")
        if h is not None:
            h = h.copy()
            for c in h.columns[1:]:
                h[c] = _num(h[c])
            dem, fc = _c(h, "Demanda real"), _c(h, "Pronóstico")
            if dem and fc:
                st.plotly_chart(plots.lines(h, h.columns[0], [dem, fc], title="Demanda real vs pronóstico (unidades)"),
                                use_container_width=True)
            err = _c(h, "Error")
            if err:
                st.plotly_chart(plots.bars(h, h.columns[0], [err], title="Error por periodo (unidades)"),
                                use_container_width=True)
            theme.show_table(h, "obj4_historia", title="Historia de demanda, pronóstico y error")
            theme.notice("Columnas tomadas del libro (suavizado exponencial). El error sigue la fórmula de la hoja.", "info")
        else:
            _missing("Historia de demanda")
        theme.kpi_row([("MAD (unidades)", _fmt(_kpi(data, "MAD")), "Dato del libro", ""),
                       ("MAPE", _fmt(_kpi(data, "MAPE"), pct=True), "Dato del libro", "coral")])

    # 4. Planificación MRP
    with tabs[3]:
        if not blocks:
            _missing("Bloques MRP por insumo")
        else:
            scen = list(dict.fromkeys(b["scenario"] for b in blocks))
            sc_sel = st.selectbox("Escenario", scen, key="obj4_scen")
            names = [b["name"] for b in blocks if b["scenario"] == sc_sel]
            sel = st.selectbox("Insumo / producto", names, key="obj4_item")
            b = next(x for x in blocks if x["scenario"] == sc_sel and x["name"] == sel)
            st.caption(f"{b['ta']} · escenario {sc_sel} · unidades según la hoja (ver etiquetas de fila)")
            t = b["table"].copy()
            t.columns = [f"Sem {c}" for c in t.columns]
            theme.show_table(t.reset_index().rename(columns={"index": "Concepto"}), f"obj4_mrp_{sc_sel}_{sel[:20]}",
                             title=f"MRP · {sel}")
            wk = pd.DataFrame(t.T.values, columns=list(t.index))
            wk.insert(0, "Semana", list(t.columns))
            cons = next((c for c in wk.columns if "consumo" in norm(c) or "demanda bruta" in norm(c)), None)
            lleg = next((c for c in wk.columns if "llegadas" in norm(c)), None)
            inv = next((c for c in wk.columns if "inventario final" in norm(c)), None)
            bars_cols = [c for c in [cons, lleg] if c]
            if bars_cols:
                for c in bars_cols:
                    wk[c] = _num(wk[c])
                st.plotly_chart(plots.bars(wk, "Semana", bars_cols, title=f"Necesidades y llegadas · {sel}"),
                                use_container_width=True)
            if inv:
                wk[inv] = _num(wk[inv])
                st.plotly_chart(plots.lines(wk, "Semana", [inv], title=f"Inventario final proyectado · {sel}"),
                                use_container_width=True)
        pmp = T.get("pmp", {}).get("df")
        if pmp is not None:
            theme.show_table(pmp, "obj4_pmp", title="Plan maestro de producción (PMP) por semana")
            dem = _row_series(pmp, "Demanda usada")
            pl = _row_series(pmp, "PMP")
            if dem and pl:
                df = pd.DataFrame({"Semana": list(dem.keys()), "Demanda usada": list(dem.values()),
                                   "PMP": [pl.get(k) for k in dem]})
                st.plotly_chart(plots.lines(df, "Semana", ["Demanda usada", "PMP"],
                                            title="Demanda usada vs PMP (unidades de producto)"),
                                use_container_width=True)

    # 5. Proveedores
    with tabs[4]:
        oc = T.get("oc", {}).get("df")
        if oc is not None:
            oc = oc.copy()
            ret = _c(oc, "Retraso")
            if ret:
                oc[ret] = _num(oc[ret])
            ok_col = _c(oc, "¿Recibida a tiempo")
            ord_rows = oc[oc[ok_col].isin(["Sí", "No"])] if ok_col else oc.iloc[0:0]
            if len(ord_rows) and ret:
                fig_df = ord_rows[[ord_rows.columns[0], ret]].copy()
                st.plotly_chart(plots.bars(fig_df, fig_df.columns[0], [ret],
                                           title="Retraso por orden de compra (semanas, AS-IS)"),
                                use_container_width=True)
                emitidas, a_tiempo = len(ord_rows), int((ord_rows[ok_col] == "Sí").sum())
                st.caption(f"Cálculo del dashboard sobre la tabla: {a_tiempo} de {emitidas} órdenes recibidas a tiempo "
                           f"({a_tiempo / emitidas:.0%}). Coincide con el indicador del libro cuando el conteo es el mismo.")
            theme.show_table(oc, "obj4_oc", title="Órdenes de compra: fecha prometida vs fecha real")
        else:
            _missing("Órdenes de compra")
        oi = T.get("oc_insumo", {}).get("df")
        if oi is not None:
            theme.show_table(oi, "obj4_oc_insumo", title="Órdenes de compra por insumo")
        od = T.get("oc_detalle", {}).get("df")
        if od is not None:
            cols = [c for c in od.columns if "a tiempo" in norm(c)]
            if cols:
                num = od.copy()
                for c in cols:
                    num[c] = _num(num[c])
                st.plotly_chart(plots.bars(num, num.columns[0], cols,
                                           title="Órdenes recibidas a tiempo por insumo: AS-IS vs TO-BE"),
                                use_container_width=True)
            theme.show_table(od, "obj4_oc_detalle", title="Detalle de órdenes a tiempo por insumo")

    # 6. Resultados
    with tabs[5]:
        res = T.get("resultados", {}).get("df")
        if res is not None:
            st.dataframe(dashboards._style_semaforo(res), use_container_width=True, hide_index=True)
            st.caption("Semáforo tomado del libro: VERDE cumple el estándar; AMARILLO no lo cumple, pero está cerca.")
        g = T.get("grafico", {}).get("df")
        if g is not None:
            gg = g.copy()
            for c in gg.columns[1:]:
                gg[c] = _num(gg[c])
            st.plotly_chart(plots.bars(gg, gg.columns[0], list(gg.columns[1:]),
                                       title="AS-IS vs TO-BE vs estándar"),
                            use_container_width=True)
            theme.show_table(g, "obj4_grafico", title="Datos del gráfico AS-IS vs TO-BE vs estándar")
        rot = T.get("roturas", {}).get("df")
        if rot is not None:
            theme.show_table(rot, "obj4_roturas", title="Roturas de stock por insumo (semanas con faltante)")
        apo = T.get("aporte", {}).get("df")
        if apo is not None:
            theme.show_table(apo, "obj4_aporte", title="Aporte del MRP y del seguimiento a proveedor (pp)")
        lc = T.get("lit_comp", {}).get("df")
        if lc is not None:
            theme.show_table(lc, "obj4_lit_comp", title="Comparación con la literatura y el estándar")
        lit = T.get("lit", {}).get("df")
        if lit is not None:
            theme.show_table(lit, "obj4_lit", title="Comparación AS-IS con la literatura")

    with tabs[6]:
        _originals_tab(wb, sheet, data)
    _texts_expander(wb, sheet)


# ----------------------------------------------------------------- Objetivo 5
def render_obj5(wb, schema):
    spec = schema["modules"]["obj5"]
    sheet = wb.sheet(spec["sheet"])
    data = extract_module(wb, "obj5", schema)
    theme.page_header(data["title"], "Diagnóstico, pronóstico, política lote por lote, inventario y resultados.")
    if sheet is None:
        _missing("Hoja Desarrollo Obj. 5")
        return
    _caveats(wb, sheet)
    T = data["tables"]
    theme.kpi_row([(k["name"], _fmt(k["value"]) if not isinstance(k["value"], str) else k["value"],
                    "Dato del libro · simulado", "coral" if i == 0 else "") for i, k in enumerate(data["kpis"])])

    tabs = st.tabs(["Diagnóstico y parámetros", "Pronóstico", "Política lote por lote",
                    "Inventario AS-IS vs TO-BE", "Indicadores", "Impacto económico", "Tablas originales"])

    with tabs[0]:
        ven = T.get("ventas", {}).get("df")
        if ven is not None:
            v = ven.copy()
            vcol = _c(v, "Ventas")
            icol = _c(v, "Inventario promedio")
            for c in v.columns[1:]:
                v[c] = _num(v[c])
            if vcol and icol:
                fig = plots.bars(v, v.columns[0], [vcol], title="Ventas e inventario promedio (S/)")
                fig.add_scatter(name=icol, x=v[v.columns[0]], y=v[icol], mode="lines+markers")
                st.plotly_chart(fig, use_container_width=True)
            theme.show_table(ven, "obj5_ventas", title="Ventas, inventario y rotación (periodo mensual)")
        else:
            _missing("Ventas e inventario")
        dr = T.get("datos_reales", {}).get("df")
        if dr is not None:
            theme.show_table(dr, "obj5_datos_reales", title="Datos reales de Mirsa vs referencia")
        ahp = T.get("ahp_alt", {}).get("df")
        if ahp is not None:
            theme.show_table(ahp, "obj5_ahp", title="Selección de la herramienta (AHP)")

    with tabs[1]:
        pr = T.get("pronostico", {}).get("df")
        if pr is not None:
            p = pr.copy()
            real, fc = _c(p, "Venta real"), _c(p, "Pronóstico")
            for c in p.columns[1:]:
                p[c] = _num(p[c])
            if real and fc:
                st.plotly_chart(plots.lines(p, p.columns[0], [real, fc], title="Venta real vs pronóstico (S/)"),
                                use_container_width=True)
            e = _c(p, "Error (%)")
            if e:
                st.plotly_chart(plots.bars(p, p.columns[0], [e], title="Error % por mes", yfmt=".0%"),
                                use_container_width=True)
            theme.show_table(pr, "obj5_pronostico", title="Ventas históricas, pronóstico y error")
            theme.notice("Columnas tomadas del libro. Pronóstico: promedio móvil de 3 meses (según la hoja).", "info")
        else:
            _missing("Pronóstico")

    with tabs[2]:
        mrp = T.get("mrp", {}).get("df")
        if mrp is not None:
            m = mrp.copy()
            bruta, neta = _c(m, "Necesidad bruta"), _c(m, "Necesidad neta")
            for c in m.columns[1:]:
                m[c] = _num(m[c])
            if bruta and neta:
                st.plotly_chart(plots.bars(m, m.columns[0], [bruta, neta], title="Necesidad bruta vs neta (S/)"),
                                use_container_width=True)
            theme.show_table(mrp, "obj5_mrp", title="Política lote por lote: necesidades, stock y órdenes")
        else:
            _missing("Política lote por lote")

    with tabs[3]:
        inv = T.get("inventario", {}).get("df")
        if inv is not None:
            i2 = inv.copy()
            for c in i2.columns[1:]:
                i2[c] = _num(i2[c])
            asis, obj = _c(i2, "Inventario As-Is"), _c(i2, "Stock objetivo")
            if asis and obj:
                st.plotly_chart(plots.lines(i2, i2.columns[0], [asis, obj],
                                            title="Inventario AS-IS vs stock objetivo con lote por lote (S/)"),
                                use_container_width=True)
            exc, red = _c(i2, "Exceso"), _c(i2, "Reducción")
            if exc and red:
                st.plotly_chart(plots.bars(i2, i2.columns[0], [exc, red], title="Excedente y reducción lograda (S/)"),
                                use_container_width=True)
            theme.show_table(inv, "obj5_inventario", title="Evolución mensual: inventario, stock objetivo y excedente")
        else:
            _missing("Inventario AS-IS vs TO-BE")

    with tabs[4]:
        ind = T.get("indicadores", {}).get("df")
        if ind is not None:
            theme.show_table(ind, "obj5_indicadores", title="Vejez, rotación, excedente y brecha")
        ven = T.get("ventas", {}).get("df")
        if ven is not None:
            rc = _c(ven, "Rotación")
            if rc:
                r = ven.copy()
                r[rc] = _num(r[rc])
                st.plotly_chart(plots.lines(r, r.columns[0], [rc], title="Rotación mensual (veces/mes)"),
                                use_container_width=True)
        lit = T.get("literatura", {}).get("df")
        if lit is not None:
            theme.show_table(lit, "obj5_literatura", title="Referencia de la literatura (EOQ = 100 %)")
            ll = lit.copy()
            for c in ll.columns[1:]:
                ll[c] = _num(ll[c])
            cols = [c for c in ll.columns[1:] if c in ("Antes", "Después")]
            if cols:
                st.plotly_chart(plots.bars(ll, ll.columns[0], cols, title="Inventario promedio: antes vs después (EOQ = 100 %)",
                                           yfmt=".0%"), use_container_width=True)

    with tabs[5]:
        eco = T.get("economia", {}).get("df")
        if eco is not None:
            e = eco.copy()
            mcol = _c(e, "Monto")
            if mcol:
                e[mcol] = _num(e[mcol])
                d = e[e[mcol].notna()]
                st.plotly_chart(plots.bars(d, d.columns[0], [mcol], title="Componentes económicos (S/)", horizontal=True),
                                use_container_width=True)
            theme.show_table(eco, "obj5_economia", title="Mermas, ahorro, inversión, costos y beneficio neto")
            theme.notice("Mermas simuladas según el libro; la fórmula de cada concepto está en la columna «Cálculo / supuesto».", "warn")
        else:
            _missing("Impacto económico")

    with tabs[6]:
        _originals_tab(wb, sheet, data)
    _texts_expander(wb, sheet)
