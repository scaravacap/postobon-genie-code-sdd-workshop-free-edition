"""Pruebas de aceptación deterministas para un ETL de capa oro.

Compara la tabla que produjo el ETL contra un resultado esperado (CSV o tabla) con
las mismas fechas de corte, llave por llave, y escribe verification_report.md.
Ninguna conclusión sale de un modelo: todo sale de queries que quedan en el reporte.

Uso desde una skill o un notebook de Databricks:
    import aceptacion as acept
    r = acept.revisar_fuentes(spark, ["cat.plata.tabla_a", ("cat.oro.fct_b", "sk_fecha")], max_dias=3)
    print(acept.formatear_fuentes(r))
    res = acept.comparar(spark, tabla="cat.oro.fct_x", esperado="/Volumes/cat/taller/archivos/esperados/x.csv",
                         llaves=["cd_planta", "cd_registro_nomina"], columnas_valor=["vl_venta_total"],
                         fecha_corte="20260831", columna_fecha="dt_corte", tolerancia=0.01)
    print(acept.formatear(res))
    acept.escribir_reporte(ruta, titulo=..., spec=..., plan=..., linter=rep, ejecucion=salida, aceptacion=res)

Requiere una sesión de Spark (Databricks). Las funciones que arman SQL no la necesitan.
"""
import datetime
import json
import os

VERSION = "1.0"


# ---------------------------------------------------------------- SQL


def _q(nombre):
    return "`" + nombre.replace("`", "``") + "`"


def _norm_fecha(col):
    return f"regexp_replace(cast({col} as string), '-', '')"


def sql_fechas(vista, columna_fecha):
    return f"SELECT {_norm_fecha(_q(columna_fecha))} AS fecha, count(*) AS filas FROM {vista} GROUP BY 1 ORDER BY 1"


def sql_duplicados(vista, llaves):
    ll = ", ".join(_q(k) for k in llaves)
    return f"SELECT count(*) AS filas, count(DISTINCT {ll}) AS llaves_distintas FROM {vista}"


def sql_comparacion(etl, esperado, llaves, columnas_valor, tolerancias):
    """Full outer join por llave con estado por fila y diferencia por columna."""
    on = " AND ".join(f"e.{_q(k)} <=> x.{_q(k)}" for k in llaves)
    claves = ", ".join(f"coalesce(e.{_q(k)}, x.{_q(k)}) AS {_q(k)}" for k in llaves)
    presencia_e = " AND ".join(f"e.{_q(k)} IS NOT NULL" for k in llaves)
    presencia_x = " AND ".join(f"x.{_q(k)} IS NOT NULL" for k in llaves)
    partes = [claves]
    estado = (
        f"CASE WHEN ({presencia_e}) AND ({presencia_x}) THEN 'ambos' "
        f"WHEN ({presencia_e}) THEN 'solo_etl' ELSE 'solo_esperado' END AS estado"
    )
    partes.append(estado)
    for c in columnas_valor:
        t = tolerancias.get(c, 0.0)
        partes.append(f"e.{_q(c)} AS {_q(c + '__etl')}")
        partes.append(f"x.{_q(c)} AS {_q(c + '__esperado')}")
        partes.append(
            f"CASE WHEN e.{_q(c)} IS NULL AND x.{_q(c)} IS NULL THEN false "
            f"WHEN e.{_q(c)} IS NULL OR x.{_q(c)} IS NULL THEN true "
            f"ELSE abs(e.{_q(c)} - x.{_q(c)}) > {t} + 1e-9 END AS {_q(c + '__difiere')}"
        )
    return f"SELECT {', '.join(partes)} FROM {etl} e FULL OUTER JOIN {esperado} x ON {on}"


def sql_resumen(comparacion, columnas_valor):
    partes = [
        "count_if(estado = 'ambos') AS ambos",
        "count_if(estado = 'solo_etl') AS solo_etl",
        "count_if(estado = 'solo_esperado') AS solo_esperado",
    ]
    for c in columnas_valor:
        partes += [
            f"count_if(estado = 'ambos' AND {_q(c + '__difiere')}) AS {_q(c + '__distintos')}",
            f"sum({_q(c + '__etl')}) AS {_q(c + '__total_etl')}",
            f"sum({_q(c + '__esperado')}) AS {_q(c + '__total_esperado')}",
        ]
    return f"SELECT {', '.join(partes)} FROM {comparacion}"


