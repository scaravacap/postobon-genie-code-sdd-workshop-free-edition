# Databricks notebook source
# MAGIC %md
# MAGIC # 31. Validación del camino del participante
# MAGIC
# MAGIC Se corre después de un `00_setup_entorno` lanzado desde una copia de `lab/` en el workspace, como la Git folder de un participante, con `instalar_controles` e `instalar_lab4` en `si`:
# MAGIC
# MAGIC 1. Lo instalado: `controles/` sin pruebas, `verificacion_aceptacion` como notebook y el ETL del Lab 4.
# MAGIC 2. El linter instalado sobre el Lab 4, estático y con `explain`.
# MAGIC 3. El error de Spark de cada `.conf` sembrado, corriendo uno por uno sobre las vistas de la referencia.
# MAGIC 4. El Lab 4 corregido: con `g_fecha` por defecto da NO COMPARABLE (E5) y a corte 20260831 pasa `verificacion_aceptacion`.
# MAGIC 5. Limpieza: borra `controles/` y el ETL del Lab 4 de la raíz de trabajo.

# COMMAND ----------

dbutils.widgets.text("entorno", "cx_postobon_sdd_workshop", "Entorno")
dbutils.widgets.text("ruta_material", "/Volumes/cx_postobon_sdd_workshop_glux/taller/privado/material", "Material privado")

# COMMAND ----------

import json
import re
import sys

from databricks.sdk import WorkspaceClient

entorno = dbutils.widgets.get("entorno").strip()
material = dbutils.widgets.get("ruta_material").rstrip("/")
sys.path.insert(0, f"{material}/entorno")
import instalador as inst

catalogo = inst.catalogo_del_taller(entorno)
usuario = spark.sql("SELECT current_user()").first()[0]
raiz = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
lab4 = f"{raiz}/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_VOLUMEN_CTV"
ref = f"{material}/entorno/referencia/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_VOLUMEN_CTV"
tabla = f"{catalogo}.oro.fct_com_var_volumen_ctv"
esperado = f"/Volumes/{catalogo}/taller/archivos/esperados/fct_com_var_volumen_ctv_20260831.csv"
FECHA = "20260831"
w = WorkspaceClient()

sys.path.insert(0, f"{raiz}/controles")
sys.path.insert(0, f"{raiz}/databricks_repo_taller")
import aceptacion as acept
import conf_linter as linter
from notebooks.DLKHNB_ORO.utilidades.procesar_tablas_vistas import procesar_tablas

CONFS = [
    "PARAMETROS/config_par_com_var_volumen_ctv.conf",
    "INSUMOS/config_ins_01_personal.conf",
    "INSUMOS/config_ins_02_rollup_volumen.conf",
    "INSUMOS/config_ins_03_producto.conf",
    "INSUMOS/config_ins_04_factor_ctv.conf",
    "INTERMEDIAS/config_int_01_registro_nomina.conf",
    "INTERMEDIAS/config_int_02_volumen_ctv_producto.conf",
    "SALIDAS/config_sal_01_fct_com_var_volumen_ctv.conf",
]
ESTATICOS = {
    ("INSUMOS/config_ins_01_personal.conf", "interpolacion"),
    ("INTERMEDIAS/config_int_01_registro_nomina.conf", "parametros_fuera_de_par"),
    ("INTERMEDIAS/config_int_02_volumen_ctv_producto.conf", "tablas_entrada"),
}
FIRMAS = {
    "INSUMOS/config_ins_01_personal.conf": "%",
    "INTERMEDIAS/config_int_01_registro_nomina.conf": "parametros",
    "INTERMEDIAS/config_int_02_volumen_ctv_producto.conf": "cd_presentacion",
    "SALIDAS/config_sal_01_fct_com_var_volumen_ctv.conf": "mbiguous",
}
r = {}


def errores(rep):
    return {(h["archivo"], h["regla"]) for h in rep["hallazgos"] if h["severidad"] == "error"}


def resumen(rep):
    return [f"{h['severidad']} {h['regla']} {h['archivo']}: {h['detalle']}"[:240] for h in rep["hallazgos"]]

# COMMAND ----------

