---
name: postobon-spec-desde-atl
description: Convierte un ATL de SAP Data Services en una spec revisable antes de escribir código. Úsala cuando el usuario entregue o mencione un archivo .atl, pida migrar un indicador o un dataflow desde un ATL, pregunte por el linaje, las fuentes, los joins, los filtros o el código comentado de un ATL, o pida una spec. Ejecuta el script atl_inventario.py, que lee el ATL completo de forma determinista; no leas el ATL con el modelo.
---

# Spec desde un ATL

Un ATL de comisiones pasa de 30.000 líneas. Leerlo por partes con el modelo produjo conclusiones con información parcial y código comentado tomado por activo. Esta skill cambia el método: el script `scripts/atl_inventario.py` lee el archivo completo y tú trabajas sobre su inventario, que cita número de línea para todo.

Si ya existe una `spec.md` con estado `APROBADA` para el indicador, úsala y no vuelvas a interpretar el ATL.

## Paso 1. Inventario determinista
Ejecuta esta celda. Cambia solo las dos rutas.

```python
import importlib.util, os

def cargar_script(skill, archivo):
    usuario = spark.sql("SELECT current_user()").first()[0]
    for base in (f"/Workspace/Users/{usuario}/.assistant/skills", "/Workspace/.assistant/skills"):
        ruta = f"{base}/{skill}/scripts/{archivo}"
        if os.path.exists(ruta):
            spec = importlib.util.spec_from_file_location(archivo[:-3], ruta)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
            print("Script:", ruta)
            return modulo
    raise FileNotFoundError(f"No encuentro {archivo}: si la skill está en una carpeta registrada, usa esa ruta")

atl = cargar_script("postobon-spec-desde-atl", "atl_inventario.py")
RUTA_ATL = "/Workspace/Users/<usuario>/<archivo>.atl"
CARPETA_SALIDA = "/Workspace/Users/<usuario>/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_<NOMBRE>/inventario"
inv = atl.inventariar(RUTA_ATL)
print(atl.resumen(inv))
print(atl.escribir_reportes(inv, CARPETA_SALIDA))
```

Muestra al usuario el resumen que imprime el script: líneas, sha256, dataflows, workflows, líneas comentadas. Si el script falla, muestra el error y detente. No leas el ATL a mano como alternativa.

## Paso 2. Ubica el indicador
- `print(atl.linaje(inv, "<TABLA_FINAL>"))` devuelve la cadena de dataflows que produce la tabla, hasta las fuentes externas, con líneas y orden de ejecución.
- `print(atl.detalle_dataflow(inv, "DF_..."))` devuelve lecturas, consultas, joins, filtros activos, código comentado, uniones (Merge) y cargas de un dataflow.
- Si necesitas el texto exacto, `print(atl.extraer_lineas(RUTA_ATL, inicio, fin))` con el rango que da el inventario. Nunca leas el archivo completo.
- Si algo no aparece, `atl.buscar(inv, "texto")`. Lo que el script no encuentra no está en el ATL.

## Paso 3. Fuentes contra Unity Catalog
Una fuente externa es una tabla que el ATL lee y que ningún dataflow del mismo ATL produce. Para cada una:
1. Busca su equivalente en el mapeo que dio el usuario (por ejemplo, `VTA_PEDIDOS_HIST` es `oro.fct_pedido_venta`).
2. Verifica que existe y lista sus columnas:
   ```sql
   SELECT table_schema, table_name FROM <catalogo>.information_schema.tables
   WHERE lower(table_name) LIKE '%<parte del nombre>%';
   SELECT column_name, data_type FROM <catalogo>.information_schema.columns
   WHERE table_schema = '<schema>' AND table_name = '<tabla>' ORDER BY ordinal_position;
   ```
3. Asigna el estado: `OK`, `NO EXISTE` (bloquea) o `AMBIGUA` (dos o más candidatas parecidas). En los dos últimos casos detente en esa rama y regístralo como pregunta que bloquea. Nunca elijas tú entre dos tablas parecidas.
4. Compara las columnas que lee el ATL con las de la tabla en UC. Anota las que cambian de nombre y las que no existen: ahí se previene `UNRESOLVED_COLUMN`.

Cada tabla intermedia (`TT_*`) que produce un dataflow se busca también en `stg`. Si ya existe, anótalo; la persona decide si se reconstruye o se reutiliza.

## Paso 4. Formato de las llaves de cada JOIN
Para cada JOIN del linaje, mide las llaves de los dos lados:
```sql
SELECT length(<llave>) AS largo, count(*) AS filas, min(<llave>) AS ejemplo
FROM <catalogo>.<schema>.<tabla> GROUP BY 1 ORDER BY 1;
```
Si los formatos no coinciden (14 contra 10 dígitos, `MM/dd/yyyy` contra `yyyyMMdd`), copia a la spec la transformación exacta que usa el ATL, con su línea.

## Paso 5. Escribe la spec
Copia `plantillas/spec.md` de esta skill a `DLKHID_<NOMBRE>/spec.md` y llénala:
- Las secciones 2, 4, 5 y 6 salen del inventario, con números de línea. No agregues lógica que no esté en el inventario.
- La sección 4 lista todas las ramas de cada Merge (UNION). Si una salida suma varias tablas, están todas.
- La sección 5 lista todo el código con `#` de los dataflows del linaje.
- La sección 8 usa la fecha de corte del archivo esperado.
- La sección 9 recoge cada supuesto y cada pregunta.
- El estado queda en `BORRADOR`.

## Paso 6. Detente y pide revisión
Muestra la ruta de la spec, cuántas fuentes quedaron en cada estado y las preguntas que bloquean. Pide a la persona que la revise y cambie el estado a `APROBADA`. Esta skill no crea `.conf` ni notebooks.

## Reglas
- El inventario manda sobre tu memoria y sobre lecturas anteriores del ATL.
- El código con `#` no es lógica activa, aunque parezca más completo o más reciente.
- Si el usuario pregunta por el linaje, responde desde `atl.linaje` y `atl.detalle_dataflow`, citando líneas.
