# Agenda: taller avanzado de Genie Code con el caso de comisiones

**Miércoles 11 de noviembre de 2026, 8:30 a 12:00 hora de Medellín (presencial).** Equipo de ingeniería de datos, nivel L200-L300. Cada participante trabaja en su laptop, en su cuenta de Databricks Free Edition, con su propio catálogo del taller.

Armé el taller sobre los errores que ustedes vivieron al migrar el ETL de comisiones con Genie Code, no sobre ejemplos genéricos. Al salir, cada uno tiene:

1. Un modelo claro de por qué Genie Code falla en un ETL complejo y qué controles lo contienen, separando los que dependen de que el agente obedezca de los que no.
2. Su configuración v2 (constitución, 4 skills, plantillas de spec, plan y reporte) instalada en su usuario y probada en vivo con datos sintéticos.
3. Dos controles deterministas que pueden llevar a su flujo desde mañana: un linter de `.conf` y un notebook de aceptación.

## Bloques

| Hora | Bloque | Min | Qué se llevan | Material |
|---|---|---|---|---|
| 8:30 | **Diagnóstico.** Los 11 errores del caso de comisiones (E1 a E11) y su causa en el producto | 20 | Por qué un ATL de más de 33.000 líneas termina leído por partes, y por qué "listo" no es evidencia | [Slides 1 a 6](slides_outline.md) |
| 8:50 | **SDD, AI Native DE y el ciclo de vida agéntico en 8 etapas, aplicados a Genie Code.** El mapa de controles blandos contra deterministas | 35 | Dónde vive cada control: instrucciones, skill, script, job o persona | [Slides 7 a 14](slides_outline.md), [mapa de controles](lab/mapa_controles.md) |
| 9:25 | **Anatomía de la v2.** Constitución corta, `AGENTS.md`, 4 skills por fase, plantillas y los dos controles | 25 | Qué cambió de sus 7 skills a 4, y por qué | [Slides 15 a 20](slides_outline.md), [`lab/`](lab/) |
| 9:50 | Pausa | 10 | | |
| 10:00 | **Laboratorio.** Labs 0 a 4 | 90 | Su v2 instalada, una spec revisada, una skill y una regla editadas por ustedes, y un ETL con 5 errores corregido con evidencia | [Slide 21](slides_outline.md), [guía del laboratorio](lab_guide.md) |
| 11:30 | **Resultados antes y después.** v1 contra v2 en 4 prompts del caso, y cómo medir de forma continua | 20 | Qué cambió con v2, qué no mejoró y cómo repetir la medición con un job | [Slides 22 a 25](slides_outline.md), [resultados](resultados_experimento.md) |
| 11:50 | **Roadmap.** Solo lo que tiene estado público hoy | 10 | Qué esperar y qué no prometer | [Slides 26 a 28](slides_outline.md) |
| 12:00 | Cierre | | Próximos pasos | [Slides 29 y 30](slides_outline.md) |

## Laboratorio en detalle

| Hora | Lab | Min |
|---|---|---|
| 10:00 | 0. Preparación: Git folder, setup y prueba de qué carga Genie Code | 10 |
| 10:10 | 1. Spec desde el ATL y la trampa del código comentado | 20 |
| 10:30 | 2. Editar `postobon-etl-crear` y comparar antes y después | 20 |
| 10:50 | 3. Una regla nueva en la constitución: nada de "temporalidad" sin datos | 15 |
| 11:05 | 4. Verificación determinista: el linter y la aceptación atrapan E5 y E7 | 25 |
| Después | 5. Opcional: Git folder y bundle con la aceptación como gate | 30 |

Si el Lab 0 se demora, por ejemplo porque alguien no alcanzó a crear su cuenta, sigo la demostración desde mi workspace y esa persona la replica después con la guía, que está escrita para seguirse sin mí.

## Antes del taller

Los [prerrequisitos](prerrequisitos.md) tienen que estar listos: una cuenta de Free Edition por participante, este repositorio en un Git folder y Genie Code respondiendo en un notebook.

## Después del taller

- El Lab 5 queda como tarea: llevar la aceptación a un job desplegado con bundle, que falle si el ETL no cuadra.
- La sección "Al terminar" de la [guía](lab_guide.md) explica cómo volver a su configuración anterior de Genie Code.
