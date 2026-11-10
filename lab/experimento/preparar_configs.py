"""Arma config_v1/ y config_v2/: instructions de usuario más el mismo adaptador de entorno, y las skills.

    python preparar_configs.py --usuario <correo>

config_v1 sale de la configuración actual de Postobón (constitución y 7 skills, en la carpeta de la tarea).
Es material del cliente: se sube solo al usuario del facilitador en DEFAULT y no se publica.
La única diferencia entre variantes es lo que va antes del adaptador y las skills.
"""
import argparse
import hashlib
import os
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS = os.path.dirname(AQUI)
TAREA = os.path.dirname(ARTIFACTS)
FUENTES = {
    "v1": (os.path.join(TAREA, "assistant_workspace_instructions.md"), os.path.join(TAREA, "skills")),
    "v2": (os.path.join(ARTIFACTS, "constitucion_v2", "assistant_workspace_instructions.md"), os.path.join(ARTIFACTS, "skills_v2")),
}
IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def adaptador(entorno, usuario):
    with open(os.path.join(ARTIFACTS, "entorno", "adaptador_entorno.md"), encoding="utf-8") as f:
        plantilla = f.read()
    raiz = f"/Workspace/Users/{usuario}/postobon_sdd_workshop"
    return plantilla.replace("@CATALOGO@", f"{entorno}_glux").replace("@ENTORNO@", entorno).replace("@RAIZ@", raiz)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--usuario", required=True)
    p.add_argument("--entorno", default="cx_postobon_sdd_workshop")
    a = p.parse_args(argv)
    bloque = adaptador(a.entorno, a.usuario)
    for variante, (instrucciones, skills) in FUENTES.items():
        destino = os.path.join(AQUI, f"config_{variante}")
        shutil.rmtree(destino, ignore_errors=True)
        shutil.copytree(skills, os.path.join(destino, "skills"), ignore=IGNORAR)
        with open(instrucciones, encoding="utf-8") as f:
            texto = f.read().rstrip() + "\n\n" + bloque
        with open(os.path.join(destino, "assistant_instructions.md"), "w", encoding="utf-8") as f:
            f.write(texto)
        nombres = sorted(os.listdir(os.path.join(destino, "skills")))
        huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]
        print(f"config_{variante}: instructions {len(texto)} caracteres (sha {huella}), {len(nombres)} skills: {', '.join(nombres)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
