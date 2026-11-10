# Spec: <indicador o tabla destino>

**Estado:** BORRADOR
<!-- Solo una persona cambia el estado a: APROBADA por <nombre>, <AAAA-MM-DD> -->

- **ATL de origen:** `<ruta del .atl>` (sha256 `<primeros 12 caracteres>`)
- **Inventario usado:** `<ruta de inventario_atl.md>`, generado con `atl_inventario.py`
- **Redactó:** Genie Code con `<usuario>`, `<fecha>`

## 1. Brief
- **Qué se construye:** <una frase>
- **Tabla destino:** `{{Environment}}_glux.oro.<tabla>` (`fct` o `dim`)
- **Parámetros y su default:** `g_fecha` = `19000101`, que se resuelve a <regla del WORKFLOW>
- **Fecha de corte para las pruebas:** `<AAAAMMDD>`
- **Archivos de salida, si hay:** <nombre exacto, separador, columnas>

## 2. Linaje, tomado del inventario
Orden de ejecución según el WORKFLOW. Cada fila cita las líneas del ATL.

| Orden | Dataflow (líneas) | Lee | Produce | Nota |
|---|---|---|---|---|
| 1 | `DF_...` (L120-L310) | `TABLA_A`, `TABLA_B` | `TT_...` | |

## 3. Fuentes: del ATL a Unity Catalog
Una fila por tabla que el ATL lee y que no produce otro dataflow del mismo ATL. La columna "Consulta" es la evidencia de `information_schema`.

| Tabla en el ATL | Tabla en UC | Consulta | Columnas que cambian | Estado |
|---|---|---|---|---|
| `TABLA_A` | `plata.<tabla>` | `SELECT ... FROM <catalogo>.information_schema.tables WHERE ...` → 1 fila | `PRESENTACION` → no existe, se obtiene de `oro.dim_producto` | OK |

Estados válidos:
- **OK:** existe y se verificaron sus columnas.
- **NO EXISTE:** bloquea, lo resuelve una persona.
- **AMBIGUA:** hay 2 o más candidatas parecidas, decide una persona y la spec registra cuál.

## 4. Lógica activa por consulta
Solo código activo. El texto con `#` va en la sección 5.

| Dataflow / consulta (líneas) | Join y llaves, con el formato de cada lado | Filtro activo | Columnas calculadas |
|---|---|---|---|
| `QRY_...` (L200-L230) | `substr(A.DK_CLIENTE, 5, 10) = B.CD_CLIENTE` (14 contra 10 dígitos) | `B.CD_PORTAFOLIO IN ('OPT', 'EST')` | `VL_X = sum(...)` |

**Uniones (Merge):** <MRG_... = UNION ALL de A y B>. Si una salida suma varias ramas, todas van aquí.

## 5. Código comentado que NO se migra
| Línea | Dónde | Texto | Por qué no aplica |
|---|---|---|---|
| L215 | `QRY_...`, filtro | `#B.CD_PORTAFOLIO = 'OPT'` | Versión anterior, comentada en el ATL |

## 6. Parámetros y fechas
Sale de las asignaciones `$L_*` del WORKFLOW. Cada variable termina como columna de `stg.par_<proceso>`.

| Variable del ATL | Expresión (línea) | Columna en `stg.par_<proceso>` |
|---|---|---|
| `$L_FECHA_FIN` | `ifthenelse($P_FECHA = '19000101', <último día hábil>, $P_FECHA)` (L6810) | `l_fecha_fin` |

## 7. Esquema de salida
| Columna | Tipo | Regla |
|---|---|---|
| `cd_periodo_mes` | STRING | `substr(l_fecha_fin, 1, 6)` |

- **Llave de la tabla:** <columnas>
- **Patrón de carga:** DELETE donde `<campo> = <valor de stg.par_*>`, luego APPEND (hechos) / `guardar_tabla()` (dimensiones)

## 8. Escenarios de aceptación
```gherkin
Escenario: mismas fechas en los dos lados
  Dado el archivo esperado "<archivo>" con dt_corte = "<AAAAMMDD>"
  Cuando ejecuto DLKH_01_<NOMBRE> con g_fecha = "<AAAAMMDD>"
  Entonces la tabla destino solo tiene filas con dt_corte = "<AAAAMMDD>"

Escenario: mismas llaves
  Entonces no hay llaves solo en la tabla ni solo en el esperado

Escenario: mismos totales
  Entonces la suma de <columna> coincide con el esperado con tolerancia de <0.01>

Escenario: mismos valores por llave
  Entonces el 100 % de las filas coincide en <columnas> con tolerancia de <0.01>
```

## 9. Supuestos y preguntas abiertas
| # | Tipo | Texto | ¿Bloquea? | Respuesta |
|---|---|---|---|---|
| 1 | Supuesto | <qué asumí y por qué> | No | |
| 2 | Pregunta | <qué necesito que decida una persona> | Sí | |
