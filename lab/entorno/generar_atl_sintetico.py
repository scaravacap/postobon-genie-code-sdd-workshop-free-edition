"""Genera com_variable_mini.atl: un ATL de SAP Data Services sintético con las trampas del caso real.

Todo es inventado: nombres DF_TALLER_*, datastores DS_TALLER_*, GUIDs de una semilla fija.
Imita la forma del formato (sentencias CREATE, ALGUIComment, mapeos con código comentado,
SELECT compilado, cargas con su XML, workflows con BEGIN_SCRIPT) para que leerlo por partes
sea tan engañoso como el real. Lo que hay que migrar son tres indicadores:

    TT_TALLER_DROPSIZE     -> oro.fct_com_var_dropsize
    TT_TALLER_VOLUMEN_CTV  -> oro.fct_com_var_volumen_ctv
    TT_TALLER_COBERTURA    -> oro.fct_com_var_cobertura

La lógica activa coincide con el oráculo de datos_sinteticos.py.

    python generar_atl_sintetico.py [--salida insumos/com_variable_mini.atl]
"""
import argparse
import os
import random
import uuid
import zlib

SEMILLA = 11112026
rng = random.Random(SEMILLA)
GUIDS = {}

DWH, SAP, STG, CW = ("DS_TALLER_DWH", "DWH"), ("DS_TALLER_SAP", "SAPHR"), ("DS_TALLER_STAGE", "STG_TALLER"), ("DS_TALLER_CELUWEB", "CW")


def g():
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def guid_de(nombre):
    if nombre not in GUIDS:
        GUIDS[nombre] = g()
    return GUIDS[nombre]


def esc(s):
    return s.replace("\\", "\\\\").replace("'", "\\'")


def mapeo_ui(expr, com):
    """Texto de mapeo de la UI. Como en el ATL real, la alternativa comentada va a veces antes y a veces después."""
    if not com:
        return expr
    comentadas = ["#" + c for c in com]
    return "\n".join(comentadas + [expr] if zlib.crc32(expr.encode()) % 3 == 0 else [expr] + comentadas)


UI_BASE = (
    '"InputSchema_WidthProp" = \'34\', "Input_1st_Column_Name" = \'Type\', "Input_2nd_Column_Name" = \'Description\', '
    '"Input_Column_Name_3" = \'Content_Type\', "Input_Column_Name_4" = \'Business_Name\', "Input_Column_Width_3" = \'100\', '
    '"Input_Column_Width_4" = \'100\', "Input_Width_Description" = \'130\', "Input_Width_Type" = \'85\', '
    '"Output_1st_Column_Name" = \'Type\', "Output_2nd_Column_Name" = \'Mapping\', "Output_3rd_Column_Name" = \'Description\', '
    '"Output_Column_Name_4" = \'Content_Type\', "Output_Column_Name_5" = \'Business_Name\', "Output_Column_Width_4" = \'100\', '
    '"Output_Column_Width_5" = \'100\', "Output_Width_Decsription" = \'130\', "Output_Width_Mapping" = \'85\', '
    '"Output_Width_Type" = \'80\', "UI_DATA_XML" = \'<UIDATA><MAINICON><LOCATION><X>0</X><Y>0</Y></LOCATION><SIZE><CX>400</CX>'
    '<CY>-164</CY></SIZE></MAINICON><DESCRIPTION><LOCATION><X>0</X><Y>-175</Y></LOCATION><SIZE><CX>200</CX><CY>200</CY></SIZE>'
    '<VISIBLE>0</VISIBLE></DESCRIPTION></UIDATA>\', "UI_PASSTHRU_VSPLIT_PCT" = \'50\', "UpperContainer_HeightProp" = \'42\''
)
UI_PLAN = (
    '"UI_DATA_XML" = \'<UIDATA><MAINICON><LOCATION><X>0</X><Y>0</Y></LOCATION><SIZE><CX>297</CX><CY>-179</CY></SIZE></MAINICON>'
    '<DESCRIPTION><LOCATION><X>0</X><Y>-190</Y></LOCATION><SIZE><CX>200</CX><CY>200</CY></SIZE><VISIBLE>0</VISIBLE></DESCRIPTION></UIDATA>\''
)
SET_VISTA = (
    'SET("distinct_run_as_separate_process" = \'no\', "group_by_run_as_separate_process" = \'no\', '
    '"join_run_as_separate_process" = \'no\', "order_by_run_as_separate_process" = \'no\', "run_as_separate_process" = \'no\')'
)


def ldr(ds, modo="append", recrear="yes"):
    tags = [
        ("odbc_database_type", "HANA"), ("newdb_version", "HANA 1.x"), ("auto_correct_using_merge", "yes"),
        ("bulk_ldr_cleanup", "yes"), ("bulk_ldr_generate_files_only", ""), ("bulk_ldr_max_discards", "10"),
        ("enable_partitioning", "no"), ("ignore_column_case", "yes"), ("ignore_columns_null", "no"), ("ignore_columns_value", ""),
        ("loader_auto_correct", "no"), ("loader_bulk_load", "1"), ("loader_compare_column", "compare_by_name"),
        ("loader_delete_map", ""), ("loader_drop_and_create_table", recrear), ("loader_insert_map", ""),
        ("loader_load_choice", modo), ("loader_newdb_bind_array_size", "10000"), ("loader_num_parallel_loaders", "default"),
        ("loader_overflow_file", ""), ("loader_post_load1", ""), ("loader_pre_load1", ""), ("loader_quote_names", "0"),
        ("loader_transactional", "no"), ("loader_transactional_order", "0"), ("loader_update_key_columns", "no"),
        ("loader_update_map", ""), ("loader_use_user_defined_keys", "no"), ("loader_xact_size", "1000"),
        ("newdb_bulk_ldr_commit_size", "default"), ("newdb_bulk_ldr_mode", "append"), ("newdb_bulk_ldr_update_method", "default"),
        ("newdb_ldr_identity_upsert", "off"), ("newdb_table_type", "column_store"), ("overflow_file_format", "write_data"),
        ("sql_text", ""), ("text_delimiter", ""), ("use_overflow_file", "no"), ("use_unicode_varchar", "no"),
    ]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', "<LDRConfigurations>", '<LDRConfiguration database_type="ODBC" database_version="ODBC">']
    xml += [f"<{k}>{v}</{k}>" for k, v in tags]
    xml += ["</LDRConfiguration>", "</LDRConfigurations>"]
    return xml


# ---------------------------------------------------------------- elementos de dataflow


def ui(display, desde=(), where=None):
    partes = [UI_BASE] + [f'"ui_acta_from_schema_{i}" = \'{d}\'' for i, d in enumerate(desde)]
    partes.append(f'"ui_display_name" = \'{display}\'')
    if where is not None:
        partes.append(f'"ui_where_text" = \'{esc(where)}\'')
    return f'ALGUIComment ({", ".join(partes)}, "x" = \'{rng.randint(100, 2400)}\', "y" = \'{-rng.randint(80, 700)}\')'


def leer_tabla(ds, tabla, alias=None):
    alias = alias or tabla
    return [
        ui(alias),
        f"GUID::'{g()}' READ TABLE {ds[0]}.{ds[1]}.{tabla} OUTPUT({alias})",
        f'SET("Initial_Load" = \'no\', "array_fetch_size" = \'1000\', "cache" = \'yes\', "connection_port" = \'no\', '
        f'"enable_partitioning" = \'no\', "name" = \'{ds[0]}\', "package_size" = \'0\', "parallel_sap_connections" = \'0\', '
        f'"reader_is_DB2CDC_table" = \'no\', "reader_overflow_file" = \'overflow_file\');',
        "",
    ]


def leer_archivo(formato, archivo):
    return [
        ui(formato),
        f'GUID::\'{g()}\' READ FILE {formato}."{archivo}" OUTPUT({formato})',
        'SET("adaptable" = \'no\', "cache" = \'yes\', "connection_port" = \'no\', "file_location" = \'local\', "name" = \'UNNAMED\', '
        '"number_of_threads" = \'<default>\', "read_subfolders" = \'yes\', "reader_capture_data_conversion_errors" = \'no\', '
        '"root_dir" = \'[$$Dir_Taller_Entrada]\');',
        "",
    ]


