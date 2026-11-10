"""Stub del taller de `guardar_tabla()` y `guardar_tabla_traza()`.

`guardar_tabla` hace MERGE por la llave de negocio, el patrón de las dimensiones `dim_*`.
No genera llaves sustitutas: si la tabla destino tiene `llave_primaria` y el DataFrame no la
trae, falla con un mensaje claro.
"""
from notebooks.DLKHNB_ORO.utilidades._taller import verificar_catalogo

ESQUEMA_TRAZA = (
    "id_pipeline STRING, archivo STRING, tipo STRING, tabla STRING, alias STRING, "
    "filas BIGINT, segundos DOUBLE, ts_registro TIMESTAMP"
)


def guardar_tabla(spark, df, tabla_destino, llave_primaria, llave_negocio, columnas_actualizar=[]):
    verificar_catalogo(tabla_destino.split(".")[0])
    llaves = [llave_negocio] if isinstance(llave_negocio, str) else list(llave_negocio)
    destino = [c.lower() for c in spark.table(tabla_destino).columns]
    origen = [c.lower() for c in df.columns]
    if llave_primaria and llave_primaria.lower() in destino and llave_primaria.lower() not in origen:
        raise ValueError(f"guardar_tabla (stub): {tabla_destino} tiene la llave {llave_primaria} y el DataFrame no la trae")
    faltan = [c for c in llaves if c.lower() not in origen]
    if faltan:
        raise ValueError(f"guardar_tabla (stub): la llave de negocio {faltan} no está en el DataFrame")
    vista = "_taller_guardar_tabla_origen"
    df.createOrReplaceTempView(vista)
    actualizar = columnas_actualizar or [c for c in df.columns if c not in llaves and c != llave_primaria]
    condicion = " AND ".join(f"t.{c} = s.{c}" for c in llaves)
    asignaciones = ", ".join(f"t.{c} = s.{c}" for c in actualizar)
    columnas = ", ".join(df.columns)
    valores = ", ".join(f"s.{c}" for c in df.columns)
    spark.sql(
        f"MERGE INTO {tabla_destino} t USING {vista} s ON {condicion} "
        + (f"WHEN MATCHED THEN UPDATE SET {asignaciones} " if asignaciones else "")
        + f"WHEN NOT MATCHED THEN INSERT ({columnas}) VALUES ({valores})"
    )
    spark.catalog.dropTempView(vista)
    print(f"MERGE en {tabla_destino} por {', '.join(llaves)}")


def guardar_tabla_traza(spark, traza, tabla_destino, id_pipeline):
    verificar_catalogo(tabla_destino.split(".")[0])
    if not traza:
        return 0
    filas = [
        (str(id_pipeline), t["archivo"], t["tipo"], t["tabla"], t["alias"], int(t["filas"]), float(t["segundos"]), t["ts_registro"])
        for t in traza
    ]
    spark.createDataFrame(filas, ESQUEMA_TRAZA).write.mode("append").saveAsTable(tabla_destino)
    print(f"Traza: {len(filas)} filas en {tabla_destino}")
    return len(filas)
