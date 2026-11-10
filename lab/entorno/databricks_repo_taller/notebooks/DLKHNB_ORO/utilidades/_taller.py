"""Guard de catálogo de las utilidades del taller.

Estas utilidades imitan las de Postobón para practicar con datos sintéticos. En un workspace
de Postobón, `{{Environment}}_glux` puede resolver a un catálogo real (`dllo_glux`); el guard
impide que un notebook del taller lea o escriba ahí.
"""
PREFIJO = "cx_postobon_sdd"


def verificar_catalogo(catalogo):
    nombre = catalogo.strip().strip("`").lower()
    if not nombre.startswith(PREFIJO):
        raise PermissionError(
            f"Guard del taller: estas utilidades solo trabajan sobre catálogos que empiezan con '{PREFIJO}'. "
            f"Recibí '{catalogo}'. Revisa la variable `entorno` del notebook."
        )
    return nombre
