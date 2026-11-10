"""Pruebas del linter de .conf. Correr con: python -m unittest test_conf_linter -v"""
import os
import shutil
import tempfile
import textwrap
import unittest

import conf_linter as L

PAR = """\
[Entrada]
tipo = insumo
catalogo = {{Environment}}_glux
schema = stg
tabla = par_prueba
alias = par_prueba
tablas_entrada = []
columnas = l_fecha_ini, l_fecha_fin

[QUERIES]
query_1 =
    WITH habiles AS (SELECT sk_fecha FROM {{catalogo}}.oro.dim_fecha WHERE bl_dia_habil = 'SI')
    SELECT '{{parametros[G_Fecha]}}' AS l_fecha_fin, '20260801' AS l_fecha_ini FROM habiles LIMIT 1
"""

INS = """\
[Entrada]
tipo = insumo
catalogo = {{Environment}}_glux
schema = plata
tabla = he_source_sap_ecc_zbpta011
alias = tt_stg_nomina
tablas_entrada = []
columnas = regnom, stext

[QUERIES]
query_1 =
    SELECT regnom, stext, EXTRACT(YEAR FROM f_ingreso) AS anio
    FROM {{catalogo}}.{{schema}}.{{tabla}}
    WHERE stext LIKE '%%REPRESENTANTE%%'
"""

INT = """\
[Entrada]
tipo = intermedia
catalogo = {{Environment}}_glux
schema = stg
tabla = tt_stg_resultado
alias = tt_stg_resultado
tablas_entrada = [tt_stg_nomina]
columnas = regnom

[QUERIES]
query_1 =
    SELECT n.regnom
    FROM tt_stg_nomina n
    WHERE n.dt BETWEEN (SELECT l_fecha_ini FROM {{catalogo}}.stg.par_prueba) AND (SELECT l_fecha_fin FROM {{catalogo}}.stg.par_prueba)
"""

SAL = """\
[Entrada]
tipo = salida
catalogo = {{Environment}}_glux
schema = oro
tabla = fct_prueba
alias = fct_prueba
tablas_entrada = [tt_stg_resultado]
columnas = regnom

[QUERIES]
query_1 =
    SELECT r.regnom FROM tt_stg_resultado r
"""

