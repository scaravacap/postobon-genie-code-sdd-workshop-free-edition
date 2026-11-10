"""Inventario determinista de un ATL de SAP Data Services.

Lee el archivo completo, sin modelo de lenguaje, y devuelve con número de línea:
dataflows, lecturas, consultas (joins, filtros activos y comentados, columnas),
uniones (Merge), transformaciones SQL, cargas, workflows con sus asignaciones
$L_* y el orden de las llamadas. También responde qué dataflow produce cada tabla.

Uso como módulo (desde una skill de Genie Code):
    inv = inventariar("/Workspace/.../archivo.atl")
    print(resumen(inv))
    print(linaje(inv, "TT_STG_COBERTURA"))
    print(detalle_dataflow(inv, "DF_..."))

Uso por línea de comandos:
    python atl_inventario.py archivo.atl --salida carpeta [--linaje TABLA] [--dataflow DF] [--buscar TEXTO]

Solo usa la biblioteca estándar de Python 3.9+.
"""
import argparse
import bisect
import hashlib
import html
import json
import os
import re
import sys

VERSION = "1.0"

_RE_SENTENCIA = re.compile(r"^[ \t]*CREATE[ \t]+(\w+)[ \t]+([^\s(:]+)", re.M)
_RE_ELEMENTO = re.compile(
    r"^GUID::'[^']*'[ \t]+(READ TABLE|READ FILE|READ __BODI_\w+|LOAD TABLE|LOAD FILE|CREATE VIEW|CALL TRANSFORM)\b",
    re.M,
)
_RE_UI_INICIO = re.compile(r"^[ \t]*ALGUIComment\b", re.M | re.I)
_RE_FIN_DF = re.compile(r"^END[ \t]*$", re.M)
_RE_CADENA_UI = re.compile(r'"(\w+)"\s*=\s*\'((?:\\.|[^\'\\])*)\'', re.S)
_RE_ACTA = re.compile(r'"?(ActaName|ActaValue)_(\d+)"?\s*=\s*\'((?:\\.|[^\'\\])*)\'', re.S)
_RE_PARAMS = re.compile(r"::'[^']*'\s*\((.*)\)\s*$")


def _parametros(cab):
    m = _RE_PARAMS.search(cab)
    return re.findall(r"(\$[A-Za-z_]\w*)\s+[A-Za-z]", m.group(1)) if m else []
_RE_LLAMADA = re.compile(r"CALL[ \t]+(PLAN|DATAFLOW)[ \t]+(\w+)::'[^']*'[ \t]*\(([^)]*)\)")
_RE_VAR_DECL = re.compile(r"^[ \t]*(\$[A-Za-z_]\w*)[ \t]+[A-Za-z]+[^;\n]*;", re.M)
_RE_SQL_TEXT = re.compile(r"<sql_text>(.*?)</sql_text>", re.S)
_RE_TABLA_EN_SQL = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w$#]*(?:\.[A-Za-z_][\w$#]*){0,2})", re.I)


# ---------------------------------------------------------------- utilidades


class _Texto:
    """Texto completo con índice de inicio de línea para convertir offsets."""

    def __init__(self, texto):
        self.texto = texto
        self.inicios = [0]
        for m in re.finditer("\n", texto):
            self.inicios.append(m.end())

    def linea(self, offset):
        return bisect.bisect_right(self.inicios, offset)


def _desescapar(valor):
    return valor.replace("\\'", "'").replace("\\\\", "\\")


def _cierre(texto, i):
    """Índice del paréntesis que cierra el que está en texto[i]. Respeta cadenas '...'."""
    profundidad, en_cadena, n = 0, False, len(texto)
    while i < n:
        c = texto[i]
        if en_cadena:
            if c == "\\":
                i += 2
                continue
            if c == "'":
                en_cadena = False
        elif c == "'":
            en_cadena = True
        elif c == "(":
            profundidad += 1
        elif c == ")":
            profundidad -= 1
            if profundidad == 0:
                return i
        i += 1
    return n - 1


def _corto(nombre):
    """DS.OWNER.TABLA -> TABLA, sin comillas."""
    return nombre.strip().strip('"').split(".")[-1].strip('"').upper()


def _archivo(nombre):
    """FF_FORMATO."archivo.csv" -> ('ARCHIVO:FF_FORMATO', 'archivo.csv')."""
    m = re.match(r'\s*([\w$]+)\s*\.\s*"?(.*?)"?\s*$', nombre)
    if not m:
        return "ARCHIVO:" + nombre.strip().strip('"').upper(), ""
    return "ARCHIVO:" + m.group(1).upper(), m.group(2)


def _partir_lineas(texto):
    activas, comentadas = [], []
    for ln in texto.splitlines():
        s = ln.strip()
        if not s:
            continue
        (comentadas if s.startswith("#") else activas).append(s)
    return " ".join(activas), comentadas


