"""Comprueba que procesar un plano no deje archivos en TEMP.

Es la promesa de privacidad mas fuerte del proyecto y la mas facil de
romper sin querer: basta con que un `open()` se quede fuera del `finally`.
Esta comprobacion se corre sola en CI, despues de la suite completa.

Mide el contenido de TEMP antes y despues de correr pytest, de modo que
atribuye a la app cualquier archivo nuevo. Filtra los que crea el propio
pytest, que es lo unico que se sabe que aparece sin relacion con la app.

Uso:  python scripts/comprobar_temporal.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# pytest crea caches propias en TEMP. No son de la app.
DE_PYTEST = (".pytest_cache", "pytest-of-", "tmp", ".tmp")


def _de_pycharm(nombre: str) -> bool:
    return any(nombre.startswith(p) for p in DE_PYTEST)


def main() -> int:
    temp = Path(tempfile.gettempdir())
    antes = {p.name for p in temp.iterdir()}

    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q"],
        cwd=str(RAIZ), capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(sin salida)")

    despues = {p.name for p in temp.iterdir()}
    nuevas = {n for n in despues - antes if not _de_pycharm(n)}

    if nuevas:
        print("FALLO: la app dejo {} archivo(s) en {}:".format(
            len(nuevas), temp))
        for n in sorted(nuevas):
            print("  -", n)
        return 1

    print("TEMP limpio: {} archivos antes, {} despues, ninguno nuevo de la app."
          .format(len(antes), len(despues)))
    return 0 if r.returncode == 0 else r.returncode


if __name__ == "__main__":
    sys.exit(main())