SPEC = """\
# Spec
Estado: APROBADA por Ana, 2026-11-09

## 3. Fuentes ATL a UC
| Tabla ATL | Tabla en UC | Consulta | Estado |
|---|---|---|---|
| ZBPTA011 | plata.he_source_sap_ecc_zbpta011 | SELECT 1 | OK |
| DIM_FECHA | oro.dim_fecha | SELECT 1 | OK |

## 4. Lógica
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.carpeta = os.path.join(self.dir, "DLKHID_PRUEBA")
        for sub in L.ORDEN:
            os.makedirs(os.path.join(self.carpeta, sub))
        open(os.path.join(self.carpeta, "DLKH_01_PRUEBA"), "w").close()
        self.escribir("PARAMETROS/config_par_prueba.conf", PAR)
        self.escribir("INSUMOS/config_ins_01_nomina.conf", INS)
        self.escribir("INTERMEDIAS/config_int_01_resultado.conf", INT)
        self.escribir("SALIDAS/config_sal_01_fct_prueba.conf", SAL)
        self.spec = os.path.join(self.carpeta, "spec.md")
        with open(self.spec, "w", encoding="utf-8") as f:
            f.write(SPEC)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def escribir(self, rel, texto):
        with open(os.path.join(self.carpeta, rel), "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(texto))

    def reglas(self, rep, severidad="error"):
        return [h["regla"] for h in rep["hallazgos"] if h["severidad"] == severidad]


class CarpetaLimpia(Base):
    def test_pasa_sin_hallazgos(self):
        rep = L.lint_carpeta(self.carpeta, spec=self.spec)
        self.assertEqual(rep["resultado"], "PASA", L.formatear(rep))
        self.assertEqual(rep["advertencias"], 0, L.formatear(rep))
        self.assertEqual(len(rep["archivos"]), 4)
        self.assertEqual(len(rep["archivos"][0]["sha256"]), 64)
        self.assertIn("PASA", L.formatear(rep))


class Reglas(Base):
    def test_porcentaje_sin_escapar(self):
        self.escribir("INSUMOS/config_ins_01_nomina.conf", INS.replace("%%REPRESENTANTE%%", "%REPRESENTANTE%"))
        rep = L.lint_carpeta(self.carpeta)
        h = [x for x in rep["hallazgos"] if x["regla"] == "interpolacion"]
        self.assertEqual(len(h), 1, L.formatear(rep))
        self.assertEqual(h[0]["linea"], 14)
        self.assertIn("must be followed by", h[0]["detalle"])

    def test_porcentaje_en_comentario_sql(self):
        self.escribir("SALIDAS/config_sal_01_fct_prueba.conf", SAL.replace("FROM tt_stg_resultado r", "FROM tt_stg_resultado r -- 10% de la base"))
        self.assertIn("interpolacion", self.reglas(L.lint_carpeta(self.carpeta)))

    def test_parametros_fuera_de_par(self):
        self.escribir(
            "INTERMEDIAS/config_int_01_resultado.conf",
            INT.replace("(SELECT l_fecha_ini FROM {{catalogo}}.stg.par_prueba)", "'{{parametros[G_Fecha_Ini]}}'"),
        )
        self.assertIn("parametros_fuera_de_par", self.reglas(L.lint_carpeta(self.carpeta)))

    def test_alias_no_declarado(self):
        self.escribir("SALIDAS/config_sal_01_fct_prueba.conf", SAL.replace("tablas_entrada = [tt_stg_resultado]", "tablas_entrada = []"))
        rep = L.lint_carpeta(self.carpeta)
        self.assertIn("tablas_entrada", self.reglas(rep))

    def test_extract_from_no_es_tabla(self):
        rep = L.lint_archivo(os.path.join(self.carpeta, "INSUMOS/config_ins_01_nomina.conf"))
        self.assertEqual(rep["errores"], 0, L.formatear(rep))

    def test_dml(self):
        self.escribir("SALIDAS/config_sal_01_fct_prueba.conf", SAL.replace("SELECT r.regnom", "INSERT INTO x SELECT r.regnom"))
        self.assertIn("solo_select", self.reglas(L.lint_carpeta(self.carpeta)))

    def test_tipo_no_coincide_con_carpeta(self):
        self.escribir("INTERMEDIAS/config_int_01_resultado.conf", INT.replace("tipo = intermedia", "tipo = salida"))
        self.assertIn("tipo_carpeta", self.reglas(L.lint_carpeta(self.carpeta)))

    def test_catalogo_a_mano(self):
        self.escribir("SALIDAS/config_sal_01_fct_prueba.conf", SAL.replace("FROM tt_stg_resultado r", "FROM tt_stg_resultado r JOIN dllo_glux.oro.dim_x d ON 1=1"))
        self.assertIn("catalogo", self.reglas(L.lint_carpeta(self.carpeta)))

    def test_plantilla_desconocida(self):
        self.escribir("SALIDAS/config_sal_01_fct_prueba.conf", SAL.replace("SELECT r.regnom", "SELECT '{{fecha}}' AS f, r.regnom"))
        self.assertIn("plantilla", self.reglas(L.lint_carpeta(self.carpeta)))

    def test_subquery_no_escalar(self):
        self.escribir(
            "SALIDAS/config_sal_01_fct_prueba.conf",
            SAL.replace("FROM tt_stg_resultado r", "FROM tt_stg_resultado r WHERE r.regnom IN (SELECT regnom FROM tt_stg_resultado)"),
        )
        self.assertIn("subquery", self.reglas(L.lint_carpeta(self.carpeta), "advertencia"))

    def test_subquery_escalar_de_fechas_permitido(self):
        rep = L.lint_archivo(os.path.join(self.carpeta, "INTERMEDIAS/config_int_01_resultado.conf"))
        self.assertNotIn("subquery", self.reglas(rep, "advertencia"))

    def test_prefijo_legacy(self):
        self.escribir(
            "INTERMEDIAS/config_int_01_resultado.conf",
            INT.replace("alias = tt_stg_resultado", "alias = tt_stg_hana_resultado").replace("tabla = tt_stg_resultado", "tabla = tt_stg_hana_resultado"),
        )
        self.assertIn("alias_stg", self.reglas(L.lint_carpeta(self.carpeta), "advertencia"))

    def test_tabla_fuente_con_sistema_en_el_nombre_permitida(self):
        self.escribir(
            "INSUMOS/config_ins_01_nomina.conf",
            INS.replace("tabla = he_source_sap_ecc_zbpta011", "tabla = he_source_celuweb_autoventa"),
        )
        self.assertNotIn("alias_stg", self.reglas(L.lint_carpeta(self.carpeta), "advertencia"))

    def test_alias_duplicado(self):
        self.escribir("INTERMEDIAS/config_int_02_otra.conf", INT)
        self.assertIn("alias_duplicado", self.reglas(L.lint_carpeta(self.carpeta)))

    def test_falta_seccion(self):
        self.escribir("SALIDAS/config_sal_01_fct_prueba.conf", "[Entrada]\ntipo = salida\n")
        self.assertIn("secciones", self.reglas(L.lint_carpeta(self.carpeta)))


class Spec(Base):
    def test_fuente_fuera_de_spec(self):
        self.escribir("INSUMOS/config_ins_01_nomina.conf", INS.replace("tabla = he_source_sap_ecc_zbpta011", "tabla = zbpta011"))
        rep = L.lint_carpeta(self.carpeta, spec=self.spec)
        detalles = [h["detalle"] for h in rep["hallazgos"] if h["regla"] == "spec_fuentes" and h["severidad"] == "error"]
        self.assertTrue(any("plata.zbpta011" in d for d in detalles), L.formatear(rep))

    def test_fuente_marcada_no_existe(self):
        with open(self.spec, "w", encoding="utf-8") as f:
            f.write(SPEC.replace("| SELECT 1 | OK |\n| DIM_FECHA", "| SELECT 1 | NO EXISTE |\n| DIM_FECHA"))
        self.assertIn("spec_fuentes", self.reglas(L.lint_carpeta(self.carpeta, spec=self.spec)))

    def test_spec_sin_aprobar(self):
        with open(self.spec, "w", encoding="utf-8") as f:
            f.write(SPEC.replace("APROBADA por Ana, 2026-11-09", "BORRADOR"))
        self.assertIn("spec_estado", self.reglas(L.lint_carpeta(self.carpeta, spec=self.spec), "advertencia"))


class _DF:
    def __init__(self, vistas, alias=None):
        self.vistas = vistas

    def limit(self, n):
        return self

    def createOrReplaceTempView(self, nombre):
        self.vistas.append(nombre)


class _Spark:
    """Spark falso: falla si la query menciona una columna marcada como inexistente."""

    def __init__(self, columna_mala=None):
        self.vistas, self.sqls, self.columna_mala = [], [], columna_mala

    def sql(self, texto):
        self.sqls.append(texto)
        if self.columna_mala and self.columna_mala in texto:
            raise Exception(f"[UNRESOLVED_COLUMN.WITH_SUGGESTION] A column with name `{self.columna_mala}` cannot be resolved.\nSQLSTATE: 42703")
        return _DF(self.vistas)


class Explain(Base):
    def test_explain_renderiza_y_registra_vistas(self):
        spark = _Spark()
        rep = L.lint_carpeta(self.carpeta, spark=spark, explain=True, entorno="cx_postobon_sdd_workshop")
        self.assertEqual(rep["errores"], 0, L.formatear(rep))
        self.assertEqual(spark.vistas, ["par_prueba", "tt_stg_nomina", "tt_stg_resultado", "fct_prueba"])
        self.assertIn("cx_postobon_sdd_workshop_glux.plata.he_source_sap_ecc_zbpta011", spark.sqls[1])
        self.assertIn("LIKE '%REPRESENTANTE%'", spark.sqls[1])
        self.assertIn("(SELECT l_fecha_ini FROM par_prueba)", spark.sqls[2])

    def test_explain_columna_inexistente_y_cascada(self):
        spark = _Spark(columna_mala="n.regnom")
        rep = L.lint_carpeta(self.carpeta, spark=spark, explain=True, entorno="cx_postobon_sdd_workshop")
        errores = [h for h in rep["hallazgos"] if h["regla"] == "explain" and h["severidad"] == "error"]
        self.assertEqual(len(errores), 1)
        self.assertTrue(errores[0]["detalle"].startswith("UNRESOLVED_COLUMN.WITH_SUGGESTION"))
        saltadas = [h for h in rep["hallazgos"] if h["regla"] == "explain" and h["severidad"] == "advertencia"]
        self.assertEqual(len(saltadas), 1)
        self.assertIn("tt_stg_resultado", saltadas[0]["detalle"])


if __name__ == "__main__":
    unittest.main()