def _comentadas_con_linea(crudo, offset, doc):
    """Líneas que empiezan con # dentro de un valor crudo, con su número de línea real."""
    salida, pos = [], 0
    for ln in crudo.split("\n"):
        s = ln.strip()
        if s.startswith("#"):
            salida.append({"linea": doc.linea(offset + pos), "texto": _recortar(_desescapar(s), 300)})
        pos += len(ln) + 1
    return salida


_RE_VALOR = r'"{}"\s*=\s*\'((?:\\.|[^\'\\])*)\''


def _cadenas_ui(texto):
    return {k: _desescapar(v) for k, v in _RE_CADENA_UI.findall(texto)}


def _recortar(s, n=400):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[: n - 3] + "..."


# ---------------------------------------------------------------- dataflows


def _parsear_columnas_vista(texto, base, doc):
    """Columnas de CREATE VIEW Q( ... ) AS. Devuelve (columnas, offset_fin_lista)."""
    m = re.search(r"CREATE VIEW\s+(\w+)\s*\(", texto)
    i = m.end()
    fin_lista = _cierre(texto, m.end() - 1)
    columnas = []
    patron = re.compile(
        r'\s*,?\s*("[^"]+"|\w+)\s+([A-Za-z_]\w*(?:\s*\(\s*\d+\s*(?:,\s*\d+\s*)?\))?)\s*(?:(?:NOT\s+NULL|NULL|KEY)\s*)*'
    )
    re_mapeo = re.compile(_RE_VALOR.format("ui_mapping_text"), re.S)
    while i < fin_lista:
        mm = patron.match(texto, i)
        if not mm or mm.end() == i:
            break
        nombre, tipo = mm.group(1).strip('"'), re.sub(r"\s+", "", mm.group(2))
        j = mm.end()
        mapeo, comentado = "", []
        if texto.startswith("SET", j):
            k = texto.index("(", j)
            fin_set = _cierre(texto, k)
            m_val = re_mapeo.search(texto, k, fin_set + 1)
            if m_val:
                mapeo, _ = _partir_lineas(_desescapar(m_val.group(1)))
                comentado = _comentadas_con_linea(m_val.group(1), base + m_val.start(1), doc)
            j = fin_set + 1
        columnas.append(
            {
                "nombre": nombre,
                "tipo": tipo,
                "linea": doc.linea(base + mm.start(1)),
                "mapeo_activo": mapeo,
                "mapeo_comentado": comentado,
            }
        )
        i = j
    return m.group(1), columnas, fin_lista


def _parsear_select(select):
    """Separa FROM, joins, WHERE y GROUP BY del SELECT compilado de una vista."""
    on_ui = [_desescapar(v) for v in re.findall(r"SET\(\s*\"ui_on_text\"\s*=\s*'((?:\\.|[^'\\])*)'\s*\)", select, re.S)]
    limpio = re.sub(r"SET\(\s*\"ui_on_text\"\s*=\s*'(?:\\.|[^'\\])*'\s*\)", " ", select, flags=re.S)
    resultado = {"desde": [], "joins": [], "where": "", "group_by": "", "order_by": ""}
    m_from = re.search(r"\bFROM\b", limpio)
    if not m_from:
        return resultado
    resto = limpio[m_from.end():]
    cortes = {}
    for clave, patron in (("where", r"\bWHERE\b"), ("group_by", r"\bGROUP BY\b"), ("order_by", r"\bORDER BY\b")):
        mm = re.search(patron, resto)
        if mm:
            cortes[clave] = mm
    fin_from = min([mm.start() for mm in cortes.values()] + [len(resto)])
    zona_from = resto[:fin_from]
    orden = sorted(cortes.items(), key=lambda kv: kv[1].start())
    for idx, (clave, mm) in enumerate(orden):
        fin = orden[idx + 1][1].start() if idx + 1 < len(orden) else len(resto)
        resultado[clave] = _recortar(resto[mm.end():fin], 2000)
    partes = re.split(r"__SAP_(INNER|LEFT_OUTER|RIGHT_OUTER|FULL_OUTER)_JOIN", zona_from)
    primeras = [p.strip() for p in partes[0].split(",") if p.strip()]
    resultado["desde"] = [p.split()[0] for p in primeras]
    n_on = 0
    for k in range(1, len(partes), 2):
        tipo = partes[k].replace("_", " ")
        cuerpo = partes[k + 1].strip()
        tabla = cuerpo.split()[0] if cuerpo.split() else ""
        on = ""
        p_on = cuerpo.find("ON")
        if p_on >= 0:
            a = cuerpo.find("(", p_on)
            if a >= 0:
                on = cuerpo[a + 1 : _cierre(cuerpo, a)]
        resultado["joins"].append(
            {"tipo": tipo, "tabla": tabla, "on": _recortar(on, 600), "on_ui": _recortar(on_ui[n_on], 600) if n_on < len(on_ui) else ""}
        )
        n_on += 1
    return resultado


