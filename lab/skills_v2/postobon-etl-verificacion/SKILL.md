---
name: postobon-etl-verificacion
description: Verifica una ETL de capa oro con scripts deterministas y deja verification_report.md. Úsala para revisar frescura y existencia de tablas fuente, pasar el linter de .conf, ejecutar la ETL y compararla contra un archivo esperado, o cuando el usuario diga que algo no cuadra, que hay diferencias contra un CSV o el ATL, o pregunte si la ETL está lista. Solo esta skill puede declarar una ETL como verificada.
---

# Verificar una ETL

"Listo" se dice con evidencia: linter sin errores y aceptación en PASA, en la misma fecha de corte que el archivo esperado. Los scripts de esta skill dan esa evidencia. Tu trabajo es ejecutarlos, leer el resultado y no adornarlo.

## Cargar los scripts
```python
import importlib.util, os

def cargar(archivo):
    usuario = spark.sql("SELECT current_user()").first()[0]
    for base in (f"/Workspace/Users/{usuario}/.assistant/skills", "/Workspace/.assistant/skills"):
        ruta = f"{base}/postobon-etl-verificacion/scripts/{archivo}"
        if os.path.exists(ruta):
            s = importlib.util.spec_from_file_location(archivo[:-3], ruta)
            m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
            return m
    raise FileNotFoundError(archivo)

linter = cargar("conf_linter.py")
acept = cargar("aceptacion.py")
```

## Modo 1. Fuentes (antes de crear la ETL)
```python
r = acept.revisar_fuentes(spark, ["<catalogo>.plata.<tabla>", "<catalogo>.oro.<tabla>"], max_dias=3)
print(acept.formatear_fuentes(r))
```
- Una tabla que no existe es un hallazgo que bloquea: repórtalo y no la reemplaces por otra parecida.
- Si alguna tabla pasa de 3 días sin actualizar, emite la alerta de frescura y detente. Cuando el usuario confirme que se actualizó, vuelve a medir. Una confirmación verbal no basta.

## Modo 2. Linter
```python
rep = linter.lint_carpeta("<ruta>/DLKHID_<NOMBRE>", spec="<ruta>/DLKHID_<NOMBRE>/spec.md",
                          spark=spark, explain=True, entorno=entorno)
print(linter.formatear(rep))
```
- `explain=True` analiza cada query en Spark sin ejecutarla. Encuentra `UNRESOLVED_COLUMN`, `AMBIGUOUS_REFERENCE` y tablas que no existen antes de correr el notebook.
- La regla `interpolacion` reproduce el error de configparser con `%` sin escapar.
- La regla `spec_fuentes` falla si un `.conf` lee una tabla que la spec no aprobó.

## Modo 3. Ejecución y aceptación
```python
salida = dbutils.notebook.run("<ruta>/DLKHID_<NOMBRE>/DLKH_01_<NOMBRE>", 1800,
                              {"g_fecha": "<AAAAMMDD de la spec>", "id_pipeline": "verificacion"})
res = acept.comparar(spark,
                     tabla="<catalogo>.oro.<tabla>",
                     esperado="<ruta del CSV esperado>",
                     llaves=["cd_planta", "cd_registro_nomina"],
                     columnas_valor=["<columna>"],
                     fecha_corte="<AAAAMMDD>",
                     columna_fecha="dt_corte",
                     tolerancia=0.01)
print(acept.formatear(res))
```
`comparar` aborta si las fechas de corte de los dos lados no coinciden. Si aborta, el siguiente paso es ejecutar con la fecha correcta, no comparar igual.

## Modo 4. "No cuadra": depuración con evidencia
1. **Fechas.** Si `comparar` abortó, corrige la fecha y vuelve a comparar. No sigas con fechas distintas.
2. **Mide antes de explicar.** Lee `filas` (llaves solo en un lado) y la razón entre sumas por columna. Una razón alta y estable suele venir de sumar varios días o de duplicar filas; llaves faltantes suelen venir de un JOIN sin match o de una rama de UNION que no aporta.
3. **Hipótesis, query, resultado.** Cada causa que propongas va con la query que la prueba y su resultado en el mismo mensaje. Sin query, escribe "Hipótesis:".
4. **Ubica la lógica en la spec o el inventario,** con su línea del ATL. No la reconstruyas de memoria.
5. **Un cambio a la vez.** Cambia un archivo, relee el fragmento, ejecuta, compara. Si mejora, corre los demás escenarios para descartar regresiones. Si empeora, revierte.
6. **No uses "temporalidad", "horario de carga" ni "snapshot distinto"** como causa sin una query que lo demuestre, sobre todo si el usuario confirmó que las fuentes son iguales.

## Modo 5. Reporte
```python
ruta = acept.escribir_reporte(
    "<ruta>/DLKHID_<NOMBRE>/verification_report.md",
    titulo="<tabla destino>",
    spec="<ruta>/spec.md", plan="<ruta>/plan.md",
    linter=rep, ejecucion=salida, aceptacion=res,
    no_verificado=["<lo que la aceptación no cubre>"],
    cambios=["<archivo>: <qué cambió y por qué>"])
print(open(ruta).read())
```
El reporte lo escribe el script con los resultados tal como salieron. Muéstralo completo al usuario. Si dice NO PASA, la ETL no está lista, aunque la mayoría de escenarios pase.

## Reglas
- No digas listo, 100 % ni un porcentaje de fidelidad sin `verification_report.md`.
- Lo que no se probó va en "Lo que NO se verificó".
- Después de cada corrección, vuelve a correr linter y aceptación completos.
