"""Empresa y diagnóstico: presentación, problemática, brechas, causa raíz, tabla resumen y base de datos."""
import streamlit as st

from core.xlsx_reader import chart_values
from ui import generic, plots, theme


def _sheet_tab(wb, name):
    s = wb.sheet(name)
    if s is None:
        theme.no_data(f"Hoja «{name}»")
        return
    generic.render_sheet(wb, s)


def render(wb, schema=None):
    theme.page_header("Empresa y diagnóstico", "Presentación, problemática identificada, brechas y análisis de causa raíz.")
    names = ["Empresa", "Problematica", "Brecha Problema 2", "Brecha Problema 3", "Brecha Problema 4",
             "Analisis Causa-Raiz", "Tabla Resumen", "Base de datos"]
    labels = ["Presentación", "Problemática", "Brecha P2", "Brecha P3", "Brecha P4",
              "Causa raíz", "Tabla resumen", "Base de datos"]
    tabs = st.tabs(labels)
    for tab, name, label in zip(tabs, names, labels):
        with tab:
            if name == "Tabla Resumen":
                _tabla_resumen(wb)
            else:
                _sheet_tab(wb, name)


def _tabla_resumen(wb):
    s = wb.sheet("Tabla Resumen")
    if s is None:
        theme.no_data("Tabla Resumen")
        return
    res = wb.read_table(s, "Impacto económico anual (S/)")
    if res:
        df, rng = res
        theme.show_table(df, "tabla_resumen", title=f"Impacto económico por problema · {rng}")
    for ch in [c for c in wb.charts if c["sheet"] == s.name]:
        cv = chart_values(wb, ch)
        st.plotly_chart(plots.from_chart_values(cv), use_container_width=True)
    theme.notice("Los valores «Valor esperado» corresponden a la referencia del libro para cada problema; "
                 "el impacto es el de la hoja, no un cálculo del dashboard.", "info")