def vista(nombre, columnas, desde, joins=(), where=None, where_ui=None, group_by=None, distinct=False):
    """columnas: [(nombre, tipo, expresion_activa, [lineas_comentadas])]. joins: [(INNER|LEFT_OUTER, tabla, condicion)]."""
    if where_ui is None and where is not None:
        where_ui = where
    out = [ui(nombre, desde=list(desde) + [j[1] for j in joins], where=where_ui)]
    for i, (col, tipo, expr, com) in enumerate(columnas):
        mapeo = mapeo_ui(expr, com)
        pref = f"GUID::'{g()}' CREATE VIEW {nombre}( " if i == 0 else " "
        suf = " ," if i < len(columnas) - 1 else "  )"
        out.append(f'{pref}{col} {tipo}  SET( "ui_mapping_text" = \'{esc(mapeo)}\'){suf}')
    out.append(" AS")
    sel = "SELECT " + ("DISTINCT " if distinct else "") + ", ".join(c[2] for c in columnas) + " FROM " + ", ".join(desde)
    for tipo, tabla, cond in joins:
        sel += f" __SAP_{tipo}_JOIN {tabla}  ON ({cond})SET(\"ui_on_text\" = '{esc(cond)}')"
    out.append(sel)
    cola = []
    if where:
        cola.append(f" WHERE ({where})")
    if group_by:
        cola.append(f" GROUP BY {group_by}")
    if cola:
        out.append("".join(cola))
    out += [SET_VISTA, ";", ""]
    return out


def merge(nombre, entradas):
    return [ui(nombre, desde=entradas), f"GUID::'{g()}' CALL TRANSFORM Merge() INPUT({', '.join(entradas)}) OUTPUT({nombre}()", ");", ""]


def transformacion_sql(nombre, ds, columnas, sql):
    cols = " , ".join(f"{c} {t}" for c, t in columnas)
    sql_xml = sql.replace("\n", "&#xD;&#xA;").replace("'", "&apos;")
    return [
        ui(nombre),
        f"GUID::'{g()}' CALL TRANSFORM SQL() OUTPUT({nombre}( {cols} ))",
        f'SET("array_fetch_size" = \'1000\', "cache" = \'yes\', "database_datastore" = \'{ds}\', "sql_transform_configurations" = '
        f"'<?xml version=\"1.0\" encoding=\"UTF-8\"?><SQLTransformConfigurations><SQLTransformConfiguration database_type=\"ODBC\">"
        f"<sql_text>{esc(sql_xml)}</sql_text></SQLTransformConfiguration></SQLTransformConfigurations>');",
        "",
    ]


def cargar_tabla(ds, tabla, entrada, modo="append", recrear="yes"):
    xml = ldr(ds[0], modo, recrear)
    return (
        [ui(tabla), f"GUID::'{g()}' LOAD TABLE {ds[0]}.{ds[1]}.{tabla} INPUT({entrada})",
         'SET("connection_port" = \'no\', "ldr_configuration_enabled" = \'yes\', "ldr_configurations" = \'' + xml[0]]
        + xml[1:-1]
        + [xml[-1] + f'\', "loader_template_table" = \'yes\', "name" = \'{ds[0]}\', "use_unicode_varchar" = \'no\');', ""]
    )


def cargar_archivo(formato, archivo, entrada):
    return [
        ui(formato),
        f'GUID::\'{g()}\' LOAD FILE {formato}."{archivo}" INPUT({entrada})',
        'SET("connection_port" = \'no\', "file_location" = \'local\', "isstreamdebugfile" = \'no\', "loader_load_choice" = \'replace\', '
        '"name" = \'UNNAMED\', "root_dir" = \'[$$Dir_Taller_Salida_TXSTA]\', "transfer_custom" = \'no\', "validate_decimal_data" = \'yes\');',
        "",
    ]


DATAFLOWS, TABLAS, WORKFLOWS = {}, {}, {}


def dataflow(nombre, parametros, elementos, descripcion):
    params = ", ".join(f"{p} VARCHAR(8)  IN " for p in parametros)
    fecha = f"Mon Mar  {rng.randint(2, 9)} {rng.randint(8, 17)}:{rng.randint(10, 59)}:{rng.randint(10, 59)} 2026"
    DATAFLOWS[nombre] = (
        [f"CREATE  DATAFLOW {nombre}::'{guid_de(nombre)}'({params})", "BEGIN", ""]
        + elementos
        + [
            "END",
            ' SET ("Cache_type" = \'pageable_cache\', "Parallelism_degree" = \'default\', "allows_both_input_and_output" = \'yes\', '
            '"dataflow_loader_bulk_load" = \'no\', "dataflow_loader_commit_size" = \'default\', "run_once" = \'no\', "use_dataflow_links" = \'no\')',
            f' AlGUIComment ("ActaName_1" = \'RSavedAfterCheckOut\', "ActaName_2" = \'RDate_modified\', "ActaName_3" = \'RDescription\', '
            f'"ActaValue_1" = \'YES\', "ActaValue_2" = \'{fecha}\', "ActaValue_3" = \'{esc(descripcion)}\', "x" = \'-1\', "y" = \'-1\')',
            "",
        ]
    )


def tabla(ds, nombre, columnas, mapeos=None, llave=None):
    """columnas: [(nombre, tipo)]. mapeos: {columna: texto ui_mapping_text} para template tables."""
    lineas = []
    for i, (c, t) in enumerate(columnas):
        props = [f'"Description" = \'{esc(c.replace("_", " ").title())}\'']
        if mapeos and c in mapeos:
            props.append(f'"ui_mapping_text" = \'{esc(mapeos[c])}\'')
        cierre = ")" if i == len(columnas) - 1 else ""
        pref = f"CREATE TABLE {ds[0]}.{ds[1]}.{nombre}(" if i == 0 else ""
        lineas.append(f"{pref}{c} {t}  NULL  SET({', '.join(props)}){cierre}, " if not cierre else f"{pref}{c} {t}  NULL  SET({', '.join(props)})) ")
    if llave:
        lineas.append(f"PRIMARY KEY ({llave}) ")
    lineas += [f'SET("db_alias_name" = \'{ds[1]}\')', ";", ""]
    plantilla = "yes" if ds == STG else "no"
    lineas += [f" AlGUIComment (ActaName_1 = 'RLoader_Is_Template_Table',ActaValue_1 = '{plantilla}' , ", " ActaName_2 = 'RTable_Type',ActaValue_2 = 'TABLE' )", ""]
    TABLAS[f"{ds[0]}.{ds[1]}.{nombre}"] = lineas


def columnas_de(vista_cols):
    return [(c[0], c[1]) for c in vista_cols]


def mapeos_de(vista_cols):
    return {c[0]: mapeo_ui(c[2], c[3]) for c in vista_cols}


# ---------------------------------------------------------------- los tres indicadores y sus extracciones


