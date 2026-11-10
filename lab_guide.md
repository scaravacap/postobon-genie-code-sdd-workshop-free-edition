# Guía de laboratorio: SDD en Genie Code con el caso de comisiones

Esta guía la pueden seguir sin mí, paso a paso. Cada lab dice qué control del [mapa de errores](lab/mapa_controles.md) ejercita, cuánto dura, qué prompt usar, qué deberían ver y qué hacer si algo falla.

Todo corre con datos sintéticos y con un ATL reducido que construí para el taller (`com_variable_mini.atl`, 5.667 líneas). Ningún paso lee ni escribe `dllo_glux`: las utilidades del taller se niegan a trabajar sobre un catálogo que no empiece por `cx_postobon_sdd`.

| Lab | Tema | Errores que ataca | Tiempo |
|---|---|---|---|
| 0 | Preparación: Git folder, setup y prueba de qué carga Genie Code | - | 10 min |
| 1 | Spec desde el ATL y la trampa del código comentado | E1, E3, E8, E11 | 20 min |
| 2 | Editar `postobon-etl-crear` y comparar antes y después | E4, E6, E11 | 20 min |
| 3 | Una regla nueva en la constitución: nada de "temporalidad" sin datos | E2, E5 | 15 min |
| 4 | Verificación determinista: el linter y la aceptación atrapan E5 y E7 | E3, E5, E7, E9, E10 | 25 min |
| 5 | Opcional, después del taller: Git folder y bundle con la aceptación como gate | E4, E6 | 30 min |

## Convenciones

Reemplacen estos valores en cada prompt y en cada celda:

| Marcador | Qué es | Ejemplo |
|---|---|---|
| `<correo>` | El correo de su cuenta de Free Edition | `aperez@gmail.com` |
| `<entorno>` | `cx_postobon_sdd_workshop`, el valor por defecto del setup | |
| `<catalogo>` | `<entorno>_glux`, que crea el setup | `cx_postobon_sdd_workshop_glux` |
| `<raiz>` | `/Workspace/Users/<correo>/postobon_sdd_workshop` | |

Como cada persona tiene su propio workspace, todos usan el mismo entorno sin pisarse. Igual que en su estándar, `catalogo = {{Environment}}_glux` en los `.conf` resuelve a `<catalogo>` cuando el entorno es `<entorno>`, sin cambiar una línea.

---

## Lab 0. Preparación (10 min)

**Objetivo.** Dejar el catálogo con datos sintéticos, la carpeta de trabajo y la configuración v2 de Genie Code en su usuario, y comprobar con un prompt qué carga Genie Code.

**Pasos**

1. Clonen el repositorio como Git folder: **Workspace > Create > Git folder**, con la URL `https://github.com/scaravacap/postobon-genie-code-sdd-workshop-free-edition`, dentro de su carpeta de usuario.
2. Abran el notebook `lab/entorno/00_setup_entorno`, conéctenlo a serverless y llenen los widgets:
   - `entorno`: `<entorno>`, el valor que ya trae
   - `ruta_material`: vacío (toma la carpeta `lab/` del Git folder)
   - `instalar_carpeta`, `instalar_controles`, `instalar_lab4` e `instalar_v2`: `si`
   - `escribir_privado`: `no`
