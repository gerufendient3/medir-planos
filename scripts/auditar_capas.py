"""Auditoria: que tan bien cubre el catalogo las capas de un plano real.

Compara cada capa del plano contra el catalogo y clasifica el resultado:
  MAPEADO      -> hay concepto asignado
  SIN_MAPEO    -> ninguna capa del catalogo coincide
  AMBIGUO     -> mas de un patron podria aplicar; revisa el orden
  CONCEPTO_SIN_UNIDAD_UTIL -> mapea a un concepto cuya unidad no encaja
"""
from __future__ import annotations

import sys
from pathlib import Path

import ezdxf

from app.medidor import _compatibles
from app.presupuesto import Catalogo


def auditar(dxf_path: str | Path, catalogo: Catalogo) -> dict:
    doc = ezdxf.readfile(str(dxf_path))
    capas = sorted({e.dxf.layer for e in doc.modelspace()})

    filas = []
    for capa in capas:
        motivo_exclusion = catalogo.es_no_medible(capa)
        if motivo_exclusion:
            filas.append({"capa": capa, "estado": "CAPA_EXCLUIDA",
                          "concepto": None, "unidad": None, "clave": None,
                          "motivo": motivo_exclusion})
            continue

        concepto = catalogo.buscar_por_capa(capa)
        if concepto is None:
            filas.append({"capa": capa, "estado": "SIN_MAPEO",
                          "concepto": None, "unidad": None, "clave": None})
            continue

        # ¿Cuantos patrones más podrían aplicar? Indica ambigüedad.
        candidatos = [c for c in catalogo.conceptos if c._regex.search(capa)]
        estado = "MAPEADO"
        if len(candidatos) > 1:
            estado = "AMBIGUO"

        filas.append({
            "capa": capa,
            "estado": estado,
            "concepto": concepto.nombre,
            "unidad": concepto.unidad,
            "clave": concepto.clave,
            "n_patrones_coincidentes": len(candidatos),
            "otros_patrones": [c.clave for c in candidatos if c.clave != concepto.clave],
        })

    resumen = {}
    for f in filas:
        resumen[f["estado"]] = resumen.get(f["estado"], 0) + 1

    # Cobertura real: solo cuentan las capas que deberian medirse.
    medibles = [f for f in filas if f["estado"] != "CAPA_EXCLUIDA"]
    cubiertas = [f for f in medibles if f["estado"] in ("MAPEADO", "AMBIGUO")]

    return {"archivo": Path(dxf_path).name, "capas": filas, "resumen": resumen,
            "total_capas": len(capas),
            "capas_medibles": len(medibles),
            "capas_cubiertas": len(cubiertas),
            "cobertura_pct": round(100.0 * len(cubiertas) / len(medibles), 1) if medibles else 0.0}


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    ruta = argv[0] if argv else "planos/capas_reales.dxf"
    cat = Catalogo.cargar()
    r = auditar(ruta, cat)

    print("AUDITORIA DE CAPAS: {}".format(r["archivo"]))
    print("total capas: {}  -> {}".format(r["total_capas"], r["resumen"]))
    print("medibles: {}  cubiertas: {}  COBERTURA: {}%".format(
        r["capas_medibles"], r["capas_cubiertas"], r["cobertura_pct"]))
    print()

    ancho = max(len(f["capa"]) for f in r["capas"])
    for f in r["capas"]:
        if f["estado"] == "CAPA_EXCLUIDA":
            print("  {:<{}}  EXCLUIDA  ({})".format(f["capa"], ancho, f["motivo"]))
        elif f["estado"] == "SIN_MAPEO":
            print("  {:<{}}  SIN_MAPEO".format(f["capa"], ancho))
        elif f["estado"] == "AMBIGUO":
            print("  {:<{}}  AMBIGUO  -> {} (otros: {})".format(
                f["capa"], ancho, f["concepto"], ", ".join(f["otros_patrones"])))
        else:
            print("  {:<{}}  {} [{}]".format(f["capa"], ancho, f["concepto"], f["unidad"]))

    sin = [f for f in r["capas"] if f["estado"] == "SIN_MAPEO"]
    amb = [f for f in r["capas"] if f["estado"] == "AMBIGUO"]
    print()
    print("BRECHAS REALES ({}):".format(len(sin)))
    for f in sin:
        print("  -", f["capa"])
    print()
    print("AMBIGUAS ({}): verifican si el despacho mezclo conceptos en una capa".format(len(amb)))
    for f in amb:
        print("  - {} -> {} | otros patrones: {}".format(
            f["capa"], f["clave"], ", ".join(f["otros_patrones"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())