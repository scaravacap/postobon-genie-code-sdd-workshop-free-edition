# Databricks notebook source
# MAGIC %md
# MAGIC # 32. Frescura de `/Workspace` después de editar un archivo
# MAGIC
# MAGIC En `31_validar_participante`, el linter leyó con `open()` un `.conf` recién sobrescrito con la API del workspace y vio el contenido viejo; la corrida siguiente, en otro proceso, ya vio el nuevo. Este notebook mide la ventana y prueba lecturas alternativas:
# MAGIC
# MAGIC 1. Sobrescritura por API (como el editor de archivos de la UI) y, en el mismo proceso que ya había leído el archivo, lectura con `open()`, con `os.stat` antes, con `posix_fadvise(DONTNEED)` antes y con la API.
# MAGIC 2. La misma sobrescritura, leída con `open()` en un proceso nuevo (`dbutils.notebook.run`).
# MAGIC
# MAGIC No escribe con `open()`: esas escrituras se vuelcan de forma asíncrona y fallan si la carpeta se borra antes. Trabaja en una carpeta temporal de la raíz del taller y la borra con la API.

# COMMAND ----------

import io
import json
import os
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ExportFormat, ImportFormat

dbutils.widgets.text("modo", "medir")
dbutils.widgets.text("ruta", "")
if dbutils.widgets.get("modo") == "leer":
    with open(dbutils.widgets.get("ruta"), "rb") as f:
        dbutils.notebook.exit(f.read().decode("utf-8"))

w = WorkspaceClient()
usuario = spark.sql("SELECT current_user()").first()[0]
carpeta = f"/Users/{usuario}/postobon_sdd_workshop/_prueba_frescura"
api = f"{carpeta}/archivo.conf"
fuse = f"/Workspace{api}"
este = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()


def subir(contenido):
    w.workspace.upload(api, io.BytesIO(contenido), format=ImportFormat.AUTO, overwrite=True)


def con_open():
    with open(fuse, "rb") as f:
        return f.read()


def con_stat():
    os.stat(fuse)
    return con_open()


def con_fadvise():
    fd = os.open(fuse, os.O_RDONLY)
    try:
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        return os.read(fd, 1 << 20)
    finally:
        os.close(fd)


def con_api():
    return w.workspace.download(api, format=ExportFormat.AUTO).read()


LECTURAS = {"open": con_open, "stat_y_open": con_stat, "fadvise": con_fadvise, "api": con_api}

# COMMAND ----------

w.workspace.mkdirs(carpeta)
subir(b"v0")
time.sleep(5)
con_open()
r = {"mismo_proceso": [], "proceso_nuevo": []}
for n in range(1, 4):
    nuevo = f"v{n}".encode()
    subir(nuevo)
    fila = {"intento": n, "inmediato": {k: f() == nuevo for k, f in LECTURAS.items()}}
    inicio, visto = time.time(), b""
    while time.time() - inicio < 45:
        visto = con_open()
        if visto == nuevo:
            break
        time.sleep(0.5)
    fila["open_segundos_hasta_ver"] = round(time.time() - inicio, 1) if visto == nuevo else None
    r["mismo_proceso"].append(fila)
for n in range(4, 6):
    nuevo = f"v{n}".encode()
    subir(nuevo)
    inicio = time.time()
    visto = dbutils.notebook.run(este, 300, {"modo": "leer", "ruta": fuse})
    r["proceso_nuevo"].append({"intento": n, "vio_nuevo": visto == nuevo.decode(), "segundos": round(time.time() - inicio, 1)})

# COMMAND ----------

w.workspace.delete(carpeta, recursive=True)
print(json.dumps(r, indent=2))
dbutils.notebook.exit(json.dumps(r))
