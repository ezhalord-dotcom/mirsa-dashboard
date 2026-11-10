"""
Extrae los datos de cada objetivo usando config/schema.yaml. No importa Streamlit ni Plotly.
Devuelve un dict con KPIs, tablas y advertencias (bloques no encontrados).
"""
from __future__ import annotations

import yaml
from pathlib import Path

from core.xlsx_reader import Workbook


def load_schema(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_module(wb: Workbook, module_id: str, schema: dict) -> dict:
    spec = schema["modules"].get(module_id)
    out = {"id": module_id, "title": "", "kpis": [], "tables": {}, "warnings": [], "sheet_found": False}
    if not spec:
        out["warnings"].append(f"No hay esquema para el módulo '{module_id}'.")
        return out
    out["title"] = spec.get("title", module_id)
    sheet = wb.sheet(spec["sheet"])
    if sheet is None:
        out["warnings"].append(f"No se encontró la hoja '{spec['sheet']}' en el libro.")
        return out
    out["sheet_found"] = True

    for key, blk in (spec.get("blocks") or {}).items():
        res = wb.read_table(sheet, blk["header"], occurrence=blk.get("occurrence", 1),
                            max_rows=blk.get("max_rows", 300))
        if res is None:
            out["warnings"].append(f"Bloque '{key}': no se encontró el encabezado «{blk['header']}».")
            continue
        df, rng = res
        out["tables"][key] = {"df": df, "range": rng}

    for kpi in spec.get("kpis") or []:
        val = wb.value_right_of(sheet, kpi["label"])
        if val is None:
            out["warnings"].append(f"KPI «{kpi['label']}»: no se encontró valor a la derecha.")
        out["kpis"].append({"name": kpi.get("name", kpi["label"]), "value": val})

    if spec.get("umbrales"):
        u = {}
        for k, label in spec["umbrales"].items():
            u[k] = wb.value_right_of(sheet, label)
        out["umbrales"] = u
    return out
