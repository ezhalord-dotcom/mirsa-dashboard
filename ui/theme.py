"""Tema visual (azul oscuro, celeste, blanco, acentos coral y verde) y componentes reutilizables."""
import html as _html

import streamlit as st

CSS = """
<style>
:root{--navy:#1B2A41;--navy2:#243A5E;--celeste:#CFE8F3;--coral:#F28B6B;--verde:#4CAF7A;
      --texto:#1B2A41;--muted:#5B6B7F;--card:#FFFFFF;--bg:#EEF5F9;}
.stApp{background:var(--bg);}
.block-container{padding-top:1.2rem;max-width:1400px;}
[data-testid="stSidebar"]{background:var(--navy);}
[data-testid="stSidebar"] *{color:#E8F1F8 !important;}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:6px 10px;border-radius:10px;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:var(--navy2);}
h1,h2,h3{color:var(--texto);}
.topbar{background:#fff;border-radius:14px;padding:12px 18px;box-shadow:0 2px 10px rgba(27,42,65,.08);
        display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px;}
.topbar .brand{font-weight:700;color:var(--navy);font-size:18px;}
.topbar .brand span{color:var(--coral);}
.kpi{background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(27,42,65,.08);margin-bottom:12px;}
.kpi .band{background:var(--navy);color:#fff;font-size:12px;letter-spacing:.06em;text-transform:uppercase;padding:8px 14px;}
.kpi .val{font-size:26px;font-weight:700;color:var(--texto);padding:12px 14px 2px;word-break:break-word;}
.kpi .sub{font-size:12px;color:var(--muted);padding:0 14px 12px;}
.kpi.coral .band{background:var(--coral);} .kpi.verde .band{background:var(--verde);}
.kpi.celeste .band{background:#2E86AB;}
.card{background:#fff;border-radius:14px;padding:16px 18px;box-shadow:0 2px 10px rgba(27,42,65,.08);margin-bottom:14px;}
.card h4{margin:0 0 8px 0;color:var(--navy);}
.notice{border-radius:10px;padding:10px 14px;margin:8px 0;font-size:14px;}
.notice.warn{background:#FFF4E5;border-left:4px solid var(--coral);}
.notice.info{background:#E8F4FB;border-left:4px solid #2E86AB;}
.notice.ok{background:#E9F7EF;border-left:4px solid var(--verde);}
.pill{display:inline-block;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;}
.pill.verde{background:#C6EFCE;color:#135C2E;} .pill.amarillo{background:#FFEB9C;color:#6B5400;}
.pill.rojo{background:#FFC7CE;color:#7A1C25;} .pill.gris{background:#E4EAF0;color:#44546A;}
@media (max-width: 768px){ .kpi .val{font-size:20px;} .topbar{flex-direction:column;align-items:flex-start;} }
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def topbar(search_placeholder="Buscar en el proyecto…"):
    st.markdown('<div class="topbar"><div class="brand">EXPORTACIONES MIRSA <span>· Dashboard de tesis</span></div>'
                '<div class="sub" style="color:#5B6B7F;font-size:13px">Fuente única: el libro de Excel</div></div>',
                unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    st.markdown(f"## {_html.escape(title)}")
    if subtitle:
        st.caption(subtitle)


def kpi_html(label, value, sub="", tone=""):
    return (f'<div class="kpi {tone}"><div class="band">{_html.escape(str(label))}</div>'
            f'<div class="val">{_html.escape(str(value))}</div>'
            f'<div class="sub">{_html.escape(str(sub))}</div></div>')


def kpi_row(items: list[tuple]):
    """items: (etiqueta, valor, subtítulo, tono)"""
    cols = st.columns(min(4, len(items)))
    for i, it in enumerate(items):
        label, value = it[0], it[1]
        sub = it[2] if len(it) > 2 else ""
        tone = it[3] if len(it) > 3 else ""
        cols[i % len(cols)].markdown(kpi_html(label, value, sub, tone), unsafe_allow_html=True)


def notice(text: str, kind: str = "info"):
    st.markdown(f'<div class="notice {kind}">{_html.escape(text)}</div>', unsafe_allow_html=True)


def no_data(what: str):
    notice(f"{what}: no hay datos en el libro (hoja vacía o etiqueta no encontrada).", "warn")


def show_table(df, key: str, title: str | None = None):
    if title:
        st.markdown(f"**{_html.escape(title)}**")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Descargar tabla (CSV)", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{key}.csv", mime="text/csv", key=f"dl_{key}")
