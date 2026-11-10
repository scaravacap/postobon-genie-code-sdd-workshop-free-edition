---
name: postobon-atl-comparacion
description: Compara una ETL existente contra su ATL de SAP Data Services con una matriz de trazabilidad que cita líneas del ATL y de cada .conf. Úsala cuando el usuario pida comparar ATL vs ETL, revisar qué falta para que la ETL sea igual al ATL, auditar fidelidad, o revisar PARAMETROS contra el WORKFLOW. No estima porcentajes de fidelidad: la fidelidad la miden las pruebas de aceptación.
---

# Comparación ATL vs ETL

La ETL debe replicar la lógica activa del ATL: mismas tablas, joins, filtros, uniones y cálculos, adaptados a Spark SQL y al estándar de carpetas. Nada se agrega ni se omite sin autorización explícita.

Esta skill no lee el ATL con el modelo. Usa el inventario de `scripts/atl_inventario.py`, que recorre el archivo completo y cita líneas.

## Paso 1. Inventario y linaje del indicador
```python
import importlib.util, os
usuario = spark.sql("SELECT current_user()").first()[0]
for base in (f"/Workspace/Users/{usuario}/.assistant/skills", "/Workspace/.assistant/skills"):
    ruta = f"{base}/postobon-atl-comparacion/scripts/atl_inventario.py"
    if os.path.exists(ruta):
        s = importlib.util.spec_from_file_location("atl_inventario", ruta)
        atl = importlib.util.module_from_spec(s); s.loader.exec_module(atl)
        break
inv = atl.inventariar("<ruta del .atl>")
print(atl.resumen(inv))
print(atl.linaje(inv, "<TABLA_FINAL>"))
```
Para cada dataflow del linaje, `print(atl.detalle_dataflow(inv, "DF_..."))`. Esa salida es la lista de chequeo: cada lectura, consulta, join, filtro activo, rama de Merge, columna calculada y carga es un renglón de la matriz.

## Paso 2. Lee todos los `.conf` de la ETL
Lista la carpeta y lee cada archivo de PARAMETROS, INSUMOS, INTERMEDIAS y SALIDAS, sin omitir ninguno. Registra cuántos leíste por carpeta. Si un archivo no se puede leer, dilo.

## Paso 3. Matriz de trazabilidad
Un renglón por elemento del inventario, en orden de ejecución:

| Elemento del ATL (línea) | Archivo `.conf` (línea) | Estado | Evidencia |
|---|---|---|---|
| `QRY_FILTRA_PORT`, filtro activo (L2140) | `config_ins_02_portafolio.conf` (L14) | Cubierto | El WHERE replica `IN ('OPT', 'EST')` |
| Merge `MRG_CLIENTES`, rama `QRY_CLI_AUTOVENTA` (L5320) | - | Falta | Ningún `.conf` lee autoventa |

Estados válidos:
- **Cubierto:** está en el `.conf` y cita la línea.
- **Distinto:** está, pero cambia la lógica. Explica qué cambia.
- **Falta:** el ATL lo tiene y ningún `.conf` lo cubre. Debe crearse.
- **Extra:** un `.conf` tiene lógica o tablas que no están en el ATL. Debe eliminarse, salvo autorización.
- **No verificado:** no se pudo confirmar. Explica por qué.

El código con `#` no es un renglón de lógica. Si un `.conf` replica código comentado, eso es **Distinto**.

## Paso 4. PARAMETROS contra el WORKFLOW
El inventario lista cada asignación `$L_*` y `$G_*` del WORKFLOW con su línea. Compara una por una contra `config_par_*.conf`:
- Condiciones combinadas idénticas (por ejemplo `G_FECHA_FIN = '19000101' OR G_FECHA_INI = '19000101'`).
- Mismos defaults.
- Dependencias entre variables respetadas (`L_FECHA_INI` se calcula desde `L_FECHA_FIN`).
- Mismas listas de exclusión (`NOT IN`).

Reporta toda diferencia, aunque parezca menor. Esta es la sección donde más errores sutiles aparecen.

## Paso 5. Reporte
- Conteo de renglones por estado. No calcules un porcentaje de fidelidad: la fidelidad se prueba con `@postobon-etl-verificacion`.
- Cada **Falta**, **Distinto** y **Extra** con línea del ATL y archivo y línea del `.conf`.
- Lo **No verificado**, sin maquillarlo.
- Antes de corregir, muestra la lista y espera confirmación. Corrige un renglón a la vez y verifica cada uno.

## Prohibiciones
- No agregues tablas que no estén en el ATL ni asumas que una tabla extra "fue una mejora".
- No simplifiques ni optimices lógica del ATL sin autorización explícita.
- No omitas ningún `.conf` ni la comparación de PARAMETROS.
- No concluyas que una tabla falta sin buscarla en `information_schema` y en el inventario: puede producirla otro dataflow del mismo ATL.
