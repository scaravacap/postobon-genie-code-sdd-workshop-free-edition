"""Datos sintéticos del taller y oráculo de los tres indicadores.

Todo es inventado y determinista (misma semilla, mismos datos). Imita la forma de las
fuentes de comisiones de capa oro, no sus valores. El oráculo implementa la lógica
ACTIVA del ATL sintético (com_variable_mini.atl), no la comentada.

    python datos_sinteticos.py --salida carpeta     # CSV de fuentes y esperados
    python datos_sinteticos.py --resumen            # conteos y fechas

Lo usa 00_setup_entorno.py para cargar las tablas en Unity Catalog.
Solo usa la biblioteca estándar de Python 3.9+.
"""
import argparse
import csv
import datetime
import os
import random
from decimal import ROUND_HALF_UP, Decimal

SEMILLA = 20261111
INICIO_CALENDARIO = datetime.date(2026, 6, 1)
FIN_CALENDARIO = datetime.date(2026, 12, 31)
INICIO_PEDIDOS = datetime.date(2026, 7, 20)
FIN_PEDIDOS = datetime.date(2026, 9, 4)
FESTIVOS = {"20260720", "20260807", "20260817", "20261012", "20261102", "20261116", "20261208", "20261225"}
PLANTAS = ["0101", "0106", "0203", "0305"]
PRESENTACIONES = {"P400": "0.4", "P1L5": "1.5", "P250": "0.25", "P2L0": "2.0", "P600": "0.6"}
SIN_FACTOR = "P099"
CATEGORIAS = ["BEBIDA_A", "BEBIDA_B", "AGUA", "JUGO"]

ESQUEMAS = {
    "oro.dim_fecha": [("sk_fecha", "STRING"), ("dt_fecha", "DATE"), ("cd_periodo_mes", "STRING"), ("nm_anio", "INT"),
                      ("nm_mes", "INT"), ("nm_dia_semana", "INT"), ("bl_dia_habil", "STRING"), ("bl_festivo", "STRING")],
    "plata.he_source_sap_ecc_zbpta011": [("pernr", "STRING"), ("regnom", "STRING"), ("stext", "STRING"), ("planta", "STRING"),
                                         ("bukrs", "STRING"), ("f_ingreso", "STRING"), ("f_retiro", "STRING"), ("zona", "STRING")],
    "plata.zbpta011": [("pernr", "STRING"), ("regnom", "STRING"), ("stext", "STRING"), ("planta", "STRING"),
                       ("bukrs", "STRING"), ("f_ingreso", "STRING"), ("f_retiro", "STRING"), ("zona", "STRING")],
    "oro.dim_producto": [("cd_producto", "STRING"), ("ds_producto", "STRING"), ("cd_presentacion", "STRING"),
                         ("ds_categoria", "STRING"), ("vl_litros", "DOUBLE")],
    "plata.commision_ctv_cf": [("_c0", "STRING"), ("_c1", "STRING")],
    "plata.commision_portafolio": [("cd_cliente", "STRING"), ("cd_planta", "STRING"), ("cd_registro_nomina", "STRING"),
                                   ("ds_portafolio", "STRING"), ("ds_canal", "STRING")],
    "oro.fct_pedido_venta": [("sk_fecha", "STRING"), ("dk_cliente", "STRING"), ("cd_registro_nomina", "STRING"),
                             ("cd_planta", "STRING"), ("cd_producto", "STRING"), ("cd_tipo_documento", "STRING"),
                             ("nm_pedido", "STRING"), ("vl_venta_neta", "DOUBLE"), ("vl_venta_bruta", "DOUBLE"),
                             ("vl_cantidad", "DOUBLE")],
    "plata.commision_rollup_volumen": [("sk_fecha", "STRING"), ("cd_registro_nomina", "STRING"), ("cd_planta", "STRING"),
                                       ("cd_producto", "STRING"), ("vl_volumen_acum", "DOUBLE")],
    "plata.he_source_celuweb_autoventa": [("fecha", "STRING"), ("cd_cliente", "STRING"), ("cd_registro_nomina", "STRING"),
                                          ("cd_planta", "STRING"), ("vl_venta", "DOUBLE")],
    "plata.commision_cobertura": [("cd_periodo", "STRING"), ("cd_registro_nomina", "STRING"), ("cd_planta", "STRING"),
                                  ("nm_clientes_meta", "INT"), ("cd_tipo_meta", "STRING")],
    "stg.tt_stg_registro_nomina_enriquecido": [("cd_registro_nomina", "STRING"), ("pernr", "STRING"), ("ds_cargo", "STRING"),
                                               ("cd_planta", "STRING"), ("cd_zona", "STRING"), ("cd_canal", "STRING"),
                                               ("dt_corte", "STRING")],
}

