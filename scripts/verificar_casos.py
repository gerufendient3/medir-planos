"""Comprueba que docs/CASOS.md no se haya quedado viejo.

El índice de casos es fácil de dejar atrás: se escriben 99 casos, luego se
añaden pruebas nuevas y el documento sigue diciendo 99. Aquí se verifica que

  1. cada test nombrado en el documento exista de verdad en la suite;
  2. la cifra de la cabecera corresponda a las filas realmente listadas;
  3. la cifra no se confunda con el total de la suite.

Uso:  python scripts/verificar_casos.py
Sale con código 1 si algo no cuadra.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOC = RAIZ / "docs" / "CASOS.md"

# | 1.1 | descripción | PASA | `test_algo` |
FILA = re.compile(r"^\|\s*(\d+\.\d+)\s*\|(.+)\|\s*([A-ZÁÉÍÓÚÑ ]+)\s*\|\s*`([^`]+)`\s*\|")


def tests_de_la_suite() -> set[str]:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
        cwd=str(RAIZ), capture_output=True, text=True)
    nombres = set()
    for linea in r.stdout.splitlines():
        if "::" in linea:
            nombres.add(linea.split("::")[-1].strip())
    return nombres


def main() -> int:
    texto = DOC.read_text(encoding="utf-8")
    existentes = tests_de_la_suite()

    filas = []
    for linea in texto.splitlines():
        m = FILA.match(linea)
        if m:
            filas.append(m.groups())

    print("Filas de caso en CASOS.md:", len(filas))

    problemas = []

    # 1. cada test nombrado existe
    faltantes = [(num, nombre) for num, _desc, _est, nombre in filas
                 if nombre not in existentes]
    for num, nombre in faltantes:
        problemas.append("CASO {} nombra `{}` y ese test no existe".format(
            num, nombre))
    if not faltantes:
        print("Los {} tests nombrados existen en la suite.".format(len(filas)))

    # 2. estados honestos
    for num, desc, estado, _nombre in filas:
        if estado.strip() != "PASA":
            problemas.append("CASO {} ({}) tiene estado '{}', no PASA".format(
                num, desc.strip()[:40], estado.strip()))

    # 3. la cabecera
    m = re.search(r"Resultado global:\s*\*\*(\d+)\s*casos,\s*(\d+)\s*pasan",
                  texto)
    if not m:
        problemas.append("CASOS.md no tiene la línea 'Resultado global' "
                         "en el formato esperado")
    else:
        declarado, pasan = int(m.group(1)), int(m.group(2))
        if declarado != len(filas):
            problemas.append(
                "CASOS.md dice {} casos pero lista {} filas."
                .format(declarado, len(filas)))
        if pasan != len(filas):
            problemas.append(
                "CASOS.md dice que pasan {} pero lista {} casos."
                .format(pasan, len(filas)))
        if not problemas:
            print("La cabecera coincide con las filas: {} casos, {} pasan."
                  .format(declarado, pasan))

    total = len(existentes)
    print("La suite completa tiene {} tests; CASOS.md es un índice "
          "curado, no el total.".format(total))

    if problemas:
        print()
        print("PROBLEMAS ({}):".format(len(problemas)))
        for p in problemas:
            print("  -", p)
        return 1
    print()
    print("CASOS.md está al día.")
    return 0


if __name__ == "__main__":
    sys.exit(main())