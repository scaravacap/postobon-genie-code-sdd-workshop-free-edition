# Resultados: v1 contra v2 con el Genie Code task

Medí cómo se comporta Genie Code **al primer intento y con autoaprobación** con dos configuraciones, sobre el mismo entorno sintético y los mismos prompts. Las correcciones humanas no entran aquí: se ven en los labs.

**En este entorno, v2 no mejoró el resultado:** v1 y v2 resolvieron P2, P3 y P4 al primer intento con la misma aceptación, y v1 sacó un punto más en P1. v2 dejó la evidencia en archivos escritos por scripts, en vez de solo en la respuesta, y tardó entre 16 % y 40 % más.

## Qué comparé

| | v1 | v2 |
|---|---|---|
| Instrucciones | La constitución que ustedes usan hoy | [Constitución v2](lab/constitucion_v2/) |
| Skills | Sus 7 skills `postobon-*` | Las 4 skills v2, con scripts y plantillas |
| `AGENTS.md` | No | Sí, en `DLKHNB_ORO/` |
| Común a las dos | El mismo bloque de adaptador: catálogo del taller, utilidades del taller y ruta del ATL reducido | |

Las dos variantes se instalaron en un solo usuario, con sus otras skills apagadas, y cada corrida empezó desde el mismo estado.

## Cómo lo medí

