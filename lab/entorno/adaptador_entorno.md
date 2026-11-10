## Adaptador de entorno del taller

Este bloque describe el workspace del taller y manda sobre cualquier ruta o catálogo mencionado antes. No cambia ninguna otra regla.

- **Catálogo.** El entorno es `@ENTORNO@`, así que `{{Environment}}_glux` resuelve a `@CATALOGO@`, el equivalente de `dllo_glux`. Tiene los schemas `oro`, `plata`, `stg`, `conf` y `taller`. Los archivos esperados están en `/Volumes/@CATALOGO@/taller/archivos/esperados/`.
- **Raíz de trabajo.** `@RAIZ@`. Las ETL van en `@RAIZ@/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_<TIPO>/DLKHID_<NOMBRE>/`. No escribas fuera de esa raíz ni fuera de `@CATALOGO@`.
- **Utilidades del framework.** Están en `@RAIZ@/databricks_repo_taller/`, con las mismas firmas que en `databricks_repo_dllo`. En el orquestador, las rutas a los `.conf` son absolutas, y los imports quedan así:

```python
usuario = spark.sql("SELECT current_user()").first()[0]
raiz_taller = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
entorno = "@ENTORNO@"
sys.path.append(f"{raiz_taller}/databricks_repo_taller")
from notebooks.DLKHNB_ORO.utilidades.procesar_tablas_vistas import procesar_tablas
from notebooks.DLKHNB_ORO.utilidades.guardar_tabla_vistas import guardar_tabla, guardar_tabla_traza
from notebooks.DLKHNB_ORO.utilidades.validar_schema import validar_schema
from notebooks.DLKHNB_ORO.utilidades.liberar_memoria import liberar_memoria
```

- **ATL.** El proceso legacy está en `@RAIZ@/insumos/com_variable_mini.atl`. La equivalencia de sus tablas en Unity Catalog está en `@RAIZ@/insumos/mapeo_tablas.md`.
- **Traza.** `guardar_tabla_traza` escribe en `@CATALOGO@.conf.traza_config_tabla`.
