"""Genera un DXF por cada caso limite de un plano real.

Casos cubiertos:
  bulge        polilinea con arco: get_points() ignoraria el arco
  abierta      polilinea de 3 puntos que parece cerrada pero no lo esta
  bloques      INSERT sin explotar (contactos, luminarias)
  mm           $INSUNITS = 4 (milimetros)
  duplicado    geometria repetida y superpuesta en la misma capa
  texto_cotas  TEXT y DIMENSION en capa de muros
  capas_limpas acentos, espacios, guiones, mayusculas mezcladas
"""
from __future__ import annotations

from pathlib import Path

import ezdxf

SALIDA = Path(__file__).resolve().parent.parent / "planos" / "casos"


def _doc(capas):
    d = ezdxf.new("R2010", setup=True)
    d.units = 6  # metros
    for n, c in capas:
        d.layers.add(n, color=c)
    return d


def caso_bulge() -> None:
    """Rectangulo 4x3 m con un semicirculo (bulge) sobre el lado derecho.

    En DXF el bulge de un vertice afecta al segmento QUE INICIA en ese
    vertice. bulge=1 equivale a un arco de 180 grados.

    Puntos: (4,0,b=1) -> (4,3) -> (0,3) -> (0,0)
    El arco parte de (4,0) hacia (4,3): cuerda 3 m, radio 1.5 m, y el
    semicirculo se abre hacia +x (fuera del rectangulo).

    area     = 4*3 + pi*1.5^2/2 = 12 + 3.5343 = 15.5343 m2
    perimetro= (14 - 3) + pi*1.5 = 11 + 4.7124 = 15.7124 m
    """
    d = _doc([("Piso-Loseta", 3)])
    msp = d.modelspace()
    pts = [(4, 0, 1.0), (4, 3), (0, 3), (0, 0)]
    msp.add_lwpolyline(pts, format="xyb", close=True, dxfattribs={"layer": "Piso-Loseta"})
    d.saveas(SALIDA / "bulge.dxf")


def caso_abierta() -> None:
    """Polilinea de 4 puntos que围ne un rectangulo pero NO esta cerrada."""
    d = _doc([("Piso-Loseta", 3)])
    msp = d.modelspace()
    pts = [(0, 0), (5, 0), (5, 4), (0, 4)]  # los ultimos dos puntos, sin cerrar
    msp.add_lwpolyline(pts, format="xy", close=False, dxfattribs={"layer": "Piso-Loseta"})
    d.saveas(SALIDA / "abierta.dxf")


def caso_bloques() -> None:
    """Contactos y luminarias como INSERT, patron real de instalaciones."""
    d = _doc([("ELEC-CONTACTO", 30), ("LAMPARA-PENDIENTE", 2)])
    msp = d.modelspace()

    # Bloque 'CONTACTO': un punto + un circulo pequeño, se explota en 3 contactos.
    blk = d.blocks.new("CONTACTO")
    blk.add_point((0, 0))
    blk.add_circle((0.1, 0), 0.05)
    blk.add_lwpolyline([(0, 0), (0.15, 0)], dxfattribs={"layer": "0"})

    for x in (1.0, 3.0, 5.0):
        msp.add_blockref("CONTACTO", (x, 2.0), dxfattribs={"layer": "ELEC-CONTACTO"})

    # Bloque 'LAMPARA' en otra capa
    blk2 = d.blocks.new("LAMPARA")
    blk2.add_circle((0, 0), 0.15)
    blk2.add_line((-0.3, 0), (0.3, 0))
    for x in (2.0, 6.0):
        msp.add_blockref("LAMPARA", (x, 4.0), dxfattribs={"layer": "LAMPARA-PENDIENTE"})

    d.saveas(SALIDA / "bloques.dxf")


def caso_mm() -> None:
    """Mismo rectangulo 4x3 pero declarado en MILIMETROS: 4000x3000."""
    d = _doc([("Piso-Loseta", 3)])
    d.units = 4  # mm
    msp = d.modelspace()
    msp.add_lwpolyline([(0, 0), (4000, 0), (4000, 3000), (0, 3000)], close=True,
                       dxfattribs={"layer": "Piso-Loseta"})
    d.saveas(SALIDA / "milimetros.dxf")


