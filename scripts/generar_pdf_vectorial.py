"""Genera un PDF VECTORIAL de plano a partir de un DXF con el que sabemos la verdad.

Los dos PDFs reales descargados de Wikimedia Commons resultaron ser imagenes
rasterizadas (0 lines, 0 rects, 0 curves). Eso no prueba la ruta vectorial.

Este generador produce un PDF vectorial cuya geometria conocemos exactamente:
  - capa MURO-PISO   : rectangulo 8 x 6 m          -> 48 m2
  - capa MURO-TABIQUE: linea de 6 m (tabique interior) -> 6 m
  - capa PISO-LOSETA : rectangulo 4 x 3 m          -> 12 m2

Se usa el backend matplotlib de ezdxf (BSD) porque ezdxf lo documenta como
backend oficial y su salida PDF es vectorial (no rasteriza).

Licencia del fixture: generado por este proyecto, dominio de la prueba.
"""
from __future__ import annotations

from pathlib import Path

import ezdxf

SALIDA = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "pdf"
DXF_ORIGEN = Path(__file__).resolve().parent.parent / "planos" / "vectorial_origen.dxf"


def crear_dxf(ruta: Path) -> None:
    doc = ezdxf.new("R2010", setup=True)
    doc.units = 6  # metros
    for nombre, color in [("MURO-PISO", 7), ("MURO-TABIQUE", 7), ("PISO-LOSETA", 3)]:
        doc.layers.add(nombre, color=color)
    msp = doc.modelspace()

    # 8 x 6 m -> 48 m2
    msp.add_lwpolyline([(0, 0), (8, 0), (8, 6), (0, 6)], close=True,
                       dxfattribs={"layer": "MURO-PISO"})
    # tabique interior de 6 m
    msp.add_line((4, 0), (4, 6), dxfattribs={"layer": "MURO-TABIQUE"})
    # 4 x 3 m -> 12 m2
    msp.add_lwpolyline([(0, 0), (4, 0), (4, 3), (0, 3)], close=True,
                       dxfattribs={"layer": "PISO-LOSETA"})

    doc.saveas(ruta)


def crear_pdf(dxf: Path, pdf: Path) -> None:
    """Dibuja el DXF a PDF vectorial con el backend matplotlib de ezdxf."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

    doc = ezdxf.readfile(str(dxf))
    msp = doc.modelspace()

    # figsize en pulgadas a 72 dpi => 1 pulgada = 72 puntos, escala 1:1 en el
    # PDF salvo por el factor de escala que apliquemos.
    fig = plt.figure(figsize=(8.5, 6.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp, finalize=True)

    # savefig a PDF produce salida VECTORIAL (no rasteriza las lineas).
    fig.savefig(pdf, format="pdf")
    plt.close(fig)


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    crear_dxf(DXF_ORIGEN)
    crear_pdf(DXF_ORIGEN, SALIDA / "vectorial_desde_dxf.pdf")
    print("generado DXF  :", DXF_ORIGEN.name)
    print("generado PDF  : vectorial_desde_dxf.pdf")
    print("verdad conocida: MURO-PISO 48 m2 | MURO-TABIQUE 6 m | PISO-LOSETA 12 m2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())