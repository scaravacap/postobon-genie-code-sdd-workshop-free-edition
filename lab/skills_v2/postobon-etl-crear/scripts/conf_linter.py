"""Linter de archivos .conf del estándar de capa oro de Postobón.

Revisa cada .conf con el mismo configparser que usa procesar_tablas(), así que un
'%' sin escapar falla aquí igual que en la ejecución. Además revisa el estándar
(solo SELECT, plantillas, tablas_entrada, carpeta y tipo, catálogo) y, con una
spec, que las fuentes de los INSUMOS estén aprobadas.

Con spark y explain=True, analiza cada query en Spark sin ejecutarla y encuentra
UNRESOLVED_COLUMN, AMBIGUOUS_REFERENCE y tablas inexistentes.

Uso como módulo:
    rep = lint_carpeta(".../DLKHID_X", spec=".../spec.md", spark=spark, explain=True, entorno=entorno)
    print(formatear(rep))
    print(formatear(lint_archivo(".../INSUMOS/config_ins_01_x.conf")))

Uso por línea de comandos (sin explain):
    python conf_linter.py --carpeta .../DLKHID_X [--spec .../spec.md]
    python conf_linter.py --archivo .../config_ins_01_x.conf

Solo usa la biblioteca estándar de Python 3.9+. Las rutas /Workspace/... se leen y se listan
con databricks-sdk, que ya viene en Databricks.
"""
import argparse
import configparser
import hashlib
import os
import re
import sys

VERSION = "1.0"

CARPETAS = {
    "PARAMETROS": {"tipo": "insumo", "prefijo": "config_par_", "schemas": {"stg"}},
    "INSUMOS": {"tipo": "insumo", "prefijo": "config_ins_", "schemas": {"plata", "oro"}},
    "INTERMEDIAS": {"tipo": "intermedia", "prefijo": "config_int_", "schemas": {"stg"}},
    "SALIDAS": {"tipo": "salida", "prefijo": "config_sal_", "schemas": {"oro"}},
}
ORDEN = ["PARAMETROS", "INSUMOS", "INTERMEDIAS", "SALIDAS"]
CLAVES_ENTRADA = ["tipo", "catalogo", "schema", "tabla", "alias", "tablas_entrada"]
PREFIJOS_LEGACY = ("hana", "as4", "sql", "celweb", "celuweb", "db2", "bw")
_RE_PLANTILLA = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")
_RE_DML = re.compile(
    r"\b(INSERT\s+(?:INTO|OVERWRITE)|UPDATE\s+\S+\s+SET|DELETE\s+FROM|MERGE\s+INTO|CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMP\w*\s+)?(?:TABLE|VIEW)|DROP\s+(?:TABLE|VIEW)|ALTER\s+TABLE|TRUNCATE\s+TABLE)\b",
    re.I,
)
_RE_CATALOGO_FIJO = re.compile(r"(?<![{\w])((?:dllo|prbs|prod)_glux|cx_postobon_sdd\w*)\s*\.", re.I)
_RE_FROM = re.compile(r"\b(?:FROM|JOIN)\s+([^\s,()]+)", re.I)
_RE_CTE = re.compile(r"(?:\bWITH|,)\s*(\w+)\s+AS\s*\(", re.I)
_RE_SUBQUERY = re.compile(r"\(\s*SELECT\b", re.I)
_RE_SUBQUERY_FECHA = re.compile(
    r"\(\s*SELECT\s+[\w\s,]+?\s+FROM\s+(?:\{\{\s*catalogo\s*\}\}\.)?(?:stg\.)?par_\w+\s*\)", re.I
)
_RE_FUENTE_SQL = re.compile(r"\{\{\s*catalogo\s*\}\}\.(\w+)\.(\w+)", re.I)


def _hallazgo(severidad, regla, archivo, linea, detalle):
    return {"severidad": severidad, "regla": regla, "archivo": archivo, "linea": linea, "detalle": detalle}


def _sin_cadenas(sql):
    """Quita literales '...', comentarios -- y funciones con FROM interno (EXTRACT, TRIM, SUBSTRING)."""
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    return re.sub(r"\b(EXTRACT|TRIM|SUBSTRING|POSITION|OVERLAY)\s*\([^()]*\)", r"\1()", sql, flags=re.I)