def _parsear_elemento(tipo, texto, ui, base, doc, df):
    linea = doc.linea(base)
    props_ui = _cadenas_ui(ui) if ui else {}
    if tipo.startswith("READ"):
        m = re.search(r"READ\s+(?:TABLE|FILE|__BODI_\w+)\s+(\S+)\s+OUTPUT\((\w+)\)", texto)
        if m:
            tabla = m.group(1)
            corto, archivo = _archivo(tabla) if ("FILE" in tipo or "BODI" in tipo) else (_corto(tabla), "")
            df["lecturas"].append(
                {"tabla": tabla, "tabla_corta": corto, "archivo": archivo, "alias": m.group(2), "tipo": tipo, "linea": linea}
            )
    elif tipo.startswith("LOAD"):
        m = re.search(r"LOAD\s+(?:TABLE|FILE)\s+(\S+(?:\s+\S+)?)\s+INPUT\((\w+)\)", texto)
        if m:
            tabla = m.group(1).split(" INPUT")[0]
            modo = re.search(r"<loader_load_choice>(\w+)</loader_load_choice>", texto) or re.search(
                r'"loader_load_choice"\s*=\s*\'(\w+)\'', texto
            )
            recrea = re.search(r"<loader_drop_and_create_table>(\w+)<", texto)
            corto, archivo = _archivo(tabla) if "FILE" in tipo else (_corto(tabla), "")
            df["cargas"].append(
                {
                    "tabla": tabla,
                    "tabla_corta": corto,
                    "archivo": archivo,
                    "entrada": m.group(2),
                    "tipo": tipo,
                    "modo": modo.group(1) if modo else "",
                    "drop_and_create": recrea.group(1) if recrea else "",
                    "linea": linea,
                }
            )
    elif tipo == "CREATE VIEW":
        nombre, columnas, fin_lista = _parsear_columnas_vista(texto, base, doc)
        resto = texto[fin_lista + 1 :]
        m_sel = re.search(r"\bSELECT\b", resto)
        select = ""
        if m_sel:
            cuerpo = resto[m_sel.start():]
            m_set = list(re.finditer(r"^SET\(", cuerpo, re.M))
            select = cuerpo[: m_set[-1].start()] if m_set else cuerpo
        partes = _parsear_select(select)
        where_ui_activo, where_comentado = "", []
        m_where = re.search(_RE_VALOR.format("ui_where_text"), ui, re.S) if ui else None
        if m_where:
            where_ui_activo, _ = _partir_lineas(_desescapar(m_where.group(1)))
            where_comentado = _comentadas_con_linea(m_where.group(1), base - len(ui) + m_where.start(1), doc)
        df["consultas"].append(
            {
                "nombre": nombre,
                "linea": linea,
                "linea_fin": doc.linea(base + len(texto) - 1),
                "columnas": columnas,
                "desde": partes["desde"],
                "joins": partes["joins"],
                "where_activo": partes["where"],
                "where_ui": _recortar(where_ui_activo, 1000),
                "where_comentado": where_comentado,
                "group_by": partes["group_by"],
                "distinct": bool(re.match(r"SELECT\s+DISTINCT", select.strip())),
            }
        )
    elif tipo == "CALL TRANSFORM":
        m = re.search(r"CALL TRANSFORM\s+(\w+)\(\)\s*(?:INPUT\(([^)]*)\))?\s*OUTPUT\((\w+)", texto)
        if not m:
            return
        clase, entradas, salida = m.group(1), m.group(2) or "", m.group(3)
        entradas = [e.strip() for e in entradas.split(",") if e.strip()]
        if clase == "Merge":
            df["uniones"].append({"nombre": salida, "entradas": entradas, "linea": linea})
        elif clase == "SQL":
            textos = [html.unescape(t) for t in _RE_SQL_TEXT.findall(texto) if t.strip()]
            sql = _desescapar(textos[0]) if textos else ""
            ds = re.search(r'"database_datastore"\s*=\s*\'([^\']*)\'', texto)
            tablas = sorted({_corto(t) for t in _RE_TABLA_EN_SQL.findall(sql)})
            proc = re.search(r"\bEXEC(?:UTE)?\s+([\w.\[\]]+)", sql, re.I)
            if not tablas and proc:
                tablas = ["PROC:" + _corto(proc.group(1).replace("[", "").replace("]", ""))]
            df["sql"].append(
                {"nombre": salida, "datastore": ds.group(1) if ds else "", "tablas": tablas, "sql": _recortar(sql, 1500), "linea": linea}
            )
        else:
            df["otras_transformaciones"].append({"clase": clase, "nombre": salida, "entradas": entradas, "linea": linea})


