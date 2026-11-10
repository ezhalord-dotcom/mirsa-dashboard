"""Conclusiones y recomendaciones tal como están en el libro."""
from core.xlsx_reader import long_texts
from ui import theme
import streamlit as st


def render(wb, schema=None):
    theme.page_header("Conclusiones y recomendaciones", "Texto original de las hojas Conclusiones y Recomendaciones.")
    for name in ["Conclusiones", "Recomendaciones"]:
        s = wb.sheet(name)
        st.markdown(f"#### {name}")
        if s is None:
            theme.no_data(f"Hoja «{name}»")
            continue
        allt = long_texts(s, min_len=1)
        headings = [t for t in allt if t["text"].strip().endswith(":")]   # encabezados de sección
        texts = [t for t in allt if not t["text"].strip().endswith(":") and len(t["text"].strip()) >= 40]
        if not texts:
            theme.notice(f"La hoja «{name}» solo tiene encabezados ({len(headings)}). "
                         "El contenido de las conclusiones/recomendaciones no está en el libro; "
                         "no se inventa texto. Agrégalo en el Excel y se mostrará aquí.", "warn")
        for t in texts:
            st.markdown(f'<div class="card">{t["text"]}</div>', unsafe_allow_html=True)