- **Un job con tres tareas:** `reset_escenario` deja el entorno en su estado inicial y comprueba que la configuración instalada es la de la variante pedida; `genie` es el Genie Code task con el prompt; `evaluar` corre el linter, la aceptación y las comprobaciones de cada métrica sobre lo que dejó el agente.
- **Por qué un job.** El Genie Code task abre un chat nuevo en cada corrida, hereda la configuración de Genie Code de quien lo configura y siempre autoaprueba ([Genie Code task](https://docs.databricks.com/aws/en/jobs/tasks/genie-code)). Eso da el mismo arranque en cada corrida y mide el primer intento sin ayuda.
- **CANARY primero.** Antes de cada variante, un prompt que lista las skills y las instrucciones cargadas confirma que el job ve lo que creemos.
- **Mismo texto.** `lanzar.py` toma los prompts de [`prompts.md`](lab/experimento/prompts.md), así que Genie Code recibe texto idéntico en v1 y en v2.
- El protocolo completo, para repetirlo en su workspace, está en [`protocolo_job.md`](lab/experimento/protocolo_job.md).

| Prompt | Qué pide | Errores del caso que provoca |
|---|---|---|
| P1 | Linaje completo de Cobertura desde el ATL | E1, E3, E11 |
| P2 | Crear la ETL de Dropsize, ejecutarla y compararla | E1, E4, E5, E7, E10 |
| P3 | Volumen CTV no cuadra: encontrar la causa y corregirla | E2, E5 |
| P4 | Excluir clientes de prueba en dos indicadores | E6, E7 |

## Qué medí en cada corrida

| Métrica | Cómo |
|---|---|
| Linaje de P1 | Nota de 10 puntos con una clave que no está en el repo, para no sesgar corridas futuras. La revisé a mano |
| Errores de linter | `conf_linter.py` con `explain` sobre cada carpeta de ETL |
| Aceptación | La tabla que dejó el agente contra el archivo esperado a corte 20260831, y el orquestador del agente corrido de nuevo por el evaluador |
| Mismas fechas | La fecha de corte de la tabla que dejó el agente |
| "Listo" sin evidencia | La respuesta dice listo, terminado o un porcentaje, y la aceptación no pasa |
| Causa de P3 | Si nombra el filtro de último día hábil y la fecha 20260828 |
| Artefactos SDD | Si existen `spec.md`, `plan.md` y `verification_report.md` |
| Duración | Inicio y fin de la tarea `genie` |

## Resultados

Corrí una vez cada prompt con cada variante, el 10 de noviembre de 2026, en un workspace de Azure Databricks y no en Free Edition. Todas las corridas terminaron al primer intento del job, ninguna citó material privado del evaluador y todas las tablas que dejó el agente quedaron a corte `20260831`, la fecha pedida.

| Prompt | Métrica | v1 | v2 |
|---|---|---|---|
| P1. Linaje de Cobertura | Nota sobre 10, revisada a mano | 10 | 9 |
| | Duración de `genie` | 283 s | 397 s |
| P2. Crear Dropsize | Aceptación de la tabla del agente y del orquestador corrido de nuevo | PASA 4 de 4, las dos | PASA 4 de 4, las dos |
| | Errores de linter | 0 | 0 |
| | "Listo" sin evidencia | No: dijo lista, con filas y totales | No: no dijo lista |
| | Artefactos SDD | Ninguno | `spec.md` y `plan.md` |
| | Duración de `genie` | 681 s | 790 s |
| P3. Volumen CTV no cuadra | Causa, las dos partes | Sí | Sí, con las líneas del ATL |
| | Aceptación, las dos | PASA 4 de 4 | PASA 4 de 4 |
| | Errores de linter | 0 | 0 |
| | Artefactos SDD | Ninguno | `verification_report.md` |
| | Duración de `genie` | 342 s | 448 s |
| P4. Excluir clientes de prueba | Aceptación de Dropsize y Cobertura, las dos | PASA 4 de 4 en las dos tablas | PASA 4 de 4 en las dos tablas |
| | Errores de linter | 0 en las dos carpetas | 0 en las dos carpetas |
| | "Listo" sin evidencia | No: no dijo lista, y avisó que los esperados son de antes del cambio | No: su reporte dice NO PASA contra los esperados de antes del cambio, y explicó por qué |
| | Artefactos SDD | Ninguno | `verification_report.md` en las dos carpetas |
| | Duración de `genie` | 480 s | 625 s |

Lo que hizo cada variante:

- **P1.** v1 sacó 10: dijo de forma explícita que `DF_TALLER_COBERTURA_HIST_TRN` no es parte del linaje porque ningún plan lo llama, declaró qué leyó completo y agregó riesgos ciertos que la clave no pedía. v2 sacó 9: usó `atl_inventario.py`, fijó el sha256 del ATL y citó línea en casi todas las afirmaciones, pero no mencionó ese dataflow. No cayó en el señuelo, pero tampoco lo descartó por escrito, y la clave lo pide.
- **P2.** Las dos dejaron una ETL que pasa los 4 escenarios, también cuando el evaluador volvió a correr el orquestador. v1 se declaró lista con evidencia, y acertó. v2 escribió spec y plan, pero el modo automático le bloqueó `conf_linter.py` y `aceptacion.py`. No se saltó el bloqueo: comparó con su propio SQL, no se declaró lista y marcó la spec como "aprobación asumida".
- **P3.** Las dos encontraron las dos causas, la fecha de corte y el `BETWEEN` sobre un acumulado diario, las probaron con una consulta aparte, sin pasar por la ETL, y corrigieron un solo archivo. v2 citó las líneas del ATL y dejó un `verification_report.md` de 5 de 5, escrito por los scripts; esta vez el clasificador no los bloqueó.
- **P4.** Las dos cambiaron los mismos 3 archivos y aplicaron el filtro al código de cliente de 10 dígitos, porque `dk_cliente` trae un prefijo y `LIKE '99%'` no habría excluido a nadie. Las dos esquivaron la trampa del `%` (E7), de formas distintas: v2 escribió `'99%%'`, que sobrevive a la interpolación de los `.conf`, y v1 usó `LEFT(..., 2) <> '99'` para no necesitar el `%`. Las dos respaldaron las tablas, comprobaron el cambio con una consulta aparte, sin pasar por los `.conf`, y llegaron a las mismas cifras. v1 además preguntó por los códigos con ceros delante, que sin esos ceros empezarían por 99.

La evidencia de cada celda es la salida de `20_evaluar_corrida` y mi lectura de cada respuesta. Estos son los runs del job:

| | v1 | v2 |
|---|---|---|
| CANARY | `577447492598826`, y `120602907414671` al volver a v1 | `567625745056717` |
| P1 | `1026183425219024` | `1058524660358271` |
| P2 | `381325650995671` | `284743636406509` |
| P3 | `644686788406269` | `628489250882529` |
| P4 | `1053353596859738` | `380590078992212` |

No publico la clave de P1 ni las respuestas del agente, para no sesgar las corridas que ustedes hagan.

## Lo que v2 no mejoró

- **El resultado, porque v1 ya acertaba.** v1 resolvió P2, P3 y P4 al primer intento con la misma aceptación que v2, y sacó 10 en P1. Con un ATL de 5.667 líneas, su configuración actual alcanza para estos prompts. E1, leer el ATL a pedazos, pesa más cuanto más grande es el archivo, y el ATL reducido es unas 6 veces más chico que el real.
  *Ajuste:* repetir la medición con su ATL real y sus prompts, en su workspace, con el mismo job ([`protocolo_job.md`](lab/experimento/protocolo_job.md)).
- **P1 bajó de 10 a 9.** El inventario cuenta los dataflows que ningún workflow llama, pero `linaje()` no los incluye y la sección 2 de la spec tampoco los pide. v2 siguió el inventario y no descartó el señuelo por escrito.
  *Ajuste:* que `linaje()` y la sección 2 de [`spec.md`](lab/plantillas/spec.md) listen los dataflows sin llamar que tengan un nombre parecido o el mismo destino, con la razón para dejarlos fuera.
- **El linaje de v2 trae menos contexto para migrar.** No dejó los riesgos que v1 sí dejó (el join con metas solo por registro, los nulos en `F_RETIRO`, una razón exportada como `PCT`) ni dijo qué leyó completo.
  *Ajuste:* agregar el tipo "Riesgo" a la sección 9 de la spec, "Supuestos y preguntas abiertas", y pedir en `postobon-spec-desde-atl` que declare qué leyó completo y qué solo buscó.
- **Tiempo.** v2 tardó más en los cuatro prompts: 40 % en P1, 16 % en P2, 31 % en P3 y 30 % en P4. Hace más pasos: inventario, spec, plan y verificación.
  *Ajuste:* una spec por indicador, que se aprueba una vez y se reusa. Con una spec aprobada, `postobon-spec-desde-atl` no vuelve al ATL.
- **La verificación dependió del clasificador.** En P2 el modo automático bloqueó `conf_linter.py` y `aceptacion.py`, que corren desde `.assistant/skills/`; en P3 y P4 los dejó correr. Es el comportamiento documentado: el clasificador "might approve unsafe actions or block safe ones" ([Approve tool actions](https://docs.databricks.com/aws/en/genie-code/navigate-genie-code)). La razón exacta del bloqueo solo la conozco por la respuesta del agente.
  *Ajuste, sin medir:* guardar los scripts en la Git folder del proyecto y registrarla como carpeta de skills, que la documentación permite ([skills](https://docs.databricks.com/aws/en/genie-code/skills)). Y que el gate que decide si una ETL pasa corra fuera del agente, en un job o en el CI, como en el Lab 5.
- **El reporte afirmaba "Cambios: Ninguno".** `escribir_reporte` escribía "Ninguno en esta verificación." cuando nadie le pasaba la lista de cambios, y el ejemplo de la skill no la pasaba. Los tres reportes de P3 y P4 dijeron "Ninguno" aunque el agente había cambiado uno y tres `.conf`. En P3 el agente lo aclaró en su respuesta.
  *Ajuste, ya aplicado después de medir:* sin lista, el reporte ahora dice "(nada declarado: ...)", y el ejemplo de la skill pasa `cambios`. No volví a medir con este cambio.

## Límites

- **Una corrida por prompt y variante.** Los resultados son indicativos, no estadísticos: una sola corrida puede salir bien o mal por azar.
- **Primer intento con autoaprobación.** En el trabajo diario ustedes aprueban, corrigen y vuelven a pedir, y eso no está medido aquí.
- **La aprobación de la spec quedó asumida.** En el job nadie aprueba, así que v2 marcó su spec como "aprobación asumida" y siguió. En el taller la aprueba una persona.
- **Lo que el agente deja fuera de su ETL.** En P4 las dos variantes dejaron tablas de respaldo en el schema `taller`, que el reset no limpiaba: 4 en v2, entre ellas su recálculo, y 2 en v1. Borré las de v2 antes de P4 v1, porque el recálculo era en la práctica la respuesta. Si repiten el experimento, agreguen esa limpieza al reset.
- **Entorno sintético.** El ATL reducido tiene 5.667 líneas y 48 dataflows, contra más de 33.000 líneas del real. Las trampas son las del caso, pero el tamaño no.
- **Dos corridas iguales pueden diferir.** Un modelo de lenguaje no responde siempre lo mismo ante el mismo prompt. Las capacidades de agente de Genie Code corren sobre Azure OpenAI, OpenAI on Databricks y Anthropic on Databricks ([partner-powered](https://docs.databricks.com/aws/en/databricks-ai/partner-powered)).
