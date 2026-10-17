"""Genera planos DXF sintéticos de prueba, con la organización por capas de un plano real.

Uso: python scripts/generar_planos.py
Salida: planos/*.dxf
"""
from __future__ import annotations

from pathlib import Path

import ezdxf

SALIDA = Path(__file__).resolve().parent.parent / "planos"

CAPAS = {
    "MUROS": 7,
    "PISOS": 3,
    "MUERTOS": 1,
    "ESCALERA": 4,
    "ELEC-TABLERO": 5,
    "ELEC-CANAL": 30,
    "ELEC-LAMP": 2,
    "PLOM-TUBO": 140,
    "PLOM-COLADERO": 4,
    "HVAC-DUCT": 6,
    "VENTANA": 8,
    "CUBIERTA": 9,
    "TEXTO-COTA": 250,
}


def nuevo_doc() -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2010", setup=True)
    # $INSUNITS: 6 = metros. Ojo: 4 es MILIMETROS. La geometria de estos
    # planos esta en metros, asi que el archivo debe declararlo como tal.
    doc.units = 6
    for nombre, color in CAPAS.items():
        doc.layers.add(nombre, color=color)
    return doc


def rect(ac, x0, y0, x1, y1, capa):
    ac.add_lwpolyline(
        [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
        close=True,
        dxfattribs={"layer": capa},
    )


def main() -> int:
    SALIDA.mkdir(exist_ok=True)

    # --- Plano 1: planta baja de vivienda 8x6 m, tabique interior y 3 paños de piso
    doc = nuevo_doc()
    msp = doc.modelspace()
    rect(msp, 0, 0, 8, 6, "MUROS")
    msp.add_line((4, 0), (4, 6), dxfattribs={"layer": "MUROS"})
    for y0, y1, nombre in [(0, 2.5, "PISO-A"), (2.5, 4.0, "PISO-B"), (4.0, 6.0, "PISO-C")]:
        rect(msp, 0, y0, 8, y1, "PISOS")
        msp.add_text(
            nombre,
            height=0.2,
            dxfattribs={"layer": "PISOS"},
        ).set_placement((0.3, y0 + 0.3))
    doc.saveas(SALIDA / "planta_baja_vivienda.dxf")

    # --- Plano 2: planta de instalaciones electricas (canalizacion y luminarias)
    doc = nuevo_doc()
    msp = doc.modelspace()
    rect(msp, 0, 0, 8, 6, "MUROS")
    msp.add_lwpolyline([(0, 6), (2, 6), (2, 0)], dxfattribs={"layer": "ELEC-CANAL"})
    msp.add_lwpolyline([(2, 0), (6, 0), (6, 6)], dxfattribs={"layer": "ELEC-CANAL"})
    msp.add_line((0, 0), (0, 6), dxfattribs={"layer": "ELEC-TABLERO"})
    for cx, cy in [(2, 3), (6, 3), (4, 1.5), (4, 4.5)]:
        msp.add_circle((cx, cy), 0.15, dxfattribs={"layer": "ELEC-LAMP"})
    doc.saveas(SALIDA / "planta_electrica.dxf")

    # --- Plano 3: planta hidraulica
    doc = nuevo_doc()
    msp = doc.modelspace()
    rect(msp, 0, 0, 8, 6, "MUROS")
    msp.add_lwpolyline([(0, 6), (3, 6), (3, 3), (8, 3)], dxfattribs={"layer": "PLOM-TUBO"})
    msp.add_lwpolyline([(3, 3), (3, 1), (6, 1)], dxfattribs={"layer": "PLOM-TUBO"})
    for cx, cy in [(3, 6), (8, 3), (6, 1)]:
        msp.add_circle((cx, cy), 0.08, dxfattribs={"layer": "PLOM-COLADERO"})
    doc.saveas(SALIDA / "planta_hidraulica.dxf")

    # --- Plano 4: cubierta con pendientes
    doc = nuevo_doc()
    msp = doc.modelspace()
    rect(msp, 0, 0, 8, 6, "CUBIERTA")
    for i in range(1, 8):
        msp.add_line((i, 0), (i, 6), dxfattribs={"layer": "CUBIERTA"})
    for j in range(1, 6):
        msp.add_line((0, j), (8, j), dxfattribs={"layer": "CUBIERTA"})
    doc.saveas(SALIDA / "planta_cubierta.dxf")

    for p in sorted(SALIDA.glob("*.dxf")):
        print(f"generado {p.name} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())