def _parsear_dataflow(nombre, ini, fin, doc):
    texto = doc.texto[ini:fin]
    cab = texto.split("\n", 1)[0]
    df = {
        "nombre": nombre,
        "linea_inicio": doc.linea(ini),
        "linea_fin": doc.linea(fin - 1),
        "parametros": _parametros(cab),
        "descripcion": "",
        "lecturas": [],
        "consultas": [],
        "uniones": [],
        "sql": [],
        "otras_transformaciones": [],
        "cargas": [],
    }
    m_fin = _RE_FIN_DF.search(texto)
    cuerpo_fin = m_fin.start() if m_fin else len(texto)
    elementos = list(_RE_ELEMENTO.finditer(texto, 0, cuerpo_fin))
    for idx, m in enumerate(elementos):
        inicio = m.start()
        siguiente = elementos[idx + 1].start() if idx + 1 < len(elementos) else cuerpo_fin
        segmento = texto[inicio:siguiente]
        m_ui = _RE_UI_INICIO.search(segmento, 1)
        propio = segmento[: m_ui.start()] if m_ui else segmento
        anterior_fin = elementos[idx - 1].start() if idx > 0 else 0
        previo = texto[anterior_fin:inicio]
        m_ui_prev = None
        for mm in _RE_UI_INICIO.finditer(previo):
            m_ui_prev = mm
        ui = previo[m_ui_prev.start():] if m_ui_prev else ""
        _parsear_elemento(m.group(1), propio, ui, ini + inicio, doc, df)
    actas = {}
    for clase, num, valor in _RE_ACTA.findall(texto[cuerpo_fin:]):
        actas.setdefault(num, {})[clase] = _desescapar(valor)
    for par in actas.values():
        if par.get("ActaName") == "RDescription":
            df["descripcion"] = _recortar(par.get("ActaValue", ""), 300)
    return df


# ---------------------------------------------------------------- workflows


def _partir_sentencias(script):
    """Parte un script por ';' respetando cadenas con comillas simples."""
    partes, actual, en_cadena, i = [], [], False, 0
    while i < len(script):
        c = script[i]
        if en_cadena:
            actual.append(c)
            if c == "\\" and i + 1 < len(script):
                actual.append(script[i + 1])
                i += 2
                continue
            if c == "'":
                en_cadena = False
        elif c == "'":
            en_cadena = True
            actual.append(c)
        elif c == ";":
            partes.append("".join(actual).strip())
            actual = []
        else:
            actual.append(c)
        i += 1
    if "".join(actual).strip():
        partes.append("".join(actual).strip())
    return partes


def _bloques_script(texto):
    """(inicio, fin) del contenido de cada BEGIN_SCRIPT ... END, con END fuera de comillas."""
    for m in re.finditer(r"\bBEGIN_SCRIPT\b[ \t]*\r?\n?", texto):
        i, en_cadena, n = m.end(), False, len(texto)
        while i < n:
            c = texto[i]
            if en_cadena:
                if c == "\\":
                    i += 2
                    continue
                if c == "'":
                    en_cadena = False
            elif c == "'":
                en_cadena = True
            elif texto.startswith("END", i) and (i == 0 or not (texto[i - 1].isalnum() or texto[i - 1] in "_$")) and (
                i + 3 >= n or not (texto[i + 3].isalnum() or texto[i + 3] == "_")
            ):
                yield m.end(), i
                break
            i += 1


def _parsear_workflow(clase, nombre, ini, fin, doc):
    texto = doc.texto[ini:fin]
    cab = texto.split("\n", 1)[0]
    wf = {
        "nombre": nombre,
        "clase": clase,
        "linea_inicio": doc.linea(ini),
        "linea_fin": doc.linea(fin - 1),
        "parametros": _parametros(cab),
        "variables": [],
        "asignaciones": [],
        "asignaciones_comentadas": [],
        "comentarios": [],
        "llamadas": [],
    }
    p_begin = re.search(r"^BEGIN\b", texto, re.M)
    decl = texto[: p_begin.start()] if p_begin else ""
    wf["variables"] = sorted(set(_RE_VAR_DECL.findall(decl)))
    wf["scripts"] = 0
    for a_ini, a_fin in _bloques_script(texto):
        wf["scripts"] += 1
        bloque = texto[a_ini:a_fin]
        for sentencia in _partir_sentencias(bloque):
            mm = re.match(r"(\$[A-Za-z_]\w*)\s*=\s*(.+)$", sentencia, re.S)
            if mm:
                var = mm.group(1)
                linea_ui = None
                patron_ui = re.compile(r"(?:^[ \t]*|')" + re.escape(var) + r"\s*=(?!=)", re.M | re.I)
                ui = None
                for ui in patron_ui.finditer(texto, 0, a_ini):
                    pass
                if ui:
                    linea_ui = doc.linea(ini + ui.start())
                expresion = mm.group(2)
                tablas = []
                if re.search(r"\bsql\s*\(", expresion, re.I):
                    tablas = sorted({_corto(t) for t in _RE_TABLA_EN_SQL.findall(_desescapar(expresion))})
                wf["asignaciones"].append(
                    {
                        "variable": var,
                        "expresion": _recortar(expresion, 600),
                        "tablas": tablas,
                        "linea": linea_ui or doc.linea(ini + a_ini),
                    }
                )
    for m in re.finditer(r"(?:^[ \t]*|=\s*')(#(?:\\.|[^'\\\n])*)", texto, re.M):
        contenido = _desescapar(m.group(1)).strip()
        if len(contenido) > 1:
            destino = "asignaciones_comentadas" if re.match(r"#\s*\$[A-Za-z_]\w*\s*=(?!=)", contenido) else "comentarios"
            wf[destino].append({"linea": doc.linea(ini + m.start(1)), "texto": _recortar(contenido, 400)})
    for m in _RE_LLAMADA.finditer(texto):
        inicio_linea = texto.rfind("\n", 0, m.start()) + 1
        if texto[inicio_linea : m.start()].strip().startswith("#"):
            continue
        wf["llamadas"].append(
            {
                "tipo": m.group(1),
                "nombre": m.group(2),
                "argumentos": [a.strip() for a in m.group(3).split(",") if a.strip()],
                "linea": doc.linea(ini + m.start()),
            }
        )
    return wf


