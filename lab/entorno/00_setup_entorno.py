# Databricks notebook source
# MAGIC %md
# MAGIC # 00. Setup del entorno sintético del taller SDD
# MAGIC
# MAGIC Deja listo el catálogo del taller y tu carpeta de trabajo:
# MAGIC
# MAGIC 1. Crea el catálogo si no existe, los schemas `oro`, `plata`, `stg`, `conf` y `taller`, y el volume `taller.archivos`.
# MAGIC 2. Carga las tablas sintéticas que imitan las fuentes de comisiones de `dllo_glux`. Todo es inventado y determinista.
# MAGIC 3. Crea vacías las tres tablas `fct_com_var_*` y `conf.traza_config_tabla`, y deja `fct_com_var_volumen_ctv` cargada con la corrida del 28 de agosto, como la encontrarían en el día a día.
# MAGIC 4. Escribe los archivos esperados a corte `20260831` en `/Volumes/<catálogo>/taller/archivos/esperados/`.
# MAGIC 5. Instala en `/Workspace/Users/<tú>/postobon_sdd_workshop/` las utilidades del framework, el ATL del taller y, si lo pides, los controles, el ETL del Lab 4 y la configuración v2 de Genie Code.
# MAGIC
# MAGIC **En Free Edition** el notebook crea el catálogo `<entorno>_glux` si no existe, porque cada persona es admin de su workspace. Se niega a trabajar sobre un catálogo que no empiece con `cx_postobon_sdd`, así que no puede tocar `dllo_glux`. Correrlo otra vez deja todo en el estado inicial.

# COMMAND ----------

dbutils.widgets.text("entorno", "cx_postobon_sdd_workshop", "Entorno (catálogo = <entorno>_glux)")
dbutils.widgets.text("ruta_material", "", "Carpeta lab/ (vacío = carpeta padre de este notebook)")
dbutils.widgets.dropdown("instalar_carpeta", "si", ["si", "no"], "Instalar carpeta de trabajo")
dbutils.widgets.dropdown("instalar_controles", "si", ["si", "no"], "Copiar controles/")
dbutils.widgets.dropdown("instalar_lab4", "si", ["si", "no"], "Copiar el ETL del Lab 4")
dbutils.widgets.dropdown("instalar_v2", "no", ["si", "no"], "Instalar instructions y skills v2 en mi usuario")
dbutils.widgets.dropdown("escribir_privado", "no", ["si", "no"], "Esperados de P4 en taller.privado (facilitador)")

# COMMAND ----------

import datetime
import json
import os
import sys

from databricks.sdk import WorkspaceClient

entorno = dbutils.widgets.get("entorno").strip()
ruta_material = (dbutils.widgets.get("ruta_material").strip() or os.path.dirname(os.getcwd())).rstrip("/")
opcion = {k: dbutils.widgets.get(k) == "si" for k in ["instalar_carpeta", "instalar_controles", "instalar_lab4", "instalar_v2", "escribir_privado"]}

sys.path.insert(0, f"{ruta_material}/entorno")
import datos_sinteticos as ds
import instalador as inst

catalogo = inst.catalogo_del_taller(entorno)
usuario = spark.sql("SELECT current_user()").first()[0]
raiz = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
w = WorkspaceClient()
spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalogo}` COMMENT 'Taller SDD Genie Code. Solo datos sinteticos'")
print(f"Catálogo {catalogo} | usuario {usuario} | material {ruta_material}")
print("Opciones:", {k: v for k, v in opcion.items() if v})

# COMMAND ----------

# MAGIC %md ## 1. Schemas y volume

# COMMAND ----------

for schema in ["oro", "plata", "stg", "conf", "taller"]:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalogo}`.`{schema}`")
spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalogo}`.taller.archivos")
if opcion["escribir_privado"]:
    spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalogo}`.taller.privado")

# COMMAND ----------

# MAGIC %md ## 2. Fuentes sintéticas

# COMMAND ----------

