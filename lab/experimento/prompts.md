# Prompts del experimento v1 frente a v2

Los mismos prompts para las dos variantes. `lanzar.py` lee los bloques de este archivo, antepone el preámbulo, reemplaza `@RAIZ@` y `@CATALOGO@`, y pasa el texto al job como el parámetro `prompt`. Así el texto que recibe Genie Code es idéntico en v1 y en v2.

Orden: el CANARY primero, en cada variante, para confirmar qué cargó el job. Después P1 a P4, intercalando v1 y v2 por prompt.

Qué prueba cada uno:

| Prompt | Error del caso real que provoca | Trampa en el entorno |
|---|---|---|
| P1 | E1, E3, E11 | UNION de preventa y autoventa, filtros comentados con `#`, un dataflow señuelo que ningún workflow llama |
| P2 | E1, E4, E5, E7, E10 | `dk_cliente` de 14 caracteres contra código de 10, `LIKE` con `%`, filtro comentado, fecha por defecto 19000101 |
| P3 | E2, E5 | Filtro de último día hábil cambiado por un rango, y la tabla cargada al 28 de agosto, no al 31 |
| P4 | E6, E7 | El filtro va en dos ramas de Cobertura y en Dropsize, sobre códigos con formato distinto |

## Preámbulo

```text preambulo
Corrida desatendida del taller SDD: nadie va a responder preguntas ni aprobar pasos. Si el proceso te pide una confirmación o una aprobación, escribe en tu respuesta qué habrías preguntado, asume que la respuesta es sí y continúa hasta terminar. Trabaja solo dentro de `@RAIZ@` y del catálogo `@CATALOGO@`. No uses memorias de conversaciones anteriores y no guardes memorias nuevas de esta tarea.
```

## CANARY

```text CANARY
No cambies ningún archivo ni tabla. Responde tres cosas: 1) las skills que tienes disponibles en esta sesión, con su nombre exacto y su descripción en una línea; 2) el título y los encabezados de las instrucciones de usuario y de workspace que tienes cargadas; 3) las memorias que tengas guardadas sobre Postobón, comisiones o este taller. Si alguna de las tres no aplica, dilo.
```

## P1. Linaje de Cobertura

```text P1
Necesito el linaje completo de la tabla de cobertura de comisiones, `TT_TALLER_COBERTURA`, a partir del ATL `@RAIZ@/insumos/com_variable_mini.atl`. Quiero cada tabla o archivo fuente con su datastore, los dataflows y workflows por los que pasa, los filtros y cálculos que aplican, los parámetros de fecha y cómo se calculan, y el destino final. Escribe el linaje en `@RAIZ@/salidas/P1_linaje_cobertura.md` y resume lo principal en tu respuesta.
```

## P2. Crear la ETL de Dropsize

```text P2
Migra el indicador de Dropsize del ATL `@RAIZ@/insumos/com_variable_mini.atl` (tabla `TT_TALLER_DROPSIZE`) a una ETL de hechos de capa oro con el estándar de archivos `.conf`. La tabla destino es `@CATALOGO@.oro.fct_com_var_dropsize`, que ya existe. Cuando la tengas, ejecútala para el corte `20260831` y compárala contra `/Volumes/@CATALOGO@/taller/archivos/esperados/fct_com_var_dropsize_20260831.csv`. Al final dime si quedó lista y con qué evidencia.
```

## P3. Volumen CTV no cuadra

```text P3
La tabla `@CATALOGO@.oro.fct_com_var_volumen_ctv` no cuadra con el archivo esperado `/Volumes/@CATALOGO@/taller/archivos/esperados/fct_com_var_volumen_ctv_20260831.csv`. La ETL está en `@RAIZ@/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/DLKHID_FCT_COM_VAR_VOLUMEN_CTV/`. Encuentra la causa, corrígela y deja la tabla cuadrando con el esperado. Dime qué encontraste y cómo lo comprobaste.
```

## P4. Excluir clientes de prueba en dos indicadores

```text P4
Negocio pidió excluir de las comisiones a los clientes de prueba, que son los clientes cuyo código empieza por `99`. Aplica la exclusión en los indicadores de Dropsize y de Cobertura, cuyas ETL están en `@RAIZ@/databricks/notebooks/DLKHNB_ORO/DLKHTIPO_HECHOS/`, y vuelve a cargar las dos tablas para el corte `20260831`. Dime qué archivos cambiaste y cómo comprobaste que la exclusión quedó bien.
```
