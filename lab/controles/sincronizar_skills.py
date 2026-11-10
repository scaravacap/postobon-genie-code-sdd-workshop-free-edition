"""Copia los scripts y plantillas canónicos a las carpetas de cada skill.

Genie Code ejecuta los scripts desde la carpeta de la skill, así que cada skill lleva
su copia. La fuente de verdad está en controles/ y plantillas/; este script evita
que las copias diverjan.

    python sincronizar_skills.py             # copia
    python sincronizar_skills.py --verificar # solo compara; sale con 1 si hay diferencias
"""
import argparse
import filecmp
import os
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ARTEFACTOS = os.path.dirname(AQUI)
SKILLS = os.path.join(ARTEFACTOS, "skills_v2")

COPIAS = [
    ("controles/atl_inventario.py", "postobon-spec-desde-atl/scripts/atl_inventario.py"),
    ("controles/atl_inventario.py", "postobon-atl-comparacion/scripts/atl_inventario.py"),
    ("controles/conf_linter.py", "postobon-etl-crear/scripts/conf_linter.py"),
    ("controles/conf_linter.py", "postobon-etl-verificacion/scripts/conf_linter.py"),
    ("controles/aceptacion.py", "postobon-etl-verificacion/scripts/aceptacion.py"),
    ("plantillas/spec.md", "postobon-spec-desde-atl/plantillas/spec.md"),
    ("plantillas/plan.md", "postobon-etl-crear/plantillas/plan.md"),
    ("plantillas/verification_report.md", "postobon-etl-verificacion/plantillas/verification_report.md"),
]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--verificar", action="store_true")
    a = p.parse_args(argv)
    distintos = []
    for origen, destino in COPIAS:
        o = os.path.join(ARTEFACTOS, origen)
        d = os.path.join(SKILLS, destino)
        igual = os.path.exists(d) and filecmp.cmp(o, d, shallow=False)
        if a.verificar:
            if not igual:
                distintos.append(destino)
            print(("OK       " if igual else "DISTINTO ") + destino)
        elif not igual:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copyfile(o, d)
            print("copiado  " + destino)
        else:
            print("igual    " + destino)
    if distintos:
        print(f"\n{len(distintos)} copias no coinciden con la fuente. Corre: python sincronizar_skills.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
