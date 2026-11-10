# Databricks notebook source
# MAGIC %md
# MAGIC # 30. Validación del entorno con las ETL de referencia
# MAGIC
# MAGIC Se corre una vez después de `00_setup_entorno`, antes del experimento:
# MAGIC
# MAGIC 1. Huella de los archivos esperados, para compararla con la de los CSV del repo.
# MAGIC 2. Estado sembrado: `fct_com_var_volumen_ctv` cargada al 28 de agosto tiene que dar NO COMPARABLE contra el esperado del 31.
# MAGIC 3. Guard: las utilidades rechazan `dllo_glux`.
# MAGIC 4. Las tres ETL de referencia: linter con `explain`, ejecución a corte 20260831 y aceptación contra su esperado.
# MAGIC 5. Limpieza: borra las referencias de la raíz de trabajo, para que el agente nunca las vea.

# COMMAND ----------

dbutils.widgets.text("entorno", "cx_postobon_sdd_workshop", "Entorno")
dbutils.widgets.text("ruta_material", "/Volumes/cx_postobon_sdd_workshop_glux/taller/privado/material", "Material privado")

# COMMAND ----------

import hashlib
import json
import sys

from databricks.sdk import WorkspaceClient

entorno = dbutils.widgets.get("entorno").strip()
material = dbutils.widgets.get("ruta_material").rstrip("/")
for sub in ["entorno", "controles"]:
    sys.path.insert(0, f"{material}/{sub}")
import aceptacion as acept
import conf_linter as linter
import instalador as inst

catalogo = inst.catalogo_del_taller(entorno)
usuario = spark.sql("SELECT current_user()").first()[0]
raiz = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
hechos = f"{raiz}/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS"
w = WorkspaceClient()
FECHA = "20260831"
LLAVES = ["cd_planta", "cd_registro_nomina"]
ETL = {
    "fct_com_var_dropsize": ("DLKHID_FCT_COM_VAR_DROPSIZE", ["vl_venta_total", "nm_pedidos", "vl_dropsize"],
                             {"vl_venta_total": 0.01, "nm_pedidos": 0, "vl_dropsize": 0.01}),
    "fct_com_var_volumen_ctv": ("DLKHID_FCT_COM_VAR_VOLUMEN_CTV", ["vl_volumen_ctv"], {"vl_volumen_ctv": 0.0001}),
    "fct_com_var_cobertura": ("DLKHID_FCT_COM_VAR_COBERTURA", ["nm_clientes_meta", "nm_clientes_compra", "vl_cobertura"],
                              {"nm_clientes_meta": 0, "nm_clientes_compra": 0, "vl_cobertura": 0.0001}),
}


def aceptar(tabla):
    _, valores, tolerancia = ETL[tabla]
    return acept.comparar(spark, tabla=f"{catalogo}.oro.{tabla}", esperado=f"/Volumes/{catalogo}/taller/archivos/esperados/{tabla}_{FECHA}.csv",
                          llaves=LLAVES, columnas_valor=valores, fecha_corte=FECHA, columna_fecha="dt_corte", tolerancia=tolerancia)


r = {"sha_esperados": {}}
for tabla in ETL:
    with open(f"/Volumes/{catalogo}/taller/archivos/esperados/{tabla}_{FECHA}.csv", "rb") as f:
        r["sha_esperados"][tabla] = hashlib.sha256(f.read()).hexdigest()
for tabla in ["fct_com_var_dropsize", "fct_com_var_cobertura"]:
    with open(f"/Volumes/{catalogo}/taller/privado/esperados_p4/{tabla}_{FECHA}_p4.csv", "rb") as f:
        r["sha_esperados"][f"{tabla}_p4"] = hashlib.sha256(f.read()).hexdigest()

sembrado = aceptar("fct_com_var_volumen_ctv")
r["estado_sembrado"] = {"resultado": sembrado["resultado"], "ok": sembrado["resultado"] == "NO COMPARABLE"}

sys.path.insert(0, f"{raiz}/databricks_repo_taller")
from notebooks.DLKHNB_ORO.utilidades._taller import verificar_catalogo
try:
    verificar_catalogo("dllo_glux")
    r["guard"] = {"ok": False}
except PermissionError as e:
    r["guard"] = {"ok": True, "mensaje": str(e)[:120]}

# COMMAND ----------

try:
    for tabla, (carpeta, _, _) in ETL.items():
        destino = f"{hechos}/{carpeta}"
        inst.borrar(w, destino)
        inst.subir_arbol(w, inst.leer_arbol(w, f"{material}/entorno/referencia/DLKHTIPO_HECHOS/{carpeta}"), destino)
        rep = linter.lint_carpeta(destino, spark=spark, explain=True, entorno=entorno)
        salida = dbutils.notebook.run(f"{destino}/DLKH_01_{carpeta[len('DLKHID_'):]}"[len("/Workspace"):], 1800,
                                      {"g_fecha": FECHA, "id_pipeline": "validacion"})
        a = aceptar(tabla)
        r[tabla] = {"linter_errores": rep["errores"], "linter_advertencias": rep["advertencias"],
                    "hallazgos": [f"{h['severidad']} {h['regla']} {h['archivo']}: {h['detalle']}"[:200] for h in rep["hallazgos"]],
                    "salida": salida, "aceptacion": a["resultado"], "detalle": a["detalle"],
                    "ok": rep["errores"] == 0 and a["resultado"] == "PASA"}
    r["traza_filas"] = spark.sql(f"SELECT count(*) FROM `{catalogo}`.conf.traza_config_tabla WHERE id_pipeline = 'validacion'").first()[0]
finally:
    for carpeta, _, _ in ETL.values():
        inst.borrar(w, f"{hechos}/{carpeta}")
    r["limpieza"] = [o.path for o in w.workspace.list(hechos[len("/Workspace"):])] if inst.existe(w, hechos) else []

r["todo_ok"] = all(v.get("ok", True) for v in r.values() if isinstance(v, dict)) and not r["limpieza"] and r["traza_filas"] > 0
print(json.dumps(r, indent=2, ensure_ascii=False))
if not r["todo_ok"]:
    raise RuntimeError("La validación del entorno no pasó; revisa el detalle arriba.")
dbutils.notebook.exit(json.dumps(r, ensure_ascii=False))
