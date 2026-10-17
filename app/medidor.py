"""Motor de medicion: agrega entidades por capa respetando la compatibilidad
entidad-concepto.

Regla central: una entidad solo se contabiliza si su forma natural (m, m2, pza)
es compatible con la unidad del concepto mapeado a esa capa. Lo que no es
compatible se reporta con su handle y NO se agrega en silencio.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import ezdxf

from app.entidades import (
    Insignificante,
    EntidadMedida,
    extraer,
    extraer_bloques,
    medir_entidad,
)

# Formas naturales de cada tipo de entidad.
#   LINE / polilinea abierta -> longitud
#   polilinea cerrada / hatch -> area
#   INSERT / POINT / circulo pequeno -> pieza
FORMA_ESPERADA = {
    "LINE": "m",
    "ARC": "m",
    "ELLIPSE": "m",
    "LWPOLYLINE": "m",     # se resuelve a m2 si esta cerrada
    "POLYLINE": "m",
    "HATCH": "m2",
    "INSERT": "pza",
    "POINT": "pza",
    "CIRCLE": "pza",       # se resuelve a m2 si el radio es grande
}

# Compatibilidad unidad-concepto <-> forma natural de entidad.
# Una pieza tambien acepta longitud: un contacto en un muro se cuenta por metro
# de muro si el concepto lo pide. Se permite explicitamente.
COMPATIBLE = {
    "m": {"m"},
    "ml": {"ml", "m"},   # metro lineal acepta trazo recto y desarrollo
    "m2": {"m2"},
    "pza": {"pza", "m"},
}


@dataclass
class MedicionCapa:
    capa: str
    unidad: str
    cantidad: float
    handles: list[str] = field(default_factory=list)
    tipos: list[str] = field(default_factory=list)


@dataclass
class Medicion:  # vista compatible con la API anterior
    capa: str
    unidades: str
    cantidad: float
    detalle: dict = field(default_factory=dict)


# Diferencia minima (m2) para considerar que dos geometrias se solapan de
# verdad y no que es ruido de redondeo.
TOLERANCIA_SOLAPE_M2 = 1e-6


def _unir_areas(ems: list) -> tuple[float | None, float]:
    """Devuelve (area_union, suma_de_areas) de las entidades con geometria 2D.

    Si algo falla devuelve (None, suma): es preferible sumar con un aviso a
    perder la medicion.
    """
    from shapely.ops import unary_union

    polys = []
    for e in ems:
        geom = getattr(e, "geometria", None)
        if geom is None or geom.is_empty:
            continue
        try:
            p = geom if geom.is_valid else geom.buffer(0)
            if not p.is_empty:
                polys.append(p)
        except Exception:
            continue

    suma = sum(p.area for p in polys)
    if not polys:
        return None, 0.0
    if len(polys) == 1:
        return suma, suma
    try:
        return unary_union(polys).area, suma
    except Exception:
        return None, suma


def _compatibles(unidad_concepto: str | None, forma: str) -> bool:
    if unidad_concepto is None:
        # Sin concepto mapeado no hay restriction: se acepta y se avisara luego.
        return True
    return forma in COMPATIBLE.get(unidad_concepto, set())


def medir(dxf_path: str | Path, escala: float = 1.0,
          capa_filtro: list[str] | None = None,
          unidades_por_capa: dict[str, str] | None = None,
          politica_bloques: str = "pieza") -> dict:
    """Mide un DXF desde una ruta."""
    doc = ezdxf.readfile(str(dxf_path))
    return _medir_documento(doc, escala, capa_filtro, unidades_por_capa,
                             politica_bloques)


def _medir_documento(doc, escala: float = 1.0,
                     capa_filtro: list[str] | None = None,
                     unidades_por_capa: dict[str, str] | None = None,
                     politica_bloques: str = "pieza",
                     dxf_path_default: str = "plano.dxf") -> dict:
    """Mide un documento ya abierto.

    Existe separada de medir() para que quien ya tiene el doc en memoria
    (la interfaz web, que no quiere escribir el archivo a disco) no tenga que
    guardarlo otra vez.
    """
    unidades_por_capa = unidades_por_capa or {}

    medidas, omitidas = extraer(doc, capa_filtro)
    if politica_bloques == "pieza":
        extras, omitidas_bloque = extraer_bloques(doc, capa_filtro)
        medidas += extras
        omitidas += omitidas_bloque

    # Acumula por (capa, unidad) la entidad aporta, separando validas de
    # incompatibles.
    validas: dict[tuple[str, str], list[EntidadMedida]] = defaultdict(list)
    incompatibles: list[dict] = []
    declaradas: dict[tuple[str, str], float] = defaultdict(float)

    for em in medidas:
        unidad_concepto = unidades_por_capa.get(em.capa)
        for forma, valor in em.contribuciones():
            if valor == 0:
                continue
            if not _compatibles(unidad_concepto, forma):
                incompatibles.append({
                    "capa": em.capa,
                    "handle": em.handle,
                    "tipo": em.tipo,
                    "forma_detectada": forma,
                    "unidad_concepto": unidad_concepto,
                    "motivo": (
                        f"entidad {em.tipo} aporta {forma} pero el concepto se cotiza "
                        f"por {unidad_concepto}"
                    ),
                })
                continue
            declaradas[(em.capa, forma)] += valor
            validas[(em.capa, forma)].append(em)

    # Construye mediciones agregadas con procedencia.
    mediciones: list[dict] = []
    solapes: list[dict] = []
    for (capa, unidad), ems in sorted(validas.items()):
        factor = escala ** 2 if unidad == "m2" else (escala if unidad in ("m", "ml") else 1.0)

        total = 0.0
        for e in ems:
            for forma, valor in e.contribuciones():
                if forma == unidad:
                    total += valor
                    break

        if unidad == "m2":
            # Para una capa de SUPERFICIE la cantidad correcta es la union
            # geometrica, no la suma de areas. Un patio dentro de una losa no
            # suma 100 + 16 = 116: son 84. Y tres copias identicas de un
            # rectangulo son una sola superficie, no tres.
            union, suma = _unir_areas(ems)
            if union is not None:
                diferencia = suma - union
                if diferencia > TOLERANCIA_SOLAPE_M2:
                    solapes.append({
                        "capa": capa,
                        "suma_areas": round(suma, 4),
                        "area_union": round(union, 4),
                        "diferencia": round(diferencia, 4),
                        "n_entidades": len(ems),
                        "handles": [e.handle for e in ems],
                        "motivo": (
                            "Las geometrias de esta capa se solapan o se contienen. "
                            "Se cobro la union (area real), no la suma."
                        ),
                    })
                total = union
            else:
                total = suma

        cantidad = total * factor
        if abs(cantidad) < 1e-9:
            continue
        mediciones.append({
            "capa": capa,
            "unidades": unidad,
            "cantidad": round(cantidad, 4),
            "handles": [e.handle for e in ems],
            "tipos": sorted({e.tipo for e in ems}),
            "n_entidades": len(ems),
        })

    return {
        "archivo": Path(getattr(doc, "filename", "") or dxf_path_default or "plano").name,
        "escala_aplicada": escala,
        "unidades_dxf": int(doc.units or 0),
        "mediciones": mediciones,
        "entidades_omitidas": omitidas,
        "entidades_incompatibles": incompatibles,
        "solapes": solapes,
        "diagnostico": construir_diagnostico(doc, doc.units, escala),
    }


# Codigos de $INSUNITS (DXF reference).
UNIDADES_DXF = {
    0: "unitless", 1: "in", 2: "ft", 3: "mi", 4: "mm",
    5: "cm", 6: "m", 7: "km", 8: "microin", 9: "mils",
    10: "yd", 11: "A", 12: "nm", 13: "um", 14: "dm", 15: "dam",
    16: "hm", 17: "Gm", 18: "AU", 19: "ly", 20: "pc",
}

# Factor a metros. MM=4 es el riesgo principal: un area en mm sale 1e6 veces
# mayor y un presupuesto con eso es 100% incorrecto.
FACTOR_A_METROS = {
    1: 0.0254, 2: 0.3048, 3: 1609.344, 4: 0.001, 5: 0.01, 6: 1.0,
    7: 1000.0, 9: 2.54e-5, 10: 0.9144, 13: 1e-6, 14: 0.1, 15: 10.0,
    16: 100.0, 12: 1e-9, 8: 2.54e-8,
}


def construir_diagnostico(doc, unidades: int, escala: float) -> dict:
    """Detecta la unidad del DXF y advierte si no es metro."""
    codigo = int(unidades or 0)
    nombre = UNIDADES_DXF.get(codigo, f"desconocido({codigo})")
    factor = FACTOR_A_METROS.get(codigo)

    advertencias = []
    if codigo == 0:
        advertencias.append(
            "El DXF no declara unidades ($INSUNITS = 0). Se asume metro 1:1. "
            "Si el plano esta en mm, el area saldra 1,000,000 veces mayor."
        )
    elif factor is not None and abs(factor - 1.0) > 1e-9:
        advertencias.append(
            f"El DXF declara unidades '{nombre}' ($INSUNITS={codigo}). "
            f"El motor multiplica por escala={escala}. "
            f"Factor a metros: {factor}. Verifica que el resultado sea coherente."
        )

    return {
        "unidades_codigo": codigo,
        "unidades_nombre": nombre,
        "factor_a_metros": factor,
        "advertencias": advertencias,
    }


if __name__ == "__main__":
    import json
    import sys

    for ruta in sys.argv[1:]:
        print(json.dumps(medir(ruta), indent=2, ensure_ascii=False))