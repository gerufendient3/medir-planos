"""Verifica el comportamiento del HATCH con isla interior y anillos concentricos.

Un area con hueco (p.ej. un patio dentro de una losa) no es la suma de sus
contornos. Este script comprueba que hace el motor.
"""
from pathlib import Path

import ezdxf

from app.medidor import medir

SALIDA = Path(__file__).resolve().parent.parent / "planos" / "casos" / "hatch_isla.dxf"


def main() -> int:
    d = ezdxf.new("R2010", setup=True)
    d.units = 6
    d.layers.add("Piso-Loseta", color=3)
    msp = d.modelspace()

    # contorno exterior 10x10 y contorno interior 4x4
    msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True,
                       dxfattribs={"layer": "Piso-Loseta"})
    msp.add_lwpolyline([(3, 3), (7, 3), (7, 7), (3, 7)], close=True,
                       dxfattribs={"layer": "Piso-Loseta"})

    d.saveas(SALIDA)
    r = medir(SALIDA)
    print("hatch_isla.dxf")
    for m in r["mediciones"]:
        print("  {} {} {}".format(m["capa"], m["cantidad"], m["unidades"]))
    print()
    print("area solida (10x10)          = 100")
    print("area con isla (100 - 4x4)     = 84")
    print("area suma de ambos contornos  = 100 + 16 = 116")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())