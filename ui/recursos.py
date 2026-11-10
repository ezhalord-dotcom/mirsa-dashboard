"""Imágenes del Excel dentro de cada sección: miniaturas por hoja, ampliación y descarga del original."""
from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from core import imagenes
from core.textnorm import norm
from ui import theme

ROOT = Path(__file__).resolve().parent.parent


def _mapping() -> dict:
    f = ROOT / "config" / "imagenes.yaml"
    return yaml.safe_load(f.read_text(encoding="utf-8")) or {} if f.exists() else {}


def panel(section_id: str, catalog: dict | None = None):
    cat = catalog or imagenes.load()
    if not cat:
        return
    spec = _mapping().get(section_id)
    if spec is None:
        return
    items = cat["imagenes"]
    if spec != "*":
        wanted = [norm(s) for s in spec]
        items = [e for e in items if norm(e["hoja"]) in wanted]
    if not items:
        return
    st.markdown("### Imágenes del libro")
    st.caption("Copia exacta de las imágenes del Excel, agrupadas por hoja de origen.")
    groups: dict[str, list] = {}
    for e in items:
        groups.setdefault(e["hoja"], []).append(e)
    for hoja, its in groups.items():
        with st.expander(f"{hoja} · {len(its)} imagen(es)", expanded=len(its) <= 6):
            cols = st.columns(2)
            for i, e in enumerate(its):
                with cols[i % 2]:
                    _thumb(e)
            _enlarge(section_id, hoja, its)


def _caption(e: dict) -> str:
    celda = e["celda"] or "posición no disponible"
    return f"{e['id']} · {e['hoja']} · imagen {e['numero_en_hoja']} · celda {celda}"


def _thumb(e: dict):
    path = imagenes.ASSETS / e["archivo"]
    if not path.exists():
        theme.notice(f"Archivo no encontrado ({e['archivo']}). Ve a Sincronización.", "warn")
        return
    if e["web"]:
        st.image(str(path), caption=_caption(e), use_container_width=True)
    else:
        theme.notice(f"{_caption(e)}: formato {e['formato'].upper()}, el navegador no lo muestra. Descárgalo abajo.", "warn")


def _enlarge(section_id: str, hoja: str, its: list):
    """Vista a tamaño completo de una imagen elegida, y descarga del original."""
    opts = {e["id"]: e for e in its}
    base = f"{section_id}_{norm(hoja).replace(' ', '_')}"
    with st.expander("Ver una imagen en tamaño completo o descargar el original"):
        pick = st.selectbox("Imagen", list(opts.keys()), key=f"amp_{base}", format_func=lambda k: _caption(opts[k]))
        e = opts[pick]
        path = imagenes.ASSETS / e["archivo"]
        if path.exists():
            if e["web"]:
                st.image(str(path), caption=_caption(e), use_container_width=True)
            st.download_button(f"⬇️ Descargar original ({e['formato'].upper()})", path.read_bytes(),
                               file_name=path.name, key=f"dl_img_{base}_{e['id']}")