SALIDAS = {
    "oro.fct_com_var_dropsize": [("cd_periodo_mes", "STRING"), ("dt_corte", "STRING"), ("cd_planta", "STRING"),
                                 ("cd_registro_nomina", "STRING"), ("vl_venta_total", "DOUBLE"), ("nm_pedidos", "BIGINT"),
                                 ("vl_dropsize", "DOUBLE"), ("ts_carga", "TIMESTAMP")],
    "oro.fct_com_var_volumen_ctv": [("cd_periodo_mes", "STRING"), ("dt_corte", "STRING"), ("cd_planta", "STRING"),
                                    ("cd_registro_nomina", "STRING"), ("vl_volumen_ctv", "DOUBLE"), ("ts_carga", "TIMESTAMP")],
    "oro.fct_com_var_cobertura": [("cd_periodo_mes", "STRING"), ("dt_corte", "STRING"), ("cd_planta", "STRING"),
                                  ("cd_registro_nomina", "STRING"), ("nm_clientes_meta", "BIGINT"),
                                  ("nm_clientes_compra", "BIGINT"), ("vl_cobertura", "DOUBLE"), ("ts_carga", "TIMESTAMP")],
}

TRAZA = [("id_pipeline", "STRING"), ("archivo", "STRING"), ("tipo", "STRING"), ("tabla", "STRING"), ("alias", "STRING"),
         ("filas", "BIGINT"), ("segundos", "DOUBLE"), ("ts_registro", "TIMESTAMP")]


def _sk(d):
    return d.strftime("%Y%m%d")


def _mdy(d):
    return d.strftime("%m/%d/%Y")


def _dias(ini, fin):
    d = ini
    while d <= fin:
        yield d
        d += datetime.timedelta(days=1)


def es_habil(d):
    return d.weekday() < 5 and _sk(d) not in FESTIVOS


def redondear(x, decimales):
    """ROUND de Spark sobre DOUBLE: HALF_UP sobre el decimal más corto (5.025 da 5.03; round() de Python da 5.02)."""
    return float(Decimal(repr(x)).quantize(Decimal(1).scaleb(-decimales), rounding=ROUND_HALF_UP))


