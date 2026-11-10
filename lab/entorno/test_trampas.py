"""Cada trampa del ATL sintético cambia el resultado: si una no lo cambia, el experimento no la mide.

Correr con: python -m unittest test_trampas -v
"""
import copy
import unittest

import datos_sinteticos as ds

T = ds.generar()
F = ds.fechas_proceso(T, "20260831")


def _llaves(filas):
    return {(f["cd_planta"], f["cd_registro_nomina"]): f for f in filas}


def distintas(a, b, columnas):
    """Llaves que faltan, sobran o cambian en alguna columna."""
    la, lb = _llaves(a), _llaves(b)
    n = len(set(la) ^ set(lb))
    for k in set(la) & set(lb):
        if any(abs(float(la[k][c]) - float(lb[k][c])) > 0.01 for c in columnas):
            n += 1
    return n


def con(cambio):
    t = copy.deepcopy(T)
    cambio(t)
    return t


DROP = ["vl_venta_total", "nm_pedidos", "vl_dropsize"]
VOL = ["vl_volumen_ctv"]
COB = ["nm_clientes_meta", "nm_clientes_compra", "vl_cobertura"]


class Fechas(unittest.TestCase):
    def test_fechas_de_agosto(self):
        self.assertEqual(F, {"l_fecha_fin": "20260831", "l_fecha_ini": "20260801", "l_fecha_ult_habil": "20260831"})

    def test_default_usa_ultimo_habil_anterior_a_hoy(self):
        f = ds.fechas_proceso(T, "19000101", hoy="20260901")
        self.assertEqual(f["l_fecha_fin"], "20260831")

    def test_ult_habil_salta_fin_de_semana(self):
        self.assertEqual(ds.fechas_proceso(T, "20260830")["l_fecha_ult_habil"], "20260828")


class Trampas(unittest.TestCase):
    base_drop = ds.dropsize(T, F)
    base_vol = ds.volumen_ctv(T, F)
    base_cob = ds.cobertura(T, F)

    def test_filtro_comentado_tradicional_en_nomina(self):
        t = con(lambda t: t.update({"plata.he_source_sap_ecc_zbpta011": [p for p in t["plata.he_source_sap_ecc_zbpta011"] if "AUTOSERVICIO" not in p["stext"]]}))
        self.assertGreater(distintas(self.base_drop, ds.dropsize(t, F), DROP), 5)
        self.assertGreater(distintas(self.base_cob, ds.cobertura(t, F), COB), 5)

    def test_venta_bruta_comentada(self):
        def cambio(t):
            for p in t["oro.fct_pedido_venta"]:
                p["vl_venta_neta"] = p["vl_venta_bruta"]
        self.assertGreater(distintas(self.base_drop, ds.dropsize(con(cambio), F), DROP), 30)

    def test_portafolio_solo_opt_comentado(self):
        def cambio(t):
            for c in t["plata.commision_portafolio"]:
                if c["ds_portafolio"].upper() == "EST":
                    c["ds_portafolio"] = "BAS"
        self.assertGreater(distintas(self.base_drop, ds.dropsize(con(cambio), F), DROP), 30)

    def test_portafolio_en_minusculas_exige_upper(self):
        def cambio(t):
            for c in t["plata.commision_portafolio"]:
                if c["ds_portafolio"] != c["ds_portafolio"].upper():
                    c["ds_portafolio"] = "SIN_UPPER"
        self.assertGreater(distintas(self.base_drop, ds.dropsize(con(cambio), F), DROP), 5)

    def test_count_distinct_de_pedidos(self):
        lineas, pedidos = {}, {}
        reg = {r["cd_registro_nomina"] for r in ds.registro_nomina(T, F["l_fecha_fin"])}
        for p in T["oro.fct_pedido_venta"]:
            if F["l_fecha_ini"] <= p["sk_fecha"] <= F["l_fecha_fin"] and p["cd_registro_nomina"] in reg:
                lineas[p["cd_registro_nomina"]] = lineas.get(p["cd_registro_nomina"], 0) + 1
                pedidos.setdefault(p["cd_registro_nomina"], set()).add(p["nm_pedido"])
        self.assertTrue(all(lineas[k] > len(pedidos[k]) for k in lineas))

    def test_tabla_parecida_desactualizada(self):
        t = con(lambda t: t.update({"plata.he_source_sap_ecc_zbpta011": t["plata.zbpta011"]}))
        self.assertGreater(distintas(self.base_drop, ds.dropsize(t, F), DROP), 3)

    def test_volumen_sin_filtro_de_ultimo_dia(self):
        self.assertEqual(distintas(self.base_vol, ds.volumen_ctv_sin_filtro_de_dia(T, F), VOL), len(self.base_vol))

    def test_volumen_sin_factor_comentado(self):
        t = con(lambda t: [x.update({"_c1": "1"}) for x in t["plata.commision_ctv_cf"]])
        self.assertEqual(distintas(self.base_vol, ds.volumen_ctv(t, F), VOL), len(self.base_vol))

    def test_cobertura_sin_rama_autoventa(self):
        t = con(lambda t: t.update({"plata.he_source_celuweb_autoventa": []}))
        self.assertGreater(distintas(self.base_cob, ds.cobertura(t, F), COB), 30)

    def test_filtro_comentado_tipo_meta(self):
        t = con(lambda t: t.update({"plata.commision_cobertura": [m for m in t["plata.commision_cobertura"] if m["cd_tipo_meta"] == "MENSUAL"]}))
        self.assertGreater(distintas(self.base_cob, ds.cobertura(t, F), COB), 3)

    def test_meta_cero_existe(self):
        self.assertTrue(any(f["nm_clientes_meta"] == 0 for f in self.base_cob))

    def test_retirado_y_nuevo(self):
        julio = {r["cd_registro_nomina"] for r in ds.registro_nomina(T, "20260731")}
        agosto = {r["cd_registro_nomina"] for r in ds.registro_nomina(T, "20260831")}
        self.assertEqual(len(julio - agosto), 4)
        self.assertEqual(len(agosto - julio), 4)


class P4(unittest.TestCase):
    def test_excluir_clientes_de_prueba_cambia_los_dos_indicadores(self):
        _, p4 = ds.esperados(T, "20260831", excluir_prueba=True)
        self.assertGreater(distintas(ds.dropsize(T, F), p4["fct_com_var_dropsize"], DROP), 2)
        self.assertGreater(distintas(ds.cobertura(T, F), p4["fct_com_var_cobertura"], COB), 2)

    def test_olvidar_la_rama_autoventa_en_p4_se_nota(self):
        _, p4 = ds.esperados(T, "20260831", excluir_prueba=True)
        t = con(lambda t: t.update({"oro.fct_pedido_venta": [p for p in t["oro.fct_pedido_venta"] if not p["dk_cliente"][4:].startswith("99")]}))
        solo_preventa = ds.cobertura(t, F)
        self.assertGreater(distintas(p4["fct_com_var_cobertura"], solo_preventa, COB), 0)


if __name__ == "__main__":
    unittest.main()