from pyspark.sql.types import DateType, DoubleType, IntegerType, LongType, StringType, StructField, StructType, TimestampType

TIPOS = {"STRING": StringType(), "INT": IntegerType(), "BIGINT": LongType(), "DOUBLE": DoubleType(),
         "DATE": DateType(), "TIMESTAMP": TimestampType()}
CONVERTIR = {"STRING": str, "INT": int, "BIGINT": int, "DOUBLE": float, "DATE": lambda v: v, "TIMESTAMP": lambda v: v}


def dataframe(columnas, filas):
    esquema = StructType([StructField(c, TIPOS[tipo], True) for c, tipo in columnas])
    datos = [tuple(None if f.get(c) is None else CONVERTIR[tipo](f[c]) for c, tipo in columnas) for f in filas]
    return spark.createDataFrame(datos, esquema)


t = ds.generar()
for nombre, columnas in ds.ESQUEMAS.items():
    dataframe(columnas, t[nombre]).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"`{catalogo}`.{nombre}")
    print(f"{nombre}: {len(t[nombre])} filas")

# COMMAND ----------

# MAGIC %md ## 3. Destinos, traza y estado inicial

# COMMAND ----------

for fila in spark.sql(f"SHOW TABLES IN `{catalogo}`.stg").collect():
    if not fila.isTemporary and f"stg.{fila.tableName}" not in ds.ESQUEMAS:
        spark.sql(f"DROP TABLE IF EXISTS `{catalogo}`.stg.`{fila.tableName}`")

for nombre, columnas in list(ds.SALIDAS.items()) + [("conf.traza_config_tabla", ds.TRAZA)]:
    spark.sql(f"CREATE OR REPLACE TABLE `{catalogo}`.{nombre} ({', '.join(f'{c} {tipo}' for c, tipo in columnas)})")

carga_previa = "20260828"
ahora = datetime.datetime.now()
filas = [dict(x, ts_carga=ahora) for x in ds.volumen_ctv_sin_filtro_de_dia(t, ds.fechas_proceso(t, carga_previa))]
dataframe(ds.SALIDAS["oro.fct_com_var_volumen_ctv"], filas).write.mode("append").saveAsTable(f"`{catalogo}`.oro.fct_com_var_volumen_ctv")
print(f"oro.fct_com_var_volumen_ctv: {len(filas)} filas de la carga del {carga_previa}")

# COMMAND ----------

# MAGIC %md ## 4. Archivos esperados a corte 20260831

# COMMAND ----------

fecha = "20260831"
fechas, esperados = ds.esperados(t, fecha)
for tabla, filas in esperados.items():
    print(ds.escribir_csv(f"/Volumes/{catalogo}/taller/archivos/esperados/{tabla}_{fecha}.csv", filas), len(filas), "filas")
if opcion["escribir_privado"]:
    _, esperados_p4 = ds.esperados(t, fecha, excluir_prueba=True)
    for tabla, filas in esperados_p4.items():
        print(ds.escribir_csv(f"/Volumes/{catalogo}/taller/privado/esperados_p4/{tabla}_{fecha}_p4.csv", filas), len(filas), "filas")
print("Fechas de la corrida de referencia:", fechas)

# COMMAND ----------

# MAGIC %md ## 5. Carpeta de trabajo

# COMMAND ----------

instalado = {}
etl = f"{raiz}/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS"
if opcion["instalar_carpeta"]:
    for carpeta in ["databricks_repo_taller", "insumos"]:
        inst.borrar(w, f"{raiz}/{carpeta}")
        instalado[carpeta] = len(inst.subir_arbol(w, inst.leer_arbol(w, f"{ruta_material}/entorno/{carpeta}"), f"{raiz}/{carpeta}"))
    w.workspace.mkdirs(etl[len("/Workspace"):])
if opcion["instalar_controles"]:
    inst.borrar(w, f"{raiz}/controles")
    archivos = [a for a in inst.leer_arbol(w, f"{ruta_material}/controles") if not a[0].startswith("test_")]
    instalado["controles"] = len(inst.subir_arbol(w, archivos, f"{raiz}/controles"))
