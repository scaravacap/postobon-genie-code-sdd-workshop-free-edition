# AGENTS.md: ETL de capa oro de Postobón

Este archivo vive en la raíz de la carpeta de ETL (`DLKHNB_ORO/`) y se versiona en Git con el código. Genie Code lo lee solo cuando trabajas en un archivo de esta carpeta o de una subcarpeta. Complementa las instructions del workspace: no las repite, fija lo que tiene que viajar con el código.

## Definition of Done de una ETL
Una ETL está terminada cuando su carpeta `DLKHID_<NOMBRE>/` tiene estos cuatro artefactos y el último dice PASA:

| Artefacto | Qué prueba | Quién lo produce |
|---|---|---|
| `spec.md` con estado `APROBADA por <persona>, <fecha>` | Qué se construye y contra qué se compara | `@postobon-spec-desde-atl` o entrevista, más una persona |
| `plan.md` | Qué archivo cubre cada requisito y con qué escenario se prueba | `@postobon-etl-crear` |
| Salida de `conf_linter.py` sin errores | Que las `.conf` cargan y siguen el estándar | `@postobon-etl-verificacion` |
| `verification_report.md` con PASA | Que los datos cuadran con el esperado, en la misma fecha | `@postobon-etl-verificacion` |

Sin `verification_report.md` no se dice "listo" ni se pide paso a `prbs`.

## Estructura de una carpeta de ETL
```
DLKHID_<NOMBRE>/
  spec.md
  plan.md
  verification_report.md
  PARAMETROS/config_par_<proceso>.conf
  INSUMOS/config_ins_##_<alias>.conf        (lee de plata u oro; tipo = insumo)
  INTERMEDIAS/config_int_##_<alias>.conf    (escribe en stg; tipo = intermedia)
  SALIDAS/config_sal_##_<tabla>.conf        (SELECT final hacia oro; tipo = salida)
  DLKH_01_<NOMBRE>                          (notebook orquestador de 13 pasos)
```
- Toda tabla de plata u oro que es primera fuente del proceso va en `INSUMOS/`.
- La carpeta de un `.conf` y su `tipo` coinciden. El linter lo revisa.
- El nombre de la tabla destino lo confirma una persona: si viene del ATL, se pregunta si se conserva.

## Cómo se verifica aquí
1. Linter de la carpeta, contra la spec:
   `conf_linter.py --carpeta <ruta>/DLKHID_<NOMBRE> --spec <ruta>/DLKHID_<NOMBRE>/spec.md`
2. Ejecución del orquestador con la fecha de corte de la spec.
3. Aceptación contra el archivo esperado, con la misma fecha de corte en los dos lados.

Las skills `@postobon-etl-crear` y `@postobon-etl-verificacion` traen los scripts y saben cómo llamarlos.

## Cambios a una ETL que ya está en `prbs` o `prod`
- No se edita a mano en `prbs` ni en `prod`. Se cambia en `dllo`, se verifica y se promueve con el pipeline de despliegue.
- Después de cada despliegue se relee la `.conf` desplegada y se compara su hash con el de `verification_report.md`. Si no coincide, el despliegue revirtió algo.
- Un cambio por vez, con su escenario de regresión. Si un mismo ajuste aplica a varios indicadores, se prueba en uno, se mide y luego se replica.