def _preparar(spark, fuente, llaves, columnas_valor, columna_fecha, fecha_corte, vista):
    """Lee la tabla o el CSV, castea llaves a string y valores a double, filtra la fecha de corte."""
    if fuente.lower().endswith(".csv"):
        df = spark.read.option("header", True).option("inferSchema", False).csv(fuente)
    else:
        df = spark.table(fuente)
    columnas = {c.lower(): c for c in df.columns}
    faltan = [c for c in list(llaves) + list(columnas_valor) if c.lower() not in columnas]
    if faltan:
        raise ValueError(f"{fuente} no tiene las columnas {faltan}. Tiene: {df.columns}")
    df.createOrReplaceTempView(vista + "_crudo")
    tiene_fecha = bool(columna_fecha and columna_fecha.lower() in columnas)
    seleccion = [f"trim(cast({_q(columnas[k.lower()])} as string)) AS {_q(k)}" for k in llaves]
    seleccion += [f"cast({_q(columnas[c.lower()])} as double) AS {_q(c)}" for c in columnas_valor]
    if tiene_fecha:
        seleccion.append(f"{_q(columnas[columna_fecha.lower()])} AS {_q(columna_fecha)}")
    sql = f"SELECT {', '.join(seleccion)} FROM {vista}_crudo"
    if tiene_fecha and fecha_corte:
        sql += f" WHERE {_norm_fecha(_q(columnas[columna_fecha.lower()]))} = '{fecha_corte}'"
    spark.sql(sql).createOrReplaceTempView(vista)
    return tiene_fecha, sql


# ---------------------------------------------------------------- fuentes


def revisar_fuentes(spark, tablas, max_dias=3, contar=True):
    """Existencia, filas, última modificación y fecha máxima de cada fuente.

    `tablas` es una lista de nombres o de tuplas (nombre, columna_fecha).
    """
    ahora = datetime.datetime.now(datetime.timezone.utc)
    salida = []
    for t in tablas:
        nombre, col = (t, None) if isinstance(t, str) else (t[0], t[1])
        fila = {"tabla": nombre, "estado": "", "filas": None, "ultima_modificacion": "", "dias": None, "fecha_max": "", "detalle": ""}
        try:
            det = spark.sql(f"DESCRIBE DETAIL {nombre}").first().asDict()
            mod = det.get("lastModified")
            if mod is not None:
                if mod.tzinfo is None:
                    mod = mod.replace(tzinfo=datetime.timezone.utc)
                fila["ultima_modificacion"] = mod.strftime("%Y-%m-%d %H:%M UTC")
                fila["dias"] = round((ahora - mod).total_seconds() / 86400, 1)
            if contar:
                fila["filas"] = spark.table(nombre).count()
            if col:
                fila["fecha_max"] = str(spark.sql(f"SELECT max({_q(col)}) AS m FROM {nombre}").first()["m"])
            if fila["filas"] == 0:
                fila["estado"] = "VACIA"
            elif fila["dias"] is not None and fila["dias"] > max_dias:
                fila["estado"] = "DESACTUALIZADA"
            else:
                fila["estado"] = "OK"
        except Exception as e:  # el mensaje de Spark es la evidencia
            texto = str(e).split("\n")[0][:300]
            fila["estado"] = "NO EXISTE" if "TABLE_OR_VIEW_NOT_FOUND" in str(e) or "not found" in str(e).lower() else "ERROR"
            fila["detalle"] = texto
        salida.append(fila)
    return {"max_dias": max_dias, "fuentes": salida, "fecha": ahora.strftime("%Y-%m-%d %H:%M UTC")}