if opcion["instalar_lab4"]:
    destino = f"{etl}/DLKHID_FCT_COM_VAR_VOLUMEN_CTV"
    inst.borrar(w, destino)
    archivos = inst.reemplazar(inst.leer_arbol(w, f"{ruta_material}/entorno/escenarios/lab4_errores/DLKHID_FCT_COM_VAR_VOLUMEN_CTV"),
                               {'entorno = "cx_postobon_sdd_workshop"': f'entorno = "{entorno}"'})
    instalado["lab4"] = len(inst.subir_arbol(w, archivos, destino))
print(json.dumps(instalado))

# COMMAND ----------

# MAGIC %md ## 6. Configuración v2 de Genie Code en tu usuario (opcional, Lab 1)
# MAGIC
# MAGIC Respalda tu `.assistant_instructions.md` actual en `postobon_sdd_workshop/respaldo/`, lo reemplaza por la constitución v2 más el adaptador de entorno, copia las 4 skills v2 a `/Users/<tú>/.assistant/skills/` y deja `AGENTS.md` en la raíz de `DLKHNB_ORO/`. Si ya tenías una skill personal con el mismo nombre, la respalda en `respaldo/skills_<fecha>/` antes de reemplazarla. Para volver atrás, copia el respaldo más antiguo a su lugar y borra las carpetas `postobon-*` de tus skills.

# COMMAND ----------

if opcion["instalar_v2"]:
    instrucciones = f"/Users/{usuario}/.assistant_instructions.md"
    actual = inst.leer_texto(w, instrucciones)
    if actual is not None:
        respaldo = f"{raiz}/respaldo/assistant_instructions_{ahora:%Y%m%d_%H%M%S}.md"
        inst.subir_arbol(w, [(respaldo.rsplit("/", 1)[1], actual.encode("utf-8"), False)], respaldo.rsplit("/", 1)[0])
        print("Respaldo:", respaldo)
    leer = lambda rel: open(f"{ruta_material}/{rel}", encoding="utf-8").read() if ruta_material.startswith("/Volumes/") else inst.leer_texto(w, f"{ruta_material}/{rel}")
    texto = leer("constitucion_v2/assistant_workspace_instructions.md").rstrip() + "\n\n" + inst.renderizar_adaptador(leer("entorno/adaptador_entorno.md"), entorno, raiz)
    inst.subir_arbol(w, [(".assistant_instructions.md", texto.encode("utf-8"), False)], f"/Users/{usuario}")
    for skill in sorted(os.listdir(f"{ruta_material}/skills_v2")) if ruta_material.startswith("/Volumes/") else sorted({a[0].split("/")[0] for a in inst.leer_arbol(w, f"{ruta_material}/skills_v2")}):
        destino = f"/Users/{usuario}/.assistant/skills/{skill}"
        if inst.existe(w, destino):
            copia = f"{raiz}/respaldo/skills_{ahora:%Y%m%d_%H%M%S}/{skill}"
            inst.subir_arbol(w, inst.leer_arbol(w, f"/Workspace{destino}"), copia)
            print("Respaldo:", copia)
        inst.borrar(w, destino)
        print(skill, len(inst.subir_arbol(w, inst.leer_arbol(w, f"{ruta_material}/skills_v2/{skill}"), destino)), "archivos")
    inst.subir_arbol(w, [("AGENTS.md", leer("constitucion_v2/AGENTS.md").encode("utf-8"), False)], f"{raiz}/databricks/notebooks/DLKHNB_ORO")
    print("Instructions v2:", len(texto), "caracteres (límite 20.000). Abre un chat nuevo de Genie Code para que las tome.")

# COMMAND ----------

resumen = {"catalogo": catalogo, "raiz": raiz, "fechas": fechas, "instalado": instalado,
           "esperados": {k: len(v) for k, v in esperados.items()}}
dbutils.notebook.exit(json.dumps(resumen))