3. **Run all.** Tarda unos 3 minutos. Crea el catálogo si no existe y al final imprime el catálogo, la raíz y las filas de cada archivo esperado. Con `instalar_v2 = si` también respalda sus instrucciones de usuario, si tenían, las reemplaza por la constitución v2 con el adaptador del taller, copia las 4 skills v2 a su carpeta y deja un `AGENTS.md` en `<raiz>/databricks/notebooks/DLKHNB_ORO/`, que Genie Code lee solo cuando trabaja en un archivo de esa carpeta ([instructions](https://docs.databricks.com/aws/en/genie-code/instructions)).
4. Abran un **chat nuevo** de Genie Code y peguen el prompt de verificación.

**Prompt**

```text
No cambies ningún archivo ni tabla. Responde tres cosas: 1) las skills que tienes disponibles en esta sesión, con su nombre exacto y su descripción en una línea; 2) el título y los encabezados de las instrucciones de usuario y de workspace que tienes cargadas; 3) las memorias que tengas guardadas sobre Postobón, comisiones o este taller. Si alguna de las tres no aplica, dilo.
```

**Resultado esperado**

- Cuatro skills `postobon-*`: `postobon-spec-desde-atl`, `postobon-etl-crear`, `postobon-etl-verificacion` y `postobon-atl-comparacion`. En Free Edition no hay skills de workspace del equipo, así que no deberían ver otras `postobon-*`.
- La descripción de `postobon-etl-crear` dice "a partir de una spec aprobada".
- Instrucciones de usuario con el título "Genie Code en Postobón: ETL de capa oro (v2)" y una sección "Adaptador de entorno del taller" que nombra `<catalogo>`.

**Cómo saber que salió bien.** El setup terminó sin error y el prompt muestra las 4 skills v2 y el adaptador con su catálogo.

**Troubleshooting**

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `Guard del taller: solo se trabaja sobre catálogos que empiezan con 'cx_postobon_sdd'` | El widget `entorno` no tiene el prefijo | Usen `cx_postobon_sdd_workshop`, sin `_glux` |
| `PERMISSION_DENIED` en `CREATE CATALOG` | El notebook no está en su workspace de Free Edition | Ábranlo en su workspace de Free Edition, donde su usuario puede crear catálogos |
| El prompt muestra skills o instrucciones viejas | Genie Code carga los cambios al abrir un chat | Chat nuevo; si persiste, refresquen el navegador ([skills](https://docs.databricks.com/aws/en/genie-code/skills)) |
| Git folder no clona | La red de la oficina bloquea github.com | Avísenme: les dejo el paquete para importarlo con **Import** |
| El compute no arranca o se apaga a mitad del lab | Se agotó la cuota de uso del día | Sigan la demostración y retomen al día siguiente: los datos no se borran ([límites de Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)) |

---

## Lab 1. Spec desde el ATL y la trampa del código comentado (20 min)

**Objetivo.** Pasar del ATL a una `spec.md` revisable sin que el modelo lea el ATL a pedazos. La skill corre `atl_inventario.py`, un script determinista que recorre el ATL completo, y la spec cita líneas del inventario. Ustedes la revisan buscando las trampas que en el caso real costaron días: código comentado tomado como activo (E1), una rama del UNION olvidada (E3), un objeto parecido usado sin avisar (E11) y porcentajes de fidelidad sin medir (E8).

**Pasos**

1. Chat nuevo de Genie Code.
2. Peguen el prompt.
3. Cuando la skill muestre el resumen del inventario (líneas, sha256, dataflows, líneas comentadas), dejen que siga hasta que escriba la spec y se detenga a pedir revisión.
4. Abran `spec.md` y el `inventario/inventario_atl.md` que dejó al lado, y revisen con la lista de abajo.

**Prompt**

```text
@postobon-spec-desde-atl Arma la spec del indicador de Cobertura (TT_TALLER_COBERTURA) a partir del ATL <raiz>/insumos/com_variable_mini.atl. La carpeta de la ETL es <raiz>/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_COBERTURA/. La tabla destino es <catalogo>.oro.fct_com_var_cobertura.
```

**Revisión: lo que tienen que encontrar**

1. **Código comentado.** El inventario lista las líneas comentadas con `#` del ATL. Busquen las que tocan el linaje de Cobertura: hay en el WORKFLOW que calcula las fechas, en filtros de las fuentes y en el conteo. Comprueben que ninguna aparece en la spec como regla activa. Ojo: muchas viven dentro de los textos de la interfaz del ATL (`ui_where_text`, `ui_mapping_text`), en la línea siguiente al código activo, y se leen como si fueran parte de él.
2. **Las dos ramas.** Cobertura cuenta clientes de dos fuentes que se unen antes de contar. ¿La spec lista las dos, con su filtro?
3. **El señuelo.** Hay un dataflow de nombre muy parecido que ningún workflow llama. ¿La spec lo deja fuera del linaje y dice por qué?
4. **Fechas.** ¿La spec dice cómo se calculan la fecha de inicio y la de fin, incluido el caso `19000101`, y cita la línea del WORKFLOW?
5. **Fuentes en Unity Catalog.** Cada fuente del ATL tiene su tabla en `<catalogo>`, según `<raiz>/insumos/mapeo_tablas.md`. ¿La spec marca `EXISTE`, `NO EXISTE` o `AMBIGUA`, con la consulta a `information_schema` que lo prueba?
6. **Sin porcentajes.** La spec no dice "95 % de fidelidad" ni "completo". Lo que no verificó, lo lista como no verificado.

Para comprobar a mano, corran el inventario en una celda de un notebook propio:

```python
import importlib.util
usuario = spark.sql("SELECT current_user()").first()[0]
raiz = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
s = importlib.util.spec_from_file_location("atl_inventario", f"{raiz}/controles/atl_inventario.py")
atl = importlib.util.module_from_spec(s); s.loader.exec_module(atl)
inv = atl.inventariar(f"{raiz}/insumos/com_variable_mini.atl")
print(atl.resumen(inv))
print(atl.linaje(inv, "TT_TALLER_COBERTURA"))
```

**Resultado esperado.** `spec.md` y `inventario/` en la carpeta `DLKHID_FCT_COM_VAR_COBERTURA/`, con la spec en estado de revisión (no aprobada) y Genie Code detenido esperando su revisión.

**Cómo saber que salió bien.** Los seis puntos de la revisión se cumplen, o encontraron con el inventario el punto que la spec tiene mal. Las dos cosas son un buen resultado: la spec existe para que el error se vea antes de escribir código.

**Troubleshooting**

| Síntoma | Qué hacer |
|---|---|
| Genie Code empieza a leer el ATL con su herramienta de lectura en vez de correr el script | Deténganlo y pidan: "usa el script `atl_inventario.py` de la skill, no leas el ATL". Si pasa siempre, revisen que la skill esté encendida |
| `No encuentro atl_inventario.py` | La skill busca en `/Users/<correo>/.assistant/skills/` y en `/Workspace/.assistant/skills/`. Revisen que el setup haya corrido con `instalar_v2 = si` |
| Escribe `.conf` sin detenerse | La spec no estaba aprobada y no debió seguir: anótenlo, es justo el comportamiento que el Lab 2 refuerza |

---

## Lab 2. Editar `postobon-etl-crear` y comparar antes y después (20 min)

**Objetivo.** Ver en acción la precondición de la skill (sin spec aprobada no hay `.conf`), aprobar la spec como paso humano, y editar ustedes mismos la skill para que el plan declare cómo se verificó cada supuesto. De paso comprueban una regla de producto que explica parte de E6: una skill editada solo aplica en un chat nuevo ([skills](https://docs.databricks.com/aws/en/genie-code/skills)).

Con v1, la misma petición creaba los `.conf` de inmediato, sin spec ni plan. Esa es la comparación de antes y después.

**Pasos**

1. **Antes de aprobar.** En el mismo chat del Lab 1 o en uno nuevo, pidan crear la ETL (prompt A). Debe detenerse en el paso 0: la spec no está aprobada.
2. **Aprobación humana.** Editen `spec.md`: resuelvan cada fila `NO EXISTE` o `AMBIGUA` (con la tabla correcta del mapeo o dejándola como pregunta abierta) y cambien el estado a `APROBADA por <su nombre>, <fecha>`.
3. **Plan.** Repitan el prompt A. Ahora debe escribir `plan.md` con la tabla de archivos y la de supuestos, y detenerse a pedir confirmación. **No confirmen todavía.**
4. **Editen la skill.** Abran `/Users/<correo>/.assistant/skills/postobon-etl-crear/SKILL.md` y agreguen esta línea al final de la sección `## Reglas`:

   ```markdown
   - Cada supuesto del plan lleva la query que lo verifica y su resultado. Si no la corriste, escribe "sin verificar" en la columna "Cómo lo verifico".
   ```

5. **Mismo chat.** Pidan el prompt B. Observen si el plan cambia.
6. **Chat nuevo.** Pidan el prompt B otra vez y comparen las dos versiones de la tabla de supuestos.

**Prompts**

```text
A: @postobon-etl-crear Crea la ETL de Cobertura con la spec de <raiz>/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_COBERTURA/spec.md.
```

```text
B: @postobon-etl-crear Rehaz el plan.md de Cobertura desde la spec aprobada y muéstrame la tabla de supuestos. No crees ningún .conf.
```

**Resultado esperado**

- Paso 1: Genie Code no escribe ningún `.conf` y dice qué falta para aprobar.
- Paso 3: `plan.md` con cada archivo, lo que lee, lo que produce, el requisito de la spec que cubre y el escenario que lo prueba.
- Paso 5: lo más probable es que el plan no cambie, porque el chat sigue con la versión de la skill que cargó al empezar.
- Paso 6: la tabla de supuestos trae una query y su resultado por fila, o "sin verificar".

**Cómo saber que salió bien.** Pueden señalar en `plan.md` la diferencia entre el paso 5 y el 6, y no hay ningún `.conf` creado antes de la aprobación.

**Troubleshooting**

| Síntoma | Qué hacer |
|---|---|
| En el chat nuevo el plan sigue igual | Refresquen el navegador y abran otro chat. Revisen que editaron la copia de su usuario y no una de workspace |
| Genie Code empieza a crear `.conf` después del plan | Activen la aprobación **Ask first** en la configuración de Genie Code ([Navigate Genie Code](https://docs.databricks.com/aws/en/genie-code/navigate-genie-code)). La autoaprobación por defecto "no es una barrera de seguridad" |
| No encuentra la spec | Revisen la ruta del prompt: la carpeta es `DLKHID_FCT_COM_VAR_COBERTURA` |

---

## Lab 3. Una regla nueva en la constitución: nada de "temporalidad" sin datos (15 min)

**Objetivo.** Agregar una regla a sus instrucciones de usuario y medir si cambia la respuesta. El escenario reproduce E2 y E5: la tabla de Volumen CTV quedó cargada con la corrida del 28 de agosto, y el archivo esperado es del 31. La explicación tentadora es "temporalidad"; la correcta sale de una query.

**Pasos**

1. **Antes de la regla.** Chat nuevo, prompt de abajo. Anoten si la respuesta trae una query con su resultado o solo una explicación.
2. **La regla.** Abran `/Users/<correo>/.assistant_instructions.md` y agreguen esta línea en la sección `## 2. Evidencia`:

   ```markdown
   - **Nada de "temporalidad" sin datos.** No atribuyas una diferencia a temporalidad, horarios de carga, snapshots o rezagos sin una query que lo demuestre. Primero compara `dt_corte` y `cd_periodo_mes` de los dos lados y muestra el resultado.
   ```

3. **Después de la regla.** Chat nuevo, el mismo prompt. Comparen las dos respuestas.

**Prompt**

```text
La tabla <catalogo>.oro.fct_com_var_volumen_ctv no cuadra con el archivo /Volumes/<catalogo>/taller/archivos/esperados/fct_com_var_volumen_ctv_20260831.csv. ¿Es un tema de temporalidad? No cambies nada todavía: solo dime qué pasa y cómo lo comprobaste.
```

**Resultado esperado.** Con la regla, la respuesta incluye una query sobre `dt_corte` y muestra que la tabla tiene el corte `20260828` y el archivo el `20260831`, así que no compara: cualquier diferencia entre fechas distintas es esperable. Si usa `@postobon-etl-verificacion`, la aceptación devuelve `NO COMPARABLE` por el mismo motivo.

**Cómo saber que salió bien.** La causa viene con su query y su resultado, o aparece marcada como "Hipótesis:" con la query que la probaría. Si las dos respuestas son iguales, también es un resultado: la regla general "Sin query no hay causa" ya estaba en v2. Anótenlo para la discusión.

**Troubleshooting**

| Síntoma | Qué hacer |
|---|---|
| La regla no se nota | Chat nuevo. Las instrucciones tienen un límite de 20.000 caracteres y lo que pase de ahí no se usa ([instructions](https://docs.databricks.com/aws/en/genie-code/instructions)) |
| Genie Code corrige la tabla aunque el prompt dice que no | Activen **Ask first** y anótenlo: es el comportamiento que la regla "un cambio a la vez" intenta contener |

---

## Lab 4. Verificación determinista: el linter y la aceptación atrapan E5 y E7 (25 min)

**Objetivo.** Ver que un control fuera del modelo encuentra los errores sin depender de que Genie Code obedezca. El setup instaló una ETL de Volumen CTV con **5 errores sembrados**, todos tomados del caso real:

| Archivo | Error | Quién lo ve |
|---|---|---|
| `INSUMOS/config_ins_01_personal.conf` | `%` sin escapar en un `LIKE` (E7) | Linter estático |
| `INTERMEDIAS/config_int_01_registro_nomina.conf` | `{{parametros[G_Fecha]}}` fuera de PARAMETROS (E9) | Linter estático |
| `INTERMEDIAS/config_int_02_volumen_ctv_producto.conf` | Usa un alias que no está en `tablas_entrada` (E3) | Linter estático |
| `INSUMOS/config_ins_03_producto.conf` | No entrega una columna que int_02 usa (E10) | Linter con `explain`, que lo reporta en int_02 |
| `SALIDAS/config_sal_01_fct_com_var_volumen_ctv.conf` | Columna ambigua después de un JOIN (E10) | Solo al ejecutar, cuando int_02 ya corre |

**Pasos**

1. **El linter, a mano.** En un notebook propio, en serverless:

   ```python
   import importlib.util
   usuario = spark.sql("SELECT current_user()").first()[0]
   raiz = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
   s = importlib.util.spec_from_file_location("conf_linter", f"{raiz}/controles/conf_linter.py")
   linter = importlib.util.module_from_spec(s); s.loader.exec_module(linter)
   etl = f"{raiz}/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_VOLUMEN_CTV"
   print(linter.formatear(linter.lint_carpeta(etl)))
   print(linter.formatear(linter.lint_carpeta(etl, spark=spark, explain=True, entorno="<entorno>")))
   ```

   La primera llamada reporta 4 hallazgos de error para 3 problemas: int_01 sale dos veces porque usa la plantilla en dos líneas. La segunda agrega `UNRESOLVED_COLUMN` en int_02 y avisa que la salida no se pudo analizar porque depende de ella.

2. **La aceptación antes de corregir (E5).** Corran el notebook de aceptación contra la tabla tal como está:

   ```python
   print(dbutils.notebook.run(f"{raiz}/controles/verificacion_aceptacion", 600, {
       "tabla": "<catalogo>.oro.fct_com_var_volumen_ctv",
       "esperado": "/Volumes/<catalogo>/taller/archivos/esperados/fct_com_var_volumen_ctv_20260831.csv",
       "columnas_valor": "vl_volumen_ctv",
       "fecha_corte": "20260831",
       "fallar_si_no_pasa": "no",
   }))
   ```

   Resultado: `NO COMPARABLE`. La tabla tiene el corte del 28 y la aceptación se niega a comparar fechas distintas. Es el control de E5.

3. **Que Genie Code corrija.** Chat nuevo, prompt de abajo. Sigan cada cambio: debe corregir un archivo, pasar el linter, releer el archivo y seguir con el siguiente.
4. **Comprueben ustedes.** Repitan el linter del paso 1 (debe dar 0 errores) y la aceptación del paso 2 (debe dar `PASA`, 4 de 4 escenarios).

**Prompt**

```text
@postobon-etl-verificacion La ETL de Volumen CTV en <raiz>/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_VOLUMEN_CTV/ no corre. Corrígela un archivo a la vez, con el linter después de cada cambio. Después ejecútala para el corte 20260831, compárala con /Volumes/<catalogo>/taller/archivos/esperados/fct_com_var_volumen_ctv_20260831.csv y deja el verification_report.md en la carpeta de la ETL.
```

**Resultado esperado**

- Linter con 0 errores.
- El orquestador termina con `OK - <catalogo>.oro.fct_com_var_volumen_ctv - corte 20260831 - 48 filas`.
- Aceptación `PASA`, 4 de 4 escenarios.
- `verification_report.md` en la carpeta de la ETL, con el sha256 de cada `.conf` y el resultado de cada escenario.

**Cómo saber que salió bien.** Las tres comprobaciones del paso 4 las corren ustedes, no Genie Code. Si Genie Code dice "listo" y la aceptación no dice `PASA`, el control funcionó: atrapó un "listo" sin evidencia (E4).

**Troubleshooting**

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `'%' must be followed by '%' or '('` | E7: configparser interpreta `%` | Escriban `%%` en el `LIKE` |
| `usa {{parametros[G_Fecha]}}, pero procesar_tablas no recibió parametros` | E9 | Lean la fecha de `stg.par_<proceso>` con el subquery escalar, como en la constitución |
| `NO COMPARABLE` después de corregir | Corrieron el orquestador con la fecha por defecto | Ejecútenlo con el widget `g_fecha = 20260831` |
| `AMBIGUOUS_REFERENCE` en la salida | E10, aparece cuando int_02 ya corre | Califiquen la columna con el alias de la tabla |
| Corrigieron un `.conf`, lo vuelven a correr en la misma sesión y ven el error anterior | En serverless, un proceso de Python puede seguir leyendo con `open()` la versión que ya leyó de `/Workspace` | Las utilidades y el linter del taller leen por la API y no tienen este problema. En su framework real, reinicien Python o ejecuten el orquestador como job |

---

## Lab 5. Opcional, después del taller: Git folder y bundle con la aceptación como gate (30 min)

**Objetivo.** Llevar la verificación fuera de la sesión: un job que corre la ETL y después la aceptación, y que **falla** si el resultado no es `PASA`. Así, una ETL que no cuadra no queda como corrida exitosa y no se promueve. Es el control D de E4 y E6 en el [mapa](lab/mapa_controles.md).

**Pasos**

1. Abran `lab/controles/databricks.yml` en su Git folder. Define un job `etl_con_aceptacion` con dos tareas: `etl` y `aceptacion` (con `fallar_si_no_pasa: si`).
2. Valídenlo y despliéguenlo, desde la interfaz de bundles del workspace o con la CLI. Con la CLI, desde `lab/controles/` y con un perfil hacia su workspace de Free Edition, que se crea con `databricks auth login --host <URL de su workspace> --profile <perfil>` ([autenticación](https://docs.databricks.com/aws/en/dev-tools/cli/authentication)):

   ```bash
   VARS=(
     --var "entorno=<entorno>"
     --var "notebook_etl=<raiz>/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_VOLUMEN_CTV/DLKH_01_FCT_COM_VAR_VOLUMEN_CTV"
     --var "tabla=<catalogo>.oro.fct_com_var_volumen_ctv"
     --var "esperado=/Volumes/<catalogo>/taller/archivos/esperados/fct_com_var_volumen_ctv_20260831.csv"
     --var "columnas_valor=vl_volumen_ctv"
   )
   databricks bundle validate --strict "${VARS[@]}" --profile <perfil>
   databricks bundle deploy "${VARS[@]}" --profile <perfil>
   databricks bundle run etl_con_aceptacion "${VARS[@]}" --profile <perfil>
   ```

   El arreglo `VARS=( ... )` funciona igual en bash y en zsh, la terminal por defecto de macOS.

   Probé estos tres comandos desde zsh el 10 de noviembre, en mi cuenta de Free Edition: con la ETL de referencia, el job termina en `SUCCESS` y la aceptación da `PASA` en 4 de 4 escenarios.

3. Vean fallar la compuerta de dos formas:
   - **Otra fecha de corte (E5).** Corran `databricks bundle run etl_con_aceptacion "${VARS[@]}" --params g_fecha=20260828 --profile <perfil>`. La ETL corre bien, pero la tarea `aceptacion` falla con `NO COMPARABLE`, porque el esperado no tiene filas con esa fecha de corte.
   - **Un `.conf` roto.** Quiten un `%` de `%%` en un `.conf` y vuelvan a correr el job. Esta vez falla la tarea `etl`, antes de llegar a la aceptación.
4. **Skills versionadas.** En Settings de Genie Code, registren `lab/skills_v2/` de su Git folder como carpeta de skills ([skills](https://docs.databricks.com/aws/en/genie-code/skills)). Si lo hacen, apaguen las copias de su usuario para no tener dos versiones con el mismo nombre.

**Resultado esperado.** El job pasa con la ETL corregida y falla en los dos casos del paso 3. `bundle run` devuelve error cuando el job termina en `FAILED`, así que en un pipeline de Azure DevOps la promoción se detiene sola ([Azure DevOps](https://docs.databricks.com/aws/en/dev-tools/ci-cd/azure-devops)). Las dos tareas van sin reintentos, así que cada falla aparece una sola vez.

**Cómo saber que salió bien.** Tienen una corrida `SUCCESS` y dos `FAILED` del mismo job: una en `aceptacion` con `NO COMPARABLE` y otra en `etl`. La CLI reporta cada falla como `INTERNAL_ERROR: Task <tarea> failed`, y en Jobs la corrida queda como `Failed`.

**Para limpiar.** `databricks bundle destroy "${VARS[@]}" --profile <perfil>` borra el job y su carpeta `.bundle` en el workspace.

**Para su promoción real.** Los bundles no tienen un recurso para skills ni para archivos sueltos del workspace ([resources](https://docs.databricks.com/aws/en/dev-tools/bundles/resources)). Las skills y las instrucciones se versionan en Git y se copian a su ruta con un script o un job, o se registra la carpeta del Git folder.

---

## Al terminar

El setup guardó sus instrucciones de usuario anteriores en `<raiz>/respaldo/`. Para volver a como estaban:

1. Copien el respaldo más antiguo, `<raiz>/respaldo/assistant_instructions_<fecha>.md`, a `/Users/<correo>/.assistant_instructions.md`. Si corrieron el setup más de una vez, los más nuevos ya son la v2. Si no hay ninguno, no tenían instrucciones antes: borren el archivo.
2. Borren las carpetas `postobon-*` de `/Users/<correo>/.assistant/skills/`. Si tenían una skill personal con el mismo nombre que una v2, el setup la guardó en `<raiz>/respaldo/skills_<fecha>/`: cópienla de vuelta.
3. Si ya no van a usar el catálogo del taller, bórrenlo con `DROP CATALOG cx_postobon_sdd_workshop_glux CASCADE`: solo tiene datos sintéticos.
