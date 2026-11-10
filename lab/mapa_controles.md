# Mapa de errores a controles

Cada error que vimos en la migración de comisiones tiene al menos un control. La columna "Tipo" dice qué tan fuerte es:

- **S (soft):** texto en la constitución o en una skill. Depende de que Genie Code obedezca.
- **A (asistido):** script determinista que una skill ejecuta. El resultado no depende del modelo, pero invocarlo sí.
- **D (duro):** determinista y fuera del agente: un job, el pipeline de CI, permisos de Unity Catalog, un guard en las utilidades.
- **H (humano):** una persona aprueba o revisa.

Genie Code no documenta hooks ni un modo de solo planear, y la autoaprobación por defecto no es una barrera de seguridad. Por eso todo control que tiene que cumplirse siempre vive en D o H.

| Error | Qué pasó | Control | Dónde vive | Tipo | Cómo se prueba |
|---|---|---|---|---|---|
| **E1. Lectura parcial del ATL** | Buscó fragmentos por palabra clave en un ATL de más de 30.000 líneas y concluyó con información parcial; tomó código comentado por activo | `atl_inventario.py` recorre el ATL completo: dataflows, fuentes, destinos, consultas, joins, Merge, código con `#` y variables del WORKFLOW, con línea | Script de `postobon-spec-desde-atl` y de `postobon-atl-comparacion` | A | Lab 1 y P1: linaje de Cobertura con sus dos ramas y sin el filtro comentado |
| | | La spec cita líneas del inventario y una persona la aprueba | `spec.md` | H | Lab 2 |
| | | "La spec manda": con spec aprobada no se reinterpreta el ATL | Constitución | S | |
| **E2. "Temporalidad" sin evidencia** | Atribuyó diferencias a horarios de carga o snapshots, aunque el usuario pidió descartarlo | "Sin query no hay causa": toda causa va con su query y resultado | Constitución, modo 4 de `postobon-etl-verificacion` | S | P3 y Lab 3 |
| | | La aceptación entrega diferencias por llave y razón entre sumas | `aceptacion.py` | A | P3 |
| **E3. Tablas omitidas** | Olvidó una rama del UNION de un indicador, no encontró una tabla que ya existía en staging, JOIN sin match por formato de llave | El inventario lista todas las ramas de cada Merge y quién produce cada tabla | `atl_inventario.py` | A | P1 y Lab 1 |
| | | La spec mide el formato de las llaves de cada JOIN | `postobon-spec-desde-atl`, paso 4 | S | P2 |
| | | El linter avisa si una fuente aprobada en la spec no la usa ningún `.conf` | `conf_linter.py`, regla `spec_fuentes` | A/D | P2 |
| | | La aceptación detecta llaves que solo están en un lado | `aceptacion.py` | A/D | P2 |
| **E4. "Listo" sin evidencia** | Declaró "todo resuelto" o valores "idénticos" sin comparar | "Listo exige reporte" | Constitución | S | P2 y P3 |
| | | `verification_report.md` lo escribe un script con el resultado real | `aceptacion.escribir_reporte` | A | Lab 4 |
| | | Job de validación en CI que corre linter y aceptación | `databricks.yml` | D | Lab 5 |
| **E5. Fechas distintas** | Comparó una corrida de un día contra archivos de otro | La aceptación aborta si las fechas de corte de los dos lados no coinciden | `aceptacion.comparar` | A/D | P3, Labs 3 y 4 (la tabla sembrada tiene otra fecha) |
| | | La fecha de corte de las pruebas está en la spec | `spec.md`, sección 1 | H | |
| **E6. Cambios "aplicados" que no estaban** | Dijo que aplicó cambios que el archivo no tenía, por lectura vieja o por un despliegue que revirtió | Releer y mostrar el fragmento final después de cada edición | Constitución | S | P4 |
| | | Hash de cada archivo en el reporte, para comparar después de desplegar | `conf_linter.py`, `verification_report.md` | A | Labs 4 y 5 |
| | | Despliegue con bundles desde Git; no se edita a mano en `prbs` ni `prod` | `AGENTS.md`, CI | D | Lab 5 |
| | | Una skill editada solo aplica en un chat nuevo | Guía del lab | S | Lab 2 |
| **E7. Cambios masivos y `%` sin escapar** | Replicó un ajuste a varios indicadores sin validarlo; comentarios con `%` rompieron la ejecución | "Un cambio a la vez" y confirmación si toca más de 3 archivos | Constitución | S | P4 |
| | | El linter usa configparser con interpolación: falla igual que en ejecución | `conf_linter.py`, regla `interpolacion` | A/D | P4 y Lab 4 |
| | | Modo "Ask first" para ediciones | Settings de Genie Code | H | Labs 2 y 3 |
| **E8. Autoevaluación de fidelidad** | Estimó "85 % de fidelidad" sobre su propio trabajo | Sin porcentajes: la matriz cuenta renglones por estado y la aceptación mide | `postobon-atl-comparacion`, `aceptacion.py` | S/A | P1 y Lab 1 |
| **E9. Fechas de `parametros_dict`** | Usó `{{parametros[l_fecha_ini]}}` en un insumo, cuando la fecha calculada vive en `stg.par_*` | Regla `parametros_fuera_de_par`: `{{parametros[...]}}` solo en `config_par_*` | `conf_linter.py` | A/D | P2 y Lab 4 |
| | | Las utilidades fallan con un mensaje claro si una plantilla de parámetros no se puede resolver | `procesar_tablas` del taller | D | P2 y Lab 4 |
| **E10. Columnas ambiguas o inexistentes** | `AMBIGUOUS_REFERENCE` después de un JOIN y columnas que no existen en la tabla de UC | Columnas verificadas en `information_schema` en la spec | `postobon-spec-desde-atl`, paso 3 | S | P2 |
| | | `--explain` analiza cada query en Spark sin ejecutarla | `conf_linter.py` | A | Lab 4 |
| **E11. Sustitución silenciosa** | Usó tablas de estructura parecida sin avisar, o no reportó que faltaba un insumo | "Antes de decir que algo falta, búscalo; nunca uses una tabla parecida sin preguntar" | Constitución | S | P1 y P2 (hay una tabla parecida en `plata`) |
| | | Estados `NO EXISTE` y `AMBIGUA` en la spec, que bloquean | `spec.md`, sección 3 | H | Labs 1 y 2 |
| | | El linter rechaza fuentes que no están en la spec | `conf_linter.py`, regla `spec_fuentes` | A/D | P2 |