# ---------------------------------------------------------------- inventario


def inventariar(ruta):
    """Lee el ATL completo y devuelve el inventario como diccionario."""
    with open(ruta, "rb") as f:
        crudo = f.read()
    texto = crudo.decode("utf-8", errors="replace")
    doc = _Texto(texto)
    sentencias = [(m.start(), m.group(1).upper(), m.group(2)) for m in _RE_SENTENCIA.finditer(texto)]
    inv = {
        "version_script": VERSION,
        "ruta": ruta,
        "sha256": hashlib.sha256(crudo).hexdigest(),
        "bytes": len(crudo),
        "lineas": len(doc.inicios),
        "conteo_sentencias": {},
        "dataflows": [],
        "workflows": [],
        "jobs": [],
        "tablas_definidas": [],
        "codigo_comentado": [],
    }
    for idx, (ini, clase, nombre) in enumerate(sentencias):
        fin = sentencias[idx + 1][0] if idx + 1 < len(sentencias) else len(texto)
        nombre_limpio = nombre.split("::")[0]
        inv["conteo_sentencias"][clase] = inv["conteo_sentencias"].get(clase, 0) + 1
        if clase == "DATAFLOW":
            inv["dataflows"].append(_parsear_dataflow(nombre_limpio, ini, fin, doc))
        elif clase == "PLAN":
            inv["workflows"].append(_parsear_workflow("PLAN", nombre_limpio, ini, fin, doc))
        elif clase == "SESSION":
            inv["jobs"].append(_parsear_workflow("SESSION", nombre_limpio, ini, fin, doc))
        elif clase == "TABLE":
            inv["tablas_definidas"].append({"tabla": nombre_limpio, "tabla_corta": _corto(nombre_limpio), "linea": doc.linea(ini)})
    for df in inv["dataflows"]:
        for q in df["consultas"]:
            for c in q["columnas"]:
                for t in c["mapeo_comentado"]:
                    inv["codigo_comentado"].append(
                        {"linea": t["linea"], "dataflow": df["nombre"], "consulta": q["nombre"], "donde": f"columna {c['nombre']}", "texto": t["texto"]}
                    )
            for t in q["where_comentado"]:
                inv["codigo_comentado"].append(
                    {"linea": t["linea"], "dataflow": df["nombre"], "consulta": q["nombre"], "donde": "filtro", "texto": t["texto"]}
                )
    for wf in inv["workflows"] + inv["jobs"]:
        for a in wf["asignaciones_comentadas"]:
            inv["codigo_comentado"].append({"linea": a["linea"], "dataflow": wf["nombre"], "consulta": "", "donde": "script", "texto": a["texto"]})
        for a in wf["comentarios"]:
            inv["codigo_comentado"].append({"linea": a["linea"], "dataflow": wf["nombre"], "consulta": "", "donde": "script (nota)", "texto": a["texto"]})
    capturadas = {c["linea"] for c in inv["codigo_comentado"]}
    inicios = [s[0] for s in sentencias]
    total, en_valor = 0, set()
    for m in re.finditer(r"^[ \t]*#(?!__AW_).*$|(\"?\w+\"?)\s*=\s*'(#(?:\\.|[^'\\\n])*)", texto, re.M):
        if m.group(2) is None:
            pos, contenido = m.start(), m.group(0).strip()
            total += 1
        else:
            pos, contenido = m.start(2), _desescapar(m.group(2)).strip()
            en_valor.add(doc.linea(pos))
        n = doc.linea(pos)
        if n in capturadas:
            continue
        capturadas.add(n)
        k = bisect.bisect_right(inicios, pos) - 1
        donde = f"{sentencias[k][1].lower()} {sentencias[k][2].split('::')[0]}" if k >= 0 else "cabecera"
        if m.group(1):
            donde += f" ({m.group(1).strip(chr(34))})"
        inv["codigo_comentado"].append({"linea": n, "dataflow": "-", "consulta": "", "donde": donde, "texto": _recortar(contenido, 300)})
    inv["codigo_comentado"].sort(key=lambda c: c["linea"])
    inv["lineas_comentadas_archivo"] = total
    inv["lineas_con_valor_comentado"] = len(en_valor)
    _indexar(inv)
    return inv


