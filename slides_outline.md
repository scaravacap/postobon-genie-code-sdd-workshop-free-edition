# Guion de diapositivas

30 diapositivas para los 210 minutos de la [agenda](agenda.md). Cada una trae el mensaje que tiene que quedar, el contenido y la fuente pública de cada afirmación de producto. Lo que describe la v2 del taller está en [`lab/`](lab/) y no necesita otra fuente.

## Bloque 1. Diagnóstico (8:30, 20 min)

### 1. Genie Code en el ETL de comisiones: de "listo" a evidencia

**Mensaje:** hoy salimos con controles que no dependen de que el agente obedezca.

- Taller avanzado, L200-L300. Spec-Driven Development y ciclo de vida agéntico, aplicados dentro de Genie Code.
- Miércoles 11 de noviembre de 2026, Medellín.

### 2. Qué se llevan hoy

**Mensaje:** tres cosas concretas, probadas en su workspace.

1. Un modelo de por qué Genie Code falla en un ETL complejo y qué control contiene cada falla.
2. Su configuración v2 instalada en su usuario: constitución, 4 skills y plantillas.
3. Dos controles deterministas para su flujo diario: el linter de `.conf` y el notebook de aceptación.

### 3. El caso: migrar comisiones desde SAP Data Services

**Mensaje:** el problema no es generar código, es generar el código correcto de un legado grande.

- Un ATL de más de 33.000 líneas, con dataflows, workflows, variables `$L_*` y código comentado mezclado con el activo.
- Un framework propio: `.conf` en PARAMETROS, INSUMOS, INTERMEDIAS y SALIDAS, un orquestador `DLKH_01_<NOMBRE>` y utilidades como `procesar_tablas`.
- Una configuración v1: constitución de workspace y 7 skills `postobon-*`.

### 4. Once errores, una causa común

**Mensaje:** cada error es una afirmación que nadie verificó.

| | Error |
|---|---|
| E1 | Leyó el ATL a pedazos y tomó código comentado por activo |
| E2 | Atribuyó diferencias a "temporalidad" sin una query |
| E3 | Omitió una rama de un UNION y no encontró tablas que existían |
| E4 | Dijo "listo" o "idéntico" sin comparar |
| E5 | Comparó una corrida de un día contra archivos de otro |
| E6 | Reportó cambios que el archivo no tenía |
| E7 | Replicó un cambio a varios archivos sin validar y rompió la interpolación con `%` |
| E8 | Se dio a sí mismo un porcentaje de fidelidad |
| E9 | Tomó fechas de `parametros_dict` donde tocaba `stg.par_*` |
| E10 | Usó columnas ambiguas o inexistentes después de un JOIN |
| E11 | Sustituyó tablas parecidas sin avisar |

Detalle completo: [mapa de controles](lab/mapa_controles.md).

### 5. Lo que el producto hace con un contexto largo

**Mensaje:** un archivo enorme siempre se lee por partes, y lo que no cupo no avisa.

