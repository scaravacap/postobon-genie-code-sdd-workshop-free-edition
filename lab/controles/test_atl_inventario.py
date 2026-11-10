"""Pruebas de atl_inventario.py contra el ATL sintético del taller.

Cada conteo se contrasta con una lectura independiente del archivo (expresiones regulares
sobre el texto crudo), no con lo que el propio inventario dice de sí mismo.

Correr con: python -m unittest test_atl_inventario -v
"""
import hashlib
import os
import re
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
ENTORNO = os.path.join(AQUI, "..", "entorno")
ATL = os.path.join(ENTORNO, "insumos", "com_variable_mini.atl")
sys.path.insert(0, AQUI)
sys.path.insert(0, ENTORNO)

import atl_inventario as a  # noqa: E402

INV = a.inventariar(ATL)
TEXTO = open(ATL, encoding="utf-8").read()


def df(nombre):
    return a._df(INV, nombre)


def consulta(nombre_df, nombre_q):
    return next(q for q in df(nombre_df)["consultas"] if q["nombre"] == nombre_q)


def columna(nombre_df, nombre_q, col):
    return next(c for c in consulta(nombre_df, nombre_q)["columnas"] if c["nombre"] == col)


class Archivo(unittest.TestCase):
    def test_el_archivo_corresponde_al_generador(self):
        import generar_atl_sintetico as g
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "x.atl")
            g.main(["--salida", ruta])
            with open(ruta, "rb") as f:
                nuevo = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(nuevo, INV["sha256"], "Regenera insumos/com_variable_mini.atl con generar_atl_sintetico.py")

    def test_conteo_de_sentencias(self):
        for clase in ("DATAFLOW", "PLAN", "SESSION", "TABLE"):
            n = len(re.findall(rf"^CREATE\s+{clase}\s", TEXTO, re.M))
            self.assertEqual(INV["conteo_sentencias"].get(clase, 0), n, clase)

    def test_lecturas_y_cargas(self):
        self.assertEqual(sum(len(d["lecturas"]) for d in INV["dataflows"]), len(re.findall(r"\bREAD (?:TABLE|FILE)\b", TEXTO)))
        self.assertEqual(sum(len(d["cargas"]) for d in INV["dataflows"]), len(re.findall(r"\bLOAD (?:TABLE|FILE)\b", TEXTO)))

    def test_columnas_de_vistas(self):
        independientes = len(re.findall(r'^(?:GUID::\'[^\']+\' CREATE VIEW \w+\( | )\w+ [A-Z]+(?:\(\d+(?:, \d+)?\))?  SET\( "ui_mapping_text"', TEXTO, re.M))
        inventario = sum(len(q["columnas"]) for d in INV["dataflows"] for q in d["consultas"])
        self.assertEqual(inventario, independientes)

    def test_parametros_multiples(self):
        self.assertEqual(df("DF_TALLER_ROLLUP_VOLUMEN_TRN")["parametros"], ["$P_FECHA_FIN", "$P_FECHA_ULT_HABIL"])
        wf = next(w for w in INV["workflows"] if w["nombre"] == "WF_TALLER_INDICADORES")
        self.assertEqual(wf["parametros"], ["$P_FECHA_INI", "$P_FECHA_FIN", "$P_FECHA_ULT_HABIL"])


class CodigoComentado(unittest.TestCase):
    def test_toda_linea_con_numeral_queda_capturada(self):
        lineas = {i for i, ln in enumerate(TEXTO.split("\n"), 1) if re.match(r"[ \t]*#(?!__AW_)", ln)}
        capturadas = {c["linea"] for c in INV["codigo_comentado"]}
        self.assertEqual(lineas - capturadas, set())

    def test_cada_fragmento_apunta_a_una_linea_con_numeral(self):
        lineas = TEXTO.split("\n")
        for c in INV["codigo_comentado"]:
            self.assertIn("#", lineas[c["linea"] - 1], c)

    def test_toda_linea_donde_el_numeral_abre_un_valor_queda_capturada(self):
        lineas = {i for i, ln in enumerate(TEXTO.split("\n"), 1) if re.search(r"=\s*'#", ln)}
        capturadas = {c["linea"] for c in INV["codigo_comentado"]}
        self.assertTrue(lineas)
        self.assertEqual(lineas - capturadas, set())
        self.assertEqual(INV["lineas_con_valor_comentado"], len(lineas))


