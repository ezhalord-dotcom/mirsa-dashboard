"""Página de estado de sincronización con el Excel."""
import pandas as pd
import streamlit as st


def render(read_at: str, md5: str, source: str, changes: list[str], status_rows: list[dict]):
    st.header("Estado de sincronización")
    c1, c2, c3 = st.columns(3)
    c1.metric("Última lectura", read_at)
    c2.metric("Archivo", source.split("/")[-1])
    c3.metric("Huella (MD5)", md5[:12])
    st.subheader("Cambios respecto a la lectura anterior")
    for m in changes:
        st.write("• " + m)
    st.subheader("Hojas del libro")
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
    st.caption("Las hojas que dicen 'No (Otras hojas)' aparecen en el menú bajo 'Otras hojas' sin error.")
