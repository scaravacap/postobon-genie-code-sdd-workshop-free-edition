# Carga de dimensiones `dim_*`: `guardar_tabla()` con MERGE

`guardar_tabla()` hace un MERGE (upsert) contra la tabla destino en Unity Catalog.

## Lo que se pregunta antes de crear archivos
1. **Llave primaria** (surrogate): identificador técnico, por ejemplo `sk_producto`.
2. **Llave de negocio** (natural): identificador real del objeto, por ejemplo `cd_producto`.
3. **Columnas a encriptar:** datos sensibles como cédula, nombre o correo.

## Propuesta de llave de negocio, con evidencia
Aunque el usuario ya haya dado la llave:
1. Mide la tabla fuente:
   ```sql
   SELECT COUNT(*) AS filas, COUNT(DISTINCT <columna>) AS distintos
   FROM {catalogo}.<schema>.<tabla>;
   ```
2. Evalúa cada candidata por unicidad (los dos conteos de arriba), significado de negocio y estabilidad en el tiempo.
3. Presenta la propuesta con el resultado de la consulta y contrástala con la del usuario.
4. No crees archivos hasta que el usuario confirme la llave.

## Uso
```python
guardar_tabla(
    spark=spark,
    df=df_salida,
    tabla_destino=f"{entorno}_glux.oro.dim_producto",
    llave_primaria="sk_producto",
    llave_negocio="cd_producto",
    columnas_actualizar=["ds_producto", "cd_presentacion", "ts_carga"],
)
```
`columnas_actualizar` son las columnas que el MERGE actualiza cuando la llave ya existe. La llave primaria y la llave de negocio se declaran siempre.

## Encriptación
- Solo en el `.conf` de SALIDAS, nunca en INSUMOS ni INTERMEDIAS.
- Por defecto `sha2(col, 256)`. Alternativas: `sha2(col, 512)`, `md5(col)` o `aes_encrypt(col, key, 'GCM')` si debe ser reversible.
- Pregunta si se reemplaza la columna (`sha2(cd_cedula, 256) AS cd_cedula`) o se agrega con sufijo `_enc`.
- Documenta en el COMMENT de la tabla qué columnas están encriptadas y con qué método.

## Ejemplo de SALIDA
```ini
[Entrada]
tipo = salida
catalogo = {{Environment}}_glux
schema = oro
tabla = dim_empleado
alias = dim_empleado
tablas_entrada = [tt_stg_empleado_enriquecido]
columnas = []

[QUERIES]
query_1 =
    SELECT
        e.sk_empleado,
        e.cd_empleado,
        e.ds_nombre_completo,
        sha2(e.cd_cedula, 256) AS cd_cedula,
        e.ds_cargo,
        e.fl_activo,
        CURRENT_TIMESTAMP() AS ts_carga
    FROM tt_stg_empleado_enriquecido e
```

Si el usuario pide otro patrón (OVERWRITE o DELETE + APPEND para una dimensión), se respeta y se anota en la spec.