try:
    objetos = {o.path.rsplit("/", 1)[1]: o.object_type.value for o in w.workspace.list(f"{raiz}/controles"[len("/Workspace"):])}
    orquestador = inst.leer_texto(w, f"{lab4}/DLKH_01_FCT_COM_VAR_VOLUMEN_CTV") or ""
    r["instalado"] = {
        "controles": objetos,
        "orquestador_es_notebook": w.workspace.get_status(f"{lab4}/DLKH_01_FCT_COM_VAR_VOLUMEN_CTV"[len("/Workspace"):]).object_type.value == "NOTEBOOK",
        "entorno_en_orquestador": f'entorno = "{entorno}"' in orquestador,
        "ok": {"conf_linter.py", "aceptacion.py", "atl_inventario.py", "databricks.yml"} <= set(objetos)
              and objetos.get("verificacion_aceptacion") == "NOTEBOOK" and not any(k.startswith("test_") for k in objetos),
    }
    r["instalado"]["ok"] = r["instalado"]["ok"] and r["instalado"]["orquestador_es_notebook"] and r["instalado"]["entorno_en_orquestador"]

    estatico = linter.lint_carpeta(lab4)
    con_explain = linter.lint_carpeta(lab4, spark=spark, explain=True, entorno=entorno)
    r["linter"] = {"estatico": resumen(estatico), "explain": resumen(con_explain),
                   "explain_errores_extra": sorted(f"{a} {b}" for a, b in errores(con_explain) - ESTATICOS),
                   "ok": errores(estatico) == ESTATICOS}

    traza = []
    parametros = {"G_Fecha": FECHA}
    for conf in CONFS:
        procesar_tablas(spark, [f"{ref}/{conf}"], entorno, traza, parametros=parametros if conf.startswith("PARAMETROS") else None)
    fallas = {}
    for conf in CONFS:
        try:
            procesar_tablas(spark, [f"{lab4}/{conf}"], entorno, traza, parametros=parametros if conf.startswith("PARAMETROS") else None)
        except Exception as e:
            fallas[conf] = str(e).strip().splitlines()[0][:300]
    r["fallas_spark"] = {"fallas": fallas,
                         "ok": set(fallas) == set(FIRMAS) and all(FIRMAS[k] in v for k, v in fallas.items())}

    corregidos = [a for a in inst.leer_arbol(w, ref) if a[0].endswith(".conf")]
    inst.subir_arbol(w, corregidos, lab4)
    r["linter_corregido"] = {"hallazgos": resumen(linter.lint_carpeta(lab4, spark=spark, explain=True, entorno=entorno))}
    r["linter_corregido"]["ok"] = not any(h.startswith("error") for h in r["linter_corregido"]["hallazgos"])

    orq = f"{lab4}/DLKH_01_FCT_COM_VAR_VOLUMEN_CTV"[len("/Workspace"):]
    salida_defecto = dbutils.notebook.run(orq, 1800, {"id_pipeline": "lab4_defecto"})
    corte = spark.sql(f"SELECT l_fecha_fin FROM `{catalogo}`.stg.par_com_var_volumen_ctv").first()[0]
    e5 = acept.comparar(spark, tabla=tabla, esperado=esperado, llaves=["cd_planta", "cd_registro_nomina"], columnas_valor=["vl_volumen_ctv"],
                        fecha_corte=FECHA, columna_fecha="dt_corte", tolerancia=0.0001)
    r["e5"] = {"salida": salida_defecto, "corte": corte, "aceptacion": e5["resultado"], "detalle": e5["detalle"]}
    r["e5"]["ok"] = corte != FECHA and e5["resultado"] in ("NO COMPARABLE", "NO PASA")

    salida = dbutils.notebook.run(orq, 1800, {"g_fecha": FECHA, "id_pipeline": "lab4"})
    verif = json.loads(dbutils.notebook.run(f"{raiz}/controles/verificacion_aceptacion"[len("/Workspace"):], 600, {
        "tabla": tabla, "esperado": esperado, "columnas_valor": "vl_volumen_ctv", "fecha_corte": FECHA, "tolerancia": "0.0001",
        "fallar_si_no_pasa": "no"}))
    r["corregido"] = {"salida": salida, "verificacion": {k: verif.get(k) for k in ("resultado", "detalle")},
                      "ok": verif.get("resultado") == "PASA"}
finally:
    inst.borrar(w, f"{raiz}/controles")
    inst.borrar(w, lab4)
    r["limpieza"] = {"controles": inst.existe(w, f"{raiz}/controles"), "lab4": inst.existe(w, lab4)}

r["todo_ok"] = all(v.get("ok", True) for v in r.values() if isinstance(v, dict)) and not any(r["limpieza"].values())
print(json.dumps(r, indent=2, ensure_ascii=False, default=str))
if not r["todo_ok"]:
    raise RuntimeError("La validación del camino del participante no pasó; revisa el detalle arriba.")
dbutils.notebook.exit(json.dumps(r, ensure_ascii=False, default=str))
