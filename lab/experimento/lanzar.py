"""Arma una corrida del job taller_sdd_experimento con el texto exacto de prompts.md.

    python lanzar.py --job-id 123 --prompt P1 --variante v1               # muestra el comando, no lo lanza
    python lanzar.py --job-id 123 --prompt P1 --variante v1 --ejecutar    # lo lanza con la CLI de Databricks
    python lanzar.py --prompt P2 --mostrar                                # solo imprime el prompt
"""
import argparse
import json
import os
import re
import subprocess

AQUI = os.path.dirname(os.path.abspath(__file__))
PROMPTS = ["CANARY", "P1", "P2", "P3", "P4"]


def prompts(raiz, catalogo):
    with open(os.path.join(AQUI, "prompts.md"), encoding="utf-8") as f:
        bloques = dict(re.findall(r"```text (\w+)\n(.*?)\n```", f.read(), re.S))
    preambulo = bloques.pop("preambulo")
    if sorted(bloques) != sorted(PROMPTS):
        raise ValueError(f"prompts.md debe tener los bloques {PROMPTS}; tiene {sorted(bloques)}")
    return {k: f"{preambulo}\n\n{v}".replace("@RAIZ@", raiz).replace("@CATALOGO@", catalogo) for k, v in bloques.items()}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--job-id")
    p.add_argument("--prompt", required=True, choices=PROMPTS)
    p.add_argument("--variante", choices=["v1", "v2"])
    p.add_argument("--usuario", required=True, help="correo del creador del job, el mismo usuario de la raíz del taller")
    p.add_argument("--entorno", default="cx_postobon_sdd_workshop")
    p.add_argument("--profile", default="DEFAULT")
    p.add_argument("--mostrar", action="store_true")
    p.add_argument("--ejecutar", action="store_true")
    a = p.parse_args(argv)
    texto = prompts(f"/Workspace/Users/{a.usuario}/postobon_sdd_workshop", f"{a.entorno}_glux")[a.prompt]
    if a.mostrar or not a.job_id:
        print(texto)
        return 0
    if not a.variante:
        p.error("--variante es obligatoria para lanzar una corrida")
    cuerpo = {"job_id": int(a.job_id), "job_parameters": {"prompt_id": a.prompt, "variante": a.variante, "prompt": texto}}
    comando = ["databricks", "jobs", "run-now", "--no-wait", "--profile", a.profile, "--json", json.dumps(cuerpo, ensure_ascii=False)]
    print(" ".join(comando[:6]), "--json '<prompt " + a.prompt + ", " + str(len(texto)) + " caracteres>'")
    if a.ejecutar:
        subprocess.run(comando, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
