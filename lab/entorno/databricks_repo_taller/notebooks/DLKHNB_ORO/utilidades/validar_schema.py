"""Stub del taller de `validar_schema()`: nombres y tipos deben coincidir con la tabla destino.

Compara sin distinguir mayúsculas en los nombres e ignora la nulabilidad. Un `INT` donde la
tabla espera `BIGINT`, o un `DECIMAL` donde espera `DOUBLE`, falla: castea en la query de salida.
"""
from notebooks.DLKHNB_ORO.utilidades._taller import verificar_catalogo


def validar_schema(nombre_tabla, df_salida, spark):
    verificar_catalogo(nombre_tabla.split(".")[0])
    destino = {f.name.lower(): f.dataType.simpleString() for f in spark.table(nombre_tabla).schema.fields}
    salida = {f.name.lower(): f.dataType.simpleString() for f in df_salida.schema.fields}
    faltan = sorted(set(destino) - set(salida))
    sobran = sorted(set(salida) - set(destino))
    tipos = sorted(f"{c} (salida {salida[c]}, destino {destino[c]})" for c in set(destino) & set(salida) if destino[c] != salida[c])
    if faltan or sobran or tipos:
        partes = []
        if faltan:
            partes.append(f"faltan {', '.join(faltan)}")
        if sobran:
            partes.append(f"sobran {', '.join(sobran)}")
        if tipos:
            partes.append(f"tipos distintos: {'; '.join(tipos)}")
        raise ValueError(f"validar_schema: la salida no coincide con {nombre_tabla}: " + " | ".join(partes))
    print(f"Schema OK: {nombre_tabla} ({len(destino)} columnas)")
    return True
