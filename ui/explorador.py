"""Explorador: todas las hojas del libro con su nombre original, y búsqueda en todo el libro."""
import streamlit as st

from core.xlsx_reader import Workbook
from ui import generic, theme


def render(wb: Workbook):
    theme.page_header("Explorador de hojas", "Todas las hojas del Excel con su nombre original y su contenido completo.")
    names = list(wb.sheets)
    choice = st.selectbox("Hoja", names, format_func=lambda n: n.strip(), key="explorer_sheet")
    generic.render_sheet(wb, wb.sheets[choice])


def search_results(wb: Workbook, query: str):
    theme.page_header(f"Resultados para «{query}»")
    hits = wb.search(query, limit=80)
    if not hits:
        theme.notice("No se encontró ese texto en ninguna hoja del libro.", "info")
        return
    st.caption(f"{len(hits)} coincidencias (máximo 80).")
    for sheet, cell, text in hits:
        st.markdown(f"**{sheet}** · celda {cell}: {text}")
