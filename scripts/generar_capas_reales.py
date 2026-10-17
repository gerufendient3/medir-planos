"""Contraste del catalogo contra nomenclatura REAL de despachos.

Este no es un plano de pruebas: reproduce como una architectural oficina
nombra sus capas en la practica. Los nombres vienen de las convenciones
habituales en_autoCAD para obra:

  - prefijos de disciplina: A-, ARQ-, E-, ELE-, HID-, SAN-, MEC-, EST-
  - sufijos de tipo: MURO, PISO, LOSETA, CIELO, TUBO, CABLE, LAMP, etc.
  - sin separacion: MUROS_PISO_2D, ELE-TAB-DIST
  - abreviaturas: TAB, PZA, VENT, PT, AL
  - capas por planta: PLANTA_ALTA, NIVEL_02
  - capas de anotacion mezcladas: A-PLANTA-MUROS, NOTAS-MUROS
  - capas de estructura que NO son conceptos de acabado

Este archivo mide que tan bien cubre el catalogo esas capas reales.
"""
from __future__ import annotations

from pathlib import Path

import ezdxf

SALIDA = Path(__file__).resolve().parent.parent / "planos" / "capas_reales.dxf"

# (capa, tipo_geom, color, nota)
CAPAS = [
    ("A-ESTRUCT-MUROS", "poly", 7, "muros de carga"),
    ("A-ESTRUCT-COLUMNAS", "line", 7, "columnas: NO es concepto de acabado"),
    ("A-PLANTA-MUROS-PT", "poly", 7, "muros de PT"),
    ("A-PLANTA-MUROS-TAB", "poly", 7, "tabiques"),
    ("A-PLANTA-PISOS-LOSETA", "poly", 3, "piso loseta"),
    ("A-PLANTA-PISOS-PORCELANATO", "poly", 3, "porcelanato: el catalogo no lo tiene"),
    ("A-PLANTA-CIELOS-YESO", "poly", 2, "cielo de yeso"),
    ("ARQ-MUROS-ACABADO", "poly", 7, "muro acabado: ambiguo"),
    ("ARQ-PUERTAS-VENTANAS", "circle", 8, "puerta y ventana en una sola capa"),
    ("ELE-TAB-DIST", "point", 5, "tablero"),
    ("ELE-TUBO-CONDUIT", "poly_open", 30, "canalizacion"),
    ("ELE-CABLE-AL", "poly_open", 30, "cable de alimentacion"),
    ("ELE-LAMP-TIPO-A", "circle", 2, "luminarias"),
    ("ELE-CONTACTO-DUPLEX", "circle", 4, "contactos: el catalogo no lo tiene"),
    ("HID-TUBO-AGUA-FRIA", "poly_open", 140, "tuberia fria"),
    ("HID-TUBO-AGUA-CALIENTE", "poly_open", 140, "tuberia caliente"),
    ("HID-COLADERA-BANO", "circle", 4, "coladeras"),
    ("MEC-DUCTO-SUP", "poly", 6, "ducto: el catalogo no lo tiene"),
    ("PLANTA_ALTA", "poly", 8, "capa por planta, sin contenido semantico"),
    ("NOTAS-MUROS", "text", 250, "capa de anotacion mezclada"),
]


def main() -> int:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = 6  # metros
    for capa, _, color, _ in CAPAS:
        doc.layers.add(capa, color=color)
    msp = doc.modelspace()

    for i, (capa, tipo, _, nota) in enumerate(CAPAS):
        x = (i % 5) * 12.0
        y = (i // 5) * 10.0
        if tipo == "poly":
            msp.add_lwpolyline([(x, y), (x + 6, y), (x + 6, y + 4), (x, y + 4)],
                               close=True, dxfattribs={"layer": capa})
        elif tipo == "poly_open":
            msp.add_lwpolyline([(x, y), (x + 5, y), (x + 5, y + 3)],
                               dxfattribs={"layer": capa})
        elif tipo == "line":
            msp.add_line((x, y), (x, y + 4), dxfattribs={"layer": capa})
        elif tipo == "point":
            msp.add_point((x, y), dxfattribs={"layer": capa})
        elif tipo == "circle":
            msp.add_circle((x, y), 0.15, dxfattribs={"layer": capa})
        elif tipo == "text":
            msp.add_text("NOTA", height=0.3,
                         dxfattribs={"layer": capa}).set_placement((x, y))

    doc.saveas(SALIDA)
    print("generado {} con {} capas".format(SALIDA.name, len(CAPAS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())