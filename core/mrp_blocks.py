"""
Lector de bloques MRP por insumo (hoja Desarrollo Obj. 4).
Cada bloque empieza con el nombre del insumo en la columna B y "TA: x sem" en la columna C,
y sus filas (Consumo, Llegadas, Inventario final, Emisión…) están debajo, con las semanas como encabezado.
El escenario (AS-IS, TO-BE, ejecución) se toma del último marcador de texto que aparezca encima.
"""
from __future__ import annotations

import pandas as pd

from core.textnorm import norm


def find_markers(sheet, markers: list[tuple[str, str]]) -> list[tuple[int, str]]:
    """markers: [(texto a buscar, nombre de escenario)] -> [(fila, escenario)] ordenado por fila."""
    out = []
    for r in sorted(sheet.grid):
        for c in sorted(sheet.grid[r]):
            v = sheet.grid[r][c]
            if not isinstance(v, str):
                continue
            for text, scen in markers:
                if norm(v).startswith(norm(text)):
                    out.append((r, scen))
    return sorted(out)


def parse_blocks(sheet, markers: list[tuple[str, str]]) -> list[dict]:
    marks = find_markers(sheet, markers)
    blocks = []
    rows = sorted(sheet.grid)
    for r in rows:
        ta = sheet.grid[r].get(3)
        name = sheet.grid[r].get(2)
        if not (isinstance(ta, str) and ta.startswith("TA:") and isinstance(name, str)):
            continue
        scen = next((s for mr, s in reversed(marks) if mr < r), "Sin escenario")
        # encabezado de semanas: primera fila debajo con "Semana" en columna B
        hr = r + 1
        while hr in sheet.grid and str(sheet.grid[hr].get(2, "")).strip().lower() != "semana" and hr < r + 3:
            hr += 1
        if hr not in sheet.grid or str(sheet.grid[hr].get(2, "")).strip().lower() != "semana":
            continue
        weeks = {c: v for c, v in sheet.grid[hr].items() if c >= 3 and isinstance(v, (int, float))}
        if not weeks:
            continue
        data, labels = {}, []
        rr = hr + 1
        while rr in sheet.grid:
            lab = sheet.grid[rr].get(2)
            if not isinstance(lab, str) or lab.startswith("TA:") or lab.strip().lower().startswith("paso") \
                    or any(mr == rr for mr, _ in marks):
                break
            labels.append(lab.strip())
            data[lab.strip()] = [sheet.grid[rr].get(c) for c in sorted(weeks)]
            rr += 1
        df = pd.DataFrame.from_dict(data, orient="index", columns=[int(weeks[c]) for c in sorted(weeks)])
        blocks.append({"name": name.strip(), "scenario": scen, "ta": ta, "row": r, "table": df})
    return blocks
