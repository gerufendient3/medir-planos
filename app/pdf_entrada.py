"""Entrada PDF vectorial con pdfplumber.

DECISIONES Y SUS LIMITES (leer antes de usar):

1) PDF NO tiene capas. Solo hay trazos, rectangulos, curvas y texto, cada uno
   con un color y un grosor. El agrupamiento por COLOR es una heuristica, no
   una equivalencia con las capas de CAD. Una misma capa de CAD puede salir
   en varios colores y dos capas pueden salir del mismo color.

   Por eso este modulo devuelve grupos nombrados COLOR_<r>_<g>_<b> y NO
   intenta adivinar el concepto. El mapeo color -> concepto lo decide el
   usuario.

2) PDF NO conserva la escala del plano. Las coordenadas estan en puntos
   (1/72 de pulgada). Este modulo exige una escala explicita (pt por metro).
   Con escala 1.0 devuelve unidades de PDF, no metros, y lo advierte.

3) PDF escaneado NO se mide. Si la pagina es una imagen, se avisa y se
   devuelve sin mediciones. No hay OCR y no se intenta medir.

Licencia de la libreria: pdfplumber es MIT (depende de pdfminer.six, MIT).
Se descarto PyMuPDF por ser AGPL o comercial.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

# Umbral: si una pagina tiene esto o mas imagenes que trazos vectoriales,
# la consideramos escaneada.
UMBRAL_IMAGENES_POR_PAGINA = 1


class PdfNoVectorial(ValueError):
    """El PDF no contiene geometria vectorial medible."""


def _color_clave(obj: dict) -> str:
    """Clave de agrupamiento por color.

    Se prioriza el color de TRAZO (stroking) sobre el de relleno. En dibujo
    tecnico el relleno es siempre el mismo (blanco o 1.0) y el trazo es lo
    que codifica la capa: en un plano CAD ploteado, un rectangulo de piso
    lleva non_stroking_color=1.0 igual que los muros, pero stroking_color
    distinto. Usar el relleno agrupaba todo en un solo color.
    """
    c = obj.get("stroking_color")
    if c is None:
        c = obj.get("non_stroking_color")
    if c is None:
        return "SIN_COLOR"
    if isinstance(c, (int, float)):
        return "COLOR_{}".format(int(c))
    if isinstance(c, (list, tuple)):
        return "COLOR_" + "_".join(str(int(round(float(v)))) for v in c)
    return "COLOR_" + str(c)


def _es_envoltura(obj: dict, ancho_pagina: float, alto_pagina: float) -> bool:
    """La caja que ocupa toda la pagina casi nunca es geometria de obra."""
    return (abs(obj["width"] - ancho_pagina) < 1.0
            and abs(obj["height"] - alto_pagina) < 1.0)


def inspeccionar(path: str | Path) -> dict:
    """Diagnostica el PDF sin medir. Usado por tests y por la deteccion de
    escaneado."""
    import pdfplumber

    with pdfplumber.open(str(path)) as pdf:
        p0 = pdf.pages[0]
        informe = {
            "archivo": Path(path).name,
            "paginas": len(pdf.pages),
            "ancho_pt": round(p0.width, 2),
            "alto_pt": round(p0.height, 2),
            "lines": len(p0.lines),
            "rects": len(p0.rects),
            "curves": len(p0.curves),
            "chars": len(p0.chars),
            "images": len(p0.images),
            "vectorial": False,
            "advertencias": [],
        }

        vectoriales = informe["lines"] + informe["rects"] + informe["curves"]
        informe["objetos_vectoriales"] = vectoriales

        if vectoriales == 0 and informe["images"] > 0:
            informe["advertencias"].append(
                "PDF ESCANEADO: la pagina {} no tiene trazados, solo {} imagen(es). "
                "No se puede medir sin OCR, y este motor no hace OCR. "
                "Se requiere el DXF de origen o un PDF vectorial.".format(
                    informe["paginas"], informe["images"])
            )
        elif vectoriales == 0 and informe["chars"] > 0:
            informe["advertencias"].append(
                "PDF con texto pero sin geometria vectorial. No hay lineas ni "
                "curvas que medir."
            )
        else:
            informe["vectorial"] = True
            informe["advertencias"].append(
                "PDF VECTORIAL detectado: {} lineas, {} rectangulos, {} curvas. "
                "Aun no tiene escala: las coordenadas estan en puntos.".format(
                    informe["lines"], informe["rects"], informe["curves"])
            )

    return informe


def leer_grupos(path: str | Path) -> dict:
    """Agrupa la geometria vectorial de la primera pagina por color.

    Devuelve {"grupos": {nombre_color: {"rects": n, "lines": n, "curves": n,
              "bbox": (x0,y0,x1,y1), "objetos": [...]}}}
    """
    import pdfplumber

    with pdfplumber.open(str(path)) as pdf:
        pagina = pdf.pages[0]
        grupos: dict[str, dict] = defaultdict(
            lambda: {"rects": 0, "lines": 0, "curves": 0, "objetos": [],
                     "bbox": None}
        )

        objetos = ([("rect", o) for o in pagina.rects]
                   + [("line", o) for o in pagina.lines]
                   + [("curve", o) for o in pagina.curves])

        for tipo, o in objetos:
            if _es_envoltura(o, pagina.width, pagina.height):
                continue
            nombre = _color_clave(o)
            g = grupos[nombre]
            g[tipo + "s"] += 1
            g["objetos"].append({"tipo": tipo, **{
                k: o[k] for k in ("x0", "y0", "x1", "y1", "width", "height")
                if k in o
            }})
            x0, y0, x1, y1 = o["x0"], o["y0"], o.get("x1", o["x0"]), o.get("y1", o["y0"])
            if g["bbox"] is None:
                g["bbox"] = [x0, y0, x1, y1]
            else:
                b = g["bbox"]
                g["bbox"] = [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]

    return {"grupos": dict(grupos)}


def medir_pdf(path: str | Path, pt_por_metro: float = 1.0,
              pagina_indice: int = 0) -> dict:
    """Mide un PDF vectorial.

    pt_por_metro: escala explicita. 1.0 significa "cada punto es una unidad",
    lo que NO son metros. El modulo avisa siempre de esto.

    Devuelve el mismo formato que app.medidor.medir() mas las advertencias
    propias del formato PDF.
    """
    informe = inspeccionar(path)

    if not informe["vectorial"]:
        return {
            "archivo": informe["archivo"],
            "formato": "pdf",
            "escala_aplicada": pt_por_metro,
            "mediciones": [],
            "entidades_omitidas": [],
            "entidades_incompatibles": [],
            "solapes": [],
            "diagnostico": {
                "unidades_codigo": 0,
                "unidades_nombre": "puntos PDF",
                "factor_a_metros": None,
                "advertencias": informe["advertencias"],
            },
        }

    import pdfplumber

    with pdfplumber.open(str(path)) as pdf:
        pagina = pdf.pages[pagina_indice]
        objetos = ([("rect", o) for o in pagina.rects]
                   + [("line", o) for o in pagina.lines]
                   + [("curve", o) for o in pagina.curves])

        # Acumula por color: areas de rectangulos, longitudes de lineas.
        # pdfplumber no distingue un "rectangulo cerrado" de una polilinea, asi
        # que cada rect cuenta como superficie.
        acum: dict[str, dict] = defaultdict(
            lambda: {"m2": 0.0, "m": 0.0, "n": 0, "handles": [], "tipos": set()}
        )

        for idx, (tipo, o) in enumerate(objetos):
            if _es_envoltura(o, pagina.width, pagina.height):
                continue
            nombre = _color_clave(o)
            g = acum[nombre]
            g["handles"].append("p{}-{}".format(pagina_indice, idx))
            g["tipos"].add(tipo.upper())

            if tipo == "rect":
                ancho = abs(o["x1"] - o["x0"]) if "x1" in o else o["width"]
                alto = abs(o["y1"] - o["y0"]) if "y1" in o else o["height"]
                g["m2"] += ancho * alto
                g["m"] += 2 * (ancho + alto)
                g["n"] += 1
            elif tipo == "line":
                largo = ((o["x1"] - o["x0"]) ** 2 + (o["y1"] - o["y0"]) ** 2) ** 0.5
                g["m"] += largo
                g["n"] += 1
            else:  # curve
                pts = o.get("pts") or []
                largo = 0.0
                for a, b in zip(pts, pts[1:]):
                    largo += ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                g["m"] += largo
                g["n"] += 1

    # pt_por_metros = cuantos puntos PDF equivalen a un metro.
    # Puesto en metros = puntos / pt_por_metro.
    factor_lineal = 1.0 / pt_por_metro if pt_por_metro else 1.0

    mediciones = []
    for nombre, g in sorted(acum.items()):
        if g["m2"] > 0:
            mediciones.append({
                "capa": nombre,
                "unidades": "m2",
                "cantidad": round(g["m2"] * (factor_lineal ** 2), 4),
                "handles": g["handles"], "tipos": sorted(g["tipos"]),
                "n_entidades": g["n"],
            })
        if g["m"] > 0:
            mediciones.append({
                "capa": nombre,
                "unidades": "m",
                "cantidad": round(g["m"] * factor_lineal, 4),
                "handles": g["handles"], "tipos": sorted(g["tipos"]),
                "n_entidades": g["n"],
            })

    advertencias = list(informe["advertencias"])
    advertencias.append(
        "PDF NO TIENE CAPAS. Los grupos son por COLOR y una heuristica: "
        "una capa de CAD puede salir en varios colores y dos capas pueden "
        "salir del mismo color. Mapea cada grupo a un concepto a mano."
    )
    if pt_por_metro == 1.0:
        advertencias.append(
            "ESCALA = 1.0: las cantidades estan en PUNTOS PDF, no en metros. "
            "Para metros indica pt_por_metro."
        )
    else:
        advertencias.append(
            "Escala aplicada: {} puntos por metro. El plano no declara su "
            "propia escala; este valor lo definiste tu.".format(pt_por_metro)
        )

    return {
        "archivo": informe["archivo"],
        "formato": "pdf",
        "escala_aplicada": pt_por_metro,
        "mediciones": mediciones,
        "entidades_omitidas": [],
        "entidades_incompatibles": [],
        "solapes": [],
        "diagnostico": {
            "unidades_codigo": 0,
            "unidades_nombre": "puntos PDF",
            "factor_a_metros": pt_por_metro,
            "advertencias": advertencias,
        },
    }