def generar(semilla=SEMILLA):
    """Devuelve {tabla: [filas como dict]} con todas las fuentes sintéticas."""
    rng = random.Random(semilla)
    t = {}

    t["oro.dim_fecha"] = [
        {"sk_fecha": _sk(d), "dt_fecha": d, "cd_periodo_mes": d.strftime("%Y%m"), "nm_anio": d.year, "nm_mes": d.month,
         "nm_dia_semana": d.isoweekday(), "bl_dia_habil": "SI" if es_habil(d) else "NO",
         "bl_festivo": "SI" if _sk(d) in FESTIVOS else "NO"}
        for d in _dias(INICIO_CALENDARIO, FIN_CALENDARIO)
    ]

    personal, pernr = [], 30010000
    for planta in PLANTAS:
        consecutivo = 100
        plan = (
            [("REPRESENTANTE VENTAS TRADICIONAL", "CO01", "2024-02-01", "9999-12-31")] * 8
            + [("REPRESENTANTE VENTAS AUTOSERVICIO", "CO01", "2023-06-15", "9999-12-31")] * 3
            + [("REPRESENTANTE VENTAS TRADICIONAL", "CO01", "2026-08-20", "9999-12-31")]
            + [("REPRESENTANTE VENTAS TRADICIONAL", "CO01", "2022-03-01", "2026-08-15")]
            + [("REPRESENTANTE VENTAS TRADICIONAL", "CC01", "2025-01-10", "9999-12-31")]
            + [("SUPERVISOR VENTAS", "CO01", "2021-09-01", "9999-12-31")]
            + [("AUXILIAR BODEGA", "CO01", "2022-01-10", "9999-12-31")] * 2
            + [("CONDUCTOR", "CO01", "2020-05-04", "9999-12-31")]
        )
        for stext, bukrs, ingreso, retiro in plan:
            pernr += rng.randint(3, 40)
            consecutivo += rng.randint(1, 9)
            personal.append({
                "pernr": str(pernr), "regnom": planta + f"{consecutivo:06d}", "stext": stext, "planta": planta,
                "bukrs": bukrs, "f_ingreso": _mdy(datetime.date.fromisoformat(ingreso)),
                "f_retiro": _mdy(datetime.date.fromisoformat(retiro)), "zona": f"10{planta[-2:]}{rng.randint(1, 4):02d}",
            })
    t["plata.he_source_sap_ecc_zbpta011"] = personal
    reps = [p for p in personal if "REPRESENTANTE VENTAS" in p["stext"]]
    nuevos = {p["regnom"] for p in reps if p["f_ingreso"].endswith("2026") and p["f_ingreso"].startswith("08/20")}
    t["plata.zbpta011"] = [dict(p) for p in personal if p["regnom"] not in nuevos and rng.random() < 0.86]

    productos = []
    for i in range(30):
        pres = list(PRESENTACIONES)[i % 5] if i < 27 else SIN_FACTOR
        productos.append({
            "cd_producto": f"{700100 + i * 7}", "ds_producto": f"PRODUCTO {i + 1:02d} {pres}", "cd_presentacion": pres,
            "ds_categoria": CATEGORIAS[i % 4], "vl_litros": {"P400": 0.4, "P1L5": 1.5, "P250": 0.25, "P2L0": 2.0, "P600": 0.6, "P099": 0.1}[pres],
        })
    t["oro.dim_producto"] = productos
    precio = {p["cd_producto"]: round(1800 + rng.random() * 5200, 0) for p in productos}
    t["plata.commision_ctv_cf"] = [{"_c0": k, "_c1": v} for k, v in PRESENTACIONES.items()]

    portafolio, clientes_de, usados = [], {}, set()

    def nuevo_cliente(prefijo):
        while True:
            cd = prefijo + f"{rng.randint(0, 99999999):08d}"
            if cd not in usados:
                usados.add(cd)
                return cd

    for r in reps:
        lista = []
        for _ in range(rng.randint(10, 14)):
            cd = nuevo_cliente("99" if rng.random() < 0.03 else "00")
            port = rng.choices(["OPT", "EST", "BAS"], [40, 35, 25])[0]
            canal = rng.choices(["TRADICIONAL", "TRADICIONAL RURAL", "AUTOSERVICIO", "INSTITUCIONAL"], [55, 15, 20, 10])[0]
            portafolio.append({"cd_cliente": cd, "cd_planta": r["planta"], "cd_registro_nomina": r["regnom"],
                               "ds_portafolio": port.lower() if rng.random() < 0.1 else port, "ds_canal": canal})
            lista.append(cd)
        clientes_de[r["regnom"]] = lista
    for r in rng.sample(reps, 4):
        cd = nuevo_cliente("99")
        portafolio.append({"cd_cliente": cd, "cd_planta": r["planta"], "cd_registro_nomina": r["regnom"],
                           "ds_portafolio": "OPT", "ds_canal": "TRADICIONAL"})
        clientes_de[r["regnom"]].append(cd)
    t["plata.commision_portafolio"] = portafolio

    def activo(r, d):
        ing = datetime.datetime.strptime(r["f_ingreso"], "%m/%d/%Y").date()
        ret = datetime.datetime.strptime(r["f_retiro"], "%m/%d/%Y").date()
        return ing <= d <= ret

    pedidos, n_pedido = [], 0
    dummy = "DUMMY00001"
    for d in _dias(INICIO_PEDIDOS, FIN_PEDIDOS):
        if not es_habil(d):
            continue
        vendedores = [(r["regnom"], r["planta"]) for r in reps if activo(r, d)]
        for regnom, planta in vendedores + [(dummy, rng.choice(PLANTAS))]:
            for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
                n_pedido += 1
                cliente = rng.choice(clientes_de.get(regnom) or [c for v in clientes_de.values() for c in v])
                tipo = "D" if rng.random() < 0.05 else "V"
                for prod in rng.sample(productos, rng.randint(1, 3)):
                    cant = float(rng.randint(1, 20))
                    bruta = round(cant * precio[prod["cd_producto"]], 2)
                    neta = round(bruta * (1 - rng.choice([0, 0.03, 0.05, 0.08, 0.12])), 2)
                    pedidos.append({
                        "sk_fecha": _sk(d), "dk_cliente": "1000" + cliente, "cd_registro_nomina": regnom, "cd_planta": planta,
                        "cd_producto": prod["cd_producto"], "cd_tipo_documento": tipo, "nm_pedido": f"PV{n_pedido:07d}",
                        "vl_venta_neta": neta, "vl_venta_bruta": bruta, "vl_cantidad": cant,
                    })
    t["oro.fct_pedido_venta"] = pedidos

    acumulado, rollup, por_dia = {}, [], {}
    for p in pedidos:
        if p["cd_tipo_documento"] == "V":
            por_dia.setdefault(p["sk_fecha"], []).append(p)
    for d in _dias(INICIO_PEDIDOS, FIN_PEDIDOS):
        if not es_habil(d):
            continue
        mes = d.strftime("%Y%m")
        for p in por_dia.get(_sk(d), []):
            k = (mes, p["cd_registro_nomina"], p["cd_planta"], p["cd_producto"])
            acumulado[k] = acumulado.get(k, 0.0) + p["vl_cantidad"]
        for (m, regnom, planta, prod), v in sorted(acumulado.items()):
            if m == mes:
                rollup.append({"sk_fecha": _sk(d), "cd_registro_nomina": regnom, "cd_planta": planta, "cd_producto": prod,
                               "vl_volumen_acum": v})
    t["plata.commision_rollup_volumen"] = rollup

    autoventa = []
    for d in _dias(INICIO_PEDIDOS, FIN_PEDIDOS):
        if not es_habil(d):
            continue
        for r in reps:
            if not activo(r, d) or rng.random() > 0.35:
                continue
            base = clientes_de[r["regnom"]]
            for _ in range(rng.randint(1, 2)):
                if rng.random() < 0.25:
                    cliente = "00" + f"{rng.randint(0, 99999999):08d}"
                elif rng.random() < 0.06:
                    cliente = "99" + f"{rng.randint(0, 99999999):08d}"
                else:
                    cliente = rng.choice(base)
                valor = 0.0 if rng.random() < 0.07 else round(5000 + rng.random() * 90000, 2)
                autoventa.append({"fecha": d.isoformat(), "cd_cliente": cliente, "cd_registro_nomina": r["regnom"],
                                  "cd_planta": r["planta"], "vl_venta": valor})
    t["plata.he_source_celuweb_autoventa"] = autoventa

    metas = []
    for periodo in ("202607", "202608", "202609"):
        for p in personal:
            if "REPRESENTANTE VENTAS" not in p["stext"] and "SUPERVISOR" not in p["stext"]:
                continue
            asignados = len(clientes_de.get(p["regnom"], [])) or 20
            meta = 0 if rng.random() < 0.06 else max(1, asignados + rng.randint(4, 14))
            metas.append({"cd_periodo": periodo, "cd_registro_nomina": p["regnom"], "cd_planta": p["planta"],
                          "nm_clientes_meta": meta, "cd_tipo_meta": "TRIMESTRAL" if rng.random() < 0.15 else "MENSUAL"})
    t["plata.commision_cobertura"] = metas

    fin_julio = "20260731"
    t["stg.tt_stg_registro_nomina_enriquecido"] = [
        {"cd_registro_nomina": r["cd_registro_nomina"], "pernr": r["pernr"], "ds_cargo": r["ds_cargo"], "cd_planta": r["cd_planta"],
         "cd_zona": r["cd_zona"], "cd_canal": r["cd_canal"], "dt_corte": fin_julio}
        for r in registro_nomina(t, fin_julio)
    ]
    return t


