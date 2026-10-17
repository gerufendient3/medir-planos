"""Comprueba que cada nombre de prueba citado en un documento exista.

Un documento de cierre que dice "esto lo respalda la prueba X" es una
afirmación fuerte: si X no existe, el documento miente en la parte que
precisamente pretende probar. Este script verifica los dos lados.

Uso:  python scripts/verificar_citas_de_pruebas.py <documento.md> [...]
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CITA = re.compile(r"`(test_\w+)`")


def pruebas_reales() -> set[str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
        cwd=str(RAIZ), capture_output=True, text=True)
    return {l.split("::")[-1].strip() for l in r.stdout.splitlines()
            if "::" in l}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    reales = pruebas_reales()
    problemas = []
    for nombre in argv:
        ruta = Path(nombre)
        texto = ruta.read_text(encoding="utf-8")
        citados = sorted(set(CITA.findall(texto)))
        faltan = [t for t in citados if t not in reales]
        print("{}: {} nombres citados, {} no existen".format(
            ruta.name, len(citados), len(faltan)))
        for t in faltan:
            print("    NO EXISTE:", t)
            partes = t.split("_")
            for n in range(len(partes), 2, -1):
                prefijo = "_".join(partes[:n])
                parecidos = sorted(x for x in reales if x.startswith(prefijo))
                if parecidos:
                    print("        candidatos: " + ", ".join(parecidos[:5]))
                    break
        problemas += faltan

    if problemas:
        print("\nHay {} nombres de prueba que no existen.".format(len(problemas)))
        return 1
    print("\nTodos los nombres citados existen.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))