def nucleo():
    # Registro de nómina: representantes vigentes a la fecha de corte.
    q1 = [
        ("PERNR", "VARCHAR(8)", "ZBPTA011.PERNR", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "ZBPTA011.REGNOM", []),
        ("DS_CARGO", "VARCHAR(40)", "ZBPTA011.STEXT", []),
        ("CD_PLANTA", "VARCHAR(4)", "ZBPTA011.PLANTA", []),
        ("CD_ZONA", "VARCHAR(10)", "ZBPTA011.ZONA", []),
        ("DT_INGRESO", "VARCHAR(8)", "to_char(to_date(ZBPTA011.F_INGRESO, 'MM/DD/YYYY'), 'YYYYMMDD')", []),
        ("DT_RETIRO", "VARCHAR(8)", "to_char(to_date(ZBPTA011.F_RETIRO, 'MM/DD/YYYY'), 'YYYYMMDD')", []),
    ]
    q2 = [
        ("PERNR", "VARCHAR(8)", "QRY_FILTRA_REPRESENTANTES.PERNR", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "QRY_FILTRA_REPRESENTANTES.CD_REGISTRO_NOMINA", []),
        ("DS_CARGO", "VARCHAR(40)", "QRY_FILTRA_REPRESENTANTES.DS_CARGO", []),
        ("CD_PLANTA", "VARCHAR(4)", "QRY_FILTRA_REPRESENTANTES.CD_PLANTA", []),
        ("CD_ZONA", "VARCHAR(10)", "QRY_FILTRA_REPRESENTANTES.CD_ZONA", []),
        ("CD_CANAL", "VARCHAR(20)", "ifthenelse(QRY_FILTRA_REPRESENTANTES.DS_CARGO like '%AUTOSERVICIO%', 'AUTOSERVICIO', 'TRADICIONAL')",
         ["ifthenelse(QRY_FILTRA_REPRESENTANTES.CD_ZONA like '10%', 'TRADICIONAL', 'OTRO')"]),
    ]
    dataflow("DF_TALLER_REGISTRO_NOMINA_EXT", ["$P_FECHA_FIN"],
             leer_tabla(SAP, "ZBPTA011")
             + vista("QRY_FILTRA_REPRESENTANTES", q1, ["ZBPTA011"],
                     where="(ZBPTA011.STEXT like '%REPRESENTANTE VENTAS%') AND (ZBPTA011.BUKRS <> 'CC01')",
                     where_ui="ZBPTA011.STEXT like '%REPRESENTANTE VENTAS%'\nAND ZBPTA011.BUKRS <> 'CC01'\n#AND ZBPTA011.STEXT like '%TRADICIONAL%'\n")
             + vista("QRY_VIGENTES", q2, ["QRY_FILTRA_REPRESENTANTES"],
                     where="(QRY_FILTRA_REPRESENTANTES.DT_INGRESO <= $P_FECHA_FIN) AND (QRY_FILTRA_REPRESENTANTES.DT_RETIRO >= $P_FECHA_FIN)",
                     where_ui="QRY_FILTRA_REPRESENTANTES.DT_INGRESO <= $P_FECHA_FIN\nAND QRY_FILTRA_REPRESENTANTES.DT_RETIRO >= $P_FECHA_FIN")
             + cargar_tabla(STG, "TT_TALLER_REGISTRO_NOMINA", "QRY_VIGENTES"),
             "Representantes de ventas vigentes a la fecha de corte, desde la ZBPTA011 de SAP HR")
    tabla(STG, "TT_TALLER_REGISTRO_NOMINA", columnas_de(q2), mapeos_de(q2), "CD_REGISTRO_NOMINA")

    # Pedidos del mes.
    cols_ped = ["SK_FECHA", "DK_CLIENTE", "CD_REGISTRO_NOMINA", "CD_PLANTA", "CD_PRODUCTO", "CD_TIPO_DOCUMENTO", "NM_PEDIDO",
                "VL_VENTA_NETA", "VL_VENTA_BRUTA", "VL_CANTIDAD"]
    tipos_ped = ["VARCHAR(8)", "VARCHAR(14)", "VARCHAR(10)", "VARCHAR(4)", "VARCHAR(10)", "VARCHAR(2)", "VARCHAR(12)",
                 "DECIMAL(18, 2)", "DECIMAL(18, 2)", "DECIMAL(18, 2)"]
    q_ped = [(c, t, f"FCT_PEDIDO_VENTA.{c}", []) for c, t in zip(cols_ped, tipos_ped)]
    dataflow("DF_TALLER_PEDIDO_VENTA_EXT", ["$P_FECHA_INI", "$P_FECHA_FIN"],
             leer_tabla(DWH, "FCT_PEDIDO_VENTA")
             + vista("QRY_PEDIDOS_MES", q_ped, ["FCT_PEDIDO_VENTA"],
                     where="(FCT_PEDIDO_VENTA.SK_FECHA >= $P_FECHA_INI) AND (FCT_PEDIDO_VENTA.SK_FECHA <= $P_FECHA_FIN)",
                     where_ui="FCT_PEDIDO_VENTA.SK_FECHA >= $P_FECHA_INI\nAND FCT_PEDIDO_VENTA.SK_FECHA <= $P_FECHA_FIN\n#AND FCT_PEDIDO_VENTA.SK_FECHA = $P_FECHA_FIN")
             + cargar_tabla(STG, "TT_TALLER_PEDIDO_VENTA", "QRY_PEDIDOS_MES"),
             "Pedidos de preventa del mes en curso")
    tabla(STG, "TT_TALLER_PEDIDO_VENTA", columnas_de(q_ped), mapeos_de(q_ped))

    # Portafolio de clientes desde archivo.
    q_port = [
        ("CD_CLIENTE", "VARCHAR(10)", "FF_TALLER_IN_PORTAFOLIO.CD_CLIENTE", []),
        ("CD_PLANTA", "VARCHAR(4)", "FF_TALLER_IN_PORTAFOLIO.CD_PLANTA", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "FF_TALLER_IN_PORTAFOLIO.CD_REGISTRO_NOMINA", []),
        ("DS_PORTAFOLIO", "VARCHAR(10)", "upper(FF_TALLER_IN_PORTAFOLIO.PORTAFOLIO)", ["FF_TALLER_IN_PORTAFOLIO.PORTAFOLIO"]),
        ("DS_CANAL", "VARCHAR(30)", "upper(FF_TALLER_IN_PORTAFOLIO.CANAL)", []),
    ]
    dataflow("DF_TALLER_PORTAFOLIO_EXT", [],
             leer_archivo("FF_TALLER_IN_PORTAFOLIO", "portafolio_clientes.csv")
             + vista("QRY_PORTAFOLIO", q_port, ["FF_TALLER_IN_PORTAFOLIO"])
             + cargar_tabla(STG, "TT_TALLER_PORTAFOLIO", "QRY_PORTAFOLIO"),
             "Portafolio y canal de cada cliente, desde el archivo que envía Comercial")
    tabla(STG, "TT_TALLER_PORTAFOLIO", columnas_de(q_port), mapeos_de(q_port))

    # Dropsize.
    q_ventas = [
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "TT_TALLER_PEDIDO_VENTA.CD_REGISTRO_NOMINA", []),
        ("CD_CLIENTE", "VARCHAR(10)", "TT_TALLER_PORTAFOLIO.CD_CLIENTE", []),
        ("NM_PEDIDO", "VARCHAR(12)", "TT_TALLER_PEDIDO_VENTA.NM_PEDIDO", []),
        ("VL_VENTA", "DECIMAL(18, 2)", "TT_TALLER_PEDIDO_VENTA.VL_VENTA_NETA", ["TT_TALLER_PEDIDO_VENTA.VL_VENTA_BRUTA"]),
    ]
    q_drop = [
        ("CD_PERIODO_MES", "VARCHAR(6)", "substr($P_FECHA_FIN, 1, 6)", []),
        ("DT_CORTE", "VARCHAR(8)", "$P_FECHA_FIN", []),
        ("CD_PLANTA", "VARCHAR(4)", "TT_TALLER_REGISTRO_NOMINA.CD_PLANTA", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA", []),
        ("VL_VENTA_TOTAL", "DECIMAL(18, 2)", "sum(QRY_VENTAS.VL_VENTA)", []),
        ("NM_PEDIDOS", "INT", "count_distinct(QRY_VENTAS.NM_PEDIDO)", ["count(QRY_VENTAS.NM_PEDIDO)"]),
    ]
    q_res = [(c[0], c[1], f"QRY_DROPSIZE.{c[0]}", []) for c in q_drop] + [
        ("VL_DROPSIZE", "DECIMAL(18, 2)", "ifthenelse(QRY_DROPSIZE.NM_PEDIDOS = 0, 0, QRY_DROPSIZE.VL_VENTA_TOTAL / QRY_DROPSIZE.NM_PEDIDOS)", []),
    ]
    dataflow("DF_TALLER_DROPSIZE_TRN", ["$P_FECHA_INI", "$P_FECHA_FIN"],
             leer_tabla(STG, "TT_TALLER_PEDIDO_VENTA") + leer_tabla(STG, "TT_TALLER_PORTAFOLIO") + leer_tabla(STG, "TT_TALLER_REGISTRO_NOMINA")
             + vista("QRY_VENTAS", q_ventas, ["TT_TALLER_PEDIDO_VENTA"],
                     joins=[("INNER", "TT_TALLER_PORTAFOLIO", "substr(TT_TALLER_PEDIDO_VENTA.DK_CLIENTE, 5, 10) = TT_TALLER_PORTAFOLIO.CD_CLIENTE")],
                     where="(TT_TALLER_PEDIDO_VENTA.CD_TIPO_DOCUMENTO = 'V') AND (TT_TALLER_PORTAFOLIO.DS_PORTAFOLIO IN ('OPT', 'EST')) "
                           "AND (TT_TALLER_PORTAFOLIO.DS_CANAL like '%TRADICIONAL%')",
                     where_ui="TT_TALLER_PEDIDO_VENTA.CD_TIPO_DOCUMENTO = 'V'\n#AND TT_TALLER_PEDIDO_VENTA.CD_TIPO_DOCUMENTO IN ('V', 'D')\n"
                              "AND TT_TALLER_PORTAFOLIO.DS_PORTAFOLIO IN ('OPT', 'EST')\n#AND TT_TALLER_PORTAFOLIO.DS_PORTAFOLIO = 'OPT'\n"
                              "AND TT_TALLER_PORTAFOLIO.DS_CANAL like '%TRADICIONAL%'")
             + vista("QRY_DROPSIZE", q_drop, ["QRY_VENTAS"],
                     joins=[("INNER", "TT_TALLER_REGISTRO_NOMINA", "QRY_VENTAS.CD_REGISTRO_NOMINA = TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA")],
                     group_by="TT_TALLER_REGISTRO_NOMINA.CD_PLANTA, TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA")
             + vista("QRY_RESULTADO", q_res, ["QRY_DROPSIZE"])
             + cargar_tabla(STG, "TT_TALLER_DROPSIZE", "QRY_RESULTADO"),
             "Dropsize: venta neta del mes sobre pedidos distintos, portafolio OPT y EST del canal tradicional")
    tabla(STG, "TT_TALLER_DROPSIZE", columnas_de(q_res), mapeos_de(q_res), "CD_PLANTA, CD_REGISTRO_NOMINA")

    # Factores CTV desde archivo.
    q_fac = [
        ("CD_PRESENTACION", "VARCHAR(10)", "FF_TALLER_IN_CTV_CF.PRESENTACION", []),
        ("VL_FACTOR", "DECIMAL(10, 4)", "cast(FF_TALLER_IN_CTV_CF.FACTOR, 'decimal(10,4)')", []),
    ]
    dataflow("DF_TALLER_CTV_CF_EXT", [],
             leer_archivo("FF_TALLER_IN_CTV_CF", "factores_ctv.csv")
             + vista("QRY_FACTOR", q_fac, ["FF_TALLER_IN_CTV_CF"])
             + cargar_tabla(STG, "TT_TALLER_FACTOR_CTV", "QRY_FACTOR"),
             "Factor de conversión a caja tipo por presentación")
    tabla(STG, "TT_TALLER_FACTOR_CTV", columnas_de(q_fac), mapeos_de(q_fac))

    # Volumen CTV.
    q_vdia = [
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "FCT_ROLLUP_VOLUMEN.CD_REGISTRO_NOMINA", []),
        ("CD_PLANTA", "VARCHAR(4)", "FCT_ROLLUP_VOLUMEN.CD_PLANTA", []),
        ("CD_PRESENTACION", "VARCHAR(10)", "DIM_PRODUCTO.CD_PRESENTACION", []),
        ("VL_FACTOR", "DECIMAL(10, 4)", "nvl(TT_TALLER_FACTOR_CTV.VL_FACTOR, 0)", []),
        ("VL_VOLUMEN_CTV", "DECIMAL(18, 4)", "(FCT_ROLLUP_VOLUMEN.VL_VOLUMEN_ACUM * nvl(TT_TALLER_FACTOR_CTV.VL_FACTOR, 0))",
         ["FCT_ROLLUP_VOLUMEN.VL_VOLUMEN_ACUM"]),
    ]
    q_vctv = [
        ("CD_PERIODO_MES", "VARCHAR(6)", "substr($P_FECHA_FIN, 1, 6)", []),
        ("DT_CORTE", "VARCHAR(8)", "$P_FECHA_FIN", []),
        ("CD_PLANTA", "VARCHAR(4)", "TT_TALLER_REGISTRO_NOMINA.CD_PLANTA", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA", []),
        ("VL_VOLUMEN_CTV", "DECIMAL(18, 4)", "sum(QRY_VOLUMEN_DIA.VL_VOLUMEN_CTV)", []),
    ]
    dataflow("DF_TALLER_ROLLUP_VOLUMEN_TRN", ["$P_FECHA_FIN", "$P_FECHA_ULT_HABIL"],
             leer_tabla(DWH, "FCT_ROLLUP_VOLUMEN") + leer_tabla(DWH, "DIM_PRODUCTO") + leer_tabla(STG, "TT_TALLER_FACTOR_CTV")
             + leer_tabla(STG, "TT_TALLER_REGISTRO_NOMINA")
             + vista("QRY_VOLUMEN_DIA", q_vdia, ["FCT_ROLLUP_VOLUMEN"],
                     joins=[("INNER", "DIM_PRODUCTO", "FCT_ROLLUP_VOLUMEN.CD_PRODUCTO = DIM_PRODUCTO.CD_PRODUCTO"),
                            ("LEFT_OUTER", "TT_TALLER_FACTOR_CTV", "DIM_PRODUCTO.CD_PRESENTACION = TT_TALLER_FACTOR_CTV.CD_PRESENTACION")],
                     where="(FCT_ROLLUP_VOLUMEN.SK_FECHA = $P_FECHA_ULT_HABIL) AND (FCT_ROLLUP_VOLUMEN.CD_REGISTRO_NOMINA NOT LIKE 'DUMMY%')",
                     where_ui="FCT_ROLLUP_VOLUMEN.SK_FECHA = $P_FECHA_ULT_HABIL\n#AND FCT_ROLLUP_VOLUMEN.SK_FECHA BETWEEN $P_FECHA_INI AND $P_FECHA_FIN\n"
                              "AND FCT_ROLLUP_VOLUMEN.CD_REGISTRO_NOMINA NOT LIKE 'DUMMY%'")
             + vista("QRY_VOLUMEN_CTV", q_vctv, ["QRY_VOLUMEN_DIA"],
                     joins=[("INNER", "TT_TALLER_REGISTRO_NOMINA", "QRY_VOLUMEN_DIA.CD_REGISTRO_NOMINA = TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA")],
                     group_by="TT_TALLER_REGISTRO_NOMINA.CD_PLANTA, TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA")
             + cargar_tabla(STG, "TT_TALLER_VOLUMEN_CTV", "QRY_VOLUMEN_CTV"),
             "Volumen en caja tipo: el rollup es acumulado del mes, se toma solo el último día hábil")
    tabla(STG, "TT_TALLER_VOLUMEN_CTV", columnas_de(q_vctv), mapeos_de(q_vctv), "CD_PLANTA, CD_REGISTRO_NOMINA")

    # Autoventa.
    q_auto = [
        ("SK_FECHA", "VARCHAR(8)", "to_char(to_date(AUTOVENTA.FECHA, 'YYYY-MM-DD'), 'YYYYMMDD')", []),
        ("CD_CLIENTE", "VARCHAR(10)", "AUTOVENTA.CD_CLIENTE", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "AUTOVENTA.CD_REGISTRO_NOMINA", []),
        ("CD_PLANTA", "VARCHAR(4)", "AUTOVENTA.CD_PLANTA", []),
        ("VL_VENTA", "DECIMAL(18, 2)", "AUTOVENTA.VL_VENTA", []),
    ]
    fecha_auto = "to_char(to_date(AUTOVENTA.FECHA, 'YYYY-MM-DD'), 'YYYYMMDD')"
    dataflow("DF_TALLER_AUTOVENTA_EXT", ["$P_FECHA_INI", "$P_FECHA_FIN"],
             leer_tabla(CW, "AUTOVENTA")
             + vista("QRY_AUTOVENTA", q_auto, ["AUTOVENTA"],
                     where=f"({fecha_auto} >= $P_FECHA_INI) AND ({fecha_auto} <= $P_FECHA_FIN)",
                     where_ui=f"{fecha_auto} >= $P_FECHA_INI\nAND {fecha_auto} <= $P_FECHA_FIN")
             + cargar_tabla(STG, "TT_TALLER_AUTOVENTA", "QRY_AUTOVENTA"),
             "Ventas de autoventa desde Celuweb; la fecha llega como YYYY-MM-DD")
    tabla(STG, "TT_TALLER_AUTOVENTA", columnas_de(q_auto), mapeos_de(q_auto))

    # Metas de cobertura desde archivo.
    q_meta = [
        ("CD_PERIODO", "VARCHAR(6)", "FF_TALLER_IN_COBERTURA.PERIODO", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "FF_TALLER_IN_COBERTURA.REGISTRO_NOMINA", []),
        ("CD_PLANTA", "VARCHAR(4)", "FF_TALLER_IN_COBERTURA.PLANTA", []),
        ("NM_CLIENTES_META", "INT", "cast(FF_TALLER_IN_COBERTURA.META_CLIENTES, 'int')", []),
        ("CD_TIPO_META", "VARCHAR(12)", "FF_TALLER_IN_COBERTURA.TIPO_META", []),
    ]
    dataflow("DF_TALLER_METAS_COBERTURA_EXT", [],
             leer_archivo("FF_TALLER_IN_COBERTURA", "metas_cobertura.csv")
             + vista("QRY_METAS", q_meta, ["FF_TALLER_IN_COBERTURA"])
             + cargar_tabla(STG, "TT_TALLER_METAS_COBERTURA", "QRY_METAS"),
             "Meta de clientes por representante y período")
    tabla(STG, "TT_TALLER_METAS_COBERTURA", columnas_de(q_meta), mapeos_de(q_meta))

    # Cobertura: preventa UNION ALL autoventa.
    q_pre = [
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "TT_TALLER_PEDIDO_VENTA.CD_REGISTRO_NOMINA", []),
        ("CD_CLIENTE", "VARCHAR(10)", "substr(TT_TALLER_PEDIDO_VENTA.DK_CLIENTE, 5, 10)", []),
    ]
    q_aut = [
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "TT_TALLER_AUTOVENTA.CD_REGISTRO_NOMINA", []),
        ("CD_CLIENTE", "VARCHAR(10)", "TT_TALLER_AUTOVENTA.CD_CLIENTE", []),
    ]
    q_compra = [
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "MRG_CLIENTES.CD_REGISTRO_NOMINA", []),
        ("NM_CLIENTES_COMPRA", "INT", "count_distinct(MRG_CLIENTES.CD_CLIENTE)", ["count(MRG_CLIENTES.CD_CLIENTE)"]),
    ]
    q_cob = [
        ("CD_PERIODO_MES", "VARCHAR(6)", "substr($P_FECHA_FIN, 1, 6)", []),
        ("DT_CORTE", "VARCHAR(8)", "$P_FECHA_FIN", []),
        ("CD_PLANTA", "VARCHAR(4)", "TT_TALLER_REGISTRO_NOMINA.CD_PLANTA", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA", []),
        ("NM_CLIENTES_META", "INT", "TT_TALLER_METAS_COBERTURA.NM_CLIENTES_META", []),
        ("NM_CLIENTES_COMPRA", "INT", "nvl(QRY_CLIENTES_COMPRA.NM_CLIENTES_COMPRA, 0)", []),
        ("VL_COBERTURA", "DECIMAL(10, 4)",
         "ifthenelse(TT_TALLER_METAS_COBERTURA.NM_CLIENTES_META = 0, 0, nvl(QRY_CLIENTES_COMPRA.NM_CLIENTES_COMPRA, 0) / TT_TALLER_METAS_COBERTURA.NM_CLIENTES_META)", []),
    ]
    dataflow("DF_TALLER_COBERTURA_TRN", ["$P_FECHA_INI", "$P_FECHA_FIN"],
             leer_tabla(STG, "TT_TALLER_PEDIDO_VENTA") + leer_tabla(STG, "TT_TALLER_AUTOVENTA")
             + leer_tabla(STG, "TT_TALLER_METAS_COBERTURA") + leer_tabla(STG, "TT_TALLER_REGISTRO_NOMINA")
             + vista("QRY_CLIENTES_PREVENTA", q_pre, ["TT_TALLER_PEDIDO_VENTA"], where="(TT_TALLER_PEDIDO_VENTA.CD_TIPO_DOCUMENTO = 'V')", distinct=True)
             + vista("QRY_CLIENTES_AUTOVENTA", q_aut, ["TT_TALLER_AUTOVENTA"], where="(TT_TALLER_AUTOVENTA.VL_VENTA > 0)", distinct=True)
             + merge("MRG_CLIENTES", ["QRY_CLIENTES_PREVENTA", "QRY_CLIENTES_AUTOVENTA"])
             + vista("QRY_CLIENTES_COMPRA", q_compra, ["MRG_CLIENTES"], group_by="MRG_CLIENTES.CD_REGISTRO_NOMINA")
             + vista("QRY_COBERTURA", q_cob, ["TT_TALLER_REGISTRO_NOMINA"],
                     joins=[("INNER", "TT_TALLER_METAS_COBERTURA", "TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA = TT_TALLER_METAS_COBERTURA.CD_REGISTRO_NOMINA"),
                            ("LEFT_OUTER", "QRY_CLIENTES_COMPRA", "TT_TALLER_REGISTRO_NOMINA.CD_REGISTRO_NOMINA = QRY_CLIENTES_COMPRA.CD_REGISTRO_NOMINA")],
                     where="(TT_TALLER_METAS_COBERTURA.CD_PERIODO = substr($P_FECHA_FIN, 1, 6))",
                     where_ui="TT_TALLER_METAS_COBERTURA.CD_PERIODO = substr($P_FECHA_FIN, 1, 6)\n#AND TT_TALLER_METAS_COBERTURA.CD_TIPO_META = 'MENSUAL'")
             + cargar_tabla(STG, "TT_TALLER_COBERTURA", "QRY_COBERTURA"),
             "Cobertura: clientes distintos con compra en preventa o autoventa sobre la meta del período")
    tabla(STG, "TT_TALLER_COBERTURA", columnas_de(q_cob), mapeos_de(q_cob), "CD_PLANTA, CD_REGISTRO_NOMINA")

    # Señuelo: la versión anterior de cobertura, que nadie llama.
    q_hist = [
        ("CD_PERIODO_MES", "VARCHAR(6)", "substr($P_FECHA_FIN, 1, 6)", []),
        ("CD_REGISTRO_NOMINA", "VARCHAR(10)", "TT_TALLER_PEDIDO_VENTA.CD_REGISTRO_NOMINA", []),
        ("NM_CLIENTES_META", "INT", "TT_TALLER_METAS_COBERTURA.NM_CLIENTES_META", []),
        ("NM_CLIENTES_COMPRA", "INT", "count(substr(TT_TALLER_PEDIDO_VENTA.DK_CLIENTE, 5, 10))", []),
        ("VL_COBERTURA", "DECIMAL(10, 4)", "count(substr(TT_TALLER_PEDIDO_VENTA.DK_CLIENTE, 5, 10)) / TT_TALLER_METAS_COBERTURA.NM_CLIENTES_META", []),
    ]
    dataflow("DF_TALLER_COBERTURA_HIST_TRN", ["$P_FECHA_INI", "$P_FECHA_FIN"],
             leer_tabla(STG, "TT_TALLER_PEDIDO_VENTA") + leer_tabla(STG, "TT_TALLER_METAS_COBERTURA")
             + vista("QRY_COBERTURA_HIST", q_hist, ["TT_TALLER_PEDIDO_VENTA"],
                     joins=[("INNER", "TT_TALLER_METAS_COBERTURA", "TT_TALLER_PEDIDO_VENTA.CD_REGISTRO_NOMINA = TT_TALLER_METAS_COBERTURA.CD_REGISTRO_NOMINA")],
                     where="(TT_TALLER_METAS_COBERTURA.CD_PERIODO = substr($P_FECHA_FIN, 1, 6))",
                     group_by="TT_TALLER_PEDIDO_VENTA.CD_REGISTRO_NOMINA, TT_TALLER_METAS_COBERTURA.NM_CLIENTES_META")
             + cargar_tabla(STG, "TT_TALLER_COBERTURA_HIST", "QRY_COBERTURA_HIST"),
             "Cobertura versión 2024 (solo preventa). Reemplazada por DF_TALLER_COBERTURA_TRN")
    tabla(STG, "TT_TALLER_COBERTURA_HIST", columnas_de(q_hist), mapeos_de(q_hist))

    # Exportaciones a TXSTA: definen qué es final.
    for indicador, origen, valor in (
        ("DROPSIZE", "TT_TALLER_DROPSIZE", "VL_DROPSIZE"),
        ("VOLUMEN_CTV", "TT_TALLER_VOLUMEN_CTV", "VL_VOLUMEN_CTV"),
        ("COBERTURA", "TT_TALLER_COBERTURA", "VL_COBERTURA"),
    ):
        q_tx = [
            ("PARTICIPANTE", "VARCHAR(10)", f"{origen}.CD_REGISTRO_NOMINA", []),
            ("PERIODO", "VARCHAR(6)", f"{origen}.CD_PERIODO_MES", []),
            ("FECHA_CORTE", "VARCHAR(8)", f"{origen}.DT_CORTE", []),
            ("TIPO_TRANSACCION", "VARCHAR(20)", f"'{indicador}'", []),
            ("VALOR", "DECIMAL(18, 4)", f"{origen}.{valor}", []),
            ("UNIDAD", "VARCHAR(10)", "'COP'" if indicador == "DROPSIZE" else ("'CTV'" if indicador == "VOLUMEN_CTV" else "'PCT'"), []),
        ]
        dataflow(f"DF_TALLER_EXPORTAR_{indicador}_LOD", [],
                 leer_tabla(STG, origen)
                 + vista("QRY_MAPEA_TXSTA", q_tx, [origen])
                 + cargar_archivo("FF_TALLER_OUT_TXSTA", f"txsta_{indicador.lower()}.csv", "QRY_MAPEA_TXSTA"),
                 f"Exporta {indicador.lower()} al formato TXSTA del sistema de comisiones")

    for nombre, ds, cols in (
        ("ZBPTA011", SAP, [("PERNR", "VARCHAR(8)"), ("REGNOM", "VARCHAR(10)"), ("STEXT", "VARCHAR(40)"), ("PLANTA", "VARCHAR(4)"),
                           ("BUKRS", "VARCHAR(4)"), ("F_INGRESO", "VARCHAR(10)"), ("F_RETIRO", "VARCHAR(10)"), ("ZONA", "VARCHAR(10)")]),
        ("FCT_PEDIDO_VENTA", DWH, list(zip(cols_ped, tipos_ped))),
        ("FCT_ROLLUP_VOLUMEN", DWH, [("SK_FECHA", "VARCHAR(8)"), ("CD_REGISTRO_NOMINA", "VARCHAR(10)"), ("CD_PLANTA", "VARCHAR(4)"),
                                     ("CD_PRODUCTO", "VARCHAR(10)"), ("VL_VOLUMEN_ACUM", "DECIMAL(18, 4)")]),
        ("DIM_PRODUCTO", DWH, [("CD_PRODUCTO", "VARCHAR(10)"), ("DS_PRODUCTO", "VARCHAR(60)"), ("CD_PRESENTACION", "VARCHAR(10)"),
                               ("DS_CATEGORIA", "VARCHAR(30)"), ("VL_LITROS", "DECIMAL(10, 4)")]),
        ("DIM_FECHA", DWH, [("SK_FECHA", "INT"), ("DT_FECHA", "DATE"), ("BL_DIA_HABIL", "VARCHAR(2)"), ("BL_FESTIVO", "VARCHAR(2)")]),
        ("AUTOVENTA", CW, [("FECHA", "VARCHAR(10)"), ("CD_CLIENTE", "VARCHAR(10)"), ("CD_REGISTRO_NOMINA", "VARCHAR(10)"),
                           ("CD_PLANTA", "VARCHAR(4)"), ("VL_VENTA", "DECIMAL(18, 2)")]),
    ):
        tabla(ds, nombre, cols)


# ---------------------------------------------------------------- ruido: indicadores que no se migran

VOCAB = ["CLIENTE", "PLANTA", "ZONA", "RUTA", "CANAL", "PRODUCTO", "CATEGORIA", "PRESENTACION", "SABOR", "MARCA", "SEGMENTO",
         "VISITA", "PEDIDO", "FACTURA", "RECAUDO", "DEVOLUCION", "META", "CUOTA", "PRESUPUESTO", "INVENTARIO", "CEDI", "VEHICULO",
         "NOVEDAD", "SUPERVISOR", "GERENCIA", "REGION", "FRECUENCIA", "SECUENCIA", "ESTADO", "MOTIVO"]
PREF = [("CD_", "VARCHAR(10)"), ("DS_", "VARCHAR(60)"), ("VL_", "DECIMAL(18, 2)"), ("NM_", "INT"), ("DT_", "VARCHAR(8)"), ("FL_", "VARCHAR(1)")]
INDICADORES_RUIDO = ["EFECTIVIDAD", "PROFUNDIDAD", "HECTOLITROS", "INGRESOS", "CLIENTES_NUEVOS", "DEVOLUCIONES", "RECAUDO",
                     "PRESUPUESTO", "CUMPLIMIENTO", "PORTAFOLIO_INFALTABLE", "VISITAS_EFECTIVAS", "RANKING", "NOVEDADES",
                     "CONSOLIDADO", "RECHAZOS", "VALIDACION", "FRECUENCIA_VISITA", "IMPULSO", "EXHIBICION", "CARTERA"]
EXTRACCIONES_RUIDO = [("VISITAS_PRG", CW, "VISITAS_PROGRAMADAS"), ("RECAUDO", DWH, "FCT_RECAUDO"), ("CLIENTES_NUEVOS", DWH, "DIM_CLIENTE"),
                      ("DEVOLUCIONES", DWH, "FCT_DEVOLUCION"), ("INVENTARIO_RUTA", DWH, "FCT_INVENTARIO_RUTA"),
                      ("PRESUPUESTO", DWH, "DIM_PRESUPUESTO"), ("ZONAS", DWH, "DIM_RUTA"), ("CEDIS", DWH, "DIM_CEDI"),
                      ("CALENDARIO", DWH, "DIM_FECHA"), ("NOVEDADES_NOMINA", SAP, "ZBPTA017")]


def columnas_ruido(alias, n):
    usadas, cols = set(), []
    while len(cols) < n:
        p, t = rng.choice(PREF)
        nombre = p + rng.choice(VOCAB) + ("" if rng.random() < 0.6 else "_" + rng.choice(VOCAB))
        if nombre in usadas:
            continue
        usadas.add(nombre)
        if p == "VL_" and rng.random() < 0.3:
            expr = f"nvl({alias}.{nombre}, 0)"
        elif p == "DS_" and rng.random() < 0.2:
            expr = f"upper(rtrim_blanks({alias}.{nombre}))"
        elif p == "FL_" and rng.random() < 0.5:
            expr = f"ifthenelse({alias}.{nombre} = 'S', 'S', 'N')"
        else:
            expr = f"{alias}.{nombre}"
        com = [f"{alias}.{nombre}_ANT"] if rng.random() < 0.06 else []
        cols.append((nombre, t, expr, com))
    return cols


def ruido():
    llamadas_ext, llamadas_trn, llamadas_lod = [], [], []
    for nombre, ds, fuente in EXTRACCIONES_RUIDO:
        cols = columnas_ruido(fuente, rng.randint(12, 40))
        elementos = leer_tabla(ds, fuente)
        if nombre == "VISITAS_PRG":
            sql_cols = [("CD_REGISTRO_NOMINA", "VARCHAR(10)"), ("CD_CLIENTE", "VARCHAR(10)"), ("SK_FECHA", "VARCHAR(8)")]
            elementos += transformacion_sql("SQL_VISITAS", "DS_TALLER_CELUWEB", sql_cols,
                                            "SELECT CD_REGISTRO_NOMINA, CD_CLIENTE, SK_FECHA\nFROM CW.VISITAS_PROGRAMADAS\nWHERE ESTADO = 'A'")
            cols = [(c, t, f"SQL_VISITAS.{c}", []) for c, t in sql_cols] + cols[:10]
            fuente_vista = "SQL_VISITAS"
        else:
            fuente_vista = fuente
        cols = [(c, t, e.replace(f"{fuente}.", f"{fuente_vista}."), [x.replace(f"{fuente}.", f"{fuente_vista}.") for x in com]) for c, t, e, com in cols]
        where_ui = None
        if rng.random() < 0.5:
            c = next(x for x in cols if x[0].startswith(("CD_", "DT_")))
            where_ui = f"{fuente_vista}.{c[0]} IS NOT NULL" + (f"\n#AND {fuente_vista}.{c[0]} <> '0'" if rng.random() < 0.4 else "")
        elementos += vista(f"QRY_{nombre}", cols, [fuente_vista], where=f"({fuente_vista}.{cols[0][0]} IS NOT NULL)" if where_ui else None, where_ui=where_ui)
        destino = f"TT_TALLER_{nombre}_EXT"
        elementos += cargar_tabla(STG, destino, f"QRY_{nombre}")
        df = f"DF_TALLER_{nombre}_EXT"
        dataflow(df, ["$P_FECHA_INI", "$P_FECHA_FIN"] if rng.random() < 0.5 else [], elementos, f"Extracción de {nombre.lower().replace('_', ' ')}")
        tabla(STG, destino, columnas_de(cols), mapeos_de(cols))
        llamadas_ext.append(df)

    for nombre in INDICADORES_RUIDO:
        entradas = rng.sample([f"TT_TALLER_{x[0]}_EXT" for x in EXTRACCIONES_RUIDO] + ["TT_TALLER_PEDIDO_VENTA", "TT_TALLER_REGISTRO_NOMINA"], 2)
        elementos = sum((leer_tabla(STG, e) for e in entradas), [])
        a, b = entradas
        base = columnas_ruido(a, rng.randint(15, 45))
        base[0] = ("CD_REGISTRO_NOMINA", "VARCHAR(10)", f"{a}.CD_REGISTRO_NOMINA", [])
        joins = [(rng.choice(["INNER", "LEFT_OUTER"]), b, f"{a}.CD_REGISTRO_NOMINA = {b}.CD_REGISTRO_NOMINA")]
        elementos += vista(f"QRY_{nombre}_01", base, [a], joins=joins)
        agregadas = [("CD_REGISTRO_NOMINA", "VARCHAR(10)", f"QRY_{nombre}_01.CD_REGISTRO_NOMINA", [])]
        for c in base[1:]:
            if c[0].startswith("VL_"):
                agregadas.append((c[0], c[1], f"sum(QRY_{nombre}_01.{c[0]})", [f"avg(QRY_{nombre}_01.{c[0]})"] if rng.random() < 0.15 else []))
            elif c[0].startswith("NM_"):
                agregadas.append((c[0], c[1], f"count_distinct(QRY_{nombre}_01.{c[0]})", []))
        if len(agregadas) < 3:
            agregadas.append(("VL_TOTAL", "DECIMAL(18, 2)", f"sum(QRY_{nombre}_01.{base[1][0]})", []))
        elementos += vista(f"QRY_{nombre}_02", agregadas, [f"QRY_{nombre}_01"], group_by=f"QRY_{nombre}_01.CD_REGISTRO_NOMINA")
        destino = f"TT_TALLER_{nombre}"
        elementos += cargar_tabla(STG, destino, f"QRY_{nombre}_02")
        df = f"DF_TALLER_{nombre}_TRN"
        dataflow(df, ["$P_FECHA_INI", "$P_FECHA_FIN"], elementos, f"Indicador de {nombre.lower().replace('_', ' ')}")
        tabla(STG, destino, columnas_de(agregadas), mapeos_de(agregadas))
        llamadas_trn.append(df)
        if rng.random() < 0.3:
            q_tx = [("PARTICIPANTE", "VARCHAR(10)", f"{destino}.CD_REGISTRO_NOMINA", []),
                    ("TIPO_TRANSACCION", "VARCHAR(20)", f"'{nombre}'", []),
                    ("VALOR", "DECIMAL(18, 4)", f"{destino}.{agregadas[1][0]}", [])]
            lod = f"DF_TALLER_EXPORTAR_{nombre}_LOD"
            dataflow(lod, [], leer_tabla(STG, destino) + vista("QRY_MAPEA_TXSTA", q_tx, [destino])
                     + cargar_archivo("FF_TALLER_OUT_TXSTA", f"txsta_{nombre.lower()}.csv", "QRY_MAPEA_TXSTA"),
                     f"Exporta {nombre.lower()} al formato TXSTA")
            llamadas_lod.append(lod)
    for _, ds, fuente in EXTRACCIONES_RUIDO:
        if f"{ds[0]}.{ds[1]}.{fuente}" not in TABLAS:
            tabla(ds, fuente, [(c, t) for c, t, _, _ in columnas_ruido(fuente, rng.randint(8, 20))])
    return llamadas_ext, llamadas_trn, llamadas_lod


# ---------------------------------------------------------------- workflows y job


def workflow(nombre, parametros, variables, script_ui, script, llamadas, clase="PLAN"):
    params = ", ".join(f"{p} VARCHAR(8)  IN " for p in parametros)
    lineas = [f"CREATE {clase} {nombre}::'{guid_de(nombre)}'({params if params else ' '})"]
    if variables:
        lineas += ["DECLARE"] + [f"     {v} ;" for v in variables]
    lineas.append("BEGIN")
    if script:
        lineas.append(f' AlGUIComment ({UI_PLAN}, "ui_script_text" = \'{esc(script_ui)}\', "x" = \'{rng.randint(100, 800)}\', "y" = \'-187\')')
        lineas += ["BEGIN_SCRIPT", script + "END"]
    for tipo, objetivo, args in llamadas:
        lineas.append(f' AlGUIComment ("ParmDefaulted_01" = \'FALSE\', {UI_PLAN}, "x" = \'{rng.randint(100, 900)}\', "y" = \'{-rng.randint(80, 400)}\')')
        lineas.append(f"CALL {tipo} {objetivo}::'{guid_de(objetivo)}'({', '.join(args)});")
    lineas += ["END", ' SET ("workflow_type" = \'Regular\')' if clase == "PLAN" else ' SET ("job_GV_$G_FECHA" = \'\\\'19000101\\\'\')',
               ' AlGUIComment ("ActaName_1" = \'RSavedAfterCheckOut\', "ActaValue_1" = \'YES\', "x" = \'-1\', "y" = \'-1\')', ""]
    WORKFLOWS[(clase, nombre)] = lineas


def workflows(ext, trn, lod):
    script_ui = (
        "#valida fecha final.\n"
        "$L_FECHA_F = sql( 'DS_TALLER_DWH','SELECT MAX(SK_FECHA) FROM DWH.DIM_FECHA WHERE BL_DIA_HABIL=\\'SI\\' AND SK_FECHA <'||cast( to_char(sysdate(),'YYYYMMDD' ),'int'));\n"
        "#$L_FECHA_F = to_char(sysdate() - 1, 'YYYYMMDD');\n"
        "$L_FECHA_FIN = ifthenelse($P_FECHA = '19000101', $L_FECHA_F, $P_FECHA);\n"
        "\n#valida fecha inicial.\n"
        "$L_FECHA_INI = substr($L_FECHA_FIN, 1, 6) || '01';\n"
        "#$L_FECHA_INI = to_char(add_months(to_date($L_FECHA_FIN, 'YYYYMMDD'), -1), 'YYYYMM') || '01';\n"
        "\n#ultimo dia habil para el rollup acumulado\n"
        "$L_FECHA_ULT_HABIL = sql( 'DS_TALLER_DWH','SELECT MAX(SK_FECHA) FROM DWH.DIM_FECHA WHERE BL_DIA_HABIL=\\'SI\\' AND SK_FECHA <= [$L_FECHA_FIN]');\n"
        "#$L_FECHA_ULT_HABIL = $L_FECHA_FIN;\n"
        "\nprint('####### Fecha inicial: ' || $L_FECHA_INI);\nprint('####### Fecha final: ' || $L_FECHA_FIN);\n"
        "print('####### Ultimo dia habil: ' || $L_FECHA_ULT_HABIL);\n"
    )
    script = (
        "$L_FECHA_F = sql('DS_TALLER_DWH', ('SELECT MAX(SK_FECHA) FROM DWH.DIM_FECHA WHERE BL_DIA_HABIL=\\'SI\\' AND SK_FECHA <' || "
        "cast(to_char(sysdate(), 'YYYYMMDD'), 'int')));"
        "$L_FECHA_FIN = ifthenelse(($P_FECHA = '19000101'), $L_FECHA_F, $P_FECHA);"
        "$L_FECHA_INI = (substr($L_FECHA_FIN, 1, 6) || '01');"
        "$L_FECHA_ULT_HABIL = sql('DS_TALLER_DWH', 'SELECT MAX(SK_FECHA) FROM DWH.DIM_FECHA WHERE BL_DIA_HABIL=\\'SI\\' AND SK_FECHA <= [$L_FECHA_FIN]');"
        "print(('####### Fecha inicial: ' || $L_FECHA_INI));print(('####### Fecha final: ' || $L_FECHA_FIN));"
        "print(('####### Ultimo dia habil: ' || $L_FECHA_ULT_HABIL));"
    )
    variables = ["$L_FECHA_INI VARCHAR(8)", "$L_FECHA_FIN VARCHAR(8)", "$L_FECHA_F VARCHAR(8)", "$L_FECHA_ULT_HABIL VARCHAR(8)"]
    workflow("WF_TALLER_COM_VARIABLE", ["$P_FECHA"], variables, script_ui, script, [
        ("PLAN", "WF_TALLER_EXTRACCION", ["$L_FECHA_INI", "$L_FECHA_FIN"]),
        ("PLAN", "WF_TALLER_INDICADORES", ["$L_FECHA_INI", "$L_FECHA_FIN", "$L_FECHA_ULT_HABIL"]),
        ("PLAN", "WF_TALLER_EXPORTAR", []),
    ])
    principales_ext = [
        ("DATAFLOW", "DF_TALLER_REGISTRO_NOMINA_EXT", ["$P_FECHA_FIN"]),
        ("DATAFLOW", "DF_TALLER_PEDIDO_VENTA_EXT", ["$P_FECHA_INI", "$P_FECHA_FIN"]),
        ("DATAFLOW", "DF_TALLER_PORTAFOLIO_EXT", []),
        ("DATAFLOW", "DF_TALLER_CTV_CF_EXT", []),
        ("DATAFLOW", "DF_TALLER_AUTOVENTA_EXT", ["$P_FECHA_INI", "$P_FECHA_FIN"]),
        ("DATAFLOW", "DF_TALLER_METAS_COBERTURA_EXT", []),
    ]
    otras_ext = [("DATAFLOW", d, ["$P_FECHA_INI", "$P_FECHA_FIN"] if "$P_FECHA_INI" in DATAFLOWS[d][0] else []) for d in ext]
    workflow("WF_TALLER_EXTRACCION", ["$P_FECHA_INI", "$P_FECHA_FIN"], [], "", "", principales_ext[:3] + otras_ext[:5] + principales_ext[3:] + otras_ext[5:])
    principales_trn = [
        ("DATAFLOW", "DF_TALLER_DROPSIZE_TRN", ["$P_FECHA_INI", "$P_FECHA_FIN"]),
        ("DATAFLOW", "DF_TALLER_ROLLUP_VOLUMEN_TRN", ["$P_FECHA_FIN", "$P_FECHA_ULT_HABIL"]),
        ("DATAFLOW", "DF_TALLER_COBERTURA_TRN", ["$P_FECHA_INI", "$P_FECHA_FIN"]),
    ]
    otras_trn = [("DATAFLOW", d, ["$P_FECHA_INI", "$P_FECHA_FIN"]) for d in trn]
    workflow("WF_TALLER_INDICADORES", ["$P_FECHA_INI", "$P_FECHA_FIN", "$P_FECHA_ULT_HABIL"], [], "", "",
             otras_trn[:7] + principales_trn[:1] + otras_trn[7:13] + principales_trn[1:] + otras_trn[13:])
    workflow("WF_TALLER_EXPORTAR", [], [], "", "",
             [("DATAFLOW", f"DF_TALLER_EXPORTAR_{x}_LOD", []) for x in ("DROPSIZE", "VOLUMEN_CTV", "COBERTURA")] + [("DATAFLOW", d, []) for d in lod])
    workflow("JB_TALLER_COM_VARIABLE", [], [], "", "", [("PLAN", "WF_TALLER_COM_VARIABLE", ["$G_FECHA"])], clase="SESSION")
    WORKFLOWS[("SESSION", "JB_TALLER_COM_VARIABLE")][1:1] = ["DECLARE", "     GLOBAL $G_FECHA VARCHAR(8) ;", "     GLOBAL $G_DWH_SCHEMA VARCHAR(10) ;"]


def archivos():
    lineas = []
    for formato, cols in (
        ("FF_TALLER_IN_COBERTURA", "PERIODO VARCHAR(6) , REGISTRO_NOMINA VARCHAR(10) , PLANTA VARCHAR(4) , META_CLIENTES VARCHAR(10) , TIPO_META VARCHAR(12) "),
        ("FF_TALLER_IN_CTV_CF", "PRESENTACION VARCHAR(10) , FACTOR VARCHAR(10) "),
        ("FF_TALLER_IN_PORTAFOLIO", "CD_CLIENTE VARCHAR(10) , CD_PLANTA VARCHAR(4) , CD_REGISTRO_NOMINA VARCHAR(10) , PORTAFOLIO VARCHAR(10) , CANAL VARCHAR(30) "),
        ("FF_TALLER_OUT_TXSTA", "PARTICIPANTE VARCHAR(10) , PERIODO VARCHAR(6) , FECHA_CORTE VARCHAR(8) , TIPO_TRANSACCION VARCHAR(20) , VALOR DECIMAL(18, 4) , UNIDAD VARCHAR(10) "),
    ):
        lineas += [
            f"CREATE FILE DATASTORE {formato}::'{g()}'({cols})",
            ' SET ("DATA_PREVIEW_FLAG" = \'yes\', "abap_file_format" = \'no\', "adaptable" = \'yes\', "cache" = \'yes\', "column_delimiter" = \';\', '
            '"file_format" = \'delimited_file\', "skip_row_header" = \'yes\')',
            ' AlGUIComment ("ActaName_1" = \'RSavedAfterCheckOut\', "ActaValue_1" = \'YES\')',
        ]
    return lineas


def generar():
    nucleo()
    ext, trn, lod = ruido()
    workflows(ext, trn, lod)
    salida = [
        "#__AW_Repository_Version '14.4.0.0000';",
        "#__AW_Product_Version '14.4.0.339';",
        "#__AW_ATL_Locale 'eng_us.utf-8';",
        ' AlGUIComment ("ActaName_1" = \'RDate_created\', "ActaValue_1" = \'Mon Mar  2 08:00:00 2026\', "x" = \'-1\', "y" = \'-1\')',
    ]
    for k in sorted(TABLAS):
        salida += TABLAS[k]
    for k in sorted(DATAFLOWS):
        salida += DATAFLOWS[k]
    salida += archivos()
    for (clase, nombre) in sorted(WORKFLOWS, key=lambda x: (x[0] != "SESSION", x[1])):
        salida += WORKFLOWS[(clase, nombre)]
    return "\n".join(salida) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "insumos", "com_variable_mini.atl"))
    a = p.parse_args(argv)
    texto = generar()
    os.makedirs(os.path.dirname(a.salida), exist_ok=True)
    with open(a.salida, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"{a.salida}: {texto.count(chr(10))} líneas, {len(texto.encode('utf-8')):,} bytes, {len(DATAFLOWS)} dataflows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
