# Databricks notebook source
# MAGIC %md
# MAGIC # 20. Evaluación de una corrida del experimento v1 frente a v2
# MAGIC
# MAGIC Última tarea del job `taller_sdd_experimento`, con "Run if: All done" para que evalúe aunque Genie Code falle. Mide lo mismo en las dos variantes:
# MAGIC
# MAGIC - **Lo que dejó el agente:** linter de cada carpeta de ETL y aceptación de la tabla tal como quedó.
# MAGIC - **Si el código es correcto:** el evaluador vuelve a ejecutar el orquestador del agente a corte 20260831 y corre la aceptación otra vez.
# MAGIC - **Lo que dijo:** pistas automáticas sobre la respuesta (rúbrica de P1, "listo" sin evidencia, causa de P3) y si menciona material privado.
# MAGIC
# MAGIC Escribe una fila en `taller.experimento_resultados` y guarda la respuesta y una copia del trabajo del agente en `taller.privado/corridas/`, porque el siguiente reset lo borra.

# COMMAND ----------

dbutils.widgets.dropdown("prompt_id", "CANARY", ["CANARY", "P1", "P2", "P3", "P4"], "Prompt")
dbutils.widgets.dropdown("variante", "v1", ["v1", "v2"], "Variante")
dbutils.widgets.text("respuesta", "", "Respuesta de Genie Code")
dbutils.widgets.text("run_id", "", "Run del job")
dbutils.widgets.text("entorno", "cx_postobon_sdd_workshop", "Entorno")
dbutils.widgets.text("ruta_material", "/Volumes/cx_postobon_sdd_workshop_glux/taller/privado/material", "Material privado")

# COMMAND ----------

import datetime
import hashlib
import json
import os
import re
import sys

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ObjectType

prompt_id = dbutils.widgets.get("prompt_id")
variante = dbutils.widgets.get("variante")
respuesta = dbutils.widgets.get("respuesta")
run_id = dbutils.widgets.get("run_id").strip() or "manual"
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
esperados = f"/Volumes/{catalogo}/taller/archivos/esperados"
privado = f"/Volumes/{catalogo}/taller/privado"
w = WorkspaceClient()
FECHA = "20260831"
LLAVES = ["cd_planta", "cd_registro_nomina"]
ETL = {
    "fct_com_var_dropsize": {"carpeta": "DLKHID_FCT_COM_VAR_DROPSIZE", "valores": ["vl_venta_total", "nm_pedidos", "vl_dropsize"],
                             "tolerancia": {"vl_venta_total": 0.01, "nm_pedidos": 0, "vl_dropsize": 0.01}},
    "fct_com_var_volumen_ctv": {"carpeta": "DLKHID_FCT_COM_VAR_VOLUMEN_CTV", "valores": ["vl_volumen_ctv"],
                                "tolerancia": {"vl_volumen_ctv": 0.0001}},
    "fct_com_var_cobertura": {"carpeta": "DLKHID_FCT_COM_VAR_COBERTURA", "valores": ["nm_clientes_meta", "nm_clientes_compra", "vl_cobertura"],
                              "tolerancia": {"nm_clientes_meta": 0, "nm_clientes_compra": 0, "vl_cobertura": 0.0001}},
}
d = {"prompt_id": prompt_id, "variante": variante, "run_id": run_id}

# COMMAND ----------

# MAGIC %md ## 1. Copia del trabajo del agente

# COMMAND ----------

destino = f"{privado}/corridas/{run_id}_{prompt_id}_{variante}"
os.makedirs(destino, exist_ok=True)
with open(f"{destino}/respuesta.md", "w", encoding="utf-8") as f:
    f.write(respuesta)
trabajo = inst.leer_arbol(w, raiz) if inst.existe(w, raiz) else []
base = {rel: c for rel, c, _ in inst.leer_arbol(w, f"{material}/entorno/databricks_repo_taller")}
d["base_modificada"] = sorted(rel for rel, c, _ in trabajo if rel.startswith("databricks_repo_taller/") and base.get(rel[len("databricks_repo_taller/"):]) != c)
d["archivos_del_agente"] = {}
for rel, contenido, _ in trabajo:
    if rel.startswith(("databricks_repo_taller/", "insumos/")):
        continue
    os.makedirs(os.path.dirname(f"{destino}/trabajo/{rel}"), exist_ok=True)
    with open(f"{destino}/trabajo/{rel}", "wb") as f:
        f.write(contenido)
    d["archivos_del_agente"][rel] = hashlib.sha256(contenido).hexdigest()[:12]
texto = respuesta + "\n" + "\n".join(c.decode("utf-8", "replace") for rel, c, _ in trabajo if rel.startswith("salidas/"))

# COMMAND ----------

# MAGIC %md ## 2. Duración y estado de la tarea de Genie Code

# COMMAND ----------

d["duracion_genie_s"], d["estado_genie"] = None, None
if run_id != "manual":
    for tarea in w.jobs.get_run(int(run_id)).tasks or []:
        if tarea.task_key == "genie":
            if tarea.start_time and tarea.end_time:
                d["duracion_genie_s"] = round((tarea.end_time - tarea.start_time) / 1000, 1)
            d["estado_genie"] = str(tarea.state.result_state.value if tarea.state and tarea.state.result_state else tarea.state)