def caso_duplicado() -> None:
    """La misma polilinea repetida 3 veces en la misma capa."""
    d = _doc([("Piso-Loseta", 3)])
    msp = d.modelspace()
    for _ in range(3):
        msp.add_lwpolyline([(0, 0), (6, 0), (6, 4), (0, 4)], close=True,
                           dxfattribs={"layer": "Piso-Loseta"})
    d.saveas(SALIDA / "duplicado.dxf")


def caso_texto_cotas() -> None:
    """TEXT, MTEXT y DIMENSION dentro de una capa de muros."""
    d = _doc([("MURO-BLOCK-15CM", 7)])
    msp = d.modelspace()
    msp.add_lwpolyline([(0, 0), (6, 0), (6, 3), (0, 3)], close=True,
                       dxfattribs={"layer": "MURO-BLOCK-15CM"})
    msp.add_text("MURO BLOCK 15 CM", height=0.25,
                 dxfattribs={"layer": "MURO-BLOCK-15CM"}).set_placement((1, 1))
    msp.add_mtext("NOTA: VER PLANO ESTRUCTURAL",
                  dxfattribs={"layer": "MURO-BLOCK-15CM"}).set_location((2, 2))
    dim = msp.add_linear_dim(base=(0, -1), p1=(0, 0), p2=(6, 0),
                             dxfattribs={"layer": "MURO-BLOCK-15CM"})
    dim.render()
    d.saveas(SALIDA / "texto_cotas.dxf")


def caso_capas_limpas() -> None:
    """Acentos, espacios, guiones y mayusculas mezcladas."""
    capas = ["Muro de Block 15 cm", "PISO-LOSETA", "cielo de  yeso", "TUBO-HID",
             "cANALización eléctrica"]
    d = _doc([(c, i + 1) for i, c in enumerate(capas)])
    msp = d.modelspace()
    msp.add_lwpolyline([(0, 0), (5, 0), (5, 4), (0, 4)], close=True,
                       dxfattribs={"layer": "Muro de Block 15 cm"})
    msp.add_lwpolyline([(0, 5), (8, 5), (8, 9), (0, 9)], close=True,
                       dxfattribs={"layer": "PISO-LOSETA"})
    msp.add_lwpolyline([(0, 10), (12, 10), (12, 14), (0, 14)], close=True,
                       dxfattribs={"layer": "cielo de  yeso"})
    msp.add_lwpolyline([(0, 15), (4, 15), (4, 20), (0, 20)], close=True,
                       dxfattribs={"layer": "TUBO-HID"})
    msp.add_lwpolyline([(0, 21), (10, 21), (10, 26), (0, 26)], close=True,
                       dxfattribs={"layer": "cANALización eléctrica"})
    d.saveas(SALIDA / "capas_limpas.dxf")


def caso_hatch_isla() -> None:
    """HATCH real con isla: una losa de 10x10 con un patio de 4x4.

    DXF marca el contorno del patio como isla (is_external=False), asi que
    el area correcta es 100 - 16 = 84 m2, no 116.

    Este es el caso que un plano de obra real produce (patio, jardin, cubeta
    en una losa) y donde sumar contornos da un numero falso.
    """
    d = _doc([("Piso-Loseta", 3)])
    msp = d.modelspace()
    # Solo el HATCH: es como un plano real representa una losa con patio.
    hatch = msp.add_hatch(color=3, dxfattribs={"layer": "Piso-Loseta"})
    # flags: external(1) marca el contorno exterior. Sin ese bit es una isla.
    # ezdxf añade el bit de polilinea al escribir, asi que lo que se lee es 3 y 2.
    hatch.paths.add_polyline_path([(0, 0), (10, 0), (10, 10), (0, 10)],
                                  is_closed=True, flags=1)
    hatch.paths.add_polyline_path([(3, 3), (3, 7), (7, 7), (7, 3)],
                                  is_closed=True, flags=0)
    hatch.set_pattern_fill("SOLID")
    d.saveas(SALIDA / "hatch_isla.dxf")


CASOS = {
    "bulge.dxf": caso_bulge,
    "abierta.dxf": caso_abierta,
    "bloques.dxf": caso_bloques,
    "milimetros.dxf": caso_mm,
    "duplicado.dxf": caso_duplicado,
    "texto_cotas.dxf": caso_texto_cotas,
    "capas_limpas.dxf": caso_capas_limpas,
    "hatch_isla.dxf": caso_hatch_isla,
}


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for nombre, fn in CASOS.items():
        fn()
        print(f"generado {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())