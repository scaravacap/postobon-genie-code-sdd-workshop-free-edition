# Databricks notebook source
# MAGIC %md
# MAGIC # Verificación de aceptación
# MAGIC
# MAGIC Compara la tabla que produjo un ETL contra su resultado esperado, con la misma fecha de corte, llave por llave.
# MAGIC Corre fuera del agente: en un job, en un bundle o a mano. Si `fallar_si_no_pasa = si`, la tarea falla cuando
# MAGIC el resultado no es PASA, y eso bloquea la promoción.

# COMMAND ----------

dbutils.widgets.text("tabla", "", "Tabla del ETL (catalogo.schema.tabla)")
dbutils.widgets.text("esperado", "", "Esperado (ruta CSV en un volume o tabla)")
dbutils.widgets.text("llaves", "cd_planta,cd_registro_nomina", "Llaves, separadas por coma")
dbutils.widgets.text("columnas_valor", "", "Columnas de valor, separadas por coma")
dbutils.widgets.text("fecha_corte", "", "Fecha de corte (YYYYMMDD)")
dbutils.widgets.text("columna_fecha", "dt_corte", "Columna de fecha de corte")
dbutils.widgets.text("tolerancia", "0.01", "Tolerancia absoluta")
dbutils.widgets.text("reporte", "", "Ruta del verification_report.md (opcional)")
dbutils.widgets.text("titulo", "", "Título del reporte")
dbutils.widgets.text("ruta_controles", "", "Carpeta de aceptacion.py (vacío = la de este notebook)")
dbutils.widgets.dropdown("fallar_si_no_pasa", "si", ["si", "no"], "Fallar si no pasa")

# COMMAND ----------

import json
import os
import sys

ruta_controles = dbutils.widgets.get("ruta_controles") or os.getcwd()
sys.path.insert(0, ruta_controles)
import aceptacion as acept

lista = lambda v: [x.strip() for x in v.split(",") if x.strip()]
tabla = dbutils.widgets.get("tabla")
esperado = dbutils.widgets.get("esperado")
if not tabla or not esperado:
    raise ValueError("Faltan los parámetros tabla y esperado")

res = acept.comparar(
    spark,
    tabla=tabla,
    esperado=esperado,
    llaves=lista(dbutils.widgets.get("llaves")),
    columnas_valor=lista(dbutils.widgets.get("columnas_valor")),
    fecha_corte=dbutils.widgets.get("fecha_corte") or None,
    columna_fecha=dbutils.widgets.get("columna_fecha") or None,
    tolerancia=float(dbutils.widgets.get("tolerancia") or 0),
)
print(acept.formatear(res))

# COMMAND ----------

if dbutils.widgets.get("reporte"):
    ruta = acept.escribir_reporte(
        dbutils.widgets.get("reporte"),
        titulo=dbutils.widgets.get("titulo") or tabla,
        aceptacion=res,
        ejecutor="notebook verificacion_aceptacion (control fuera del agente)",
        no_verificado=["El linter no corre en este notebook: el reporte de aceptación no cubre los .conf."],
    )
    print("Reporte:", ruta)

salida = {"resultado": res["resultado"], "detalle": res.get("detalle", ""), "escenarios": res["escenarios"]}
if res["resultado"] != "PASA" and dbutils.widgets.get("fallar_si_no_pasa") == "si":
    raise Exception(f"Aceptación {res['resultado']}: {json.dumps(salida, ensure_ascii=False)}")
dbutils.notebook.exit(json.dumps(salida, ensure_ascii=False))