def _porcentajes_sueltos(texto):
    """Posiciones de '%' que configparser no acepta (ni %% ni %(nombre)s)."""
    malos, i = [], 0
    while i < len(texto):
        if texto[i] == "%":
            sig = texto[i + 1] if i + 1 < len(texto) else ""
            if sig == "%":
                i += 2
                continue
            malos.append((i, "%(" if sig == "(" else "%"))
        i += 1
    return malos


def _lista(valor):
    valor = (valor or "").strip().strip("[]")
    return [v.strip().strip("'\"") for v in valor.split(",") if v.strip().strip("'\"")]


def _carpeta_de(ruta):
    partes = os.path.normpath(ruta).split(os.sep)
    for p in reversed(partes[:-1]):
        if p.upper() in CARPETAS:
            return p.upper()
    return None


_WORKSPACE = "/Workspace/"
_cliente = None


def _ws():
    # En serverless, open() y os.listdir sobre /Workspace devuelven lo que el proceso ya había leído,
    # aunque el archivo se haya editado después desde la UI o desde otro proceso. La API da lo vigente.
    global _cliente
    if _cliente is None:
        from databricks.sdk import WorkspaceClient
        _cliente = WorkspaceClient()
    return _cliente


def _leer(ruta):
    if ruta.startswith(_WORKSPACE):
        from databricks.sdk.service.workspace import ExportFormat
        crudo = _ws().workspace.download(ruta[len("/Workspace"):], format=ExportFormat.AUTO).read()
    else:
        with open(ruta, "rb") as f:
            crudo = f.read()
    return crudo, crudo.decode("utf-8", errors="replace")


def _listar(carpeta):
    """Nombres que cuelgan de carpeta, o None si no es una carpeta."""
    if carpeta.startswith(_WORKSPACE):
        from databricks.sdk.errors import NotFound
        from databricks.sdk.service.workspace import ObjectType
        try:
            if _ws().workspace.get_status(carpeta[len("/Workspace"):]).object_type not in (ObjectType.DIRECTORY, ObjectType.REPO):
                return None
            return sorted(o.path.rsplit("/", 1)[1] for o in _ws().workspace.list(carpeta[len("/Workspace"):]))
        except NotFound:
            return None
    return sorted(os.listdir(carpeta)) if os.path.isdir(carpeta) else None


def _existe(ruta):
    if ruta.startswith(_WORKSPACE):
        from databricks.sdk.errors import NotFound
        try:
            _ws().workspace.get_status(ruta[len("/Workspace"):])
            return True
        except NotFound:
            return False
    return os.path.exists(ruta)


