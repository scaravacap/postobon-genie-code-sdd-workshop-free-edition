# Genie Code en Postobón: ETL de capa oro (v2)

Responde en español. El usuario sale de `current_user()`.

## 1. Flujo: Brief, Spec, Plan, Implementar, Verificar
1. **Brief.** Resume en 5 líneas: tabla destino, fuentes, parámetros con default y archivos de salida.
2. **Spec.** Sin spec `APROBADA` por una persona no se escriben `.conf` ni notebooks. Con ATL usa `@postobon-spec-desde-atl`: el ATL se inventaría con su script, no se lee entero. Sin ATL, entrevista con las preguntas de `@postobon-etl-crear`.
3. **Plan.** `@postobon-etl-crear` escribe `plan.md` y espera confirmación.
4. **Implementar.** Un archivo a la vez, con el linter después de cada `.conf`.
5. **Verificar.** `@postobon-etl-verificacion` deja `verification_report.md`. Para ATL vs ETL, `@postobon-atl-comparacion`.

## 2. Evidencia
- **Sin query no hay causa.** Una causa raíz va con la query y su resultado. Si no, escribe "Hipótesis:" y la query que la probaría.
- **"Listo" exige reporte.** Ni listo, ni 100 %, ni % de fidelidad sin el resumen de `verification_report.md`. Lo no probado se lista como no verificado.
- **Antes de decir que algo falta, búscalo** en `information_schema` y muestra el resultado. Si no existe, detente y avisa. Nunca uses una tabla parecida sin preguntar.
- **Relee lo que editas** y muestra el fragmento final. Sin relectura no hay "aplicado".
- **Un cambio a la vez:** cambia, ejecuta, verifica. Si toca más de 3 archivos, lista y pide confirmación.
- **Mismas fechas.** Antes de comparar, confirma que los dos lados tienen la misma fecha de corte.
- **La spec manda.** Si la spec no cubre algo, es una pregunta abierta, no una suposición.

## 3. Contexto
- Catálogo `{{Environment}}_glux` (`dllo`, `prbs`, `prod`). Schemas `oro` (`fct_*`, `dim_*`), `plata`, `stg` (`par_*`, `tt_stg_*`) y `conf` (`traza_config_tabla`).
- Carpeta `DLKHID_<NOMBRE>` con `PARAMETROS/`, `INSUMOS/`, `INTERMEDIAS/`, `SALIDAS/` y notebook `DLKH_01_<NOMBRE>` en `/Users/{usuario}/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_<TIPO>/`.
- Archivos `config_par_<proceso>`, `config_ins_##_<alias>`, `config_int_##_<alias>`, `config_sal_##_<tabla>`. Alias `tt_stg_*` sin prefijos legacy (hana, as4, sql, celweb).
- Utilidades de `/Workspace/Shared/databricks_repo_{entorno}`: `from notebooks.DLKHNB_ORO.utilidades.<modulo> import ...`, nunca `functions.functions`.
- `fct_*` con DELETE acotado + APPEND; `dim_*` con `guardar_tabla()`, salvo indicación contraria.

## 4. `.conf` que rompen en ejecución
- Solo SELECT con CTEs. Único subquery: el escalar de fechas `(SELECT l_fecha_ini FROM {{catalogo}}.stg.par_<proceso>)`.
- `{{parametros[...]}}` solo en `config_par_*`; el resto lee fechas de `stg.par_*`.
- `%` literal se escribe `%%`: `LIKE '%%TRADICIONAL%%'`.
- Todo alias del SQL va en `tablas_entrada`; el catálogo no se escribe a mano; columnas calificadas después de un JOIN.
