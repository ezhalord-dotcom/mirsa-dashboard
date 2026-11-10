"""Renderizado genérico de cualquier hoja: tablas detectadas, textos, gráficos e imágenes."""
import streamlit as st

from core.xlsx_reader import SheetData, Workbook, chart_values, detect_tables, long_texts
from ui import plots


def render_sheet(wb: Workbook, sheet: SheetData, title: str | None = None):
    st.header(title or sheet.name.strip())
    if sheet.formulas_sin_valor:
        st.warning(f"{len(sheet.formulas_sin_valor)} fórmulas sin valor guardado en esta hoja "
                   f"(ej.: {', '.join(sheet.formulas_sin_valor[:5])}). Abre el Excel, recalcula y guárdalo.")

    texts = long_texts(sheet)
    for t in texts:
        st.markdown(t["text"])

    charts = [c for c in wb.charts if c["sheet"] == sheet.name]
    if charts:
        st.subheader("Gráficos del libro")
        cols = st.columns(2)
        for i, ch in enumerate(charts):
            cv = chart_values(wb, ch)
            with cols[i % 2]:
                st.plotly_chart(plots.from_chart_values(cv), use_container_width=True)
                for w in cv["warnings"]:
                    st.caption(w)

    tables = detect_tables(wb, sheet)
    if tables:
        st.subheader("Tablas")
        for t in tables:
            with st.expander(f"{t['title']}  ·  {t['range']}", expanded=len(tables) <= 4):
                st.dataframe(t["df"], use_container_width=True, hide_index=True)

    imgs = [i for i in wb.images if i["sheet"] == sheet.name]
    if imgs:
        st.subheader(f"Imágenes ({len(imgs)})")
        grid = st.columns(3)
        for i, im in enumerate(imgs):
            if im.get("file") and im["ext"] in ("png", "jpg", "jpeg", "gif", "bmp"):
                grid[i % 3].image(im["file"], use_container_width=True)
            else:
                grid[i % 3].caption(f"Imagen {im['ext']} no mostrable: {im.get('media')}")

    if not (texts or charts or tables or imgs):
        st.info("Esta hoja no tiene tablas, textos, gráficos ni imágenes detectables.")
