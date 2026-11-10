"""Stub del taller de `procesar_tablas()`.

Respeta la firma y el contrato que describen las skills de Postobón:

    procesar_tablas(spark, rutas, entorno, traza, parametros=None) -> {alias: DataFrame}

Por cada `.conf`, en el orden de `rutas`:
1. Lo lee con `configparser` e interpolación, como la utilidad real: un `%` sin escapar falla aquí.
2. Resuelve `{{Environment}}` del catálogo con `entorno` y aplica el guard de catálogo.
3. Verifica que cada alias de `tablas_entrada` ya esté registrado.
4. Sustituye `{{catalogo}}`, `{{schema}}`, `{{tabla}}` y `{{parametros[X]}}`.
5. Ejecuta `query_1`, `query_2`... en orden; el resultado de la última es la salida.
6. Si `schema = stg` (PARAMETROS e INTERMEDIAS), persiste en `{catalogo}.stg.{tabla}`.
7. Registra la salida como vista temporal con su `alias` y anota una fila en `traza`.

Diferencias declaradas con la utilidad real, que no conozco por dentro: aquí `{{parametros[X]}}`
sin `parametros`, o con una llave que no existe, falla con un mensaje claro, y una plantilla sin
resolver también. Eso hace el stub más estricto, no más permisivo. Además, las rutas /Workspace/...
se leen por la API de workspace y no con open(): en serverless, open() puede devolver la versión
que el proceso ya había leído aunque el .conf se haya editado después.
"""
import configparser
import re
import time
from datetime import datetime

from notebooks.DLKHNB_ORO.utilidades._taller import verificar_catalogo

_PARAMETRO = re.compile(r"\{\{\s*parametros\s*\[\s*['\"]?([A-Za-z_]\w*)['\"]?\s*\]\s*\}\}")


def _lista(valor):
    valor = (valor or "").strip()
    if valor in ("", "[]"):
        return []
    return [x.strip().strip("'\"") for x in valor.strip("[]").split(",") if x.strip()]


_WORKSPACE = "/Workspace/"
_cliente = None


def _texto(ruta):
    if not ruta.startswith(_WORKSPACE):
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    global _cliente
    if _cliente is None:
        from databricks.sdk import WorkspaceClient
        _cliente = WorkspaceClient()
    from databricks.sdk.service.workspace import ExportFormat
    return _cliente.workspace.download(ruta[len("/Workspace"):], format=ExportFormat.AUTO).read().decode("utf-8")


def _leer(ruta):
    cp = configparser.ConfigParser()
    cp.read_string(_texto(ruta), source=ruta)
    if not cp.has_section("Entrada") or not cp.has_section("QUERIES"):
        raise ValueError(f"{ruta}: faltan las secciones [Entrada] y [QUERIES]")
    entrada = {k: cp.get("Entrada", k) for k in cp.options("Entrada")}
    claves = sorted((k for k in cp.options("QUERIES") if re.fullmatch(r"query_\d+", k)), key=lambda k: int(k.split("_")[1]))
    if not claves:
        raise ValueError(f"{ruta}: [QUERIES] no tiene query_1")
    return entrada, [cp.get("QUERIES", k) for k in claves]


def _renderizar(sql, catalogo, schema, tabla, parametros, ruta):
    def parametro(m):
        if parametros is None:
            raise ValueError(
                f"{ruta}: usa {{{{parametros[{m.group(1)}]}}}}, pero procesar_tablas no recibió `parametros`. "
                "En el estándar solo config_par_* lo usa; el resto lee las fechas de stg.par_<proceso>."
            )
        if m.group(1) not in parametros:
            raise KeyError(f"{ruta}: el parámetro {m.group(1)} no está en parametros_dict ({', '.join(parametros) or 'vacío'})")
        return str(parametros[m.group(1)])

    sql = _PARAMETRO.sub(parametro, sql)
    sql = sql.replace("{{catalogo}}", catalogo).replace("{{schema}}", schema).replace("{{tabla}}", tabla)
    sin_resolver = re.findall(r"\{\{[^}]*\}\}", sql)
    if sin_resolver:
        raise ValueError(f"{ruta}: plantillas sin resolver: {', '.join(sorted(set(sin_resolver)))}")
    return sql


def procesar_tablas(spark, rutas, entorno, traza, parametros=None):
    resultado = {}
    for ruta in rutas:
        inicio = time.time()
        entrada, queries = _leer(ruta)
        for clave in ("tipo", "catalogo", "schema", "tabla", "alias"):
            if not entrada.get(clave, "").strip():
                raise ValueError(f"{ruta}: falta `{clave}` en [Entrada]")
        catalogo = entrada["catalogo"].strip().replace("{{Environment}}", entorno)
        verificar_catalogo(catalogo)
        tipo, schema, tabla, alias = (entrada[k].strip() for k in ("tipo", "schema", "tabla", "alias"))
        for previo in _lista(entrada.get("tablas_entrada")):
            if not spark.catalog.tableExists(previo):
                raise ValueError(
                    f"{ruta}: el alias `{previo}` de tablas_entrada no está registrado. "
                    "Revisa el orden de las rutas o el alias del .conf que lo produce."
                )
        df = None
        for sql in queries:
            df = spark.sql(_renderizar(sql, catalogo, schema, tabla, parametros, ruta))
        columnas = _lista(entrada.get("columnas"))
        if columnas:
            df = df.select(*columnas)
        if schema == "stg":
            destino = f"{catalogo}.stg.{tabla}"
            df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(destino)
            df = spark.table(destino)
        df.createOrReplaceTempView(alias)
        traza.append(
            {
                "archivo": ruta.rsplit("/", 1)[-1],
                "tipo": tipo,
                "tabla": f"{catalogo}.{schema}.{tabla}",
                "alias": alias,
                "filas": df.count(),
                "segundos": round(time.time() - inicio, 2),
                "ts_registro": datetime.now(),
            }
        )
        resultado[alias] = df
    return resultado