# ---------------------------------------------------------------- oráculo (lógica activa del ATL)


def fechas_proceso(t, p_fecha, hoy=None):
    """$L_FECHA_FIN, $L_FECHA_INI y $L_FECHA_ULT_HABIL como los calcula WF_TALLER_COM_VARIABLE."""
    habiles = sorted(f["sk_fecha"] for f in t["oro.dim_fecha"] if f["bl_dia_habil"] == "SI")
    if p_fecha == "19000101":
        hoy = hoy or _sk(datetime.date.today())
        fin = max(s for s in habiles if s < hoy)
    else:
        fin = p_fecha
    ini = fin[:6] + "01"
    ult = max(s for s in habiles if s <= fin)
    return {"l_fecha_fin": fin, "l_fecha_ini": ini, "l_fecha_ult_habil": ult}


def registro_nomina(t, fin):
    """DF_TALLER_REGISTRO_NOMINA_EXT: representantes vigentes a la fecha de corte."""
    salida = []
    for p in t["plata.he_source_sap_ecc_zbpta011"]:
        ingreso = datetime.datetime.strptime(p["f_ingreso"], "%m/%d/%Y").strftime("%Y%m%d")
        retiro = datetime.datetime.strptime(p["f_retiro"], "%m/%d/%Y").strftime("%Y%m%d")
        if "REPRESENTANTE VENTAS" in p["stext"] and p["bukrs"] != "CC01" and ingreso <= fin and retiro >= fin:
            salida.append({"pernr": p["pernr"], "cd_registro_nomina": p["regnom"], "ds_cargo": p["stext"], "cd_planta": p["planta"],
                           "cd_zona": p["zona"], "cd_canal": "AUTOSERVICIO" if "AUTOSERVICIO" in p["stext"] else "TRADICIONAL"})
    return salida