def _indexar(inv):
    productores, lectores = {}, {}
    for df in inv["dataflows"]:
        for c in df["cargas"]:
            productores.setdefault(c["tabla_corta"], []).append(df["nombre"])
        for l in df["lecturas"]:
            lectores.setdefault(l["tabla_corta"], []).append(df["nombre"])
        for s in df["sql"]:
            for t in s["tablas"]:
                lectores.setdefault(t, []).append(df["nombre"])
    for wf in inv["workflows"] + inv["jobs"]:
        for a in wf["asignaciones"]:
            for t in a.get("tablas", []):
                lectores.setdefault(t, []).append(wf["nombre"])
    inv["productores"] = {k: sorted(set(v)) for k, v in productores.items()}
    inv["lectores"] = {k: sorted(set(v)) for k, v in lectores.items()}
    inv["orden_ejecucion"] = _orden(inv)


def _orden(inv):
    wfs = {w["nombre"]: w for w in inv["workflows"]}
    orden, visitados = [], set()

    def recorrer(wf, profundidad):
        if wf["nombre"] in visitados or profundidad > 20:
            return
        visitados.add(wf["nombre"])
        for ll in wf["llamadas"]:
            if ll["tipo"] == "DATAFLOW":
                if ll["nombre"] not in orden:
                    orden.append(ll["nombre"])
            elif ll["nombre"] in wfs:
                recorrer(wfs[ll["nombre"]], profundidad + 1)

    raices = inv["jobs"] or inv["workflows"]
    for raiz in raices:
        recorrer(raiz, 0)
    return orden


def _df(inv, nombre):
    for df in inv["dataflows"]:
        if df["nombre"].upper() == nombre.upper():
            return df
    raise KeyError(f"No hay un dataflow llamado {nombre}. Usa buscar(inv, '{nombre}').")


# ---------------------------------------------------------------- consultas


def resumen(inv):
    externas = [t for t in inv["lectores"] if t not in inv["productores"]]
    llamados = set(inv["orden_ejecucion"])
    sin_llamar = [d["nombre"] for d in inv["dataflows"] if d["nombre"] not in llamados]
    lineas = [
        f"ATL: {inv['ruta']}",
        f"sha256: {inv['sha256']}  bytes: {inv['bytes']}  lineas: {inv['lineas']}",
        f"Sentencias: " + ", ".join(f"{k}={v}" for k, v in sorted(inv["conteo_sentencias"].items())),
        f"Dataflows: {len(inv['dataflows'])}  Workflows: {len(inv['workflows'])}  Jobs: {len(inv['jobs'])}",
        f"Lecturas: {sum(len(d['lecturas']) for d in inv['dataflows'])}  Consultas: {sum(len(d['consultas']) for d in inv['dataflows'])}  "
        f"Merge: {sum(len(d['uniones']) for d in inv['dataflows'])}  SQL: {sum(len(d['sql']) for d in inv['dataflows'])}  "
        f"Cargas: {sum(len(d['cargas']) for d in inv['dataflows'])}",
        f"Tablas producidas dentro del ATL: {len(inv['productores'])}  Fuentes externas: {len(externas)}",
        f"Código comentado: {len(inv['codigo_comentado'])} fragmentos ({inv['lineas_comentadas_archivo']} líneas que empiezan con #, "
        f"{inv['lineas_con_valor_comentado']} líneas donde el # abre un valor y grep '^#' no lo ve)",
        f"Orden de ejecución: {len(inv['orden_ejecucion'])} dataflows llamados desde los workflows; {len(sin_llamar)} sin llamar",
    ]
    return "\n".join(lineas)


def linaje(inv, tabla):
    """Cadena de dataflows que produce `tabla`, hasta las fuentes externas."""
    objetivo = _corto(tabla)
    if objetivo not in inv["productores"]:
        lect = inv["lectores"].get(objetivo)
        nota = f" La leen: {', '.join(lect)}." if lect else ""
        return f"Ningún dataflow carga {objetivo}: es una fuente externa o el nombre no coincide.{nota}"
    orden_pos = {n: i for i, n in enumerate(inv["orden_ejecucion"])}
    cadena, pendientes, vistos, externas = [], [objetivo], set(), {}
    while pendientes:
        t = pendientes.pop()
        for nombre_df in inv["productores"].get(t, []):
            if nombre_df in vistos:
                continue
            vistos.add(nombre_df)
            df = _df(inv, nombre_df)
            cadena.append(df)
            leidas = [l["tabla_corta"] for l in df["lecturas"]] + [x for s in df["sql"] for x in s["tablas"]]
            for x in leidas:
                if x in inv["productores"]:
                    pendientes.append(x)
                else:
                    externas.setdefault(x, set()).add(nombre_df)
    cadena.sort(key=lambda d: (orden_pos.get(d["nombre"], 10**6), d["linea_inicio"]))
    salida = [f"## Linaje de {objetivo}", "", "| Orden | Dataflow (líneas) | Lee | Produce | Merge | Comentado |", "|---|---|---|---|---|---|"]
    for d in cadena:
        pos = orden_pos.get(d["nombre"])
        lee = ", ".join(sorted({l["tabla_corta"] for l in d["lecturas"]} | {x for s in d["sql"] for x in s["tablas"]}))
        produce = ", ".join(sorted({c["tabla_corta"] for c in d["cargas"]}))
        merges = "; ".join(f"{u['nombre']} = {' UNION ALL '.join(u['entradas'])} (L{u['linea']})" for u in d["uniones"]) or "-"
        com = sum(len(c["mapeo_comentado"]) for q in d["consultas"] for c in q["columnas"]) + sum(len(q["where_comentado"]) for q in d["consultas"])
        salida.append(
            f"| {pos + 1 if pos is not None else 'sin llamar'} | `{d['nombre']}` (L{d['linea_inicio']}-L{d['linea_fin']}) | {lee} | {produce} | {merges} | {com} |"
        )
    salida += ["", "**Fuentes externas** (ningún dataflow del ATL las produce):", ""]
    for t in sorted(externas):
        salida.append(f"- `{t}` (la lee {', '.join(sorted(externas[t]))})")
    salida += ["", "Para el detalle de cada dataflow: detalle_dataflow(inv, nombre)."]
    return "\n".join(salida)


