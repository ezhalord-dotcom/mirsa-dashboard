"""
Extracción de imágenes incrustadas en el Excel y catálogo de metadatos.

- Recorre TODAS las hojas del libro (no solo las de los objetivos).
- Cada ancla de imagen (no cada archivo) queda en el catálogo, con hoja, número dentro de la
  hoja y fila/columna de anclaje.
- Los bytes se copian tal cual (sin recomprimir). El Excel original no se modifica.
- Estructura: assets/excel_images/<hoja>/<NN>_<hash>.<ext>  +  catalogo_imagenes.json / .csv
- Sincronización: si el MD5 del libro no cambió y los archivos existen, no hace nada.
  Si cambió, reconstruye el catálogo, escribe solo archivos nuevos o distintos y borra las
  imágenes obsoletas de versiones anteriores.
No importa Streamlit.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

from core.xlsx_reader import _rels, _scan_drawings, _sheet_parts, file_md5

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets" / "excel_images"
CATALOG_JSON = ASSETS / "catalogo_imagenes.json"
CATALOG_CSV = ASSETS / "catalogo_imagenes.csv"
WEB_FORMATS = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}


def _slug(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s or "hoja"


def scan(xlsx_path: str | Path) -> list[dict]:
    """Todas las anclas de imagen del libro, ordenadas por hoja, fila y columna."""
    with zipfile.ZipFile(xlsx_path) as z:
        _, anchors = _scan_drawings(z, _sheet_parts(z))
    return anchors


def build(xlsx_path: str | Path, out_dir: Path = ASSETS) -> dict:
    """Escribe las imágenes y devuelve el catálogo. Idempotente."""
    xlsx_path = Path(xlsx_path)
    md5 = file_md5(xlsx_path)
    anchors = scan(xlsx_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries, written, reused, per_sheet_n = [], set(), 0, {}
    sheet_hash_file: dict[tuple[str, str], str] = {}

    with zipfile.ZipFile(xlsx_path) as z:
        for a in anchors:
            sheet = a["sheet"]
            per_sheet_n[sheet] = per_sheet_n.get(sheet, 0) + 1
            n = per_sheet_n[sheet]
            data = z.read(a["media"])
            h = hashlib.md5(data).hexdigest()
            ext = a["ext"]
            key = (sheet, h)
            if key in sheet_hash_file:      # misma imagen dos veces en la misma hoja: un solo archivo
                rel = sheet_hash_file[key]
                reused += 1
                repetida = True
            else:
                rel = f"{_slug(sheet)}/{n:02d}_{h[:8]}.{ext}"
                path = out_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                if not (path.exists() and hashlib.md5(path.read_bytes()).hexdigest() == h):
                    path.write_bytes(data)     # solo se escribe si falta o cambió
                sheet_hash_file[key] = rel
                repetida = False
            written.add(rel)
            entries.append({
                "id": f"{_slug(sheet)}-{n:02d}",
                "hoja": sheet.strip(),
                "numero_en_hoja": n,
                "fila": a["row"],
                "columna": a["col"],
                "celda": f"{_col_letter(a['col'])}{a['row']}" if a["row"] and a["col"] else "",
                "archivo": rel,
                "formato": ext,
                "md5": h,
                "web": ext in WEB_FORMATS,
                "repetida_en_hoja": repetida,
            })

    _remove_obsolete(out_dir, written)
    catalog = {
        "fuente": xlsx_path.name,
        "fuente_md5": md5,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "total_anclas": len(entries),
        "total_archivos": len(written),
        "hojas": _per_sheet(entries),
        "imagenes": entries,
    }
    (out_dir / CATALOG_JSON.name).write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / CATALOG_CSV.name).open("w", encoding="utf-8-sig", newline="") as f:
        cols = ["id", "hoja", "numero_en_hoja", "fila", "columna", "celda", "archivo", "formato", "md5", "web", "repetida_en_hoja"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for e in entries:
            w.writerow({k: e[k] for k in cols})
    return catalog


def sync(xlsx_path: str | Path, out_dir: Path = ASSETS) -> dict:
    """Carga el catálogo si el libro no cambió; si cambió, lo reconstruye."""
    xlsx_path = Path(xlsx_path)
    cat_file = out_dir / CATALOG_JSON.name
    md5 = file_md5(xlsx_path)
    if cat_file.exists():
        cat = json.loads(cat_file.read_text(encoding="utf-8"))
        if cat.get("fuente_md5") == md5 and all((out_dir / e["archivo"]).exists() for e in cat["imagenes"]):
            return cat
    return build(xlsx_path, out_dir)


def load(out_dir: Path = ASSETS) -> dict | None:
    f = out_dir / CATALOG_JSON.name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _remove_obsolete(out_dir: Path, keep: set[str]):
    for p in out_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() not in (".json", ".csv"):
            if p.relative_to(out_dir).as_posix() not in keep:
                p.unlink()
    for d in sorted([d for d in out_dir.rglob("*") if d.is_dir()], reverse=True):
        if not any(d.iterdir()):
            d.rmdir()


def _per_sheet(entries: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for e in entries:
        s = out.setdefault(e["hoja"], {"anclas": 0, "archivos": set()})
        s["anclas"] += 1
        s["archivos"].add(e["archivo"])
    return {k: {"anclas": v["anclas"], "archivos": len(v["archivos"])} for k, v in out.items()}


def _col_letter(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s
