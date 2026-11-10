# Archivos `.conf` del estándar de capa oro

Cada `.conf` es una unidad de transformación que lee `procesar_tablas()`. Se parsea con `configparser`, y eso fija dos reglas que rompen en ejecución: el `%` y los comentarios.

## Estructura
```ini
[Entrada]
tipo = insumo
catalogo = {{Environment}}_glux
schema = plata
tabla = he_source_sap_ecc_zbpta011
alias = tt_stg_personal
tablas_entrada = []
columnas = []

[QUERIES]
query_1 =
    SELECT ...
```

| Campo | Regla |
|---|---|
| `tipo` | `insumo` en INSUMOS y PARAMETROS, `intermedia` en INTERMEDIAS, `salida` en SALIDAS |
| `catalogo` | Siempre `{{Environment}}_glux` |
| `schema` | `plata` u `oro` en insumos, `stg` en parámetros e intermedias, `oro` en salidas |
| `tabla` | Tabla que lee (insumo) o que produce (intermedia, salida, parámetros) |
| `alias` | Nombre con el que otros `.conf` la referencian. En staging, `tt_stg_<nombre>` |
| `tablas_entrada` | Todos los alias que usa el SQL. Vacío en insumos |
| `columnas` | `[]` para todas |

## Reglas del SQL
1. **Solo SELECT.** INSERT, DELETE, UPDATE y MERGE van en el notebook orquestador.
2. **CTEs** (`WITH ... AS`) para más de una transformación. El único subquery permitido es el escalar de fechas.
3. **Plantillas:** `{{catalogo}}`, `{{schema}}`, `{{tabla}}` y, solo en `config_par_*`, `{{parametros[NOMBRE]}}`.
4. **Fechas fuera de PARAMETROS:** se leen de la tabla de parámetros, nunca de `{{parametros[...]}}`:
   `WHERE dt_entrega BETWEEN (SELECT l_fecha_ini FROM {{catalogo}}.stg.par_<proceso>) AND (SELECT l_fecha_fin FROM {{catalogo}}.stg.par_<proceso>)`
5. **El `%` se escribe `%%`.** `configparser` interpreta `%` como interpolación y la celda falla con `'%' must be followed by '%' or '('`. Aplica también a comentarios SQL dentro de la query:
   - `WHERE ds_canal LIKE '%%TRADICIONAL%%'`
   - `-- descuento del 10%%`
6. **Columnas calificadas después de un JOIN** (`v.cd_planta`, no `cd_planta`) para evitar `AMBIGUOUS_REFERENCE`.
7. **Columnas verificadas.** Antes de usar una columna, confírmala en `information_schema.columns`. Una columna que existía en la tabla legacy puede no existir en UC (`UNRESOLVED_COLUMN`); la spec dice de dónde sale.
8. **Catálogo nunca a mano:** `{{catalogo}}.plata.tabla`, no `dllo_glux.plata.tabla`.

## Ejemplos

### PARAMETROS
```ini
[Entrada]
tipo = insumo
catalogo = {{Environment}}_glux
schema = stg
tabla = par_ventas_mes
alias = par_ventas_mes
tablas_entrada = []
columnas = []

[QUERIES]
query_1 =
    WITH fecha_fin AS (
        SELECT CASE
                 WHEN '{{parametros[G_Fecha]}}' = '19000101'
                 THEN CAST(MAX(sk_fecha) AS STRING)
                 ELSE '{{parametros[G_Fecha]}}'
               END AS l_fecha_fin
        FROM {{catalogo}}.oro.dim_fecha
        WHERE bl_dia_habil = 'SI'
          AND sk_fecha < CAST(DATE_FORMAT(CURRENT_DATE(), 'yyyyMMdd') AS INT)
    )
    SELECT l_fecha_fin,
           CONCAT(SUBSTR(l_fecha_fin, 1, 6), '01') AS l_fecha_ini
    FROM fecha_fin
```

### INSUMO
```ini
[Entrada]
tipo = insumo
catalogo = {{Environment}}_glux
schema = plata
tabla = he_source_sap_ecc_zbpta011
alias = tt_stg_personal
tablas_entrada = []
columnas = []

[QUERIES]
query_1 =
    SELECT DISTINCT
        CAST(pernr AS STRING) AS pernr,
        stext AS ds_cargo
    FROM {{catalogo}}.plata.he_source_sap_ecc_zbpta011
    WHERE stext LIKE '%%REPRESENTANTE%%'
```

### INTERMEDIA
```ini
[Entrada]
tipo = intermedia
catalogo = {{Environment}}_glux
schema = stg
tabla = tt_stg_ventas_enriquecido
alias = tt_stg_ventas_enriquecido
tablas_entrada = [tt_stg_personal, tt_stg_ventas_raw]
columnas = []

[QUERIES]
query_1 =
    WITH ventas_mes AS (
        SELECT *
        FROM tt_stg_ventas_raw
        WHERE dt_entrega BETWEEN (SELECT l_fecha_ini FROM {{catalogo}}.stg.par_ventas_mes)
                             AND (SELECT l_fecha_fin FROM {{catalogo}}.stg.par_ventas_mes)
    ),
    ventas_con_personal AS (
        SELECT v.cd_planta, v.cd_registro_nomina, v.vl_vol_litros_vta, p.ds_cargo
        FROM ventas_mes v
        INNER JOIN tt_stg_personal p
            ON v.cd_registro_nomina = p.pernr
    )
    SELECT * FROM ventas_con_personal
```

### SALIDA
```ini
[Entrada]
tipo = salida
catalogo = {{Environment}}_glux
schema = oro
tabla = fct_ventas_v1_mes
alias = fct_ventas_v1_mes
tablas_entrada = [tt_stg_ventas_enriquecido]
columnas = []

[QUERIES]
query_1 =
    SELECT
        e.cd_planta,
        e.cd_registro_nomina,
        e.ds_cargo,
        SUM(e.vl_vol_litros_vta) AS vl_total_litros,
        CURRENT_TIMESTAMP() AS ts_carga
    FROM tt_stg_ventas_enriquecido e
    GROUP BY e.cd_planta, e.cd_registro_nomina, e.ds_cargo
```

## Nombres de archivo
| Tipo | Patrón | Ejemplo |
|---|---|---|
| Parámetros | `config_par_<proceso>.conf` | `config_par_ventas_mes.conf` |
| Insumo | `config_ins_##_<alias>.conf` | `config_ins_01_personal.conf` |
| Intermedia | `config_int_##_<alias>.conf` | `config_int_01_ventas_enriquecido.conf` |
| Salida | `config_sal_##_<tabla>.conf` | `config_sal_01_fct_ventas_v1_mes.conf` |

El linter (`scripts/conf_linter.py`) revisa todas estas reglas. Si una regla del linter y esta referencia no coinciden, avisa: es un error de la skill.