def detalle_dataflow(inv, nombre):
    d = _df(inv, nombre)
    s = [f"## {d['nombre']} (L{d['linea_inicio']}-L{d['linea_fin']})"]
    if d["descripcion"]:
        s.append(f"Descripción: {d['descripcion']}")
    s.append(f"Parámetros: {', '.join(d['parametros']) or '-'}")
    s += ["", "### Lecturas"]
    for l in d["lecturas"]:
        s.append(f"- L{l['linea']}: `{l['tabla']}` como `{l['alias']}`")
    for x in d["sql"]:
        s.append(f"- L{x['linea']}: transformación SQL `{x['nombre']}` sobre {x['datastore']}: tablas {', '.join(x['tablas']) or '-'}")
        s.append(f"  SQL: {x['sql']}")
    s += ["", "### Consultas"]
    for q in d["consultas"]:
        s.append(f"#### `{q['nombre']}` (L{q['linea']}-L{q['linea_fin']})")
        s.append(f"- Desde: {', '.join(q['desde']) or '-'}{' (DISTINCT)' if q['distinct'] else ''}")
        for j in q["joins"]:
            s.append(f"- {j['tipo']} JOIN `{j['tabla']}` ON {j['on']}")
        if q["where_activo"]:
            s.append(f"- Filtro activo: {q['where_activo']}")
        for t in q["where_comentado"]:
            s.append(f"- Filtro COMENTADO (L{t['linea']}, no aplica): {t['texto']}")
        if q["group_by"]:
            s.append(f"- GROUP BY: {q['group_by']}")
        calculadas = [c for c in q["columnas"] if not re.fullmatch(r"[\w$]+\.[\w$]+", c["mapeo_activo"] or "")]
        if calculadas:
            s.append("- Columnas calculadas:")
            for c in calculadas:
                s.append(f"  - L{c['linea']} `{c['nombre']}` {c['tipo']} = {_recortar(c['mapeo_activo'], 500)}")
        for c in q["columnas"]:
            for t in c["mapeo_comentado"]:
                s.append(f"  - COMENTADO en `{c['nombre']}` (L{t['linea']}, no aplica): {t['texto']}")
        s.append(f"- Columnas: {len(q['columnas'])} ({', '.join(c['nombre'] for c in q['columnas'][:40])}{'...' if len(q['columnas']) > 40 else ''})")
    if d["uniones"]:
        s += ["", "### Uniones (Merge = UNION ALL)"]
        for u in d["uniones"]:
            s.append(f"- L{u['linea']}: `{u['nombre']}` = {' UNION ALL '.join(u['entradas'])}")
    if d["otras_transformaciones"]:
        s += ["", "### Otras transformaciones"]
        for t in d["otras_transformaciones"]:
            s.append(f"- L{t['linea']}: {t['clase']} `{t['nombre']}` desde {', '.join(t['entradas']) or '-'}")
    s += ["", "### Cargas"]
    for c in d["cargas"]:
        s.append(f"- L{c['linea']}: `{c['tabla']}` desde `{c['entrada']}` (modo {c['modo'] or '-'}, drop_and_create {c['drop_and_create'] or '-'})")
    return "\n".join(s)


def buscar(inv, texto, maximo=50):
    """Busca un texto (sin distinguir mayúsculas) en el ATL. Devuelve [(línea, contenido)]."""
    hallazgos = []
    with open(inv["ruta"], encoding="utf-8", errors="replace") as f:
        for n, ln in enumerate(f, 1):
            if texto.lower() in ln.lower():
                hallazgos.append((n, _recortar(ln, 300)))
                if len(hallazgos) >= maximo:
                    break
    return hallazgos