class Trampas(unittest.TestCase):
    def test_filtro_activo_y_comentado_de_portafolio(self):
        q = consulta("DF_TALLER_DROPSIZE_TRN", "QRY_VENTAS")
        self.assertIn("IN ('OPT', 'EST')", q["where_activo"])
        self.assertTrue(any("= 'OPT'" in t["texto"] for t in q["where_comentado"]))

    def test_venta_neta_activa_y_bruta_comentada(self):
        c = columna("DF_TALLER_DROPSIZE_TRN", "QRY_VENTAS", "VL_VENTA")
        self.assertEqual(c["mapeo_activo"], "TT_TALLER_PEDIDO_VENTA.VL_VENTA_NETA")
        self.assertTrue(any("VL_VENTA_BRUTA" in t["texto"] for t in c["mapeo_comentado"]))

    def test_count_distinct_activo(self):
        c = columna("DF_TALLER_DROPSIZE_TRN", "QRY_DROPSIZE", "NM_PEDIDOS")
        self.assertIn("count_distinct", c["mapeo_activo"])
        self.assertTrue(any(t["texto"].startswith("#count(") for t in c["mapeo_comentado"]))

    def test_volumen_toma_solo_el_ultimo_dia_habil(self):
        q = consulta("DF_TALLER_ROLLUP_VOLUMEN_TRN", "QRY_VOLUMEN_DIA")
        self.assertIn("SK_FECHA = $P_FECHA_ULT_HABIL", q["where_activo"])
        self.assertTrue(any("BETWEEN" in t["texto"] for t in q["where_comentado"]))
        self.assertEqual([j["tipo"] for j in q["joins"]], ["INNER", "LEFT OUTER"])

    def test_filtro_tradicional_comentado_en_nomina(self):
        q = consulta("DF_TALLER_REGISTRO_NOMINA_EXT", "QRY_FILTRA_REPRESENTANTES")
        self.assertNotIn("TRADICIONAL", q["where_activo"])
        self.assertTrue(any("TRADICIONAL" in t["texto"] for t in q["where_comentado"]))

    def test_cobertura_une_preventa_y_autoventa(self):
        u = df("DF_TALLER_COBERTURA_TRN")["uniones"]
        self.assertEqual([x["entradas"] for x in u], [["QRY_CLIENTES_PREVENTA", "QRY_CLIENTES_AUTOVENTA"]])

    def test_tipo_meta_comentado(self):
        q = consulta("DF_TALLER_COBERTURA_TRN", "QRY_COBERTURA")
        self.assertTrue(any("CD_TIPO_META" in t["texto"] for t in q["where_comentado"]))
        self.assertNotIn("CD_TIPO_META", q["where_activo"])


class Linaje(unittest.TestCase):
    def test_senuelo_sin_llamar(self):
        llamados = set(INV["orden_ejecucion"])
        self.assertEqual([d["nombre"] for d in INV["dataflows"] if d["nombre"] not in llamados], ["DF_TALLER_COBERTURA_HIST_TRN"])

    def test_linaje_de_cobertura_sin_senuelo(self):
        texto = a.linaje(INV, "TT_TALLER_COBERTURA")
        for nombre in ("DF_TALLER_REGISTRO_NOMINA_EXT", "DF_TALLER_PEDIDO_VENTA_EXT", "DF_TALLER_AUTOVENTA_EXT",
                       "DF_TALLER_METAS_COBERTURA_EXT", "DF_TALLER_COBERTURA_TRN"):
            self.assertIn(nombre, texto)
        self.assertNotIn("HIST", texto)

    def test_exportaciones_definen_lo_final(self):
        for indicador, origen in (("DROPSIZE", "TT_TALLER_DROPSIZE"), ("VOLUMEN_CTV", "TT_TALLER_VOLUMEN_CTV"), ("COBERTURA", "TT_TALLER_COBERTURA")):
            d = df(f"DF_TALLER_EXPORTAR_{indicador}_LOD")
            self.assertEqual([l["tabla_corta"] for l in d["lecturas"]], [origen])
            self.assertTrue(d["cargas"][0]["tabla_corta"].startswith("ARCHIVO:FF_TALLER_OUT_TXSTA"))

    def test_extraccion_antes_que_indicadores(self):
        orden = INV["orden_ejecucion"]
        self.assertLess(orden.index("DF_TALLER_REGISTRO_NOMINA_EXT"), orden.index("DF_TALLER_DROPSIZE_TRN"))
        self.assertLess(orden.index("DF_TALLER_COBERTURA_TRN"), orden.index("DF_TALLER_EXPORTAR_COBERTURA_LOD"))


class Fechas(unittest.TestCase):
    wf = next(w for w in INV["workflows"] if w["nombre"] == "WF_TALLER_COM_VARIABLE")

    def test_asignaciones_activas(self):
        variables = [x["variable"] for x in self.wf["asignaciones"]]
        self.assertEqual(variables, ["$L_FECHA_F", "$L_FECHA_FIN", "$L_FECHA_INI", "$L_FECHA_ULT_HABIL"])

    def test_fecha_por_defecto_lee_dim_fecha(self):
        a_f = next(x for x in self.wf["asignaciones"] if x["variable"] == "$L_FECHA_F")
        self.assertIn("DIM_FECHA", a_f["tablas"])
        self.assertIn("DIM_FECHA", INV["lectores"])

    def test_alternativas_comentadas(self):
        self.assertEqual([x["texto"].split("=")[0].strip() for x in self.wf["asignaciones_comentadas"]],
                         ["#$L_FECHA_F", "#$L_FECHA_INI", "#$L_FECHA_ULT_HABIL"])

    def test_notas_del_script_no_son_asignaciones(self):
        self.assertEqual([x["texto"] for x in self.wf["comentarios"]][:1], ["#valida fecha final."])
        self.assertEqual(len(self.wf["comentarios"]), 3)

    def test_lineas_apuntan_al_texto_de_la_ui(self):
        lineas = TEXTO.split("\n")
        for x in self.wf["asignaciones"]:
            self.assertIn(x["variable"] + " =", lineas[x["linea"] - 1], x)


if __name__ == "__main__":
    unittest.main()