def _analizar_archivo(ruta, base=None):
    """Aplica las reglas de un archivo. Devuelve (info, hallazgos)."""
    rel = os.path.relpath(ruta, base) if base else os.path.basename(ruta)
    crudo, texto = _leer(ruta)
    lineas = texto.split("\n")
    info = {
        "ruta": ruta,
        "rel": rel,
        "sha256": hashlib.sha256(crudo).hexdigest(),
        "lineas": len(lineas),
        "carpeta": _carpeta_de(ruta),
        "tipo": None,
        "schema": None,
        "tabla": None,
        "alias": None,
        "tablas_entrada": [],
        "queries": {},
        "fuentes": set(),
        "catalogo": None,
    }
    h = []
    cp = configparser.ConfigParser()
    try:
        cp.read_string(texto, source=rel)
    except configparser.Error as e:
        h.append(_hallazgo("error", "formato", rel, None, f"configparser no puede leer el archivo: {e}"))
        return info, h

    for n, ln in enumerate(lineas, 1):
        malos = _porcentajes_sueltos(ln)
        if not malos or ln.lstrip().startswith(("#", ";")):
            continue
        pista = "escribe %% en lugar de %" if malos[0][1] == "%" else "un %( se interpreta como variable; escribe %%("
        h.append(
            _hallazgo(
                "error", "interpolacion", rel, n,
                f"'%' sin escapar: configparser fallará con \"'%' must be followed by '%' or '('\". {pista}: {ln.strip()[:120]}",
            )
        )
    for seccion in cp.sections():
        for clave in cp[seccion]:
            try:
                cp.get(seccion, clave)
            except configparser.InterpolationError as e:
                if not any(x["regla"] == "interpolacion" for x in h):
                    h.append(_hallazgo("error", "interpolacion", rel, None, f"[{seccion}] {clave}: {type(e).__name__}: {e}"))

    if "Entrada" not in cp:
        h.append(_hallazgo("error", "secciones", rel, None, "falta la sección [Entrada]"))
    if "QUERIES" not in cp:
        h.append(_hallazgo("error", "secciones", rel, None, "falta la sección [QUERIES]"))
    if h and any(x["regla"] in ("formato", "secciones") for x in h):
        return info, h

    entrada = cp["Entrada"]
    for clave in CLAVES_ENTRADA:
        if clave not in entrada:
            h.append(_hallazgo("error", "secciones", rel, None, f"[Entrada] no tiene '{clave}'"))
    raw = lambda k: cp.get("Entrada", k, raw=True, fallback="").strip()
    info.update(
        tipo=raw("tipo").lower(), schema=raw("schema").lower(), tabla=raw("tabla"), alias=raw("alias"),
        tablas_entrada=_lista(raw("tablas_entrada")), catalogo=raw("catalogo"),
    )
    queries = {k: cp.get("QUERIES", k, raw=True) for k in cp["QUERIES"] if re.match(r"query_\d+$", k)}
    if not queries:
        h.append(_hallazgo("error", "secciones", rel, None, "[QUERIES] no tiene ninguna query_N"))
    info["queries"] = queries

    carpeta = info["carpeta"]
    nombre = os.path.basename(ruta)
    if carpeta:
        regla = CARPETAS[carpeta]
        if info["tipo"] != regla["tipo"]:
            h.append(_hallazgo("error", "tipo_carpeta", rel, None, f"está en {carpeta}/ pero dice tipo = {info['tipo'] or '(vacío)'}; debe ser {regla['tipo']}"))
        if not nombre.startswith(regla["prefijo"]):
            h.append(_hallazgo("advertencia", "nombre_archivo", rel, None, f"en {carpeta}/ el nombre empieza por {regla['prefijo']}"))
        elif carpeta != "PARAMETROS" and not re.match(re.escape(regla["prefijo"]) + r"\d{2}_\w+\.conf$", nombre):
            h.append(_hallazgo("advertencia", "nombre_archivo", rel, None, f"el patrón es {regla['prefijo']}##_<nombre>.conf"))
        if info["schema"] and info["schema"] not in regla["schemas"]:
            h.append(_hallazgo("advertencia", "schema", rel, None, f"en {carpeta}/ el schema esperado es {'/'.join(sorted(regla['schemas']))}, no {info['schema']}"))
    else:
        h.append(_hallazgo("advertencia", "tipo_carpeta", rel, None, "el archivo no está en PARAMETROS, INSUMOS, INTERMEDIAS ni SALIDAS"))

    if info["catalogo"] and info["catalogo"].replace(" ", "") != "{{Environment}}_glux":
        h.append(_hallazgo("error", "catalogo", rel, None, f"catalogo = {info['catalogo']}; debe ser {{{{Environment}}}}_glux"))

    alias_stg = info["alias"] or ""
    if carpeta == "INTERMEDIAS" and alias_stg and not alias_stg.startswith("tt_stg_"):
        h.append(_hallazgo("advertencia", "alias_stg", rel, None, f"el alias {alias_stg} de una intermedia empieza por tt_stg_"))
    nombres_propios = [alias_stg] + ([info["tabla"] or ""] if (info["schema"] or "").lower() == "stg" else [])
    for valor in nombres_propios:
        partes = [p for p in valor.lower().split("_") if p]
        sufijo = partes[2:] if valor.lower().startswith("tt_stg_") else partes
        if any(p in PREFIJOS_LEGACY for p in sufijo):
            h.append(_hallazgo("advertencia", "alias_stg", rel, None, f"{valor} lleva un prefijo legacy ({', '.join(PREFIJOS_LEGACY)})"))
            break

    inicio_q = next((i for i, ln in enumerate(lineas) if ln.strip().upper() == "[QUERIES]"), 0)
    for desplazamiento, ln in enumerate(lineas[inicio_q:], inicio_q + 1):
        limpio = _sin_cadenas(ln)
        m = _RE_DML.search(limpio)
        if m:
            h.append(_hallazgo("error", "solo_select", rel, desplazamiento, f"{m.group(1).upper()} en un .conf: el DML va en el notebook orquestador"))
        m = _RE_CATALOGO_FIJO.search(ln)
        if m:
            h.append(_hallazgo("error", "catalogo", rel, desplazamiento, f"catálogo escrito a mano ({m.group(1)}); usa {{{{catalogo}}}}"))
        for p in _RE_PLANTILLA.findall(ln):
            p = p.strip()
            if p.startswith("parametros["):
                if carpeta != "PARAMETROS":
                    h.append(
                        _hallazgo(
                            "error", "parametros_fuera_de_par", rel, desplazamiento,
                            f"{{{{{p}}}}} fuera de PARAMETROS: las fechas calculadas viven en stg.par_*; usa (SELECT <columna> FROM {{{{catalogo}}}}.stg.par_<proceso>)",
                        )
                    )
            elif p not in ("catalogo", "schema", "tabla", "Environment"):
                h.append(_hallazgo("error", "plantilla", rel, desplazamiento, f"plantilla desconocida {{{{{p}}}}}"))

    for nombre_q, sql in queries.items():
        limpio = _sin_cadenas(sql)
        ctes = {c.lower() for c in _RE_CTE.findall(limpio)}
        usados = set()
        for objetivo in _RE_FROM.findall(limpio):
            objetivo = objetivo.strip().rstrip(";")
            if objetivo.startswith("{{") or objetivo.upper() == "SELECT":
                for esq, tab in _RE_FUENTE_SQL.findall(objetivo):
                    info["fuentes"].add(f"{esq.lower()}.{tab.lower()}")
                continue
            if "." in objetivo:
                continue
            if objetivo.lower() in ctes:
                continue
            usados.add(objetivo)
        declarados = {t.lower() for t in info["tablas_entrada"]}
        for u in sorted(usados):
            if u.lower() not in declarados:
                h.append(_hallazgo("error", "tablas_entrada", rel, None, f"{nombre_q} usa {u}, que no está en tablas_entrada"))
        for d in sorted(declarados - {u.lower() for u in usados}):
            h.append(_hallazgo("advertencia", "tablas_entrada", rel, None, f"{d} está en tablas_entrada pero {nombre_q} no la usa"))
        cuerpos_cte = len(re.findall(r"(?:\bWITH|,)\s*\w+\s+AS\s*\(\s*SELECT\b", limpio, re.I))
        n_sub = len(_RE_SUBQUERY.findall(limpio)) - cuerpos_cte - len(_RE_SUBQUERY_FECHA.findall(sql))
        if n_sub > 0:
            h.append(_hallazgo("advertencia", "subquery", rel, None, f"{nombre_q} tiene {n_sub} subquery; el estándar pide CTEs (solo se acepta el escalar de fechas de stg.par_*)"))
    if carpeta == "INSUMOS" and info["schema"] in ("plata", "oro") and info["tabla"]:
        info["fuentes"].add(f"{info['schema']}.{info['tabla'].lower()}")
    if carpeta in ("INTERMEDIAS", "SALIDAS"):
        for fuente in sorted(f for f in info["fuentes"] if not f.startswith("stg.")):
            h.append(_hallazgo("advertencia", "fuente_fuera_de_insumos", rel, None, f"lee {fuente} directo; las fuentes de plata y oro entran por INSUMOS"))
    return info, h


