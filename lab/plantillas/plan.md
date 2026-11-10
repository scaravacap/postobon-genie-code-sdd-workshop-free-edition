# Plan: <tabla destino>

- **Spec:** `<ruta>/spec.md`, estado `APROBADA por <nombre>, <fecha>`
- **Carpeta:** `<ruta>/DLKHID_<NOMBRE>/`
- **Redactó:** Genie Code con `<usuario>`, `<fecha>`

## 1. Archivos a crear o modificar, en orden de ejecución
Cada requisito de la spec aparece en al menos una fila. Cada fila tiene un escenario que la prueba.

| # | Archivo | Tipo | Lee (alias) | Produce | Cubre de la spec | Escenario |
|---|---|---|---|---|---|---|
| 1 | `PARAMETROS/config_par_<proceso>.conf` | insumo | - | `stg.par_<proceso>` | Sección 6 | mismas fechas |
| 2 | `INSUMOS/config_ins_01_<alias>.conf` | insumo | `plata.<tabla>` | `tt_stg_<alias>` | Sección 3, fila 1 | mismas llaves |

## 2. Orquestador `DLKH_01_<NOMBRE>`
- **Widgets:** `id_pipeline` y <los de la spec, con default>
- **Patrón de carga:** <DELETE donde ... + APPEND, o `guardar_tabla()` con llave primaria y de negocio>
- **Fechas del DELETE:** salen de `stg.par_<proceso>`, no de los widgets

## 3. Supuestos de implementación
| # | Supuesto | Cómo lo verifico |
|---|---|---|
| 1 | | |

## 4. Riesgos que ya conocemos y cómo los detecto
| Riesgo | Detección |
|---|---|
| `%` sin escapar en un LIKE | `conf_linter.py` (regla `interpolacion`) |
| JOIN sin match por formato de llave | Conteo de filas antes y después del JOIN; escenario "mismas llaves" |
| Columna que no existe en la tabla de UC | `conf_linter.py --explain` |

## 5. Verificación
1. `conf_linter.py` después de cada `.conf`, y al final con `--carpeta` y `--spec`.
2. Ejecutar `DLKH_01_<NOMBRE>` con `g_fecha = <fecha de corte>`.
3. Aceptación contra `<archivo esperado>`.
4. `verification_report.md` con el resultado.

## 6. Fuera de alcance
- <lo que no se construye en esta iteración>