def extraer_lineas(ruta, inicio, fin, ancho=400):
    """Devuelve las líneas [inicio, fin] del archivo con su número. Corta líneas muy largas."""
    salida = []
    with open(ruta, encoding="utf-8", errors="replace") as f:
        for n, ln in enumerate(f, 1):
            if n < inicio:
                continue
            if n > fin:
                break
            ln = ln.rstrip("\n")
            salida.append(f"{n:>6}| {ln if len(ln) <= ancho else ln[:ancho] + ' [...]'}")
    return "\n".join(salida)


def _markdown(inv):
    s = ["# Inventario del ATL", "", "```", resumen(inv), "```", "", f"Generado por atl_inventario.py v{VERSION}. Cada dato cita su línea.", ""]
    s += ["## Orden de ejecución", ""]
    for i, n in enumerate(inv["orden_ejecucion"], 1):
        s.append(f"{i}. `{n}`")
    llamados = set(inv["orden_ejecucion"])
    sin_llamar = [d["nombre"] for d in inv["dataflows"] if d["nombre"] not in llamados]
    if sin_llamar:
        s += ["", "Dataflows definidos que ningún workflow llama: " + ", ".join(f"`{n}`" for n in sin_llamar)]
    s += ["", "## Workflows y variables", ""]
    for w in inv["jobs"] + inv["workflows"]:
        s.append(f"### {w['clase']} `{w['nombre']}` (L{w['linea_inicio']}-L{w['linea_fin']})")
        s.append(f"Parámetros: {', '.join(w['parametros']) or '-'}")
        for a in w["asignaciones"]:
            lee = f" (lee {', '.join(a['tablas'])})" if a.get("tablas") else ""
            s.append(f"- L{a['linea']}: `{a['variable']}` = {a['expresion']}{lee}")
        for a in w["asignaciones_comentadas"]:
            s.append(f"- L{a['linea']} COMENTADO: {a['texto']}")
        if w["llamadas"]:
            s.append("- Llama, en orden: " + ", ".join(f"{c['nombre']}({', '.join(c['argumentos'])})" for c in w["llamadas"]))
        s.append("")
    s += ["## Dataflows", "", "| Dataflow | Líneas | Lee | Produce | Merge | Consultas |", "|---|---|---|---|---|---|"]
    for d in inv["dataflows"]:
        lee = ", ".join(sorted({l["tabla_corta"] for l in d["lecturas"]} | {x for q in d["sql"] for x in q["tablas"]}))
        produce = ", ".join(sorted({c["tabla_corta"] for c in d["cargas"]}))
        s.append(
            f"| `{d['nombre']}` | L{d['linea_inicio']}-L{d['linea_fin']} | {lee} | {produce} | {len(d['uniones'])} | {len(d['consultas'])} |"
        )
    externas = sorted(t for t in inv["lectores"] if t not in inv["productores"])
    s += ["", "## Fuentes externas", "", "Tablas que el ATL lee y que ningún dataflow produce. Cada una necesita su tabla equivalente en Unity Catalog.", ""]
    for t in externas:
        s.append(f"- `{t}`: la leen {', '.join(inv['lectores'][t])}")
    s += ["", "## Tablas producidas dentro del ATL", ""]
    for t in sorted(inv["productores"]):
        s.append(f"- `{t}`: la produce {', '.join(inv['productores'][t])}; la leen {', '.join(inv['lectores'].get(t, [])) or 'ningún dataflow'}")
    s += ["", "## Código comentado (no es lógica activa)", "", "| Línea | Dataflow o workflow | Consulta | Dónde | Texto |", "|---|---|---|---|---|"]
    for c in sorted(inv["codigo_comentado"], key=lambda x: x["linea"]):
        texto = c["texto"].replace("|", "\\|")
        s.append(f"| L{c['linea']} | `{c['dataflow']}` | {c['consulta'] or '-'} | {c['donde']} | `{texto}` |")
    return "\n".join(s) + "\n"


def escribir_reportes(inv, carpeta):
    """Escribe inventario_atl.md e inventario_atl.json en `carpeta`. Devuelve las rutas."""
    os.makedirs(carpeta, exist_ok=True)
    ruta_md = os.path.join(carpeta, "inventario_atl.md")
    ruta_json = os.path.join(carpeta, "inventario_atl.json")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(_markdown(inv))
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=1)
    return ruta_md, ruta_json


def main(argv=None):
    p = argparse.ArgumentParser(description="Inventario determinista de un ATL de SAP Data Services")
    p.add_argument("atl")
    p.add_argument("--salida", help="carpeta donde escribir inventario_atl.md y .json")
    p.add_argument("--linaje", help="tabla final cuyo linaje se quiere ver")
    p.add_argument("--dataflow", help="dataflow a detallar")
    p.add_argument("--buscar", help="texto a buscar en el ATL")
    a = p.parse_args(argv)
    inv = inventariar(a.atl)
    print(resumen(inv))
    if a.salida:
        print("Escrito:", *escribir_reportes(inv, a.salida))
    if a.linaje:
        print(linaje(inv, a.linaje))
    if a.dataflow:
        print(detalle_dataflow(inv, a.dataflow))
    if a.buscar:
        for n, ln in buscar(inv, a.buscar):
            print(f"L{n}: {ln}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
