# Databricks notebook source
# MAGIC %md
# MAGIC # DLKH_01_FCT_COM_VAR_DROPSIZE
# MAGIC **Objetivo:** dropsize del mes por representante: venta neta sobre pedidos distintos, portafolio OPT y EST del canal tradicional.
# MAGIC
# MAGIC **Tabla destino:** `{entorno}_glux.oro.fct_com_var_dropsize`
# MAGIC
# MAGIC **Fuentes:** `plata.he_source_sap_ecc_zbpta011`, `oro.fct_pedido_venta`, `plata.commision_portafolio`, `oro.dim_fecha`
# MAGIC
# MAGIC **Patrón de carga:** DELETE por `cd_periodo_mes` + APPEND
# MAGIC
# MAGIC **Origen:** `DF_TALLER_DROPSIZE_TRN` del ATL `com_variable_mini.atl`

# COMMAND ----------

import os
import sys
import time

tiempo_inicio = time.time()
# Adaptador del taller. En Postobón estas líneas son:
#   entorno = os.environ.get("Environment", "dllo")
#   sys.path.append(f"/Workspace/Shared/databricks_repo_{entorno}")
usuario = spark.sql("SELECT current_user()").first()[0]
raiz_taller = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
entorno = "cx_postobon_sdd_workshop"
sys.path.append(f"{raiz_taller}/databricks_repo_taller")

from notebooks.DLKHNB_ORO.utilidades.procesar_tablas_vistas import procesar_tablas
from notebooks.DLKHNB_ORO.utilidades.guardar_tabla_vistas import guardar_tabla_traza
from notebooks.DLKHNB_ORO.utilidades.validar_schema import validar_schema
from notebooks.DLKHNB_ORO.utilidades.liberar_memoria import liberar_memoria

# COMMAND ----------

dbutils.widgets.text("id_pipeline", "0")
dbutils.widgets.text("g_fecha", "19000101")

parametros_dict = {"G_Fecha": dbutils.widgets.get("g_fecha")}
id_pipeline = dbutils.widgets.get("id_pipeline")

# COMMAND ----------

ruta_base = f"{raiz_taller}/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_DROPSIZE"

rutas_parametros = [f"{ruta_base}/PARAMETROS/config_par_com_var_dropsize.conf"]
rutas_insumos = [
    f"{ruta_base}/INSUMOS/config_ins_01_personal.conf",
    f"{ruta_base}/INSUMOS/config_ins_02_pedidos.conf",
    f"{ruta_base}/INSUMOS/config_ins_03_portafolio.conf",
]
rutas_intermedias = [
    f"{ruta_base}/INTERMEDIAS/config_int_01_registro_nomina.conf",
    f"{ruta_base}/INTERMEDIAS/config_int_02_ventas_portafolio.conf",
]
rutas_salidas = [f"{ruta_base}/SALIDAS/config_sal_01_fct_com_var_dropsize.conf"]

# COMMAND ----------

traza = []
dict_parametros = procesar_tablas(spark, rutas_parametros, entorno, traza, parametros=parametros_dict)
dict_insumos = procesar_tablas(spark, rutas_insumos, entorno, traza)
dict_intermedias = procesar_tablas(spark, rutas_intermedias, entorno, traza)
dict_salidas = procesar_tablas(spark, rutas_salidas, entorno, traza)

# COMMAND ----------

nombre_tabla = f"{entorno}_glux.oro.fct_com_var_dropsize"
df_salida = dict_salidas["fct_com_var_dropsize"]
validar_schema(nombre_tabla, df_salida, spark)

# COMMAND ----------

fechas = dict_parametros["par_com_var_dropsize"].first()
periodo = fechas["l_fecha_fin"][:6]
spark.sql(f"DELETE FROM {nombre_tabla} WHERE cd_periodo_mes = '{periodo}'")
df_salida.write.mode("append").saveAsTable(nombre_tabla)
filas = spark.table(nombre_tabla).where(f"cd_periodo_mes = '{periodo}'").count()
print(f"Filas insertadas para {periodo} (corte {fechas['l_fecha_fin']}): {filas}")

# COMMAND ----------

guardar_tabla_traza(spark=spark, traza=traza, tabla_destino=f"{entorno}_glux.conf.traza_config_tabla", id_pipeline=id_pipeline)

# COMMAND ----------

liberar_memoria(spark, dict_insumos, dict_intermedias, dict_salidas)
tiempo_total = round(time.time() - tiempo_inicio, 2)
dbutils.notebook.exit(f"OK - {nombre_tabla} - corte {fechas['l_fecha_fin']} - {filas} filas - {tiempo_total}s")
