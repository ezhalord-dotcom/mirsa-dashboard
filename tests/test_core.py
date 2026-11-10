"""
Pruebas del núcleo (sin Streamlit ni Plotly). Ejecutar:
    MIRSA_XLSX=/ruta/al/libro.xlsx python -m pytest -q tests      (o: python tests/test_core.py)
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.modules import extract_module, load_schema  # noqa: E402
from core.sync import load_source, sheet_status  # noqa: E402
from core.xlsx_reader import read_workbook  # noqa: E402

XLSX = os.environ.get("MIRSA_XLSX", "")
SCHEMA = load_schema(ROOT / "config" / "schema.yaml")


def _wb():
    assert XLSX and Path(XLSX).exists(), "Define MIRSA_XLSX con la ruta del libro"
    return read_workbook(XLSX)


def test_obj3_bloques_y_kpis():
    d = extract_module(_wb(), "obj3", SCHEMA)
    assert d["warnings"] == [], d["warnings"]
    assert len(d["tables"]["ira_mensual"]["df"]) == 12
    assert len(d["tables"]["semaforo"]["df"]) == 6
    assert len(d["tables"]["ciclos"]["df"]) == 3
    k = {x["name"]: x["value"] for x in d["kpis"]}
    assert abs(k["Relación beneficio / costo"] - 2.31) < 0.01
    assert abs(k["Ahorro estimado anual (S/)"] - 32861.9) < 1


def test_obj3_ira_coincide_con_kardex():
    d = extract_module(_wb(), "obj3", SCHEMA)
    base = d["tables"]["ira_base"]["df"]
    assert abs(base.iloc[0, 1] - 514 / 712) < 0.001       # AS IS = 514 de 712
    assert abs(base.iloc[0, 2] - 13 / 14) < 0.001          # TO BE = 13 de 14


def test_obj2_bloques():
    d = extract_module(_wb(), "obj2", SCHEMA)
    assert d["warnings"] == [], d["warnings"]
    assert len(d["tables"]["semaforo"]["df"]) == 6
    assert len(d["tables"]["ciclo_fases"]["df"]) == 5


def test_hoja_inexistente_no_falla():
    wb = _wb()
    fake = {"modules": {"x": {"sheet": "NO EXISTE", "title": "x", "blocks": {}, "kpis": []}}}
    d = extract_module(wb, "x", fake)
    assert d["warnings"] and not d["sheet_found"]


def test_sincronizacion_detecta_cambios():
    d = tempfile.mkdtemp()
    r1 = load_source(XLSX, d)
    assert r1.reloaded
    r2 = load_source(XLSX, d)
    assert not r2.reloaded          # mismo archivo: no vuelve a leer
    assert r2.changes


def test_estado_de_hojas_y_menu():
    import yaml
    menu = [s for s in yaml.safe_load(open(ROOT / "config" / "menu.yaml", encoding="utf-8"))["sections"]
            if "sheet" in s]
    rows = sheet_status(_wb(), menu)
    assert any(r["Hoja"].startswith("DesarrolloOBJ3") for r in rows)
    assert any(r["Hoja"] == "Flujo Caja" for r in rows)


def test_imagenes_catalogo_coincide_con_el_libro():
    from core import imagenes
    out = Path(tempfile.mkdtemp()) / "excel_images"
    cat = imagenes.build(XLSX, out)
    anclas = imagenes.scan(XLSX)
    assert cat["total_anclas"] == len(anclas) == len(cat["imagenes"])
    assert sum(v["anclas"] for v in cat["hojas"].values()) == cat["total_anclas"]
    assert all((out / e["archivo"]).exists() for e in cat["imagenes"])
    # cada hoja del catálogo sale en su carpeta
    assert all(e["archivo"].startswith(imagenes._slug(e["hoja"]) + "/") for e in cat["imagenes"])


def test_imagenes_no_duplican_ni_conservan_obsoletas():
    from core import imagenes
    out = Path(tempfile.mkdtemp()) / "excel_images"
    imagenes.sync(XLSX, out)
    n1 = sorted(p.name for p in out.rglob("*") if p.is_file())
    mt = {p: p.stat().st_mtime_ns for p in out.rglob("*") if p.is_file()}
    imagenes.sync(XLSX, out)                       # mismo libro: no reescribe nada
    assert sorted(p.name for p in out.rglob("*") if p.is_file()) == n1
    assert all(p.stat().st_mtime_ns == t for p, t in mt.items())
    basura = out / "hoja_vieja" / "01_obsoleta.png"  # imagen de una versión anterior
    basura.parent.mkdir(parents=True)
    basura.write_bytes(b"x")
    imagenes.build(XLSX, out)
    assert not basura.exists() and not basura.parent.exists()


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in fns:
        fn()
        print("OK", fn.__name__)
    print(f"{len(fns)} pruebas correctas")