def dropsize(t, f, excluir_prueba=False):
    """DF_TALLER_DROPSIZE_TRN."""
    reg = {r["cd_registro_nomina"]: r for r in registro_nomina(t, f["l_fecha_fin"])}
    port = {}
    for c in t["plata.commision_portafolio"]:
        port[c["cd_cliente"]] = c
    acum = {}
    for p in t["oro.fct_pedido_venta"]:
        if not (f["l_fecha_ini"] <= p["sk_fecha"] <= f["l_fecha_fin"]) or p["cd_tipo_documento"] != "V":
            continue
        c = port.get(p["dk_cliente"][4:14])
        if not c or c["ds_portafolio"].upper() not in ("OPT", "EST") or "TRADICIONAL" not in c["ds_canal"].upper():
            continue
        if excluir_prueba and c["cd_cliente"].startswith("99"):
            continue
        r = reg.get(p["cd_registro_nomina"])
        if not r:
            continue
        k = (r["cd_planta"], r["cd_registro_nomina"])
        a = acum.setdefault(k, {"venta": 0.0, "pedidos": set()})
        a["venta"] += p["vl_venta_neta"]
        a["pedidos"].add(p["nm_pedido"])
    filas = []
    for (planta, regnom), a in sorted(acum.items()):
        total, n = redondear(a["venta"], 2), len(a["pedidos"])
        filas.append({"cd_periodo_mes": f["l_fecha_fin"][:6], "dt_corte": f["l_fecha_fin"], "cd_planta": planta,
                      "cd_registro_nomina": regnom, "vl_venta_total": total, "nm_pedidos": n,
                      "vl_dropsize": 0.0 if n == 0 else redondear(total / n, 2)})
    return filas


def volumen_ctv(t, f):
    """DF_TALLER_ROLLUP_VOLUMEN_TRN: volumen acumulado del último día hábil por el factor CTV."""
    reg = {r["cd_registro_nomina"]: r for r in registro_nomina(t, f["l_fecha_fin"])}
    prod = {p["cd_producto"]: p for p in t["oro.dim_producto"]}
    factor = {x["_c0"]: float(x["_c1"]) for x in t["plata.commision_ctv_cf"]}
    acum = {}
    for x in t["plata.commision_rollup_volumen"]:
        if x["sk_fecha"] != f["l_fecha_ult_habil"] or x["cd_registro_nomina"].startswith("DUMMY"):
            continue
        p = prod.get(x["cd_producto"])
        r = reg.get(x["cd_registro_nomina"])
        if not p or not r:
            continue
        k = (r["cd_planta"], r["cd_registro_nomina"])
        acum[k] = acum.get(k, 0.0) + x["vl_volumen_acum"] * factor.get(p["cd_presentacion"], 0.0)
    return [{"cd_periodo_mes": f["l_fecha_fin"][:6], "dt_corte": f["l_fecha_fin"], "cd_planta": planta,
             "cd_registro_nomina": regnom, "vl_volumen_ctv": redondear(v, 4)} for (planta, regnom), v in sorted(acum.items())]


