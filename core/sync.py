"""
Sincronización: lee el Excel solo si cambió (MD5), guarda la lectura anterior y
genera el resumen de cambios. No importa Streamlit.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.xlsx_reader import read_workbook, compact_snapshot, diff_snapshots, file_md5, Workbook
from core.textnorm import norm


class SyncResult:
    def __init__(self, wb: Workbook, changes: list[str], reloaded: bool, md5: str):
        self.wb = wb
        self.changes = changes
        self.reloaded = reloaded
        self.md5 = md5


def _sync_images(path, assets_dir):
    """Extrae las imágenes del libro y reemplaza las de versiones anteriores (ver core/imagenes.py)."""
    from core import imagenes
    imagenes.sync(path, assets_dir or imagenes.ASSETS)


def load_source(path: str | Path, data_dir: str | Path, force: bool = False, assets_dir=None) -> SyncResult:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    state_file = data_dir / "state.json"
    last_file = data_dir / "last_snapshot.json"
    md5 = file_md5(path)
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}

    if not force and state.get("md5") == md5 and state.get("changes") is not None:
        wb = read_workbook(path)  # rápido: solo celdas y XML
        _sync_images(path, assets_dir)
        return SyncResult(wb, state.get("changes", []), False, md5)

    prev = json.loads(last_file.read_text(encoding="utf-8")) if last_file.exists() else None
    wb = read_workbook(path)
    _sync_images(path, assets_dir)
    cur = compact_snapshot(wb)
    changes = diff_snapshots(prev, cur)
    last_file.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8")
    state_file.write_text(json.dumps({"md5": md5, "read_at": wb.read_at, "changes": changes,
                                      "path": str(path)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return SyncResult(wb, changes, True, md5)


def sheet_status(wb: Workbook, menu_items: list[dict]) -> list[dict]:
    """Tabla por hoja para la página de estado de sincronización."""
    from core.xlsx_reader import detect_tables
    rows = []
    menu_keys = {norm(i["sheet"]): i for i in menu_items}
    for name, sd in wb.sheets.items():
        tables = detect_tables(wb, sd)
        rows.append({
            "Hoja": name.rstrip(),
            "En menú": "Sí" if norm(name) in menu_keys else "No (Otras hojas)",
            "Tablas detectadas": len(tables),
            "Gráficos": sum(1 for c in wb.charts if c["sheet"] == name),
            "Imágenes": sum(1 for i in wb.images if i["sheet"] == name),
            "Fórmulas sin valor": len(sd.formulas_sin_valor),
            "Celdas con valor": sum(len(r) for r in sd.grid.values()),
        })
    for item in menu_items:
        if wb.sheet(item["sheet"]) is None:
            rows.append({"Hoja": item["sheet"].rstrip() + " (en menú, no existe)", "En menú": "Sí",
                         "Tablas detectadas": 0, "Gráficos": 0, "Imágenes": 0,
                         "Fórmulas sin valor": 0, "Celdas con valor": 0})
    return rows