def formatear_fuentes(r):
    s = [f"Fuentes revisadas {r['fecha']} (umbral {r['max_dias']} días)", "", "| Tabla | Estado | Filas | Última modificación | Días | Fecha máx | Detalle |", "|---|---|---|---|---|---|---|"]
    for f in r["fuentes"]:
        s.append(
            f"| {f['tabla']} | {f['estado']} | {f['filas'] if f['filas'] is not None else '-'} | {f['ultima_modificacion'] or '-'} | "
            f"{f['dias'] if f['dias'] is not None else '-'} | {f['fecha_max'] or '-'} | {f['detalle'] or '-'} |"
        )
    return "\n".join(s)


# ---------------------------------------------------------------- comparación


def comparar(spark, tabla, esperado, llaves, columnas_valor, fecha_corte=None, columna_fecha=None, tolerancia=0.01, ejemplos=10):
    """Compara `tabla` (lo que produjo el ETL) contra `esperado` (CSV o tabla).

    `tolerancia` es absoluta: un número para todas las columnas o un dict por columna.
    Si las fechas de corte no coinciden, no compara y lo dice.
    """
    tolerancias = tolerancia if isinstance(tolerancia, dict) else {c: tolerancia for c in columnas_valor}
    res = {
        "version": VERSION,
        "tabla": tabla,
        "esperado": esperado,
        "llaves": list(llaves),
        "columnas_valor": list(columnas_valor),
        "fecha_corte": fecha_corte,
        "columna_fecha": columna_fecha,
        "tolerancias": tolerancias,
        "consultas": [],
        "escenarios": [],
        "fechas_etl": [],
        "fechas_esperado": [],
        "resultado": "",
        "detalle": "",
    }

    def correr(sql):
        res["consultas"].append(sql)
        return spark.sql(sql).collect()

    if columna_fecha:
        for fuente, vista, campo in ((tabla, "__acept_fechas_etl", "fechas_etl"), (esperado, "__acept_fechas_esp", "fechas_esperado")):
            df = spark.read.option("header", True).csv(fuente) if fuente.lower().endswith(".csv") else spark.table(fuente)
            if columna_fecha.lower() in [c.lower() for c in df.columns]:
                df.createOrReplaceTempView(vista)
                res[campo] = [(r["fecha"], r["filas"]) for r in correr(sql_fechas(vista, columna_fecha))]
    _, sql_etl = _preparar(spark, tabla, llaves, columnas_valor, columna_fecha, fecha_corte, "__acept_etl")
    _, sql_esp = _preparar(spark, esperado, llaves, columnas_valor, columna_fecha, fecha_corte, "__acept_esp")
    res["consultas"] += [sql_etl, sql_esp]

    n_etl = correr("SELECT count(*) AS n FROM __acept_etl")[0]["n"]
    n_esp = correr("SELECT count(*) AS n FROM __acept_esp")[0]["n"]
    res["filas_etl"], res["filas_esperado"] = n_etl, n_esp

    fechas_ok = True
    if fecha_corte and columna_fecha:
        en_etl = [f for f, _ in res["fechas_etl"]]
        if n_etl == 0:
            fechas_ok = False
            res["detalle"] = (
                f"El ETL no tiene filas con {columna_fecha} = {fecha_corte}; tiene {en_etl or 'ninguna fecha'}. "
                "No comparo: con fechas distintas cualquier diferencia es esperable."
            )
        if res["fechas_esperado"] and n_esp == 0:
            fechas_ok = False
            res["detalle"] = f"El esperado no tiene filas con {columna_fecha} = {fecha_corte}."
    res["escenarios"].append(
        {
            "escenario": "mismas_fechas",
            "pasa": fechas_ok,
            "evidencia": f"ETL: {res['fechas_etl'] or 'sin columna de fecha'}; esperado: {res['fechas_esperado'] or 'sin columna de fecha'}; corte pedido: {fecha_corte}",
        }
    )
    if not fechas_ok:
        res["resultado"] = "NO COMPARABLE"
        return res

    dup_etl = correr(sql_duplicados("__acept_etl", llaves))[0]
    dup_esp = correr(sql_duplicados("__acept_esp", llaves))[0]
    spark.sql(sql_comparacion("__acept_etl", "__acept_esp", llaves, columnas_valor, tolerancias)).createOrReplaceTempView("__acept_cmp")
    res["consultas"].append(sql_comparacion("__acept_etl", "__acept_esp", llaves, columnas_valor, tolerancias))
    resumen = correr(sql_resumen("__acept_cmp", columnas_valor))[0].asDict()
    res["resumen"] = resumen

    duplicadas = (dup_etl["filas"] - dup_etl["llaves_distintas"]) + (dup_esp["filas"] - dup_esp["llaves_distintas"])
    llaves_ok = resumen["solo_etl"] == 0 and resumen["solo_esperado"] == 0 and duplicadas == 0
    res["escenarios"].append(
        {
            "escenario": "mismas_llaves",
            "pasa": llaves_ok,
            "evidencia": f"ambos {resumen['ambos']}, solo ETL {resumen['solo_etl']}, solo esperado {resumen['solo_esperado']}, "
            f"llaves duplicadas ETL {dup_etl['filas'] - dup_etl['llaves_distintas']}, esperado {dup_esp['filas'] - dup_esp['llaves_distintas']}",
        }
    )
    totales_ok, valores_ok, ev_tot, ev_val = True, True, [], []
    for c in columnas_valor:
        te, tx = resumen[c + "__total_etl"] or 0.0, resumen[c + "__total_esperado"] or 0.0
        t = tolerancias.get(c, 0.0)
        margen = max(t * max(n_etl, n_esp, 1), t)
        if abs(te - tx) > margen:
            totales_ok = False
        ev_tot.append(f"{c}: ETL {te:,.4f} vs esperado {tx:,.4f} (dif {te - tx:,.4f})")
        d = resumen[c + "__distintos"]
        if d:
            valores_ok = False
        ev_val.append(f"{c}: {d} llaves con diferencia > {t}")
    res["escenarios"].append({"escenario": "mismos_totales", "pasa": totales_ok, "evidencia": "; ".join(ev_tot)})
    res["escenarios"].append({"escenario": "mismos_valores_por_llave", "pasa": valores_ok, "evidencia": "; ".join(ev_val)})

    filtros = ["estado <> 'ambos'"] + [f"{_q(c + '__difiere')}" for c in columnas_valor]
    sql_ej = f"SELECT * FROM __acept_cmp WHERE {' OR '.join(filtros)} ORDER BY estado, {', '.join(_q(k) for k in llaves)} LIMIT {int(ejemplos)}"
    res["ejemplos"] = [r.asDict() for r in correr(sql_ej)]
    aprobados = sum(1 for e in res["escenarios"] if e["pasa"])
    res["resultado"] = "PASA" if aprobados == len(res["escenarios"]) else "NO PASA"
    res["detalle"] = f"{aprobados} de {len(res['escenarios'])} escenarios"
    return res