def volumen_ctv_sin_filtro_de_dia(t, f):
    """El error sembrado de P3: suma el acumulado de todos los días del mes en lugar del último día hábil."""
    reg = {r["cd_registro_nomina"]: r for r in registro_nomina(t, f["l_fecha_fin"])}
    prod = {p["cd_producto"]: p for p in t["oro.dim_producto"]}
    factor = {x["_c0"]: float(x["_c1"]) for x in t["plata.commision_ctv_cf"]}
    acum = {}
    for x in t["plata.commision_rollup_volumen"]:
        if not (f["l_fecha_ini"] <= x["sk_fecha"] <= f["l_fecha_fin"]) or x["cd_registro_nomina"].startswith("DUMMY"):
            continue
        p, r = prod.get(x["cd_producto"]), reg.get(x["cd_registro_nomina"])
        if p and r:
            k = (r["cd_planta"], r["cd_registro_nomina"])
            acum[k] = acum.get(k, 0.0) + x["vl_volumen_acum"] * factor.get(p["cd_presentacion"], 0.0)
    return [{"cd_periodo_mes": f["l_fecha_fin"][:6], "dt_corte": f["l_fecha_fin"], "cd_planta": planta,
             "cd_registro_nomina": regnom, "vl_volumen_ctv": redondear(v, 4)} for (planta, regnom), v in sorted(acum.items())]


def cobertura(t, f, excluir_prueba=False):
    """DF_TALLER_COBERTURA_TRN: clientes con compra (preventa UNION ALL autoventa) sobre la meta del período."""
    reg = {r["cd_registro_nomina"]: r for r in registro_nomina(t, f["l_fecha_fin"])}
    pares = set()
    for p in t["oro.fct_pedido_venta"]:
        if f["l_fecha_ini"] <= p["sk_fecha"] <= f["l_fecha_fin"] and p["cd_tipo_documento"] == "V":
            pares.add((p["cd_registro_nomina"], p["dk_cliente"][4:14]))
    for a in t["plata.he_source_celuweb_autoventa"]:
        sk = a["fecha"].replace("-", "")
        if f["l_fecha_ini"] <= sk <= f["l_fecha_fin"] and a["vl_venta"] > 0:
            pares.add((a["cd_registro_nomina"], a["cd_cliente"]))
    compra = {}
    for regnom, cliente in pares:
        if excluir_prueba and cliente.startswith("99"):
            continue
        compra.setdefault(regnom, set()).add(cliente)
    periodo = f["l_fecha_fin"][:6]
    filas = []
    for m in t["plata.commision_cobertura"]:
        r = reg.get(m["cd_registro_nomina"])
        if m["cd_periodo"] != periodo or not r:
            continue
        n = len(compra.get(m["cd_registro_nomina"], ()))
        meta = m["nm_clientes_meta"]
        filas.append({"cd_periodo_mes": periodo, "dt_corte": f["l_fecha_fin"], "cd_planta": r["cd_planta"],
                      "cd_registro_nomina": m["cd_registro_nomina"], "nm_clientes_meta": meta, "nm_clientes_compra": n,
                      "vl_cobertura": 0.0 if meta == 0 else redondear(n / meta, 4)})
    return sorted(filas, key=lambda x: (x["cd_planta"], x["cd_registro_nomina"]))


def esperados(t, p_fecha="20260831", excluir_prueba=False):
    f = fechas_proceso(t, p_fecha)
    return f, {
        "fct_com_var_dropsize": dropsize(t, f, excluir_prueba),
        "fct_com_var_volumen_ctv": volumen_ctv(t, f),
        "fct_com_var_cobertura": cobertura(t, f, excluir_prueba),
    }


def escribir_csv(ruta, filas, columnas=None):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    columnas = columnas or (list(filas[0].keys()) if filas else [])
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        for fila in filas:
            w.writerow({k: (v.isoformat() if isinstance(v, datetime.date) else v) for k, v in fila.items()})
    return ruta


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--salida")
    p.add_argument("--fecha", default="20260831")
    p.add_argument("--resumen", action="store_true")
    a = p.parse_args(argv)
    t = generar()
    f, esp = esperados(t, a.fecha)
    _, esp_p4 = esperados(t, a.fecha, excluir_prueba=True)
    if a.resumen or not a.salida:
        for k, v in t.items():
            print(f"{k}: {len(v)} filas")
        print("Fechas:", f)
        for k, v in esp.items():
            print(f"esperado {k}: {len(v)} filas; P4: {len(esp_p4[k])} filas")
    if a.salida:
        for k, v in t.items():
            escribir_csv(os.path.join(a.salida, "fuentes", k + ".csv"), v)
        for k, v in esp.items():
            escribir_csv(os.path.join(a.salida, "esperados", f"{k}_{a.fecha}.csv"), v)
        for k, v in esp_p4.items():
            escribir_csv(os.path.join(a.salida, "privado", f"{k}_{a.fecha}_p4.csv"), v)
        print("Escrito en", a.salida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
