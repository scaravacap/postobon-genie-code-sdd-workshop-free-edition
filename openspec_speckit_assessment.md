# OpenSpec y Spec Kit dentro de Genie Code

**Mi recomendación: SDD nativo en Genie Code, con skills y artefactos en markdown.** Tomen de OpenSpec y Spec Kit el método y la forma de los artefactos, pero hoy no instalen ninguno de los dos para usarlo dentro de Genie Code. Para ustedes, el costo de adoptarlos tal cual es alto y lo que aportan ya está en la v2 del taller.

Revisé las dos herramientas el 9 de noviembre de 2026, en sus repositorios públicos.

## Qué son

| | Spec Kit | OpenSpec |
|---|---|---|
| Repositorio | [github/spec-kit](https://github.com/github/spec-kit), licencia MIT | [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec), licencia MIT |
| Versión al 9-nov | v1.3.2, del 6-nov. Unas 149.000 estrellas | v1.16.1, del 7-nov. Unas 74.000 estrellas |
| Instalación | `uv tool install specify-cli` y `specify init <proyecto> --integration <agente>`, en una terminal con Python 3.11 o superior | La CLI por script, npm (Node.js 22.12 o superior) o Homebrew, y luego `openspec init` |
| Flujo | `/speckit-constitution`, `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement` y `/speckit-converge`, que se repite con implement hasta que reporta `Converged` | `/opsx:explore`, `/opsx:propose`, `/opsx:apply` y `/opsx:archive` |
| Artefactos | Markdown en el repo: constitución, spec, plan y tareas por feature, con su configuración en `.specify/` | Una carpeta por cambio en `openspec/changes/<id>/`, con `proposal.md`, `specs/`, `design.md` y `tasks.md`, que al cerrar pasa a `archive/` |
| Agentes | Varios agentes de código, más una integración genérica. El ejemplo oficial usa GitHub Copilot | Más de 30 herramientas |
| ¿Genie Code en su lista? | No | No |

## Qué pasa si los traen tal cual

1. **Se instalan en una terminal, no en Genie Code.** Los dos piden una CLI local y un `init` que escribe los comandos para un agente concreto, y Genie Code no está entre sus integraciones. Spec Kit pide explícitamente "a supported AI coding agent on Linux, macOS, or Windows".
2. **Dependen de su CLI o de sus scripts mientras trabajan.** Los comandos de OpenSpec consultan su CLI durante el flujo, así que dentro de Genie Code necesitarían Node.js y la CLI en el compute del chat, que es serverless por defecto ([skills](https://docs.databricks.com/aws/en/genie-code/skills)). Los de Spec Kit llaman a los scripts en bash, PowerShell o Python que vienen con la herramienta, pensados para la terminal de un agente local. No probé ninguno de los dos dentro de Genie Code.
3. **No conocen su framework.** Ninguno sabe qué es un `.conf`, una plantilla `{{parametros[...]}}` o un ATL de SAP Data Services. Los errores que más costaron en la migración de comisiones, como leer el ATL a pedazos (E1), comparar fechas distintas (E5) o romper la interpolación (E7), se atrapan con controles del dominio, no con un flujo genérico de spec y plan.

## Lo que tomé de ellos para la v2

| Idea | De dónde viene | Cómo quedó en la v2 |
|---|---|---|
| Una constitución corta que rige todo el trabajo | Spec Kit, `/speckit-constitution` | Las instrucciones de usuario v2, más un `AGENTS.md` que viaja con el código en Git |
| Spec antes de código, con aprobación de una persona | Los dos | `postobon-spec-desde-atl` escribe `spec.md`, y `postobon-etl-crear` no arranca sin una spec aprobada |
| Plan y tareas como artefacto que se revisa | Spec Kit (`/speckit-plan`, `/speckit-tasks`) y OpenSpec (`design.md`, `tasks.md`) | `plan.md`, con cada supuesto y la query que lo verifica |
| Una carpeta por cambio que se cierra con evidencia | OpenSpec, `changes/` y `archive/` | La carpeta de cada ETL guarda `spec.md`, `plan.md` y `verification_report.md` |
| Implementar y verificar en ciclo hasta cerrar | Spec Kit, `/speckit-converge` | `postobon-etl-verificacion`, con el linter de `.conf` y la aceptación como criterio de salida |

Lo que la v2 agrega y ninguno de los dos trae son los controles deterministas del dominio: el inventario completo del ATL, el linter de `.conf` y la aceptación contra archivos esperados. Están en [`lab/controles/`](lab/controles/) y el [mapa de controles](lab/mapa_controles.md) explica qué error atrapa cada uno.

## Cuándo volver a evaluarlos

- Si Genie Code aparece en la lista de integraciones de alguno de los dos.
- Si parte del equipo trabaja con un agente local, como GitHub Copilot, sobre su repositorio de Azure DevOps. Ahí sí corren como están diseñados.
