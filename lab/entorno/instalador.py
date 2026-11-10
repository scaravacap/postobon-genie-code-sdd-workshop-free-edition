"""Copia material del taller a la carpeta de trabajo del workspace con el SDK de Databricks.

Lo usan 00_setup_entorno (participantes y facilitador) y 10_reset_escenario (experimento).
El origen puede ser un volume o una carpeta local (/Volumes/..., se lee con os.walk) o una
carpeta del workspace, por ejemplo la Git folder del repo (/Workspace/..., se lee con el SDK).
Un .py que empieza con la cabecera de notebook se sube como notebook; el resto, como archivo.
"""
import io
import os

CABECERA = b"# Databricks notebook source"
IGNORAR = {"__pycache__", ".DS_Store", ".ipynb_checkpoints"}
PREFIJO = "cx_postobon_sdd"


def catalogo_del_taller(entorno):
    catalogo = f"{entorno.strip()}_glux"
    if not catalogo.startswith(PREFIJO):
        raise PermissionError(f"Guard del taller: solo se trabaja sobre catálogos que empiezan con '{PREFIJO}'; se recibió {catalogo}.")
    return catalogo


def _sin_workspace(ruta):
    return ruta[len("/Workspace"):] if ruta.startswith("/Workspace/") else ruta


def leer_arbol(w, origen):
    """Devuelve [(ruta_relativa, contenido_bytes, es_notebook)] de todo lo que cuelga de origen."""
    archivos = []
    if origen.startswith("/Workspace/"):
        from databricks.sdk.service.workspace import ExportFormat, ObjectType
        base = _sin_workspace(origen).rstrip("/")
        for obj in w.workspace.list(base, recursive=True):
            if obj.object_type not in (ObjectType.NOTEBOOK, ObjectType.FILE):
                continue
            rel = obj.path[len(base) + 1:]
            if any(parte in IGNORAR for parte in rel.split("/")):
                continue
            es_nb = obj.object_type == ObjectType.NOTEBOOK
            formato = ExportFormat.SOURCE if es_nb else ExportFormat.AUTO
            contenido = w.workspace.download(obj.path, format=formato).read()
            archivos.append((rel + ".py" if es_nb and not rel.endswith(".py") else rel, contenido, es_nb))
    else:
        if not os.path.isdir(origen):
            raise FileNotFoundError(f"No existe la carpeta de origen {origen}")
        for carpeta, subcarpetas, nombres in os.walk(origen):
            subcarpetas[:] = sorted(s for s in subcarpetas if s not in IGNORAR)
            for nombre in sorted(nombres):
                if nombre in IGNORAR or nombre.endswith(".pyc"):
                    continue
                ruta = os.path.join(carpeta, nombre)
                with open(ruta, "rb") as f:
                    contenido = f.read()
                es_nb = nombre.endswith(".py") and contenido.lstrip().startswith(CABECERA)
                archivos.append((os.path.relpath(ruta, origen).replace(os.sep, "/"), contenido, es_nb))
    return sorted(archivos)


def reemplazar(archivos, reemplazos):
    """Aplica reemplazos de texto a los .py y notebooks (por ejemplo, la línea `entorno = ...` del adaptador)."""
    salida = []
    for rel, contenido, es_nb in archivos:
        if reemplazos and (es_nb or rel.endswith(".py")):
            texto = contenido.decode("utf-8")
            for viejo, nuevo in reemplazos.items():
                texto = texto.replace(viejo, nuevo)
            contenido = texto.encode("utf-8")
        salida.append((rel, contenido, es_nb))
    return salida


def subir_arbol(w, archivos, destino):
    """Sube los archivos bajo destino (/Workspace/... o /Users/...). Devuelve las rutas creadas."""
    from databricks.sdk.service.workspace import ImportFormat, Language
    base = _sin_workspace(destino).rstrip("/")
    creadas, carpetas = [], set()
    for rel, contenido, es_nb in archivos:
        ruta = f"{base}/{rel}"
        carpeta = ruta.rsplit("/", 1)[0]
        if carpeta not in carpetas:
            w.workspace.mkdirs(carpeta)
            carpetas.add(carpeta)
        if es_nb:
            ruta = ruta[:-3] if ruta.endswith(".py") else ruta
            w.workspace.upload(ruta, io.BytesIO(contenido), format=ImportFormat.SOURCE, language=Language.PYTHON, overwrite=True)
        else:
            w.workspace.upload(ruta, io.BytesIO(contenido), format=ImportFormat.AUTO, overwrite=True)
        creadas.append(ruta)
    return creadas


def borrar(w, ruta):
    """Borra una carpeta o archivo del workspace si existe. Devuelve True si había algo."""
    from databricks.sdk.errors import NotFound
    try:
        w.workspace.delete(_sin_workspace(ruta), recursive=True)
        return True
    except NotFound:
        return False


def existe(w, ruta):
    from databricks.sdk.errors import NotFound
    try:
        w.workspace.get_status(_sin_workspace(ruta))
        return True
    except NotFound:
        return False


def leer_texto(w, ruta):
    """Contenido de un archivo o notebook del workspace como texto, o None si no existe."""
    from databricks.sdk.errors import NotFound
    from databricks.sdk.service.workspace import ExportFormat, ObjectType
    try:
        tipo = w.workspace.get_status(_sin_workspace(ruta)).object_type
        formato = ExportFormat.SOURCE if tipo == ObjectType.NOTEBOOK else ExportFormat.AUTO
        return w.workspace.download(_sin_workspace(ruta), format=formato).read().decode("utf-8")
    except NotFound:
        return None


def renderizar_adaptador(plantilla, entorno, raiz):
    """Llena la plantilla adaptador_entorno.md con el entorno y la raíz de trabajo del usuario."""
    catalogo = catalogo_del_taller(entorno)
    return plantilla.replace("@CATALOGO@", catalogo).replace("@ENTORNO@", entorno).replace("@RAIZ@", raiz.rstrip("/"))
