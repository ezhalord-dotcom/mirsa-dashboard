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

## Objetivos 4 y 5 (dashboards analíticos)
- `ui/analitica.py` construye las pestañas de cada objetivo a partir de `config/schema.yaml` y `core/mrp_blocks.py`.
- Objetivo 4: Selección de herramienta · Datos de planificación · Pronóstico de demanda · Planificación MRP (selector de escenario e insumo) · Proveedores · Resultados · Tablas originales.
- Objetivo 5: Diagnóstico y parámetros · Pronóstico · Política lote por lote · Inventario AS-IS vs TO-BE · Indicadores · Impacto económico · Tablas originales.
- Cada gráfico se alimenta de una tabla que se muestra debajo. Los cálculos del dashboard se limitan a sumas y conteos, y se indican con un aviso.
- Las tablas que el esquema no reconoce aparecen en «Tablas originales» con aviso.
- Los avisos de datos simulados y supuestos salen de frases del propio libro.

## Pendiente
- Min-Max y Resultados generales siguen con su vista actual (sin cambios en esta versión).
- Verificación visual real con Streamlit pendiente: en el entorno de desarrollo no hay red para instalarlo; se verificó con stubs y con los datos del libro original.
- Hojas de Brecha 2/3/4 agrupadas en una sola página con pestañas.
- Simuladores con controles (ABC, factor de desempeño, umbrales) y comparación con el Excel.
- Recalcular fórmulas sin valor con LibreOffice (hoy solo avisa).
- Modo observación (reléer al guardar el archivo).
- Hojas de fase posterior: Base de datos, Plan.Objetivos, Artículos, Flujo Caja, Conclusiones, Recomendaciones, Anexos, Bibliografía, Asist-Contr.

## Rediseño (versión 2)
- Navegación por secciones con íconos: Inicio, Empresa y diagnóstico, Selección AHP, Objetivos 2 a 5,
  Min-Max, Resultados generales, Evaluación económica, Conclusiones y recomendaciones, Explorador y Sincronización.
  Se edita en `config/menu.yaml`.
- Barra superior con búsqueda en todo el libro (celda por celda, con la hoja de origen).
- Tarjetas KPI, avisos cuando un dato no existe en el libro, y descarga CSV de cada tabla.
- Los datos simulados del propio libro (Objetivos 4 y 5, Min-Max) se marcan como avisos.
- Hojas vacías (Flujo Caja, Resultados-Indicadores) y encabezados sin texto (Conclusiones, Recomendaciones)
  se muestran como "no disponible"; no se inventa contenido.

## Despliegue en Streamlit Community Cloud
1. Sube el repositorio a GitHub con `app.py`, `requirements.txt`, `config/`, `core/`, `ui/`.
2. Incluye el Excel en `data/source/AvanceT3G55X.xlsx` (o súbelo desde la barra lateral; en la nube
   el disco se borra al reiniciar, así que para una versión fija conviene incluirlo en el repositorio).
3. En "New app" elige el repositorio y `app.py` como archivo principal.

## Imágenes del libro
- `core/imagenes.py` recorre todas las hojas del Excel y copia cada imagen tal cual en `assets/excel_images/<hoja>/`.
- El catálogo está en `assets/excel_images/catalogo_imagenes.json` y `.csv`: id, hoja, número dentro de la hoja, fila, columna, celda, archivo, formato y MD5.
- Cada ancla de imagen tiene su entrada. Si la misma imagen aparece dos veces en una hoja, se guarda una sola vez y la entrada queda marcada como `repetida_en_hoja`.
- Al cambiar el Excel (Sincronización), el catálogo se reconstruye, se escriben solo archivos nuevos y se borran las imágenes de versiones anteriores.
- `config/imagenes.yaml` indica qué hojas se muestran en cada sección. Las hojas no asignadas se ven en el Explorador.
- Formatos: PNG y JPEG se muestran en pantalla. EMF no se puede mostrar en navegadores; se ofrece su descarga.