def formatear(res):
    s = [
        f"Aceptación: {res['resultado']} ({res.get('detalle', '')})",
        f"Tabla: {res['tabla']}  Esperado: {res['esperado']}",
        f"Llaves: {', '.join(res['llaves'])}  Corte: {res['fecha_corte'] or '-'} en {res['columna_fecha'] or '-'}",
        f"Filas ETL: {res.get('filas_etl', '-')}  Filas esperado: {res.get('filas_esperado', '-')}",
        "",
        "| Escenario | Resultado | Evidencia |",
        "|---|---|---|",
    ]
    for e in res["escenarios"]:
        s.append(f"| {e['escenario']} | {'PASA' if e['pasa'] else 'NO PASA'} | {e['evidencia']} |")
    if res.get("ejemplos"):
        s += ["", f"Primeras {len(res['ejemplos'])} diferencias:", ""]
        cols = list(res["ejemplos"][0].keys())
        s += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for fila in res["ejemplos"]:
            s.append("| " + " | ".join("" if fila[c] is None else str(fila[c]) for c in cols) + " |")
    return "\n".join(s)


# ---------------------------------------------------------------- reporte


def escribir_reporte(ruta, titulo, spec=None, plan=None, linter=None, ejecucion=None, aceptacion=None, no_verificado=None, cambios=None, ejecutor=None):
    """Escribe verification_report.md con la estructura de la plantilla. Devuelve la ruta."""
    escenarios = (aceptacion or {}).get("escenarios", [])
    pasa_linter = linter is not None and linter.get("errores", 1) == 0
    pasa_acept = aceptacion is not None and aceptacion.get("resultado") == "PASA"
    total = len(escenarios) + 1
    aprobados = sum(1 for e in escenarios if e["pasa"]) + (1 if pasa_linter else 0)
    resultado = "PASA" if pasa_linter and pasa_acept else "NO PASA"
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    s = [
        f"# Verification report: {titulo}",
        "",
        f"**Resultado:** {resultado} ({aprobados} de {total} comprobaciones)",
        f"**Fecha:** {ahora}",
        f"**Ejecutó:** {ejecutor or 'Genie Code con la skill postobon-etl-verificacion'}",
        f"**Spec:** {spec or 'no indicada'}",
        f"**Plan:** {plan or 'no indicado'}",
        "",
        "Este reporte lo escriben scripts deterministas (conf_linter.py, aceptacion.py). Cada resultado trae su evidencia.",
        "",
        "## 1. Archivos verificados",
        "",
        "| Archivo | sha256 (12) | Líneas |",
        "|---|---|---|",
    ]
    for a in (linter or {}).get("archivos", []):
        s.append(f"| {a['rel']} | {a['sha256'][:12]} | {a['lineas']} |")
    s += ["", "## 2. Linter", ""]
    if linter is None:
        s.append("No se corrió el linter.")
    else:
        s.append(f"{linter['resultado']}: {linter['errores']} errores, {linter['advertencias']} advertencias.")
        if linter["hallazgos"]:
            s += ["", "| Severidad | Regla | Archivo | Línea | Detalle |", "|---|---|---|---|---|"]
            for x in linter["hallazgos"]:
                s.append(f"| {x['severidad']} | {x['regla']} | {x['archivo']} | {x['linea'] or '-'} | {x['detalle'].replace('|', '/')} |")
    s += ["", "## 3. Ejecución", ""]
    if ejecucion is None:
        s.append("No se ejecutó el notebook.")
    elif isinstance(ejecucion, dict):
        for k, v in ejecucion.items():
            s.append(f"- **{k}:** {v}")
    else:
        s.append(f"- Salida del notebook: {ejecucion}")
    s += ["", "## 4. Aceptación", ""]
    if aceptacion is None:
        s.append("No se corrió la aceptación.")
    else:
        s.append(f"- Corte: {aceptacion['fecha_corte']} en `{aceptacion['columna_fecha']}`")
        s.append(f"- Fechas en la tabla del ETL: {aceptacion['fechas_etl'] or '-'}")
        s.append(f"- Fechas en el esperado: {aceptacion['fechas_esperado'] or '-'}")
        s.append(f"- Filas: ETL {aceptacion.get('filas_etl', '-')}, esperado {aceptacion.get('filas_esperado', '-')}")
        s += ["", "| Escenario | Resultado | Evidencia |", "|---|---|---|"]
        for e in escenarios:
            s.append(f"| {e['escenario']} | {'PASA' if e['pasa'] else 'NO PASA'} | {e['evidencia']} |")
        if aceptacion.get("ejemplos"):
            s += ["", "Primeras diferencias:", "", "```", json.dumps(aceptacion["ejemplos"], ensure_ascii=False, default=str, indent=1), "```"]
        s += ["", "<details><summary>Consultas usadas</summary>", "", "```sql"] + [q + ";" for q in aceptacion["consultas"]] + ["```", "</details>"]
    s += ["", "## 5. Lo que NO se verificó", ""]
    for x in no_verificado or ["(nada declarado: revisa si es cierto)"]:
        s.append(f"- {x}")
    s += ["", "## 6. Cambios", ""]
    for x in cambios or ["(nada declarado: compara los sha256 de la sección 1 con los del reporte anterior)"]:
        s.append(f"- {x}")
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(s) + "\n")
    return ruta