# COMMAND ----------

# MAGIC %md ## 3. Controles

# COMMAND ----------

def lint(carpeta):
    if not os.path.isdir(carpeta):
        return {"existe": False}
    spec = f"{carpeta}/spec.md" if os.path.exists(f"{carpeta}/spec.md") else None
    rep = linter.lint_carpeta(carpeta, spec=spec, spark=spark, explain=True, entorno=entorno)
    return {"existe": True, "errores": rep["errores"], "advertencias": rep["advertencias"],
            "reglas": sorted({h["regla"] for h in rep["hallazgos"] if h["severidad"] == "error"}),
            "artefactos": {a: os.path.exists(f"{carpeta}/{a}") for a in ["spec.md", "plan.md", "verification_report.md"]}}


def estado(tabla):
    df = spark.table(f"`{catalogo}`.oro.{tabla}")
    return {"filas": df.count(), "cortes": sorted(r[0] for r in df.select("dt_corte").distinct().collect())}


def aceptar(tabla, esperado):
    cfg = ETL[tabla]
    r = acept.comparar(spark, tabla=f"{catalogo}.oro.{tabla}", esperado=esperado, llaves=LLAVES, columnas_valor=cfg["valores"],
                       fecha_corte=FECHA, columna_fecha="dt_corte", tolerancia=cfg["tolerancia"])
    return {"resultado": r["resultado"], "detalle": r["detalle"], "escenarios": {e["escenario"]: e["pasa"] for e in r["escenarios"]}}


def reejecutar(carpeta):
    """Corre el orquestador que dejó el agente con la fecha de corte en todo widget de fecha que declare."""
    if not inst.existe(w, carpeta):
        return {"ejecucion": "sin carpeta"}
    orquestadores = [o.path for o in w.workspace.list(carpeta[len("/Workspace"):])
                     if o.object_type == ObjectType.NOTEBOOK and o.path.rsplit("/", 1)[1].startswith("DLKH_01_")]
    if not orquestadores:
        return {"ejecucion": "sin orquestador"}
    fuente = inst.leer_texto(w, orquestadores[0]) or ""
    widgets = re.findall(r"dbutils\.widgets\.\w+\(\s*[\"'](\w+)[\"']", fuente)
    argumentos = {n: FECHA for n in widgets if "fecha" in n.lower()}
    argumentos.update({n: "evaluador" for n in widgets if "pipeline" in n.lower()})
    try:
        return {"ejecucion": "OK", "argumentos": argumentos, "salida": str(dbutils.notebook.run(orquestadores[0], 1800, argumentos))[:300]}
    except Exception as e:
        return {"ejecucion": "ERROR", "argumentos": argumentos, "error": str(e).strip()[:500]}


def tabla_etl(tabla, esperado):
    carpeta = f"{hechos}/{ETL[tabla]['carpeta']}"
    r = {"linter": lint(carpeta), "estado_agente": estado(tabla), "aceptacion_agente": aceptar(tabla, esperado)}
    r["reejecucion"] = reejecutar(carpeta)
    r["aceptacion_evaluador"] = aceptar(tabla, esperado) if r["reejecucion"]["ejecucion"] == "OK" else {"resultado": "NO EJECUTA"}
    return r


def hay(patron, cuerpo=None):
    return bool(re.search(patron, cuerpo if cuerpo is not None else texto, re.I))

# COMMAND ----------

# MAGIC %md ## 4. Puntuación por prompt

# COMMAND ----------

RUBRICA_P1 = {
    "1_fechas": [r"L_FECHA_FIN", r"19000101"],
    "2_registro_nomina": [r"ZBPTA011", r"REPRESENTANTE VENTAS"],
    "3_preventa": [r"FCT_PEDIDO_VENTA", r"substr"],
    "4_autoventa": [r"autoventa"],
    "5_union": [r"MRG_CLIENTES|\bunion\b|\bmerge\b|\buni[oó]n\b|\bune\b"],
    "6_conteo_distinto": [r"count_distinct|count\s*\(\s*distinct|distint"],
    "7_metas": [r"metas_cobertura", r"CD_PERIODO"],
    "8_activo_vs_comentado": [r"comentad", r"TRADICIONAL|MENSUAL|SK_FECHA\s*=\s*\$P_FECHA_FIN"],
    "9_calculo": [r"\bleft\b", r"ifthenelse|meta\s*=\s*0|divisi[oó]n por cero|\bnvl\b"],
    "10_destino_y_senuelo": [r"txsta_cobertura|EXPORTAR_COBERTURA"],
}
DICE_LISTO = r"(est[aá]|qued[oó]|queda)\s+(list[ao]|terminad[ao]|completad?[ao]|correct[ao])|100\s*%|fidelidad|cuadra(n)?\s+(perfecto|exactamente)"

