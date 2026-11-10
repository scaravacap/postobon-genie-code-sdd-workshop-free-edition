# Databricks notebook source
# MAGIC %md
# MAGIC # 10. Reset de escenario del experimento v1 frente a v2
# MAGIC
# MAGIC Primera tarea del job `taller_sdd_experimento`. Deja la carpeta de trabajo y el catálogo en el estado inicial del prompt que se va a correr, para que v1 y v2 partan exactamente del mismo lugar:
# MAGIC
# MAGIC - Borra todo lo que el agente creó en la corrida anterior y reinstala las utilidades y el ATL desde el material privado.
# MAGIC - Vacía las tablas destino y la traza, y borra las tablas de `stg` que no son del setup.
# MAGIC - Pone `AGENTS.md` solo en las corridas v2, y aborta si la configuración de Genie Code instalada no es la de la variante.
# MAGIC - P3: instala la ETL de Volumen CTV sembrada y la carga a 20260828. P4: instala Dropsize y Cobertura correctas y las carga a 20260831.
# MAGIC
# MAGIC Este notebook vive fuera de la raíz que ve el agente, igual que el material privado.

# COMMAND ----------

dbutils.widgets.dropdown("prompt_id", "CANARY", ["CANARY", "P1", "P2", "P3", "P4"], "Prompt")
dbutils.widgets.dropdown("variante", "v1", ["v1", "v2"], "Variante")
dbutils.widgets.text("entorno", "cx_postobon_sdd_workshop", "Entorno")
dbutils.widgets.text("ruta_material", "/Volumes/cx_postobon_sdd_workshop_glux/taller/privado/material", "Material privado")

# COMMAND ----------

import json
import sys

from databricks.sdk import WorkspaceClient

prompt_id = dbutils.widgets.get("prompt_id")
variante = dbutils.widgets.get("variante")
entorno = dbutils.widgets.get("entorno").strip()
material = dbutils.widgets.get("ruta_material").rstrip("/")
sys.path.insert(0, f"{material}/entorno")
import datos_sinteticos as ds
import instalador as inst

catalogo = inst.catalogo_del_taller(entorno)
usuario = spark.sql("SELECT current_user()").first()[0]
raiz = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
oro = f"{raiz}/databricks/notebooks/DLKHNB_ORO"
hechos = f"{oro}/DLKHTIPO_HECHOS"
w = WorkspaceClient()
resumen = {"prompt_id": prompt_id, "variante": variante, "catalogo": catalogo}

# COMMAND ----------

# MAGIC %md ## 1. La configuración instalada corresponde a la variante

# COMMAND ----------

instrucciones = inst.leer_texto(w, f"/Users/{usuario}/.assistant_instructions.md") or ""
skills = {o.path.rsplit("/", 1)[1] for o in w.workspace.list(f"/Users/{usuario}/.assistant/skills")} if inst.existe(w, f"/Users/{usuario}/.assistant/skills") else set()
esperado = {
    "v1": ("Contexto Organizacional", {"postobon-etl-hechos", "postobon-etl-orquestador", "postobon-conf-archivos"}),
    "v2": ("ETL de capa oro (v2)", {"postobon-spec-desde-atl", "postobon-etl-verificacion"}),
}[variante]
problemas = []
if esperado[0] not in instrucciones or "Adaptador de entorno del taller" not in instrucciones:
    problemas.append(f"las instructions de usuario no son las de {variante} con el adaptador")
if not esperado[1] <= skills:
    problemas.append(f"faltan skills de {variante}: {sorted(esperado[1] - skills)}")
otra = {"v1": "postobon-spec-desde-atl", "v2": "postobon-etl-hechos"}[variante]
if otra in skills:
    problemas.append(f"está instalada {otra}, que es de la otra variante")
if problemas:
    raise RuntimeError("Configuración de Genie Code incorrecta para esta corrida: " + "; ".join(problemas))
resumen["skills_usuario"] = sorted(skills)

# COMMAND ----------

# MAGIC %md ## 2. Carpeta de trabajo limpia

# COMMAND ----------

borradas = []
if inst.existe(w, raiz):
    for obj in w.workspace.list(raiz[len("/Workspace"):]):
        inst.borrar(w, obj.path)
        borradas.append(obj.path.rsplit("/", 1)[1])
for carpeta in ["databricks_repo_taller", "insumos"]:
    inst.subir_arbol(w, inst.leer_arbol(w, f"{material}/entorno/{carpeta}"), f"{raiz}/{carpeta}")
w.workspace.mkdirs(hechos[len("/Workspace"):])
if variante == "v2":
    with open(f"{material}/constitucion_v2/AGENTS.md", "rb") as f:
        inst.subir_arbol(w, [("AGENTS.md", f.read(), False)], oro)
resumen["borrado_de_la_corrida_anterior"] = borradas

# COMMAND ----------

# MAGIC %md ## 3. Tablas en estado inicial

# COMMAND ----------

for nombre in ds.SALIDAS:
    spark.sql(f"DELETE FROM `{catalogo}`.{nombre}")
spark.sql(f"DELETE FROM `{catalogo}`.conf.traza_config_tabla")
for fila in spark.sql(f"SHOW TABLES IN `{catalogo}`.stg").collect():
    if not fila.isTemporary and f"stg.{fila.tableName}" not in ds.ESQUEMAS:
        spark.sql(f"DROP TABLE IF EXISTS `{catalogo}`.stg.`{fila.tableName}`")

# COMMAND ----------

# MAGIC %md ## 4. Escenario del prompt

# COMMAND ----------

def instalar_etl(origen, nombre):
    destino = f"{hechos}/{nombre}"
    inst.subir_arbol(w, inst.leer_arbol(w, f"{material}/entorno/{origen}/{nombre}"), destino)
    return f"{destino}/DLKH_01_{nombre[len('DLKHID_'):]}"


def cargar(orquestador, g_fecha):
    return dbutils.notebook.run(orquestador[len("/Workspace"):], 1800, {"g_fecha": g_fecha, "id_pipeline": "carga_previa"})


if prompt_id == "P3":
    orq = instalar_etl("escenarios/P3_volumen_ctv", "DLKHID_FCT_COM_VAR_VOLUMEN_CTV")
    resumen["carga_previa"] = [cargar(orq, "20260828")]
elif prompt_id == "P4":
    resumen["carga_previa"] = [cargar(instalar_etl("referencia/DLKHTIPO_HECHOS", n), "20260831")
                               for n in ["DLKHID_FCT_COM_VAR_DROPSIZE", "DLKHID_FCT_COM_VAR_COBERTURA"]]
for nombre in ds.SALIDAS:
    resumen.setdefault("filas", {})[nombre] = spark.table(f"`{catalogo}`.{nombre}").count()
print(json.dumps(resumen, indent=2, ensure_ascii=False))
dbutils.notebook.exit(json.dumps(resumen, ensure_ascii=False))
