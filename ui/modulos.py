"""Módulos de objetivo. Cada objetivo tiene su propia vista, sus tablas originales y sus avisos."""
import streamlit as st

from core.modules import extract_module
from core.xlsx_reader import chart_values, long_texts
from ui import analitica, dashboards, generic, plots, theme

# Objetivos con dashboard analítico propio (pestañas + tablas originales al final).
ANALYTIC = {"obj4": analitica.render_obj4, "obj5": analitica.render_obj5}


def render(wb, schema, module_id: str):
    spec = schema["modules"][module_id]
    sheet = wb.sheet(spec["sheet"])
    if sheet is None:
        theme.no_data(f"Hoja «{spec['sheet']}»")
        return
    if module_id in ANALYTIC:
        ANALYTIC[module_id](wb, schema)
        return
    if module_id in dashboards.MODULE_RENDERERS:
        dashboards.MODULE_RENDERERS[module_id](wb, schema)
    else:
        _generic_module(wb, schema, module_id, sheet)

    allt = long_texts(sheet, min_len=120)
    def _clean(x):
        return x.replace("&quot;", '"').lstrip(' "“')
    prompts = [t for t in allt if _clean(t["text"]).startswith(("Actúa como", "Genera un", "Genera "))]
    texts = [t for t in allt if t not in prompts]
    CAVEAT_WORDS = ("simulad", "supuesto", "datos reales")
    notes = [t for t in long_texts(sheet, min_len=20) if t not in prompts]
    sim = [t for t in notes if any(w in t["text"][:80].lower() for w in CAVEAT_WORDS)]
    for t in sim:
        theme.notice("Aviso del libro: " + t["text"][:400], "warn")
    rest = [t for t in texts if t not in sim]
    if rest:
        with st.expander(f"Textos del objetivo ({len(rest)})"):
            for t in rest:
                st.markdown(f'<div class="card">{t["text"]}</div>', unsafe_allow_html=True)
    if prompts:
        with st.expander(f"Instrucciones (prompts) usadas en el libro ({len(prompts)})"):
            for t in prompts:
                st.markdown(f'<div class="card">{t["text"]}</div>', unsafe_allow_html=True)
    charts = [c for c in wb.charts if c["sheet"] == sheet.name]
    if charts:
        with st.expander(f"Gráficos del libro ({len(charts)})", expanded=False):
            cols = st.columns(2)
            for i, ch in enumerate(charts):
                cv = chart_values(wb, ch)
                with cols[i % 2]:
                    st.plotly_chart(plots.from_chart_values(cv), use_container_width=True)
    with st.expander("Hoja original completa (tablas y cálculos)"):
        generic.render_sheet(wb, sheet)


def _generic_module(wb, schema, module_id, sheet):
    data = extract_module(wb, module_id, schema)
    theme.page_header(data["title"], "Vista del objetivo construida con los datos del libro.")
    cards = []
    for k in data["kpis"]:
        v = k["value"]
        if v is None:
            cards.append((k["name"], "No disponible", "Etiqueta no encontrada en el libro", ""))
        else:
            cards.append((k["name"], str(v), "Dato del libro", ""))
    if cards:
        theme.kpi_row(cards)
    for w in data["warnings"]:
        theme.notice(w, "warn")