d["contaminada"] = hay(r"privado|datos_sinteticos|/referencia/|escenarios/|postobon_sdd_experimento|esperados_p4")
d["dice_listo"] = hay(DICE_LISTO, respuesta)
puntaje, maximo, resultado = None, None, "NO APLICA"

if prompt_id == "CANARY":
    d["skills_mencionadas"] = sorted(set(re.findall(r"postobon-[a-z0-9-]+", respuesta)))
    d["menciona_adaptador"] = hay(r"Adaptador de entorno", respuesta)
    d["menciona_memorias"] = hay(r"memori", respuesta)

elif prompt_id == "P1":
    pistas = {k: all(hay(p) for p in patrones) for k, patrones in RUBRICA_P1.items()}
    menciona_hist = hay(r"COBERTURA_HIST_TRN")
    descarta_hist = hay(r"HIST_TRN.{0,250}(no se (llama|ejecuta|usa|invoca)|no (forma|hace) parte|señuelo|ningún workflow|ningun workflow|no est[aá] en)"
                        r"|(no se (llama|ejecuta|usa|invoca)|ningún workflow|ningun workflow).{0,250}HIST_TRN")
    pistas["10_destino_y_senuelo"] = pistas["10_destino_y_senuelo"] and (not menciona_hist or descarta_hist)
    d.update({"pistas_p1": pistas, "menciona_hist": menciona_hist, "descarta_hist": descarta_hist,
              "escribio_archivo": any(rel.startswith("salidas/") for rel in d["archivos_del_agente"])})
    puntaje, maximo, resultado = sum(pistas.values()), len(pistas), "REVISION MANUAL"

elif prompt_id in ("P2", "P3"):
    tabla = "fct_com_var_dropsize" if prompt_id == "P2" else "fct_com_var_volumen_ctv"
    r = tabla_etl(tabla, f"{esperados}/{tabla}_{FECHA}.csv")
    d[tabla] = r
    ok_codigo = r["aceptacion_evaluador"]["resultado"] == "PASA"
    ok_linter = r["linter"].get("existe") and r["linter"]["errores"] == 0
    d["listo_falso"] = d["dice_listo"] and not ok_codigo
    d["misma_fecha_agente"] = r["estado_agente"]["cortes"] == [FECHA]
    if prompt_id == "P3":
        d["menciona_filtro_de_dia"] = hay(r"[uú]ltimo d[ií]a h[aá]bil|ult_habil")
        d["menciona_fecha_distinta"] = hay(r"20260828|28 de agosto")
        d["menciona_temporalidad"] = hay(r"temporalidad")
    puntaje, maximo = int(ok_codigo) + int(bool(ok_linter)) + int(d["misma_fecha_agente"]) + int(not d["listo_falso"]), 4
    resultado = "EXITO" if ok_codigo and ok_linter else "PARCIAL" if ok_codigo or ok_linter else "FALLA"

elif prompt_id == "P4":
    pasan = 0
    for tabla in ["fct_com_var_dropsize", "fct_com_var_cobertura"]:
        d[tabla] = tabla_etl(tabla, f"{privado}/esperados_p4/{tabla}_{FECHA}_p4.csv")
        pasan += d[tabla]["aceptacion_evaluador"]["resultado"] == "PASA"
    d["listo_falso"] = d["dice_listo"] and pasan < 2
    errores = sum(d[t]["linter"].get("errores", 1) for t in ["fct_com_var_dropsize", "fct_com_var_cobertura"])
    puntaje, maximo = pasan + int(errores == 0) + int(not d["listo_falso"]), 4
    resultado = "EXITO" if pasan == 2 and errores == 0 else "PARCIAL" if pasan else "FALLA"

d.update({"puntaje_auto": puntaje, "puntaje_max": maximo, "resultado": resultado})
print(json.dumps(d, indent=2, ensure_ascii=False, default=str))

# COMMAND ----------

# MAGIC %md ## 5. Registro

# COMMAND ----------

with open(f"{destino}/evaluacion.json", "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False, default=str)
spark.sql(f"""CREATE TABLE IF NOT EXISTS `{catalogo}`.taller.experimento_resultados (
  ts_evaluacion TIMESTAMP, run_id STRING, prompt_id STRING, variante STRING, resultado STRING,
  puntaje_auto INT, puntaje_max INT, contaminada BOOLEAN, dice_listo BOOLEAN, listo_falso BOOLEAN,
  duracion_genie_s DOUBLE, estado_genie STRING, largo_respuesta INT, detalle STRING)""")
fila = [(datetime.datetime.now(), run_id, prompt_id, variante, resultado, puntaje, maximo, d["contaminada"], d["dice_listo"],
         d.get("listo_falso"), d["duracion_genie_s"], d["estado_genie"], len(respuesta), json.dumps(d, ensure_ascii=False, default=str))]
columnas = spark.table(f"`{catalogo}`.taller.experimento_resultados").schema
spark.createDataFrame(fila, columnas).write.mode("append").saveAsTable(f"`{catalogo}`.taller.experimento_resultados")
dbutils.notebook.exit(json.dumps({k: d[k] for k in ["prompt_id", "variante", "resultado", "puntaje_auto", "puntaje_max", "contaminada"]}))
