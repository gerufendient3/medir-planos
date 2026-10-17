"""Pipeline completo: DXF -> takeoff -> presupuesto -> Excel + PDF.

Uso:
    python -m app.pipeline planos/plano_realista.dxf --salida salida/
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.exportar import exportar_excel, exportar_pdf
from app.medidor import medir
from app.presupuesto import Catalogo, construir_presupuesto


def _abrir_para_medir(ruta: str | Path, escala: float, pt_por_metro: float | None):
    """Devuelve (takeoff, capas).

    Un solo punto de entrada para DXF y PDF: si el archivo es PDF se usa la
    ruta vectorial, si es DXF la nativa. La decision se toma por extension y
    se avisa si algo no cuadra.
    """
    ruta = Path(ruta)
    ext = ruta.suffix.lower()

    if ext == ".pdf":
        from app.pdf_entrada import medir_pdf

        if pt_por_metro is None:
            pt_por_metro = 1.0
        takeoff = medir_pdf(ruta, pt_por_metro=pt_por_metro)
        # En PDF los "capas" son grupos por color; no hay mapa de unidad.
        capas = sorted({m["capa"] for m in takeoff["mediciones"]})
        return takeoff, capas

    if ext == ".dwg":
        from app.entidades import leer_dwg

        doc = leer_dwg(ruta)
        import ezdxf

        capas = sorted({e.dxf.layer for e in doc.modelspace()})
        catalogo = Catalogo.cargar()
        unidades_por_capa = catalogo.unidades_por_capa(capas)
        # ODA convierte a DXF; se mide igual que un DXF normal.
        takeoff = medir(doc, escala=escala, unidades_por_capa=unidades_por_capa)
        return takeoff, capas

    # DXF
    import ezdxf

    doc = ezdxf.readfile(str(ruta))
    capas = sorted({e.dxf.layer for e in doc.modelspace()})
    catalogo = Catalogo.cargar()
    unidades_por_capa = catalogo.unidades_por_capa(capas)
    takeoff = medir(ruta, escala=escala, unidades_por_capa=unidades_por_capa)
    return takeoff, capas


def ejecutar(dxf: str | Path, catalogo_path: str | Path | None = None,
             escala: float = 1.0, tasa_iva: float = 0.16,
             pt_por_metro: float | None = None) -> dict:
    """Plano (DXF, DWG o PDF vectorial) -> takeoff -> presupuesto.

    El mapa capa->unidad se calcula ANTES de medir para que el motor descarte
    entidades incompatibles a nivel de entidad, no despues de agregar.
    """
    catalogo = Catalogo.cargar(catalogo_path)
    takeoff, capas = _abrir_para_medir(dxf, escala, pt_por_metro)

    # Para PDF el mapa de unidades se recalcula sobre los grupos por color.
    if Path(dxf).suffix.lower() == ".pdf":
        unidades_por_capa = catalogo.unidades_por_capa(capas)
        takeoff["mediciones"] = [
            m for m in takeoff["mediciones"]
            if unidades_por_capa.get(m["capa"])
        ]
        takeoff["diagnostico"]["advertencias"].append(
            "Los grupos por color sin concepto asignado se omitieron. "
            "Mapea cada grupo (COLOR_*) a un concepto en el catalogo."
        )

    presupuesto = construir_presupuesto(takeoff["mediciones"], catalogo, tasa_iva=tasa_iva)
    return {"takeoff": takeoff, "presupuesto": presupuesto, "catalogo": catalogo,
            "capas": capas}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Plano -> presupuesto")
    p.add_argument("dxf")
    p.add_argument("--catalogo")
    p.add_argument("--salida", default="salida")
    p.add_argument("--escala", type=float, default=1.0)
    p.add_argument("--iva", type=float, default=0.16)
    p.add_argument("--pt-por-metro", type=float, default=None,
                   help="solo PDF: puntos PDF por metro (el PDF no trae escala)")
    args = p.parse_args(argv)

    r = ejecutar(args.dxf, args.catalogo, args.escala, args.iva, args.pt_por_metro)
    pres, take = r["presupuesto"], r["takeoff"]

    print("\n== CAPAS DETECTADAS: {}".format(len(r["capas"])))
    print("== UNIDADES DEL DXF: {} (codigo {})".format(
        take["diagnostico"]["unidades_nombre"], take["diagnostico"]["unidades_codigo"]))

    print("\n== TAKOFF ({})".format(take["archivo"]))
    for m in take["mediciones"]:
        print("  {:<26} {:>12.4f} {:<4} ({} entidades)".format(
            m["capa"], m["cantidad"], m["unidades"], m["n_entidades"]))

    if take["entidades_incompatibles"]:
        print("\n== ENTIDADES INCOMPATIBLES (descartadas, NO agregadas)")
        for i in take["entidades_incompatibles"]:
            print("  capa={} handle={} tipo={} aporta={} concepto={}".format(
                i["capa"], i["handle"], i["tipo"], i["forma_detectada"], i["unidad_concepto"]))

    if take["entidades_omitidas"]:
        print("\n== ENTIDADES OMITIDAS")
        for o in take["entidades_omitidas"]:
            print("  capa={} handle={} tipo={} motivo={}".format(
                o["capa"], o["handle"], o["tipo"], o["motivo"]))

    if take["diagnostico"]["advertencias"]:
        print("\n== DIAGNOSTICO DEL DOCUMENTO")
        for a in take["diagnostico"]["advertencias"]:
            print("  ! {}".format(a))

    print("\n== PRESUPUESTO ({})".format(pres.moneda))
    for l in pres.lineas:
        imp = "{:>12,.2f}".format(l.importe) if l.importe is not None else "{:>12}".format("EXCLUIDA")
        print("  {:<22} {:<34} {:>10.2f} {:<4} {}".format(
            l.estado, l.concepto[:34], l.cantidad_ajustada, l.unidad, imp))

    print("\n== TOTALES")
    print("  Subtotal: {:>14,.2f}".format(pres.subtotal))
    print("  IVA 16%: {:>14,.2f}".format(pres.iva))
    print("  TOTAL:    {:>14,.2f}".format(pres.total))

    for a in pres.advertencias():
        print("  ! {}".format(a))

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    base = Path(args.dxf).stem
    excel = exportar_excel(pres, take, salida / "{}.xlsx".format(base))
    pdf = exportar_pdf(pres, take, salida / "{}.pdf".format(base))
    (salida / "{}.json".format(base)).write_text(json.dumps({
        "takeoff": take,
        "lineas": [l.__dict__ for l in pres.lineas],
        "subtotal": pres.subtotal, "iva": pres.iva, "total": pres.total,
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\n  escrito: {}, {}, {}.json".format(excel.name, pdf.name, base))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())