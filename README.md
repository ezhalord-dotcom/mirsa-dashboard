# Mirsa · Dashboard de tesis (Streamlit)

El Excel es la única fuente de verdad. Cambia el libro, súbelo (o pulsa **Recargar**) y la app
se actualiza sin tocar el código.

## Ejecutar
```bash
pip install -r requirements.txt
cp /ruta/AvanceT3G55X.xlsx data/source/      # o súbelo desde la barra lateral
streamlit run app.py
```

## Cómo se sincroniza
- Cada lectura calcula el MD5 del .xlsx. Si no cambió, usa la lectura guardada.
- Si cambió (o pulsas Recargar / subes una versión nueva), relee celdas, gráficos (XML), imágenes
  y tablas, y compara con la lectura anterior. El resumen aparece en **Sistema › Estado de sincronización**.
- Las imágenes se re-extraen en cada lectura (duplicados por MD5 descartados).
- Los gráficos se reconstruyen en Plotly leyendo el XML de cada gráfico y los rangos a los que apuntan.
  Si un rango apunta a otro libro (p. ej. `[8]...`), la app usa la caché del gráfico y lo avisa.

## Qué editar sin tocar código
- `config/schema.yaml`: etiquetas que buscan los dashboards (encabezados de tabla, KPIs y su `occurrence`).
  Si cambias el texto de un encabezado en el Excel, cambia aquí el texto; la app muestra un aviso si no lo encuentra.
- `config/menu.yaml`: orden y agrupación del menú. Las hojas que no estén aquí aparecen en "Otras hojas".

## Estructura
```
app.py                  entrada de Streamlit (barra lateral, menú, enrutado)
core/xlsx_reader.py     lectura del libro: celdas, búsqueda por etiqueta, tablas, gráficos XML, imágenes, diff
core/sync.py            MD5, caché, resumen de cambios, estado por hoja
core/modules.py         extrae los datos de cada objetivo según schema.yaml
ui/dashboards.py        dashboards de Objetivo 2 y 3 (con pestañas)
ui/generic.py           render genérico de cualquier hoja (tablas, textos, gráficos, imágenes)
ui/plots.py             gráficos Plotly
ui/sync_page.py         página de estado de sincronización
tests/test_core.py      pruebas del núcleo (sin Streamlit)
```

## Pruebas
```bash
MIRSA_XLSX=/ruta/AvanceT3G55X.xlsx python tests/test_core.py
```
Las pruebas comprueban los KPIs de Objetivo 3 (514/712 AS IS, 13/14 TO BE, B/C 2.31) y que cada bloque se encuentre.

## Pendiente (siguiente fase)
- Dashboards propios para Objetivo 4, Objetivo 5 y Min-Max (hoy usan el render genérico).
- Hojas de Brecha 2/3/4 agrupadas en una sola página con pestañas.
- Simuladores con controles (ABC, factor de desempeño, umbrales) y comparación con el Excel.
- Recalcular fórmulas sin valor con LibreOffice (hoy solo avisa).
- Modo observación (reléer al guardar el archivo).
- Hojas de fase posterior: Base de datos, Plan.Objetivos, Artículos, Flujo Caja, Conclusiones, Recomendaciones, Anexos, Bibliografía, Asist-Contr.
