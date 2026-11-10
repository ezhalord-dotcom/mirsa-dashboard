"""
Mirsa · Dashboard de tesis (Streamlit).
El Excel es la única fuente de verdad. Ejecutar:  streamlit run app.py
"""
import os
from pathlib import Path

import streamlit as st
import yaml

from core.modules import load_schema
from core.sync import load_source, sheet_status
from ui import (recursos, theme, home, diagnostico, modulos, resultados, economia,
                conclusiones, explorador, sync_page, dashboards)

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SOURCE_DIR = DATA / "source"
SCHEMA = load_schema(ROOT / "config" / "schema.yaml")
NAV = yaml.safe_load(open(ROOT / "config" / "menu.yaml", encoding="utf-8"))["sections"]

st.set_page_config(page_title="Mirsa · Dashboard de tesis", layout="wide", page_icon="📦")
theme.inject()


def default_source() -> Path | None:
    env = os.environ.get("MIRSA_XLSX")
    if env and Path(env).exists():
        return Path(env)
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    xs = sorted(SOURCE_DIR.glob("*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return xs[0] if xs else None


@st.cache_resource(show_spinner="Leyendo el Excel…")
def get_source(path: str, token: int, force: bool):
    return load_source(path, DATA, force=force)


# ------------------------------------------------------------ barra lateral
with st.sidebar:
    st.markdown("### 📦 Mirsa")
    st.caption("Dashboard de tesis · fuente: Excel")
    up = st.file_uploader("Subir nueva versión del .xlsx", type=["xlsx"])
    if up is not None:
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        (SOURCE_DIR / "AvanceT3G55X.xlsx").write_bytes(up.getbuffer())
        st.session_state["token"] = st.session_state.get("token", 0) + 1
        st.success("Versión nueva guardada.")
    if st.button("🔄 Recargar desde el Excel", use_container_width=True):
        st.session_state["token"] = st.session_state.get("token", 0) + 1
        st.session_state["force"] = True

src = default_source()
if src is None:
    st.error("No encuentro el Excel. Súbelo en la barra lateral o copia el .xlsx en data/source/.")
    st.stop()

token = st.session_state.get("token", 0)
force = st.session_state.pop("force", False)
sync = get_source(str(src), token, force)
wb = sync.wb

with st.sidebar:
    labels = [f"{s['icon']}  {s['label']}" for s in NAV]
    choice = st.radio("Navegación", labels, label_visibility="collapsed")
    section = NAV[labels.index(choice)]
    st.caption(f"Última lectura: {wb.read_at}")

# ------------------------------------------------------------ barra superior y búsqueda
theme.topbar()
query = st.text_input("Buscar en todo el proyecto", placeholder="Ej.: rotación, ABC, IRA, ROP…",
                      label_visibility="collapsed", key="q")
if query.strip():
    explorador.search_results(wb, query.strip())
    st.stop()

# ------------------------------------------------------------ enrutado
view = section["view"]
if view == "home":
    home.render(wb, SCHEMA)
elif view == "diagnostico":
    diagnostico.render(wb)
elif view == "ahp":
    s = wb.sheet(section["sheet"])
    theme.page_header("Selección de problemas (AHP)", "Criterios, comparaciones por pares y ponderaciones del libro.")
    if s is None:
        theme.no_data("Hoja Matriz AHP")
    else:
        from ui import generic
        generic.render_sheet(wb, s)
elif view == "module":
    modulos.render(wb, SCHEMA, section["module"])
elif view == "resultados":
    resultados.render(wb, SCHEMA)
elif view == "economia":
    economia.render(wb, SCHEMA)
elif view == "conclusiones":
    conclusiones.render(wb)
elif view == "explorador":
    explorador.render(wb)
elif view == "sync":
    known = [{"sheet": s["sheet"]} for s in NAV if "sheet" in s]
    known += [{"sheet": m["sheet"]} for m in SCHEMA["modules"].values()]
    known += [{"sheet": n} for n in ["Empresa", "Problematica", "Brecha Problema 2", "Brecha Problema 3",
                                     "Brecha Problema 4", "Analisis Causa-Raiz", "Tabla Resumen",
                                     "Base de datos", "Planteamiento ", "Resultados-Indicadores",
                                     "Conclusiones", "Recomendaciones", "Flujo Caja", "EOp", "EPr ", "Indice", "Carátula"]]
    sync_page.render(wb.read_at, wb.md5, str(src), sync.changes, sheet_status(wb, known))

# ------------------------------------------------------------ imágenes del libro por sección
if view != "sync":
    recursos.panel(section["id"])
