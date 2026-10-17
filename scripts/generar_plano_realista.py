"""Genera un DXF que imita las Deficiencias de un plano real, no uno sintetico limpio.

Este archivo existe para hacer fallar el pipeline de forma barata: nombres de capa
inconsistentes, entidades en bloques, escala distinta a la esperada y una capa sin
catalogo. Un plano que sale perfecto de un generador no prueba nada.
"""
from __future__ import annotations

from pathlib import Path

import ezdxf

SALIDA = Path(__file__).resolve().parent.parent / "planos" / "plano_realista.dxf"

CAPAS = [
    # Nombre sucio, con acentos y guiones bajos, como en la practica real.
    ("MURO-BLOCK-15CM", 7), ("Muro_Bloque_Interior", 7),
    ("Piso-Loseta", 3), ("PISO-VINILICO", 3),
    ("CIELO DE YESO", 2),
    ("A-C-01", 5),  # tablero de distribucion, nombre opaco
    ("Canal-Electrico-Piso", 30), ("LAMPARA-PENDIENTE", 2),
    ("TUBO-HID", 140), ("Coladera", 4),
    ("VENTANA-A1", 8), ("CANCEL-PVC", 8),
    ("CUBIERTAS-MUROS", 9),
    ("REFORZADOS-ESTRUCTURA", 6),  # capa que el catalogo no cubre
]


def main() -> int:
    doc = ezdxf.new("R2010", setup=True)
    # $INSUNITS: 6 = metros. Ojo: 4 es MILIMETROS.
    doc.units = 6
    for nombre, color in CAPAS:
        doc.layers.add(nombre, color=color)
    msp = doc.modelspace()

    def rect(capa, x0, y0, x1, y1):
        msp.add_lwpolyline([(x0,y0),(x1,y0),(x1,y1),(x0,y1)], close=True,
                           dxfattribs={"layer": capa})

    # Envolvente 12 x 9 m (metros, escala correcta)
    rect("MURO-BLOCK-15CM", 0, 0, 12, 9)
    rect("REFORZADOS-ESTRURA", 0, 0, 12, 9)  # typo intencional: capa distinta

    # Tabique interior que cruza
    msp.add_line((6, 0), (6, 9), dxfattribs={"layer": "Muro_Bloque_Interior"})

    # Pisos por paños
    rect("Piso-Loseta", 0, 0, 6, 4.5)
    rect("PISO-VINILICO", 6, 0, 12, 9)

    # Cielo (superficie completa)
    rect("CIELO DE YESO", 0, 0, 12, 9)

    # Tablero como punto, no poligono (debe contar 1 pza)
    msp.add_point((0.5, 0.5), dxfattribs={"layer": "A-C-01"})

    # Canalizacion como polilinea abierta (debe dar metros)
    msp.add_lwpolyline([(0.5,0.5),(0.5,6),(6,6),(6,2),(11,2)],
                       dxfattribs={"layer": "Canal-Electrico-Piso"})

    # Dos luminarias
    msp.add_circle((3, 4.5), 0.15, dxfattribs={"layer": "LAMPARA-PENDIENTE"})
    msp.add_circle((9, 4.5), 0.15, dxfattribs={"layer": "LAMPARA-PENDIENTE"})

    # Tubería hidraulica
    msp.add_lwpolyline([(0,9),(4,9),(4,5),(9,5),(9,2)],
                       dxfattribs={"layer": "TUBO-HID"})
    msp.add_circle((4, 5), 0.08, dxfattribs={"layer": "Coladera"})

    # Carpinteria: ventanas como circulos pequenos (simplificado)
    for x in (3, 9):
        msp.add_circle((x, 9), 0.3, dxfattribs={"layer": "VENTANA-A1"})

    doc.saveas(SALIDA)
    print(f"generado {SALIDA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())