- "Genie Code automatically summarizes, compacts, and truncates long context, but only a new chat clears it completely." ([guía de consumo](https://docs.databricks.com/aws/en/genie/consumption-guide))
- Las instrucciones tienen un límite de 20.000 caracteres, y "Genie Code doesn't use any instructions past this limit." ([instructions](https://docs.databricks.com/aws/en/genie-code/instructions))
- Una skill editada aplica solo en un chat nuevo. ([skills](https://docs.databricks.com/aws/en/genie-code/skills))
- En su caso: E1 y E6 nacen aquí.

### 6. Instrucciones y aprobaciones guían, no bloquean

**Mensaje:** todo lo que está escrito en texto es una preferencia del modelo.

- Entre instrucciones de workspace y de usuario, "Genie Code generally prioritizes workspace instructions over user instructions." Es una tendencia, no una regla. ([instructions](https://docs.databricks.com/aws/en/genie-code/instructions))
- La aprobación por defecto es Auto-approve, que "is a productivity feature, not a security boundary". Existe la opción de pedir aprobación antes de actuar. ([Navigate Genie Code](https://docs.databricks.com/aws/en/genie-code/navigate-genie-code))
- No encontré en la documentación hooks que corran antes o después de una acción del agente.
- La práctica que pide la propia guía: "Work in steps and verify as you go" y "Give verification targets". ([guía de consumo](https://docs.databricks.com/aws/en/genie/consumption-guide))

## Bloque 2. SDD, AI Native DE y el ciclo de vida agéntico (8:50, 35 min)

### 7. Spec-Driven Development en una frase

**Mensaje:** la spec es el contrato y el código es una derivación que se puede verificar contra ella.

- Orden de trabajo: spec, plan, tareas, implementación y verificación, con una revisión humana entre spec y código.
- Herramientas públicas que lo empaquetan: [Spec Kit](https://github.com/github/spec-kit) y [OpenSpec](https://github.com/Fission-AI/OpenSpec). Las evalué en [este documento](openspec_speckit_assessment.md).

### 8. AI Native Data Engineering

**Mensaje:** el recurso escaso deja de ser escribir SQL y pasa a ser verificarlo.

- El agente escribe `.conf`, SQL y pruebas en minutos.
- El equipo escribe y aprueba lo que el agente no puede inventar: la spec, los criterios de aceptación y los controles.
- Un ETL se da por terminado cuando su evidencia pasa, no cuando el agente lo dice.

### 9. Qué lleva la spec de un indicador

**Mensaje:** la spec cierra las puertas por donde entraron E1, E3, E5 y E11.

- Fuentes en Unity Catalog, cada una marcada EXISTE, NO EXISTE o AMBIGUA. Las dos últimas bloquean.
- Linaje completo desde el ATL, con cada rama de cada UNION.
- Filtros y cálculos activos, separados del código comentado.
- Parámetros y fechas de corte fijos, con su origen en `stg.par_*`.
- Llaves de comparación y criterios de aceptación.
- Plantilla: [`lab/plantillas/spec.md`](lab/plantillas/spec.md).

### 10. Un ciclo de vida agéntico en 8 etapas

**Mensaje:** un agente necesita las mismas etapas que un equipo, con evidencia en cada salida.

1. **Encargo.** Qué se pide, con qué datos y cómo se sabrá que quedó bien.
2. **Plan.** Archivos, supuestos y cómo se verifica cada uno, antes de tocar nada.
3. **Ejecución acotada.** Solo lo planeado, un archivo a la vez.
4. **Revisión.** Otra mirada contra el encargo, no contra lo que el agente cree que hizo.
5. **Prueba.** Evidencia ejecutable: linter, `EXPLAIN` y aceptación.
6. **Entrega.** Versionado y despliegue repetible.
7. **Observación.** Qué pasó en uso real y cuánto costó.
8. **Mejora.** Cada error nuevo se vuelve una regla o un control.

### 11. Las 8 etapas dentro de Genie Code, hoy

**Mensaje:** cada etapa tiene un artefacto y un responsable.

| Etapa | En Genie Code | Artefacto | Control |
|---|---|---|---|
| Encargo | Prompt con `@skill` | `spec.md` aprobada | Humano |
| Plan | `postobon-etl-crear` | `plan.md` | Skill y humano |
| Ejecución acotada | Un archivo a la vez, con aprobación antes de editar | `.conf` | Skill y humano |
| Revisión | Relectura del fragmento editado, revisión de una persona | Fragmento releído | Skill y humano |
| Prueba | `conf_linter.py`, `explain` y aceptación | `verification_report.md` | Script y job |
| Entrega | Git folder, bundle y Azure DevOps | Commit y job | CI |
| Observación | Tabla de sistema, tracing y costo | Consultas | Plataforma |
| Mejora | Editar skill o constitución, y volver a medir | Nueva versión | Humano y job |

### 12. Blando contra determinista

**Mensaje:** si un control tiene que cumplirse siempre, no puede vivir solo en texto.

- **S, blando:** una regla en la constitución o en una skill. Depende de que el agente obedezca.
- **A, asistido:** un script que la skill ejecuta. El resultado no depende del modelo, aunque invocarlo sí.
- **D, determinista:** fuera del agente. Un job, el CI, permisos de Unity Catalog o un guard en las utilidades.
- **H, humano:** una persona aprueba la spec, el plan o la edición.
- La guía de consumo describe la palanca de A: cuando una skill trae un script, Genie Code "loads the skill, and runs the script rather than planning". ([guía de consumo](https://docs.databricks.com/aws/en/genie/consumption-guide))

### 13. Cada error con su control

**Mensaje:** ningún error depende de un solo control blando.

| Error | Control principal | Tipo |
|---|---|---|
| E1 | `atl_inventario.py` lee el ATL completo | A |
| E2 | Sin query no hay causa, y la aceptación entrega el diff | S, A/D |
| E3 | Inventario de `information_schema` y linter contra la spec | A |
| E4 | `verification_report.md` generado por script | A |
| E5 | La aceptación aborta si las fechas no coinciden | A/D |
| E6 | Releer y mostrar el fragmento final, sha256 en el reporte | S, A |
| E7 | El linter interpola como producción | A/D |
| E8 | Sin porcentajes: estados contados y escenarios | S, A |
| E9 | Solo `config_par_*` usa `{{parametros[...]}}` | A/D |
| E10 | El linter corre `EXPLAIN` sobre cada query | A |
| E11 | Detenerse y reportar, fuentes limitadas a la spec | S, A/D |

### 14. Dónde vive cada control en Genie Code

**Mensaje:** ustedes ya tienen todos estos puntos de apoyo, sin pedir nada nuevo.

- **Instrucciones de usuario:** `/Users/<usuario>/.assistant_instructions.md`. Las de workspace solo las edita un admin. ([instructions](https://docs.databricks.com/aws/en/genie-code/instructions))
- **`AGENTS.md`:** Genie Code lo lee solo, subiendo por las carpetas desde el archivo abierto. Es una constitución que viaja con el código en Git. ([instructions](https://docs.databricks.com/aws/en/genie-code/instructions))
- **Skills:** de usuario, de workspace o en carpetas registradas, incluidas Git folders. Pueden traer scripts que el agente ejecuta. ([skills](https://docs.databricks.com/aws/en/genie-code/skills))
- **Jobs:** el Genie Code task corre un prompt dentro de un job. ([Genie Code task](https://docs.databricks.com/aws/en/jobs/tasks/genie-code))
- **Plataforma:** Genie Code "is governed by your Unity Catalog permissions" ([Genie Code](https://docs.databricks.com/aws/en/genie-code/)), y los presupuestos de Genie alertan o bloquean ([budgets](https://docs.databricks.com/aws/en/genie/budgets)).

## Bloque 3. Anatomía de la v2 (9:25, 25 min)

### 15. De 7 skills a 4

**Mensaje:** una skill por fase del trabajo, no por tipo de archivo.

| v1 | v2 |
|---|---|
| `postobon-conf-archivos`, `postobon-etl-orquestador`, `postobon-etl-hechos`, `postobon-etl-dimensiones` | Referencias dentro de `postobon-etl-crear` |
| `postobon-etl-validacion` | `postobon-etl-verificacion` |
| `postobon-atl-comparacion` | `postobon-atl-comparacion`, con aceptación determinista |
| (no existía) | `postobon-spec-desde-atl` |

### 16. Constitución corta y `AGENTS.md`

**Mensaje:** la constitución dice qué nunca se hace, y las skills dicen cómo se hace.

- Reglas de evidencia: sin query no hay causa, sin reporte no hay "listo", sin porcentajes de fidelidad.
- Reglas de alcance: un cambio a la vez, releer lo editado, comparar solo con la misma fecha de corte y detenerse si falta un insumo.
- `AGENTS.md` en `DLKHNB_ORO/`, versionado con el código.
- Las instrucciones no pueden mandar a leer otros archivos, así que el detalle va en las skills. ([instructions](https://docs.databricks.com/aws/en/genie-code/instructions))
- Archivos: [`lab/constitucion_v2/`](lab/constitucion_v2/).

### 17. `postobon-spec-desde-atl`

**Mensaje:** el ATL lo lee un script, no el modelo.

- Corre `atl_inventario.py`, que recorre el ATL completo: dataflows, queries, fuentes, destinos, variables y cada línea comentada, incluidas las que están dentro de un valor.
- Con el inventario arma `spec.md` y la deja para aprobación.
- Si ya hay una spec aprobada, no vuelve al ATL.
- Ataca E1, E3, E8 y E11.

### 18. `postobon-etl-crear`

**Mensaje:** sin spec aprobada no hay código.

- Primero un `plan.md`: archivos, supuestos y la query que verifica cada supuesto.
- Una persona aprueba el plan.
- Después escribe un `.conf` a la vez, corre el linter, lo relee y muestra el fragmento final.
- Trae como referencia las convenciones que antes vivían en cuatro skills.

### 19. `postobon-etl-verificacion` y los controles

**Mensaje:** "listo" es un reporte que generó un script.

- `conf_linter.py` interpola cada `.conf` con configparser, igual que en producción, y revisa plantillas de parámetros, `tablas_entrada`, fuentes contra la spec y catálogos fijos.
- Con `explain`, renderiza cada query y corre `EXPLAIN` en Spark sin ejecutarla.
- La aceptación compara contra el archivo esperado por llave, aborta si las fechas de corte no coinciden y corre 4 escenarios.
- `verification_report.md` guarda el sha256 de cada `.conf` y el resultado de cada escenario.

### 20. Las plantillas

**Mensaje:** una plantilla vacía obliga a contestar lo que el agente saltaría.

- `spec.md`: fuentes con estado, linaje, reglas activas y comentadas, fechas, llaves y criterios.
- `plan.md`: archivos, supuestos con "Cómo lo verifico" y riesgos.
- `verification_report.md`: hashes, linter, escenarios y lo que quedó sin verificar.
- Archivos: [`lab/plantillas/`](lab/plantillas/).

## Bloque 4. Laboratorio (10:00, 90 min)

### 21. Laboratorio

**Mensaje:** cada lab ataca errores concretos del caso.

| Lab | Min | Errores |
|---|---|---|
| 0. Preparación | 10 | |
| 1. Spec desde el ATL | 20 | E1, E3, E8, E11 |
| 2. Editar `postobon-etl-crear` | 20 | E4, E6, E11 |
| 3. Una regla contra la "temporalidad" | 15 | E2, E5 |
| 4. Linter y aceptación | 25 | E3, E5, E7, E9, E10 |
| 5. Opcional: bundle con gate | 30 | E4, E6 |

Guía: [`lab_guide.md`](lab_guide.md).

## Bloque 5. Resultados y medición continua (11:30, 20 min)

### 22. Cómo medí v1 contra v2

**Mensaje:** el mismo prompt, la misma tabla y el mismo arranque, cambiando solo la configuración.

- Un job con tres tareas: reiniciar el escenario, el Genie Code task con el prompt, y una evaluación con linter y aceptación.
- El Genie Code task abre un chat nuevo con el prompt, hereda la configuración de Genie Code de quien lo configura y siempre autoaprueba: "Auto-approval is always on for job tasks". Por eso mide el primer intento, sin correcciones humanas. ([Genie Code task](https://docs.databricks.com/aws/en/jobs/tasks/genie-code))
- Cuatro prompts del caso: linaje de Cobertura, crear Dropsize, Volumen CTV que no cuadra y un filtro en varias confs.
- Una corrida por prompt y variante: los resultados son indicativos, no estadísticos.

### 23. Resultados

**Mensaje:** en este entorno, v2 no mejoró el resultado: cambió dónde queda la evidencia, y costó más tiempo.

| Prompt | v1 | v2 |
|---|---|---|
| P1. Linaje de Cobertura | 10 de 10 | 9 de 10: no descartó por escrito el dataflow señuelo |
| P2. Crear Dropsize | Pasa 4 de 4. Dijo lista, con evidencia | Pasa 4 de 4, con spec y plan. El clasificador bloqueó su verificación |
| P3. Volumen CTV no cuadra | Pasa 4 de 4, con las dos causas | Pasa 4 de 4, con las dos causas, las líneas del ATL y el reporte del script |
| P4. Excluir clientes de prueba | Pasa 4 de 4 en las dos tablas | Pasa 4 de 4 en las dos tablas, con el reporte del script |
| Minutos de Genie Code, de P1 a P4 | 4,7 · 11,4 · 5,7 · 8,0 | 6,6 · 13,2 · 7,5 · 10,4 |

Detalle, evidencia y runs: [`resultados_experimento.md`](resultados_experimento.md).

### 24. Lo que v2 no mejoró

**Mensaje:** cada hallazgo trae el ajuste que propongo, y los ajustes se miden con el mismo job.

- El resultado: v1 ya resolvía los cuatro prompts en un ATL de 5.667 líneas. Propongo medir con su ATL real, unas 6 veces más grande.
- P1 bajó a 9: el inventario no lista los dataflows que nadie llama. Propongo que el linaje y la spec los listen.
- Tardó entre 16 % y 40 % más. Propongo una spec por indicador, aprobada una vez y reusada.
- El clasificador de autoaprobación bloqueó la verificación en P2 y la dejó correr en P3 y P4. Propongo los scripts en la Git folder del proyecto, registrada como carpeta de skills, y el gate final en un job o en el CI. ([Navigate Genie Code](https://docs.databricks.com/aws/en/genie-code/navigate-genie-code), [skills](https://docs.databricks.com/aws/en/genie-code/skills))
- El reporte decía "Cambios: Ninguno" sin que nadie lo declarara. Ya lo corregí, sin volver a medir.

### 25. Medir de forma continua

**Mensaje:** cada cambio a una skill se mide igual que un cambio a un ETL.

- El mismo job, con un prompt fijo por error del caso, después de cada cambio a la configuración.
- `system.access.assistant_events` registra una fila por mensaje de usuario, en Public Preview. ([tabla de sistema](https://docs.databricks.com/aws/en/admin/system-tables/assistant))
- Costo: cada usuario recibe 150 DBU gratis al mes, y Genie Code se cobra por encima de eso. Hasta el 31 de enero de 2027 el uso cobrado tiene 25 % de descuento. Se filtra en la tabla de facturación con `usage_metadata.genie.surface = 'GENIE_CODE'`. ([costo de Genie](https://docs.databricks.com/aws/en/genie/monitor-cost))
- Los presupuestos de Genie alertan o bloquean, por usuario o compartidos. ([budgets](https://docs.databricks.com/aws/en/genie/budgets))

## Bloque 6. Roadmap (11:50, 10 min)

### 26. Genie Code CLI, en Beta

**Mensaje:** útil para trabajo local, pero no replica su configuración del workspace.

- "Genie Code CLI loads skills only from local folders. It does not load skills or instructions from your workspace or from Unity Catalog." ([CLI](https://docs.databricks.com/aws/en/genie-code/genie-code-cli))
- Lee `AGENTS.md`, así que la constitución versionada sí viaja.
- Repositorio público: [databricks/genie-code-cli](https://github.com/databricks/genie-code-cli).

### 27. Observabilidad

**Mensaje:** ya se puede ver qué hizo el agente, no solo qué dijo.

- Tracing de Genie Code, en Beta, que hay que activar en el workspace: cada turno queda como spans de OpenTelemetry, con el prompt, la respuesta, los datos citados, la duración y las acciones que tomó el agente. ([Genie traces](https://docs.databricks.com/aws/en/ai-gateway/genie-traces))
- `system.access.assistant_events`, en Public Preview. ([tabla de sistema](https://docs.databricks.com/aws/en/admin/system-tables/assistant))
- Lo que no hay: tokens por sesión en ninguna tabla de sistema.

### 28. Lo que hoy no existe, y qué hacer mientras tanto

**Mensaje:** no diseñen sobre capacidades que no están documentadas.

- Desde el 29 de junio Genie Code trabaja solo en modo agente. ([notas de junio](https://docs.databricks.com/aws/en/release-notes/product/2026/june))
- No hay un modo de solo planear ni hooks documentados. Para que no ejecute, se le pide en el prompt: "Just explain this to me, don't run any code". ([Genie Code](https://docs.databricks.com/aws/en/genie-code/))
- Mientras tanto: plan aprobado por una persona, aprobación antes de editar, y controles en scripts y jobs.
- Orquestadores externos: el proyecto open source Omnigent tiene trabajo abierto para usar Genie Code como harness ([issue](https://github.com/omnigent-ai/omnigent/issues/9886)). Hasta que se integre, no lo pondría en su flujo.

## Cierre (12:00)

### 29. Próximos pasos

**Mensaje:** el taller termina cuando la v2 corre en su primer ETL real.

1. Lab 5: la aceptación como gate en un job desplegado con bundle.
2. Llevar la v2 a una Git folder del equipo y registrarla como carpeta de skills.
3. Medir v1 contra v2 en su workspace con el job del experimento.
4. Volver a su configuración anterior si lo necesitan: sección "Al terminar" de la [guía](lab_guide.md).

### 30. Fuentes

- Genie Code: [overview](https://docs.databricks.com/aws/en/genie-code/), [instructions](https://docs.databricks.com/aws/en/genie-code/instructions), [skills](https://docs.databricks.com/aws/en/genie-code/skills), [Navigate Genie Code](https://docs.databricks.com/aws/en/genie-code/navigate-genie-code), [memory](https://docs.databricks.com/aws/en/genie-code/memory), [CLI](https://docs.databricks.com/aws/en/genie-code/genie-code-cli).
- Operación: [guía de consumo](https://docs.databricks.com/aws/en/genie/consumption-guide), [costo de Genie](https://docs.databricks.com/aws/en/genie/monitor-cost), [budgets](https://docs.databricks.com/aws/en/genie/budgets), [tabla de sistema](https://docs.databricks.com/aws/en/admin/system-tables/assistant), [Genie traces](https://docs.databricks.com/aws/en/ai-gateway/genie-traces).
- Jobs y CI: [Genie Code task](https://docs.databricks.com/aws/en/jobs/tasks/genie-code), [recursos de bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/resources), [Azure DevOps](https://docs.databricks.com/aws/en/dev-tools/ci-cd/azure-devops).
- Estándares y herramientas: [Agent Skills](https://agentskills.io/specification), [Spec Kit](https://github.com/github/spec-kit), [OpenSpec](https://github.com/Fission-AI/OpenSpec).