def lint_archivo(ruta):
    """Revisa un solo .conf. Devuelve un reporte."""
    info, h = _analizar_archivo(ruta)
    return _reporte(os.path.dirname(ruta), [info], h)


def _fuentes_spec(ruta_spec):
    """Tablas de la sección 3 de la spec, con su estado: {'plata.x': 'OK', ...}."""
    texto = _leer(ruta_spec)[1]
    m = re.search(r"^##\s*3\b.*?$(.*?)(?=^##\s|\Z)", texto, re.M | re.S)
    if not m:
        return None, texto
    filas = [ln for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(filas) < 2:
        return {}, texto
    cab = [c.strip().lower() for c in filas[0].strip().strip("|").split("|")]
    i_uc = next((i for i, c in enumerate(cab) if "uc" in c or "unity" in c), None)
    i_estado = next((i for i, c in enumerate(cab) if "estado" in c), None)
    fuentes = {}
    for fila in filas[2:]:
        celdas = [c.strip() for c in fila.strip().strip("|").split("|")]
        if i_uc is None or i_uc >= len(celdas):
            continue
        estado = celdas[i_estado].upper() if i_estado is not None and i_estado < len(celdas) else ""
        for esq, tab in re.findall(r"\b(plata|oro|stg)\.(\w+)", celdas[i_uc], re.I):
            fuentes[f"{esq.lower()}.{tab.lower()}"] = estado
    return fuentes, texto


def _renderizar(sql, catalogo, schema, tabla, parametros):
    def reemplazo(m):
        p = m.group(1).strip()
        if p == "catalogo":
            return catalogo
        if p == "schema":
            return schema
        if p == "tabla":
            return tabla
        if p.startswith("parametros["):
            return str(parametros.get(p[len("parametros["):-1].strip(), "19000101"))
        return m.group(0)

    return _RE_PLANTILLA.sub(reemplazo, sql)


def _explain(infos, spark, entorno, h):
    """Analiza cada query en Spark (sin ejecutarla), en el orden de ejecución."""
    producidos = {}
    fallidos = set()
    for info in infos:
        if not info.get("queries") or not info.get("alias"):
            continue
        catalogo = (info["catalogo"] or "").replace("{{Environment}}", entorno or "dllo")
        dependencias = {d.lower() for d in info["tablas_entrada"]}
        caidas = sorted(dependencias & fallidos)
        if caidas:
            h.append(_hallazgo("advertencia", "explain", info["rel"], None, f"no analizada: depende de {', '.join(caidas)}, que falló"))
            fallidos.add(info["alias"].lower())
            continue
        ultimo = None
        try:
            for clave in sorted(info["queries"], key=lambda k: int(k.split("_")[1])):
                texto = info["queries"][clave].replace("%%", "%")
                sql = _renderizar(texto, catalogo, info["schema"], info["tabla"], {})
                for (esq, tab), alias in producidos.items():
                    sql = re.sub(rf"\b{re.escape(catalogo)}\.{esq}\.{tab}\b", alias, sql, flags=re.I)
                ultimo = spark.sql(sql)
            ultimo.limit(0).createOrReplaceTempView(info["alias"])
            if info["schema"] == "stg" and info["tabla"]:
                producidos[("stg", info["tabla"].lower())] = info["alias"]
        except Exception as e:  # el mensaje de Spark es la evidencia
            mensaje = str(e).strip().split("\n")
            codigo = re.search(r"\[([A-Z_]+(?:\.[A-Z_]+)?)\]", str(e))
            detalle = (codigo.group(1) + ": " if codigo else "") + " ".join(mensaje[:2])[:400]
            h.append(_hallazgo("error", "explain", info["rel"], None, detalle))
            fallidos.add(info["alias"].lower())


def lint_carpeta(carpeta, spec=None, spark=None, explain=False, entorno=None):
    """Revisa todos los .conf de una carpeta DLKHID_<NOMBRE>. Devuelve un reporte."""
    h, infos = [], []
    contenido = {sub: _listar(os.path.join(carpeta, sub)) for sub in ORDEN}
    for sub in ORDEN:
        if contenido[sub] is None:
            h.append(_hallazgo("advertencia", "estructura", sub + "/", None, "no existe la subcarpeta"))
    for sub in ORDEN:
        for nombre in contenido[sub] or []:
            if nombre.endswith(".conf"):
                info, hh = _analizar_archivo(os.path.join(carpeta, sub, nombre), carpeta)
                infos.append(info)
                h += hh
    raiz = _listar(carpeta)
    for n in [n for n in raiz or [] if n.endswith(".conf")]:
        h.append(_hallazgo("advertencia", "estructura", n, None, "un .conf fuera de PARAMETROS, INSUMOS, INTERMEDIAS y SALIDAS no se ejecuta"))
    if raiz is not None and not any(n.startswith("DLKH_01_") for n in raiz):
        h.append(_hallazgo("advertencia", "estructura", "-", None, "no encuentro el notebook orquestador DLKH_01_<NOMBRE>"))
    alias_vistos = {}
    for info in infos:
        a = (info.get("alias") or "").lower()
        if a and a in alias_vistos:
            h.append(_hallazgo("error", "alias_duplicado", info["rel"], None, f"alias {a} repetido (también en {alias_vistos[a]})"))
        elif a:
            alias_vistos[a] = info["rel"]
    if spec:
        if not _existe(spec):
            h.append(_hallazgo("error", "spec_fuentes", os.path.basename(spec), None, "no existe la spec indicada"))
        else:
            aprobadas, texto_spec = _fuentes_spec(spec)
            if not re.search(r"APROBADA\s+por", texto_spec, re.I):
                h.append(_hallazgo("advertencia", "spec_estado", os.path.basename(spec), None, "la spec no dice 'APROBADA por <persona>'"))
            if aprobadas is None:
                h.append(_hallazgo("error", "spec_fuentes", os.path.basename(spec), None, "la spec no tiene la sección 3 (fuentes)"))
            else:
                usadas = set()
                for info in infos:
                    for fuente in sorted(info["fuentes"]):
                        if fuente.startswith("stg."):
                            continue
                        usadas.add(fuente)
                        if fuente not in aprobadas:
                            h.append(_hallazgo("error", "spec_fuentes", info["rel"], None, f"lee {fuente}, que no está en la sección 3 de la spec"))
                        elif aprobadas[fuente] and "OK" not in aprobadas[fuente]:
                            h.append(_hallazgo("error", "spec_fuentes", info["rel"], None, f"lee {fuente}, que la spec marca como {aprobadas[fuente]}"))
                for fuente, estado in sorted(aprobadas.items()):
                    if fuente.startswith(("plata.", "oro.")) and fuente not in usadas and "OK" in (estado or "OK"):
                        h.append(_hallazgo("advertencia", "spec_fuentes", "spec.md", None, f"la spec aprueba {fuente} y ningún .conf la lee"))
    if explain:
        if spark is None:
            h.append(_hallazgo("advertencia", "explain", "-", None, "explain=True necesita la sesión spark"))
        else:
            _explain(infos, spark, entorno, h)
    return _reporte(carpeta, infos, h)


def _reporte(carpeta, infos, h):
    errores = sum(1 for x in h if x["severidad"] == "error")
    advertencias = sum(1 for x in h if x["severidad"] == "advertencia")
    return {
        "version_linter": VERSION,
        "carpeta": carpeta,
        "archivos": [
            {k: info[k] for k in ("rel", "sha256", "lineas", "carpeta", "tipo", "alias")} for info in infos
        ],
        "hallazgos": h,
        "errores": errores,
        "advertencias": advertencias,
        "resultado": "PASA" if errores == 0 else "NO PASA",
    }


def formatear(rep):
    s = [
        f"Linter v{rep['version_linter']}: {rep['resultado']} ({rep['errores']} errores, {rep['advertencias']} advertencias, {len(rep['archivos'])} archivos)",
        "",
    ]
    if rep["hallazgos"]:
        s += ["| Severidad | Regla | Archivo | Línea | Detalle |", "|---|---|---|---|---|"]
        for x in sorted(rep["hallazgos"], key=lambda x: (x["severidad"] != "error", x["archivo"], x["linea"] or 0)):
            detalle = x["detalle"].replace("|", "\\|")
            s.append(f"| {x['severidad']} | {x['regla']} | {x['archivo']} | {x['linea'] or '-'} | {detalle} |")
    else:
        s.append("Sin hallazgos.")
    s += ["", "| Archivo | sha256 (12) | Líneas |", "|---|---|---|"]
    for a in rep["archivos"]:
        s.append(f"| {a['rel']} | {a['sha256'][:12]} | {a['lineas']} |")
    return "\n".join(s)


def main(argv=None):
    p = argparse.ArgumentParser(description="Linter de .conf del estándar de capa oro")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--carpeta")
    g.add_argument("--archivo")
    p.add_argument("--spec")
    a = p.parse_args(argv)
    rep = lint_carpeta(a.carpeta, spec=a.spec) if a.carpeta else lint_archivo(a.archivo)
    print(formatear(rep))
    return 0 if rep["errores"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
