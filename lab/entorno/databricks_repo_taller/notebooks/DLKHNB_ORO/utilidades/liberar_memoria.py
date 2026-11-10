"""Stub del taller de `liberar_memoria()`: borra las vistas temporales de cada alias."""


def liberar_memoria(spark, *diccionarios):
    borradas = 0
    for d in diccionarios:
        for alias in list(d or {}):
            if spark.catalog.dropTempView(alias):
                borradas += 1
    print(f"Vistas temporales liberadas: {borradas}")
    return borradas
