# Taller avanzado de Genie Code: Spec-Driven Development en un ETL de comisiones

Material del taller para el equipo de ingeniería de datos de Postobón, nivel L200-L300. Muestra cómo aplicar Spec-Driven Development (SDD) y un ciclo de vida agéntico **dentro de Genie Code**, con los errores reales de la migración de un ETL de comisiones desde SAP Data Services como punto de partida.

Esta es la variante para **Databricks Free Edition**, con una cuenta gratuita por participante, para cuando su workspace de desarrollo no tenga listos los permisos del taller. Los labs, los prompts y los controles son los mismos de la [versión para su workspace](https://github.com/scaravacap/postobon-genie-code-sdd-workshop), y se pueden seguir con o sin facilitador. Todo el laboratorio corre con **datos sintéticos** y con un ATL reducido construido para el taller: no contiene datos ni código reales de la empresa.

## Por dónde empezar

1. Revisen los [prerrequisitos](prerrequisitos.md): una cuenta de Free Edition y este repositorio en un Git folder.
2. Sigan la [guía del laboratorio](lab_guide.md) desde el Lab 0. Está escrita para seguirse sin facilitador.

## Qué cambia frente a la versión para su workspace

| Tema | Su workspace de desarrollo | Free Edition |
|---|---|---|
| Catálogo | Lo crea el admin, uno por participante | Lo crea el setup: `cx_postobon_sdd_workshop_glux` en cada cuenta |
| Permisos | Entitlement Workspace access y acceso a GitHub desde Git folders | Ninguno que pedir: el repositorio es público y cada persona tiene su propio workspace |
| Skills `postobon-*` del equipo | Cada participante las apaga solo para sí durante el taller | No existen en Free Edition, así que ese paso no aplica |
| Compute | Serverless | Serverless, con una cuota de uso diaria |
| Documentación citada | Azure Databricks | Databricks en AWS, la nube donde corre Free Edition |

## Contenido

| Archivo | Qué es |
|---|---|
| [`agenda.md`](agenda.md) | Bloques del taller de 210 minutos |
| [`slides_outline.md`](slides_outline.md) | Guion de diapositivas, con fuentes públicas |
| [`lab_guide.md`](lab_guide.md) | Labs 0 a 4 y el 5 opcional, con prompts, resultado esperado y troubleshooting |
| [`resultados_experimento.md`](resultados_experimento.md) | Experimento v1 contra v2 con el Genie Code task de Jobs |
| [`openspec_speckit_assessment.md`](openspec_speckit_assessment.md) | Si OpenSpec o Spec Kit sirven tal cual dentro de Genie Code |
| [`prerrequisitos.md`](prerrequisitos.md) | Lo que debe estar listo en el workspace antes del taller |
| [`lab/`](lab/) | Todo lo que se instala y se ejecuta en el workspace |

## Qué hay en `lab/`

| Carpeta | Qué contiene |
|---|---|
| [`mapa_controles.md`](lab/mapa_controles.md) | Los 11 errores del caso (E1 a E11), con su control, dónde vive y si es blando o determinista |
| `constitucion_v2/` | Instrucciones v2 de Genie Code y el `AGENTS.md` que viaja con el código |
| `skills_v2/` | Las 4 skills v2: `postobon-spec-desde-atl`, `postobon-etl-crear`, `postobon-etl-verificacion` y `postobon-atl-comparacion`, con sus scripts y plantillas |
| `plantillas/` | `spec.md`, `plan.md` y `verification_report.md` |
| `controles/` | `atl_inventario.py`, `conf_linter.py`, `aceptacion.py`, el notebook `verificacion_aceptacion` y un `databricks.yml` mínimo, con sus pruebas |
| `entorno/` | Setup del catálogo sintético, utilidades del framework con las mismas firmas, el ATL del taller, las ETL de referencia y los escenarios con errores sembrados |
| `experimento/` | Prompts, notebooks de reset y evaluación, y el protocolo del job del experimento v1 contra v2 |

## Cómo protege el taller su entorno

- **Guard de catálogo.** El setup y las utilidades se niegan a trabajar sobre un catálogo que no empiece por `cx_postobon_sdd`. Es el mismo guard que en su workspace impide escribir en `dllo_glux`, `prbs_glux` y `prod_glux`.
- **Configuración personal.** Las skills y las instrucciones v2 se instalan en la carpeta del usuario, con respaldo de las instrucciones anteriores.
- **Datos sintéticos.** Las tablas, el ATL y los archivos esperados se generan con una semilla fija: son inventados y reproducibles. Free Edition es para uso personal y no comercial ([límites](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)): no suban ahí datos ni código reales de la empresa.

## Qué está probado

En mi cuenta de Free Edition, el 10 de noviembre de 2026, desde un Git folder de este repositorio clonado sin credenciales de Git:

- El setup creó el catálogo `cx_postobon_sdd_workshop_glux` y cargó los datos sintéticos en 107 s.
- Las 3 ETL de referencia pasan el linter y la aceptación, 4 de 4 escenarios, y la tabla sembrada da `NO COMPARABLE`, como espera el Lab 3.
- El Lab 0 con todo en `si`, sobre el catálogo ya creado, terminó en 60 s e instaló en mi usuario la constitución v2, las 4 skills v2 y el `AGENTS.md`.
- El prompt de verificación del Lab 0, en un chat nuevo de Genie Code: lista las 4 skills v2 y las instrucciones v2 con el adaptador del taller.
- El camino del participante: la ETL del Lab 4 muestra sus 5 errores como se diseñaron, y corregida da `PASA` con 48 filas.
- El bundle del Lab 5, desplegado y corrido desde zsh: pasa con la ETL correcta, falla en `aceptacion` con otra fecha de corte y falla en `etl` con la ETL del Lab 4, que trae un `%` suelto.

Antes lo había instalado y corrido en un workspace de Azure Databricks con serverless, el 9 y el 10 de noviembre de 2026:

- Las 3 ETL de referencia pasan el linter y la aceptación, 4 de 4 escenarios.
- El camino del participante, desde una copia de `lab/` en el workspace: setup, controles y la ETL del Lab 4, cuyos 5 errores aparecen como se diseñaron.
- Las pruebas locales de los controles y del entorno pasan.
- El bundle del Lab 5, desplegado y corrido desde zsh: pasa con la ETL correcta, falla en `aceptacion` con otra fecha de corte y falla en `etl` con un `%` suelto en un `.conf`.
- El 10 de noviembre, el setup con `instalar_v2 = si` desde una copia de `lab/`: instaló la constitución y las 4 skills v2 en mi usuario, y esa fue la v2 del experimento.
- El 10 de noviembre, el Lab 0 completo desde un Git folder de la versión para su workspace: el setup con todo en `si` terminó en 127 s, instaló la v2 en mi usuario y respaldó mis instrucciones y las 2 skills con el mismo nombre.

Lo que todavía no probé:

- Los prompts de los Labs 1 a 4 con Genie Code en Free Edition. Los corrí en Azure con el job del experimento, que se crea desde la interfaz de Jobs.

La comparación de v1 contra v2 está en [`resultados_experimento.md`](resultados_experimento.md). En el entorno sintético, v2 no mejoró el resultado: las dos variantes resolvieron casi lo mismo al primer intento, y v2 dejó más evidencia escrita por scripts y tardó más.

## Fuentes

Las afirmaciones de producto del material citan la documentación pública de Databricks en AWS, la nube donde corre Free Edition. Las principales: [Genie Code](https://docs.databricks.com/aws/en/genie-code/), [instructions](https://docs.databricks.com/aws/en/genie-code/instructions), [skills](https://docs.databricks.com/aws/en/genie-code/skills), [Navigate Genie Code](https://docs.databricks.com/aws/en/genie-code/navigate-genie-code) y [Genie Code task para jobs](https://docs.databricks.com/aws/en/jobs/tasks/genie-code).
