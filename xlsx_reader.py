"""
Lector del libro de Excel. No importa Streamlit ni Plotly: solo lee el archivo.

- Lee valores calculados (data_only=True) y detecta fórmulas sin valor guardado.
- Busca bloques por ETIQUETA (no por dirección de celda).
- Detecta tablas, textos largos, gráficos (XML) e imágenes (xl/media) de cada hoja.
- Compara dos lecturas para el panel de sincronización.
"""
from __future__ import annotations

import hashlib
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from core.textnorm import cell_ref, norm

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
}

CHART_KINDS = ["barChart", "lineChart", "pieChart", "doughnutChart", "scatterChart", "areaChart"]


def file_md5(path: str | Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class SheetData:
    name: str                       # nombre real de la hoja (puede tener espacios al final)
    key: str                        # nombre normalizado para buscar
    max_row: int = 0
    max_col: int = 0
    grid: dict = field(default_factory=dict)        # {row: {col: value}} solo celdas con valor
    formulas_sin_valor: list = field(default_factory=list)  # celdas con fórmula y sin valor guardado


@dataclass
class Workbook:
    path: str
    md5: str
    read_at: str
    sheets: dict                    # {name: SheetData}
    charts: list                    # lista de dicts (ver parse_charts)
    images: list                    # lista de dicts {sheet, row, col, file, md5}

    # ---------- búsqueda ----------
    def sheet(self, name_or_key: str) -> SheetData | None:
        k = norm(name_or_key)
        for s in self.sheets.values():
            if s.key == k:
                return s
        return None

    def find(self, sheet: SheetData, text: str, occurrence: int = 1):
        """Devuelve la celda (fila, col) de la n-ésima aparición de un texto (exacto y luego parcial)."""
        target = norm(text)
        hits = []
        for r in sorted(sheet.grid):
            for c in sorted(sheet.grid[r]):
                v = sheet.grid[r][c]
                if isinstance(v, str) and norm(v) == target:
                    hits.append((r, c))
        if not hits:
            for r in sorted(sheet.grid):
                for c in sorted(sheet.grid[r]):
                    v = sheet.grid[r][c]
                    if isinstance(v, str) and target and target in norm(v):
                        hits.append((r, c))
        return hits[occurrence - 1] if len(hits) >= occurrence else None

    def value_right_of(self, sheet: SheetData, label: str, occurrence: int = 1):
        """
        Para pares etiqueta -> valor: primer valor no vacío a la derecha de la etiqueta.
        Si una aparición de la etiqueta no tiene valor a la derecha, prueba la siguiente.
        """
        hits = self.find_all(sheet, label)
        for r, c in hits[occurrence - 1:] if occurrence > 1 else hits:
            row = sheet.grid.get(r, {})
            for j in sorted(k for k in row if k > c):
                return row[j]
        return None

    def find_all(self, sheet: SheetData, text: str) -> list:
        target = norm(text)
        exact = [(r, c) for r in sorted(sheet.grid) for c in sorted(sheet.grid[r])
                 if isinstance(sheet.grid[r][c], str) and norm(sheet.grid[r][c]) == target]
        if exact:
            return exact
        return [(r, c) for r in sorted(sheet.grid) for c in sorted(sheet.grid[r])
                if isinstance(sheet.grid[r][c], str) and target and target in norm(sheet.grid[r][c])]

    def read_table(self, sheet: SheetData, header_text: str, occurrence: int = 1,
                   max_rows: int = 300) -> tuple[pd.DataFrame, str] | None:
        """
        Lee una tabla a partir de su fila de encabezado.
        El encabezado se extiende a izquierda y derecha mientras haya celdas con valor en esa fila.
        Las filas se leen hasta la primera fila totalmente vacía (o hasta max_rows).
        """
        hit = self.find(sheet, header_text, occurrence)
        if not hit:
            return None
        r, c = hit
        head_row = sheet.grid.get(r, {})
        c0 = c
        while (c0 - 1) in head_row:
            c0 -= 1
        c1 = c
        while (c1 + 1) in head_row:
            c1 += 1
        cols = list(range(c0, c1 + 1))
        headers, seen = [], {}
        for j in cols:
            h = str(head_row.get(j, f"col{j}")).strip() or f"col{j}"
            seen[h] = seen.get(h, 0) + 1
            headers.append(h if seen[h] == 1 else f"{h} ({seen[h]})")
        rows, rr = [], r + 1
        while rr <= sheet.max_row and len(rows) < max_rows:
            vals = [sheet.grid.get(rr, {}).get(j) for j in cols]
            if all(v is None for v in vals):
                break
            rows.append(vals)
            rr += 1
        df = pd.DataFrame(rows, columns=headers)
        rng = f"{cell_ref(r, c0)}:{cell_ref(rr - 1, c1)}"
        return df, rng

    def values_of_range(self, ref: str) -> list | None:
        """Resuelve una referencia tipo 'Hoja'!$D$32:$D$38 usando las celdas leídas."""
        m = re.match(r"^'?(.*?)'?!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?$", ref or "")
        if not m:
            return None
        sheet = self.sheet(m.group(1))
        if sheet is None:
            return None  # p. ej. libros externos [8]...
        c_a, r_a = _col_num(m.group(2)), int(m.group(3))
        c_b, r_b = (_col_num(m.group(4)), int(m.group(5))) if m.group(4) else (c_a, r_a)
        out = []
        for r in range(r_a, r_b + 1):
            for c in range(c_a, c_b + 1):
                out.append(sheet.grid.get(r, {}).get(c))
        return out


def _col_num(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


# ---------------------------------------------------------------- lectura de celdas
def _read_cells(path: str) -> tuple[dict, dict]:
    sheets = {}
    wb_v = load_workbook(path, read_only=True, data_only=True)
    for ws in wb_v.worksheets:
        sd = SheetData(name=ws.title, key=norm(ws.title))
        for r_idx, row in enumerate(ws.iter_rows(min_row=1), start=1):
            for c_idx, cell in enumerate(row, start=1):
                v = cell.value
                if v is not None and v != "":
                    sd.grid.setdefault(r_idx, {})[c_idx] = v
                    sd.max_row = max(sd.max_row, r_idx)
                    sd.max_col = max(sd.max_col, c_idx)
        sheets[ws.title] = sd
    wb_v.close()

    # Segunda pasada: fórmulas sin valor guardado (la app no recalcula en silencio)
    wb_f = load_workbook(path, read_only=True, data_only=False)
    for ws in wb_f.worksheets:
        sd = sheets[ws.title]
        for r_idx, row in enumerate(ws.iter_rows(min_row=1), start=1):
            for c_idx, cell in enumerate(row, start=1):
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    if sd.grid.get(r_idx, {}).get(c_idx) is None:
                        sd.formulas_sin_valor.append(cell_ref(r_idx, c_idx))
    wb_f.close()
    return sheets, {}


# ---------------------------------------------------------------- XML: gráficos e imágenes
def _rels(z: zipfile.ZipFile, part: str) -> dict:
    d, base = posixpath.split(part)
    rel_path = posixpath.join(d, "_rels", base + ".rels")
    if rel_path not in z.namelist():
        return {}
    root = ET.fromstring(z.read(rel_path))
    out = {}
    for rel in root.findall("pr:Relationship", NS):
        target = rel.get("Target")
        if target.startswith("/"):
            full = target.lstrip("/")
        else:
            full = posixpath.normpath(posixpath.join(d, target))
        out[rel.get("Id")] = {"target": full, "type": rel.get("Type", "")}
    return out


def _sheet_parts(z: zipfile.ZipFile) -> dict:
    """{nombre de hoja: ruta xml de la hoja}"""
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = _rels(z, "xl/workbook.xml")
    out = {}
    for s in wb.find("m:sheets", NS):
        rid = s.get(f"{{{NS['r']}}}id")
        out[s.get("name")] = rels[rid]["target"]
    return out


def _chart_info(z: zipfile.ZipFile, chart_part: str) -> dict:
    root = ET.fromstring(z.read(chart_part))
    chart = root.find("c:chart", NS)
    title_el = chart.find("c:title", NS) if chart is not None else None
    title = "".join(t.text or "" for t in title_el.iter(f"{{{NS['a']}}}t")) if title_el is not None else ""
    plot = chart.find("c:plotArea", NS)
    kinds, series = [], []
    for child in plot:
        tag = child.tag.split("}")[1]
        if tag in CHART_KINDS:
            kinds.append(tag)
            bar_dir = child.find("c:barDir", NS)
            if bar_dir is not None and bar_dir.get("val") == "bar":
                kinds[-1] = "horizontalBar"
            for ser in child.findall("c:ser", NS):
                name_el = ser.find("c:tx", NS)
                name_f = _f(name_el)
                name_v = _cache(name_el)
                cat = ser.find("c:cat", NS) or ser.find("c:xVal", NS)
                val = ser.find("c:val", NS) or ser.find("c:yVal", NS)
                series.append({
                    "kind": tag,
                    "name": name_v or name_f or "",
                    "name_ref": name_f,
                    "cat_ref": _f(cat), "cat_cache": _cache(cat),
                    "val_ref": _f(val), "val_cache": _cache(val),
                })
    return {"title": title, "kinds": kinds, "series": series, "part": chart_part}


def _f(el):
    if el is None:
        return ""
    f = el.find(".//c:f", NS)
    return f.text if f is not None and f.text else ""


def _cache(el):
    if el is None:
        return []
    vals = []
    for pt in el.iter(f"{{{NS['c']}}}pt"):
        v = pt.find("c:v", NS)
        if v is not None:
            vals.append(v.text)
    if not vals:
        for v in el.iter(f"{{{NS['c']}}}v"):
            vals.append(v.text)
    return vals


def _scan_drawings(z: zipfile.ZipFile, sheet_parts: dict) -> tuple[list, list]:
    charts, images = [], []
    for sheet_name, sheet_part in sheet_parts.items():
        for rel in _rels(z, sheet_part).values():
            if not rel["type"].endswith("/drawing"):
                continue
            drawing = rel["target"]
            drels = _rels(z, drawing)
            root = ET.fromstring(z.read(drawing))
            for anchor in list(root):
                frm = anchor.find("xdr:from", NS)
                row = int(frm.find("xdr:row", NS).text) + 1 if frm is not None else 0
                col = int(frm.find("xdr:col", NS).text) + 1 if frm is not None else 0
                for el in anchor.iter(f"{{{NS['c']}}}chart"):
                    rid = el.get(f"{{{NS['r']}}}id")
                    part = drels.get(rid, {}).get("target")
                    if part and part in z.namelist():
                        info = _chart_info(z, part)
                        info.update({"sheet": sheet_name, "row": row, "col": col})
                        charts.append(info)
                for el in anchor.iter(f"{{{NS['a']}}}blip"):
                    rid = el.get(f"{{{NS['r']}}}embed")
                    part = drels.get(rid, {}).get("target")
                    if part and part in z.namelist():
                        images.append({"sheet": sheet_name, "row": row, "col": col,
                                       "media": part, "ext": part.rsplit(".", 1)[-1].lower()})
    images.sort(key=lambda d: (d["sheet"], d["row"], d["col"]))
    return charts, images


def extract_images(z_path: str, images: list, out_dir: Path) -> list:
    """Re-extrae imágenes en cada lectura: borra las anteriores, descarta duplicados (MD5)."""
    import shutil
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved, seen = [], {}
    with zipfile.ZipFile(z_path) as z:
        for img in images:
            data = z.read(img["media"])
            h = hashlib.md5(data).hexdigest()
            if h in seen:
                continue  # logo o imagen repetida
            fname = f"{h[:10]}.{img['ext']}"
            (out_dir / fname).write_bytes(data)
            seen[h] = fname
            saved.append({**img, "file": str(out_dir / fname), "md5": h})
    return saved


# ---------------------------------------------------------------- API pública
def read_workbook(path: str, images_dir: Path | None = None) -> Workbook:
    md5 = file_md5(path)
    sheets, _ = _read_cells(path)
    with zipfile.ZipFile(path) as z:
        sheet_parts = _sheet_parts(z)
        charts, images = _scan_drawings(z, sheet_parts)
    saved_images = extract_images(path, images, images_dir) if images_dir else images
    return Workbook(path=str(path), md5=md5, read_at=datetime.now().isoformat(timespec="seconds"),
                    sheets=sheets, charts=charts, images=saved_images)


def detect_tables(wb: Workbook, sheet: SheetData, min_cols: int = 3) -> list[dict]:
    """
    Detección genérica (para hojas sin esquema): encabezado = fila con >= min_cols celdas de texto
    contiguas, seguida de una fila con números en esas mismas columnas.
    """
    out, used = [], set()
    rows = sorted(sheet.grid)
    for r in rows:
        if r in used:
            continue
        row = sheet.grid[r]
        runs, run = [], []
        for c in sorted(row):
            if isinstance(row[c], str) and len(row[c]) < 80:
                if run and c != run[-1] + 1:
                    runs.append(run)
                    run = []
                run.append(c)
            else:
                if run:
                    runs.append(run)
                run = []
        if run:
            runs.append(run)
        for run in runs:
            if len(run) < min_cols:
                continue
            nxt = sheet.grid.get(r + 1, {})
            if not any(isinstance(nxt.get(c), (int, float)) for c in run):
                continue
            body, rr = [], r + 1
            while rr <= sheet.max_row:
                vals = [sheet.grid.get(rr, {}).get(c) for c in run]
                if all(v is None for v in vals):
                    break
                body.append(vals)
                used.add(rr)
                rr += 1
            headers = [str(row[c]).strip() for c in run]
            df = pd.DataFrame(body, columns=headers)
            # Título: texto de una sola celda en las 3 filas superiores
            title = ""
            for up in range(r - 1, max(0, r - 4), -1):
                cells = [v for v in sheet.grid.get(up, {}).values() if isinstance(v, str)]
                if len(cells) == 1:
                    title = cells[0].strip()
                    break
            out.append({"title": title or f"Tabla en fila {r}", "row": r, "df": df,
                        "range": f"{cell_ref(r, run[0])}:{cell_ref(rr - 1, run[-1])}"})
    return out


def long_texts(sheet: SheetData, min_len: int = 120) -> list[dict]:
    out = []
    for r in sorted(sheet.grid):
        for c in sorted(sheet.grid[r]):
            v = sheet.grid[r][c]
            if isinstance(v, str) and len(v) >= min_len:
                out.append({"cell": cell_ref(r, c), "row": r, "text": v})
    return out


def chart_values(wb: Workbook, chart: dict) -> dict:
    """Resuelve valores de cada serie desde las celdas del libro; si no se puede, usa la caché del gráfico."""
    res = {"title": chart["title"], "kinds": chart["kinds"], "series": [], "warnings": []}
    for s in chart["series"]:
        cats = wb.values_of_range(s["cat_ref"]) if s["cat_ref"] else None
        vals = wb.values_of_range(s["val_ref"]) if s["val_ref"] else None
        source = "libro"
        if vals is None:
            vals = s["val_cache"] or []
            cats = s["cat_cache"] or None
            source = "caché del gráfico"
            res["warnings"].append(f"Serie '{s['name'] or s['val_ref']}' usa caché (referencia externa o no resuelta).")
        res["series"].append({"kind": s["kind"], "name": s["name"], "cats": cats or [], "vals": vals, "source": source})
    return res


def diff_snapshots(prev: dict | None, cur: dict) -> list[str]:
    """Resumen de cambios entre dos lecturas (guardadas como JSON compacto)."""
    if prev is None:
        return ["Primera lectura: no hay versión anterior para comparar."]
    msgs = []
    ps, cs = set(prev["sheets"]), set(cur["sheets"])
    for s in sorted(cs - ps):
        msgs.append(f"Hoja agregada: {s}")
    for s in sorted(ps - cs):
        msgs.append(f"Hoja eliminada: {s}")
    for s in sorted(ps & cs):
        pv, cv = prev["sheets"][s]["cells"], cur["sheets"][s]["cells"]
        changed = [k for k in set(pv) | set(cv) if pv.get(k) != cv.get(k)]
        if changed:
            msgs.append(f"{s}: {len(changed)} celdas con valor distinto")
        for key in ("charts", "images"):
            d = cur["sheets"][s][key] - prev["sheets"][s][key]
            if d:
                msgs.append(f"{s}: {'+' if d > 0 else ''}{d} {key}")
    return msgs or ["Sin cambios en valores, hojas, gráficos ni imágenes."]


def compact_snapshot(wb: Workbook) -> dict:
    """Versión compacta para comparar entre lecturas (sólo valores no vacíos)."""
    out = {"md5": wb.md5, "read_at": wb.read_at, "sheets": {}}
    for name, sd in wb.sheets.items():
        cells = {}
        for r, row in sd.grid.items():
            for c, v in row.items():
                cells[cell_ref(r, c)] = str(v)
        out["sheets"][name] = {
            "cells": cells,
            "charts": sum(1 for ch in wb.charts if ch["sheet"] == name),
            "images": sum(1 for im in wb.images if im["sheet"] == name),
            "sin_valor": len(sd.formulas_sin_valor),
        }
    return out
