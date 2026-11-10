# Notebook orquestador `DLKH_01_<NOMBRE>`: 13 pasos

El notebook solo orquesta. La lógica vive en los `.conf`. Una celda por paso agrupado, en este orden.

## 1. Markdown de objetivo
```markdown
# DLKH_01_FCT_VENTAS_V1_MES
**Objetivo:** volumen de ventas mensual por planta y empleado.
**Tabla destino:** `{entorno}_glux.oro.fct_ventas_v1_mes`
**Fuentes:** `plata.he_source_sap_ecc_zbpta011`, `oro.fct_pedido_venta`
**Patrón de carga:** DELETE por `cd_periodo_mes` + APPEND
**Spec:** `spec.md` de esta carpeta
```

## 2. Imports y entorno
```python
import sys
import os
import time

tiempo_inicio = time.time()
entorno = os.environ.get("Environment", "dllo")
sys.path.append(f"/Workspace/Shared/databricks_repo_{entorno}")

from notebooks.DLKHNB_ORO.utilidades.procesar_tablas_vistas import procesar_tablas
from notebooks.DLKHNB_ORO.utilidades.guardar_tabla_vistas import guardar_tabla, guardar_tabla_traza
from notebooks.DLKHNB_ORO.utilidades.validar_schema import validar_schema
from notebooks.DLKHNB_ORO.utilidades.liberar_memoria import liberar_memoria
```
Nunca `from functions.functions` ni rutas relativas.

## 3. Widgets
```python
dbutils.widgets.text("id_pipeline", "0")
dbutils.widgets.text("g_fecha", "19000101")
```
`id_pipeline` va siempre. Los demás salen de la spec, con su default.

## 4. Diccionario de parámetros
```python
parametros_dict = {
    "G_Fecha": dbutils.widgets.get("g_fecha"),
}
id_pipeline = dbutils.widgets.get("id_pipeline")
```
Solo valores de widgets. Las fechas calculadas (`l_fecha_ini`, `l_fecha_fin`) no van aquí: las calcula `config_par_*` y quedan en `stg.par_<proceso>`.

## 5. Rutas de los `.conf`
```python
usuario = spark.sql("SELECT current_user()").first()[0]
ruta_base = f"/Workspace/Users/{usuario}/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_VENTAS_V1_MES"

rutas_parametros = [f"{ruta_base}/PARAMETROS/config_par_ventas_mes.conf"]
rutas_insumos = [
    f"{ruta_base}/INSUMOS/config_ins_01_personal.conf",
    f"{ruta_base}/INSUMOS/config_ins_02_ventas.conf",
]
rutas_intermedias = [f"{ruta_base}/INTERMEDIAS/config_int_01_ventas_enriquecido.conf"]
rutas_salidas = [f"{ruta_base}/SALIDAS/config_sal_01_fct_ventas_v1_mes.conf"]
```
El orden de las listas es el orden de ejecución del plan.

## 6 a 9. Procesar PARAMETROS, INSUMOS, INTERMEDIAS y SALIDAS
```python
traza = []
dict_parametros = procesar_tablas(spark, rutas_parametros, entorno, traza, parametros=parametros_dict)
dict_insumos = procesar_tablas(spark, rutas_insumos, entorno, traza)
dict_intermedias = procesar_tablas(spark, rutas_intermedias, entorno, traza)
dict_salidas = procesar_tablas(spark, rutas_salidas, entorno, traza)
```

## 10. Validar schema
```python
nombre_tabla = f"{entorno}_glux.oro.fct_ventas_v1_mes"
df_salida = dict_salidas["fct_ventas_v1_mes"]
validar_schema(nombre_tabla, df_salida, spark)
```

## 11. Persistir
- Hechos: `referencias/hechos.md`. Las fechas del DELETE salen de `dict_parametros`, no de los widgets.
- Dimensiones: `referencias/dimensiones.md`.

## 12. Trazabilidad
```python
guardar_tabla_traza(
    spark=spark,
    traza=traza,
    tabla_destino=f"{entorno}_glux.conf.traza_config_tabla",
    id_pipeline=id_pipeline,
)
```

## 13. Liberar memoria y salir
```python
liberar_memoria(spark, dict_insumos, dict_intermedias, dict_salidas)
tiempo_total = round(time.time() - tiempo_inicio, 2)
dbutils.notebook.exit(f"OK - {nombre_tabla} - {tiempo_total}s")
```
