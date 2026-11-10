# Carga de hechos `fct_*`: DELETE + APPEND

Primero se borra el período que se recarga y después se agregan las filas nuevas. Así una reejecución del mismo período no duplica.

## Las fechas del DELETE salen de `stg.par_<proceso>`
Los widgets traen `19000101` por defecto. Un DELETE con la fecha del widget no borra nada y el APPEND duplica el período. Las fechas resueltas están en el resultado de PARAMETROS:

```python
fechas = dict_parametros["par_ventas_mes"].first()
fecha_ini, fecha_fin = fechas["l_fecha_ini"], fechas["l_fecha_fin"]

spark.sql(f"""
    DELETE FROM {nombre_tabla}
    WHERE dt_entrega BETWEEN '{fecha_ini}' AND '{fecha_fin}'
""")

df_salida.write.mode("append").saveAsTable(nombre_tabla)
print(f"Filas insertadas: {df_salida.count()}")
```

## Reglas
- El campo y el rango del DELETE están en la spec (sección 7). Si no están, pregúntalos.
- Nunca un DELETE sin WHERE.
- Nunca `mode("overwrite")` en un hecho: borra toda la tabla.
- `validar_schema()` va antes del DELETE, no después.

## Variantes
DELETE con más de una condición:
```python
spark.sql(f"""
    DELETE FROM {nombre_tabla}
    WHERE dt_entrega BETWEEN '{fecha_ini}' AND '{fecha_fin}'
      AND cd_planta IN ({lista_plantas})
""")
```

DELETE por período mes (`yyyyMM`):
```python
spark.sql(f"DELETE FROM {nombre_tabla} WHERE cd_periodo_mes = '{fecha_fin[:6]}'")
```

## Qué preguntar si la spec no lo dice
1. Campo de fecha del DELETE (`dt_entrega`, `dt_factura`, `dt_corte`, `cd_periodo_mes`).
2. Rango: `BETWEEN` inicio y fin, o igualdad con un período.
3. Otras condiciones del borrado (planta, indicador).

Si el usuario pide otro patrón (OVERWRITE o MERGE para un hecho), se respeta y se anota en la spec como desviación del estándar.
