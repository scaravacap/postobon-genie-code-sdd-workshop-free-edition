# Protocolo del experimento v1 frente a v2 con el Genie Code task

El experimento mide cómo se comporta Genie Code **al primer intento y con autoaprobación** con dos configuraciones: v1, la que Postobón usa hoy (constitución y 7 skills), y v2 (constitución, `AGENTS.md`, 4 skills con scripts y plantillas SDD). Las correcciones humanas no se miden aquí: se ven en los labs.

Con una corrida por prompt y variante, o dos si alcanza el tiempo, los resultados son **indicativos, no estadísticos**.

## Por qué un job

- El Genie Code task abre un chat nuevo en cada corrida, con las mismas herramientas que la sesión interactiva, y hereda las skills e instructions de quien lo creó ([Genie Code task](https://docs.databricks.com/aws/en/jobs/tasks/genie-code)).
- Siempre autoaprueba y solo se define desde la UI de Jobs: bundles, la Jobs API y los SDKs no lo soportan.
- La respuesta queda en `{{tasks.genie.output.response}}`, y eso permite evaluarla en una tarea siguiente del mismo job.

## Qué hay en el workspace

| Ruta | Qué es | ¿La ve el agente? |
|---|---|---|
| `/Workspace/Users/<tú>/postobon_sdd_workshop/` | Raíz de trabajo: utilidades stub, ATL mini, mapeo y las ETL | Sí, es su carpeta |
| `/Workspace/Users/<tú>/postobon_sdd_experimento/` | Notebooks `00_setup_entorno`, `10_reset_escenario`, `20_evaluar_corrida` y las validaciones `30_validar_referencia` y `31_validar_participante` | No se le menciona |
| `/Volumes/cx_postobon_sdd_workshop_glux/taller/archivos/esperados/` | Archivos esperados a corte 20260831 | Sí, los prompts los nombran |
| `/Volumes/cx_postobon_sdd_workshop_glux/taller/privado/` | Material del evaluador: oráculo, ETL de referencia, escenarios, esperados de P4 y copias de cada corrida | No se le menciona |

La evaluación marca como contaminada una respuesta que nombre el material privado.

## Pasos del facilitador antes de crear el job

1. Apaga tus skills personales en la configuración de Genie Code y, si tienes permisos, las de workspace. No hace falta moverlas ni borrarlas.
2. Confirma que las instructions de usuario ya son las de v1. Yo las instalo con la CLI después de respaldar las tuyas.

## Crear el job

La tarea de Genie Code solo se define en la UI: "Defining a Genie Code task in Declarative Automation Bundles, the Jobs API, or the Databricks SDKs isn't supported" ([Genie Code task](https://docs.databricks.com/aws/en/jobs/tasks/genie-code)). Lo demás sí se crea por API, así que el job se arma en dos partes. No sirve un bundle: el siguiente `bundle deploy` reescribe el job y borra la tarea agregada a mano.

**Parte 1, por API.** `job_experimento.json` trae `@USUARIO@` en las rutas: `sed "s/@USUARIO@/<tu correo>/" job_experimento.json > /tmp/job.json` y luego `databricks jobs create --json @/tmp/job.json` crea el job `taller_sdd_experimento` con:
- tres parámetros: `prompt_id` (por defecto `CANARY`), `variante` (`v1`) y `prompt` (vacío);
- la tarea `reset_escenario`, notebook `10_reset_escenario` en serverless;
- la tarea `evaluar`, notebook `20_evaluar_corrida` en serverless con **Run if: All done**, `run_id` = `{{job.run_id}}` y `respuesta` vacío. La API valida las referencias entre tareas y rechaza `{{tasks.genie.output.response}}` mientras `genie` no exista ("Invalid reference... Task 'genie' does not exist"), así que ese valor se pone en la UI;
- **Maximum concurrent runs = 1**, porque todas las corridas comparten la raíz de trabajo y las tablas, y la cola activada;
- **sin reintentos** en las dos tareas: `max_retries = 0` y `disable_auto_optimization = true`. En serverless, la autooptimización reintenta sola una tarea fallida; en la prueba del participante eso corrió la validación dos veces. Un reintento del agente contaría como segundo intento, así que en la UI la tarea `genie` también va sin reintentos.

Quien corre el `create` queda como creador y como run-as. Tiene que ser el facilitador: hoy la tarea de Genie Code solo corre si el run-as es quien creó el job.

**Parte 2, en la UI (unos 3 minutos):**
1. Abre el job, selecciona `reset_escenario` y haz clic en **Add task**.
2. Nombre `genie`, tipo **Genie Code**, depende de `reset_escenario`. En **Prompt** va solo `{{prompt}}`: dentro del prompt, un parámetro del job se referencia por su nombre. Timeout de 45 minutos y **Retries** en ninguno.
3. Abre `evaluar`, cambia **Depends on** a `genie`, quitando `reset_escenario`, y deja **Run if: All done**. En sus parámetros, pon `respuesta` = `{{tasks.genie.output.response}}`.
4. Guarda y confirma que la UI no muestra advertencias bajo el prompt.

Si la tarea `genie` falla, puede que `evaluar` no arranque porque `{{tasks.genie.output.response}}` no se resuelve. En ese caso la corrida cuenta como FALLA y `20_evaluar_corrida` se corre a mano con la respuesta vacía.

## Secuencia de corridas

Cada corrida se lanza con `python lanzar.py --job-id <id> --prompt <P> --variante <v> --ejecutar`, que toma el texto exacto de `prompts.md`.

1. **v1 instalada:** CANARY v1. Si no lista las 7 skills `postobon-*` de v1 y el adaptador, me detengo: el job no está cargando lo que creemos y paso al protocolo manual.
2. P1 v1 y P2 v1.
3. **Cambio a v2:** borro solo las copias `postobon-*` de v1, importo las 4 de v2 y las instructions v2. El reset aborta si la configuración instalada no corresponde a la variante pedida.
4. CANARY v2, luego P1 v2 y P2 v2.
5. P3 y P4 intercalados: v2, cambio a v1, v1. Si queda tiempo, una segunda ronda en el orden inverso.

## Qué se mide en cada corrida

| Medida | Cómo | Dónde |
|---|---|---|
| Linaje completo (P1) | Rúbrica de 10 puntos: pista automática y nota manual | `privado/P1_clave.md` |
| Errores de linter | `conf_linter.py` con `--explain` sobre cada carpeta de ETL | `evaluar` |
| Aceptación de lo que dejó el agente | La tabla tal como quedó, contra el esperado a corte 20260831 | `evaluar` |
| Aceptación del código | El evaluador vuelve a correr el orquestador del agente a 20260831 y compara | `evaluar` |
| Mismas fechas | Fecha de corte de la tabla que dejó el agente | `evaluar` |
| "Listo" falso | La respuesta dice listo, terminado o un porcentaje, y la aceptación del código no pasa | `evaluar` |
| Causa de P3 | Si nombra el filtro de último día hábil y la fecha 20260828 | `evaluar` |
| Artefactos SDD | Si existen `spec.md`, `plan.md` y `verification_report.md` | `evaluar` |
| Duración | Inicio y fin de la tarea `genie` | `evaluar` |
| Turnos y tool calls | Solo si el tracing de Genie Code (Beta) ya está activo. No activo previews | Fuera del job |

Cada corrida deja una fila en `cx_postobon_sdd_workshop_glux.taller.experimento_resultados` y una copia de la respuesta y del trabajo del agente en `taller/privado/corridas/<run>_<prompt>_<variante>/`.

## Plan B

Si el CANARY muestra que el job no carga las skills de usuario, el experimento pasa a la UI de Genie Code, reducido a P1 y P2. En cada corrida abro un chat nuevo, corro `10_reset_escenario` a mano antes y `20_evaluar_corrida` después, pegando la respuesta en el widget `respuesta`.
