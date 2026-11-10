---
name: postobon-etl-crear
description: Crea o modifica una ETL de capa oro con el estándar de Postobón, a partir de una spec aprobada. Úsala cuando el usuario pida crear una ETL, una tabla nueva en oro, un .conf de PARAMETROS, INSUMOS, INTERMEDIAS o SALIDAS, el notebook orquestador DLKH_01, o cargar un fct_ (DELETE + APPEND) o un dim_ (guardar_tabla). Si no hay spec, primero la construye por entrevista o con @postobon-spec-desde-atl.
---

# Crear una ETL de capa oro

Esta skill implementa. No interpreta el ATL: eso ya está en la spec. Las reglas de detalle viven en `referencias/`; léelas cuando llegues al paso que las usa.

| Paso | Referencia |
|---|---|
| Archivos `.conf` | `referencias/conf_archivos.md` |
| Notebook orquestador | `referencias/orquestador.md` |
| Hechos `fct_*` | `referencias/hechos.md` |
| Dimensiones `dim_*` | `referencias/dimensiones.md` |

## Paso 0. Precondición: spec aprobada
Busca `DLKHID_<NOMBRE>/spec.md`.
- Si existe con estado `APROBADA por ...`, sigue al Paso 1.
- Si hay un ATL y no hay spec, usa `@postobon-spec-desde-atl` y detente hasta que la aprueben.
- Si no hay ATL ni SQL probado, entrevista al usuario y llena `plantillas/spec.md` de `@postobon-spec-desde-atl` con sus respuestas:
  1. Nombre de la tabla destino en `oro`. Si viene de un ATL, pregunta si se conserva el nombre.
  2. Tablas fuente de `plata` u `oro`, verificadas en `information_schema`.
  3. Reglas de negocio, filtros y columnas requeridas.
  4. Parámetros además de `id_pipeline` y su default (`g_fecha`, `g_fecha_ini`, `g_fecha_fin`, `g_centro_sap`, `g_fecha_reproceso`, `p_destinatarios_email`). `id_pipeline` se incluye siempre, sin preguntar.
  5. Si es `dim_*`: llave primaria, llave de negocio y columnas a encriptar (ver `referencias/dimensiones.md`).
  6. Si es `fct_*`: campo y rango del DELETE (ver `referencias/hechos.md`).
  7. Archivo esperado y fecha de corte para la aceptación.

  Muestra la spec y espera a que la persona la apruebe.

## Paso 1. Plan
Copia `plantillas/plan.md` a `DLKHID_<NOMBRE>/plan.md` y llénalo desde la spec: cada archivo con lo que lee, lo que produce, el requisito que cubre y el escenario que lo prueba. Muestra el plan y espera confirmación antes de crear archivos.

## Paso 2. Frescura de las fuentes
Con `@postobon-etl-verificacion`, modo "fuentes": ninguna fuente de `plata` u `oro` con más de 3 días sin actualizar. Si alguna falla, emite la alerta y no continúes. Una confirmación verbal no basta: se vuelve a medir.

## Paso 3. Estructura de carpetas
```
DLKHID_<NOMBRE>/
  PARAMETROS/  INSUMOS/  INTERMEDIAS/  SALIDAS/
  DLKH_01_<NOMBRE>
```
El nombre va en mayúsculas, el de la tabla destino (`DLKHID_FCT_VENTAS_V1_MES`), bajo `DLKHTIPO_HECHOS/`, `DLKHTIPO_DIMENSIONES/` o `DLKHTIPO_VISTAS/`.

## Paso 4. Archivos `.conf`, uno a la vez
Orden: PARAMETROS, INSUMOS, INTERMEDIAS, SALIDAS. Para cada archivo:
1. Escríbelo con `referencias/conf_archivos.md`.
2. Pásale el linter:
   ```python
   import importlib.util, os
   usuario = spark.sql("SELECT current_user()").first()[0]
   for base in (f"/Workspace/Users/{usuario}/.assistant/skills", "/Workspace/.assistant/skills"):
       ruta = f"{base}/postobon-etl-crear/scripts/conf_linter.py"
       if os.path.exists(ruta):
           s = importlib.util.spec_from_file_location("conf_linter", ruta)
           linter = importlib.util.module_from_spec(s); s.loader.exec_module(linter)
           break
   print(linter.formatear(linter.lint_archivo("<ruta del .conf>")))
   ```
3. Si hay errores, corrígelos antes de pasar al siguiente archivo.
4. Relee el archivo y muestra el fragmento final.

Toda tabla de `plata` u `oro` que es primera fuente del proceso va en `INSUMOS/`. No uses tablas que no estén en la sección 3 de la spec; si hace falta una, detente y pregúntalo.

## Paso 5. Notebook orquestador
Sigue `referencias/orquestador.md` (13 pasos). Para el paso de persistencia:
- `fct_*`: DELETE con las fechas de `stg.par_<proceso>`, luego APPEND (`referencias/hechos.md`).
- `dim_*`: `guardar_tabla()` con llave primaria y llave de negocio (`referencias/dimensiones.md`).

## Paso 6. Entrega a verificación
Corre el linter de la carpeta completa contra la spec y pasa a `@postobon-etl-verificacion`:
```python
print(linter.formatear(linter.lint_carpeta("<ruta>/DLKHID_<NOMBRE>", spec="<ruta>/DLKHID_<NOMBRE>/spec.md")))
```
Esta skill no declara la ETL como terminada. Eso solo lo hace `verification_report.md` con PASA.

## Reglas
- Un archivo por vez. Si un cambio toca más de 3 archivos, lista los archivos y pide confirmación.
- No optimices ni simplifiques lógica de la spec sin autorización explícita.
- Si la spec no responde algo, pregúntalo; no lo decidas.
