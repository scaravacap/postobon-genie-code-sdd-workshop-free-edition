# Mapeo de tablas: ATL `com_variable_mini.atl` a Unity Catalog

El ATL del taller lee tablas de datastores legacy (`DS_TALLER_*`) y archivos planos (`FF_TALLER_*`). En Unity Catalog existen con otro nombre, dentro del catálogo `{{Environment}}_glux`. Esta tabla es la fuente para la sección 3 de la spec: si una fuente del ATL no aparece aquí, no se reemplaza por una tabla parecida, se pregunta.

## Fuentes

| En el ATL | En Unity Catalog | Notas |
|---|---|---|
| `DS_TALLER_SAP.SAPHR.ZBPTA011` | `plata.he_source_sap_ecc_zbpta011` | `f_ingreso` y `f_retiro` llegan como texto `MM/dd/yyyy` |
| `DS_TALLER_DWH.DWH.FCT_PEDIDO_VENTA` | `oro.fct_pedido_venta` | `dk_cliente` tiene 14 caracteres: `1000` seguido del código de cliente de 10 |
| `DS_TALLER_DWH.DWH.DIM_PRODUCTO` | `oro.dim_producto` | |
| `DS_TALLER_DWH.DWH.DIM_FECHA` | `oro.dim_fecha` | `sk_fecha` es texto `yyyyMMdd`; `bl_dia_habil` vale `SI` o `NO` |
| `DS_TALLER_DWH.DWH.FCT_ROLLUP_VOLUMEN` | `plata.commision_rollup_volumen` | Acumulado del mes a cada día hábil |
| `DS_TALLER_CELUWEB.CW.AUTOVENTA` | `plata.he_source_celuweb_autoventa` | `fecha` llega como texto `yyyy-MM-dd` |
| `FF_TALLER_IN_PORTAFOLIO."portafolio_clientes.csv"` | `plata.commision_portafolio` | Columnas renombradas: `PORTAFOLIO` es `ds_portafolio`, `CANAL` es `ds_canal` |
| `FF_TALLER_IN_CTV_CF."factores_ctv.csv"` | `plata.commision_ctv_cf` | Se cargó sin encabezado: `_c0` es la presentación y `_c1` el factor, como texto |
| `FF_TALLER_IN_COBERTURA."metas_cobertura.csv"` | `plata.commision_cobertura` | `PERIODO` es `cd_periodo` y `META_CLIENTES` es `nm_clientes_meta` |

## Destinos

| En el ATL | En Unity Catalog |
|---|---|
| `TT_TALLER_DROPSIZE` | `oro.fct_com_var_dropsize` |
| `TT_TALLER_VOLUMEN_CTV` | `oro.fct_com_var_volumen_ctv` |
| `TT_TALLER_COBERTURA` | `oro.fct_com_var_cobertura` |

Las tablas `TT_TALLER_*` intermedias del ATL no se migran como tablas: en el estándar son pasos `tt_stg_*` dentro de la carpeta del proceso. Las salidas finales del ATL son las que `WF_TALLER_EXPORTAR` envía al formato TXSTA.

Las tres tablas destino ya existen, con el esquema que valida `validar_schema()`. Todas llevan `cd_periodo_mes`, `dt_corte`, `cd_planta`, `cd_registro_nomina`, sus columnas de valor y `ts_carga`.

## Fechas de la corrida de referencia

Con `P_FECHA = 20260831`: `l_fecha_ini = 20260801`, `l_fecha_fin = 20260831` y `l_fecha_ult_habil = 20260831`. Los archivos esperados están en `/Volumes/{{Environment}}_glux/taller/archivos/esperados/`, uno por tabla destino, con la fecha en el nombre.