## Dos hallazgos en el estándar v1

Al revisar las skills v1 encontré dos patrones que reproducen errores del caso:

1. **El ejemplo de INTERMEDIA de `postobon-conf-archivos` filtra con `{{parametros[G_Fecha_Ini]}}`.** Si la plantilla se resuelve con el default `19000101`, el filtro no devuelve filas. Si no se resuelve, porque el orquestador estándar no le pasa `parametros` a `procesar_tablas` en las intermedias, la query falla. En los dos casos es el patrón de E9. En v2 el ejemplo lee las fechas de `stg.par_*`.
2. **El ejemplo de `postobon-etl-hechos` borra con la fecha del widget.** Con el default `19000101` el DELETE no borra nada y el APPEND duplica el período. En v2 el DELETE usa las fechas resueltas de PARAMETROS.

## Qué cambió de v1 a v2

| v1 (7 skills) | v2 (4 skills) |
|---|---|
| `postobon-etl-crear` | `postobon-etl-crear`, ahora con spec aprobada como precondición, plan y linter por archivo |
| `postobon-conf-archivos`, `postobon-etl-orquestador`, `postobon-etl-hechos`, `postobon-etl-dimensiones` | Referencias dentro de `postobon-etl-crear` |
| `postobon-atl-comparacion` | `postobon-atl-comparacion`, con inventario determinista y matriz de trazabilidad |
| `postobon-etl-validacion` | `postobon-etl-verificacion`, que suma linter, aceptación, depuración y reporte |
| - | `postobon-spec-desde-atl` (nueva) |

La constitución pasa de 3.556 a unos 2.900 bytes y cambia de contenido: deja la lista de skills (Genie Code las descubre por su descripción) y suma el flujo SDD y las reglas de evidencia.
