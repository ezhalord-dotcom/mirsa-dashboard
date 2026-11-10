"""
Mirsa · Dashboard de tesis (Streamlit).
El Excel es la única fuente de verdad: la app lee el libro en cada cambio (MD5),
no tiene números escritos a mano y los bloques se buscan por etiqueta.

Ejecutar:  streamlit run app.py
"""
import os
from pathlib import Path

import streamlit as st
import yaml

from core.modules import load_schema
from core.sync import load_source, sheet_status
from core.textnorm import norm
from ui import dashboards, generic, sync_page

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SOURCE_DIR = DATA / "source"
SCHEMA = load_schema(ROOT / "config" / "schema.yaml")
MENU = yaml.safe_load(open(ROOT / "config" / "menu.yaml", encoding="utf-8"))

st.set_page_config(page_title="Mirsa · Tesis", layout="wide", page_icon="📦")


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


# ----------------------------------------------------------------- barra lateral
with st.sidebar:
    st.title("Mirsa · Tesis")
    st.caption("Fuente: el Excel. Cambia el libro y recarga; no hay que tocar el código.")

    up = st.file_uploader("Subir nueva versión del .xlsx", type=["xlsx"])
    if up is not None:
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        dest = SOURCE_DIR / "AvanceT3G55X.xlsx"
        dest.write_bytes(up.getbuffer())
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

if sync.reloaded:
    st.sidebar.info("Excel leído de nuevo. Cambios detectados: " + str(len(sync.changes)))

# ----------------------------------------------------------------- menú
menu_items = [dict(it, group=g["name"]) for g in MENU["groups"] for it in g["items"]]
pages = []
for g in MENU["groups"]:
    for it in g["items"]:
        if wb.sheet(it["sheet"]) is not None:
            title = it.get("title") or it["sheet"].strip()
            pages.append((f"{g['name']} › {title}", it))
menu_keys = {norm(i["sheet"]) for i in menu_items}
for s in wb.sheets:
    if norm(s) not in menu_keys:
        pages.append((f"Otras hojas › {s.strip()}", {"sheet": s, "view": "generic"}))
pages.append(("Sistema › Estado de sincronización", {"view": "sync"}))

labels = [p[0] for p in pages]
choice = st.sidebar.radio("Sección", labels, index=0)
item = dict(pages[labels.index(choice)][1])

# ----------------------------------------------------------------- contenido
if item.get("view") == "sync":
    sync_page.render(wb.read_at, wb.md5, str(src), sync.changes, sheet_status(wb, menu_items))
elif item.get("view") == "dashboard" and item.get("module") in dashboards.MODULE_RENDERERS:
    dashboards.MODULE_RENDERERS[item["module"]](wb, SCHEMA)
else:
    sheet = wb.sheet(item["sheet"])
    if sheet is None:
        st.error(f"La hoja «{item['sheet']}» no existe en el libro.")
    else:
        generic.render_sheet(wb, sheet)
