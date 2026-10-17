"""Repara doble codificacion UTF-8 en archivos de texto del proyecto.

Un Set-Content de PowerShell con la codificacion por defecto puede escribir
UTF-8 leido como latin-1, dejando cada vocal acentuada con un caracter
extra delante. Este script las revierte sin tocar el resto del archivo.

Este archivo se salta a si mismo a proposito: su docstring describe el
defecto y contendria el patron literal, asi que se repararia sin querer.

Uso:  python scripts/reparar_utf8.py <archivo> [...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

YO = Path(__file__).name

# Un caracter como U+00C3 seguido de un byte de continuacion UTF-8 es la
# huella de la doble codificacion: en latin-1, la vocal acentuada (dos
# bytes, por ejemplo C3 B3) reinterpretada como texto produce esa pareja.
MOJIBAKE = re.compile(r"[\u00c2\u00c3\u00c4\u00c5][\u0080-\u00bf]")


def reparar(texto: str) -> tuple[str, int]:
    n = 0

    def sub(m):
        nonlocal n
        n += 1
        return m.group(0).encode("latin-1").decode("utf-8")

    return MOJIBAKE.sub(sub, texto), n


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    for nombre in argv:
        ruta = Path(nombre)
        if ruta.name == YO:
            print("{}: omitido (es este mismo archivo)".format(ruta))
            continue
        original = ruta.read_text(encoding="utf-8-sig")
        nuevo, n = reparar(original)
        if n:
            ruta.write_text(nuevo, encoding="utf-8", newline="\n")
        print("{}: {} secuencia(s) reparada(s)".format(ruta, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))