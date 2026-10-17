"""Exportacion del presupuesto a Excel y PDF.

Regla: nada se omite en silencio. Si una partida quedo excluida por una
advertencia, el aviso aparece en el Excel y en el PDF con el motivo y la
procedencia.
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

AZUL = "1F3A5F"
GRIS_FALTA = "FFF4CE"
GRIS_SINMAPEO = "FDE2E2"
GRIS_INCOMPAT = "FFE0B2"
VERDE_OK = "E8F5E9"

FONDO_POR_ESTADO = {
    "OK": VERDE_OK,
    "FALTA_PRECIO": GRIS_FALTA,
    "UNIDAD_INCOMPATIBLE": GRIS_INCOMPAT,
    "SIN_MAPEO": GRIS_SINMAPEO,
}

ENCABEZADOS = ["Estado", "Categoría", "Concepto", "Capa", "Cant.", "Und.",
               "Rend.", "P. unitario", "Importe", "Entidades", "Handles"]


def exportar_excel_bytes(presupuesto, takeoff) -> bytes:
    """Genera el XLSX en memoria. No toca el disco.

    La interfaz web lo usa para no dejar archivos temporales.
    """
    import io

    buf = io.BytesIO()
    _construir_excel(presupuesto, takeoff).save(buf)
    return buf.getvalue()


def exportar_excel(presupuesto, takeoff, ruta: str | Path) -> Path:
    _construir_excel(presupuesto, takeoff).save(str(ruta))
    return Path(ruta)


def _construir_excel(presupuesto, takeoff):
    wb = Workbook()
    ws = wb.active
    ws.title = "Presupuesto"

    ws["A1"] = "PRESUPUESTO DE OBRA"
    ws.merge_cells("A1:K1")
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color=AZUL)
    ws["A2"] = "Plano: {}".format(takeoff["archivo"])
    ws["A3"] = "Unidades del DXF: {} ($INSUNITS={})".format(
        takeoff["diagnostico"]["unidades_nombre"],
        takeoff["diagnostico"]["unidades_codigo"])
    ws["A4"] = "Escala aplicada: {}".format(takeoff["escala_aplicada"])

    for i, c in enumerate(ENCABEZADOS, start=1):
        celda = ws.cell(row=6, column=i, value=c)
        celda.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor=AZUL)
        celda.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)

    borde = Border(*[Side(style="thin", color="CCCCCC")] * 4)
    r = 7
    for l in presupuesto.lineas:
        vals = [
            l.estado, l.categoria, l.concepto, l.capa,
            l.cantidad_ajustada, l.unidad, l.rendimiento,
            l.precio_unitario if l.precio_unitario is not None else "SIN PRECIO",
            l.importe if l.importe is not None else "EXCLUIDA",
            l.n_entidades,
            ", ".join(l.handles[:6]) + ("..." if len(l.handles) > 6 else ""),
        ]
        fill = FONDO_POR_ESTADO.get(l.estado, "FFFFFF")
        for i, v in enumerate(vals, start=1):
            celda = ws.cell(row=r, column=i, value=v)
            celda.font = Font(name="Calibri", size=10)
            celda.border = borde
            celda.fill = PatternFill("solid", fgColor=fill)
            if i in (5, 7) and isinstance(v, (int, float)):
                celda.number_format = "0.0000"
            if i in (8, 9) and isinstance(v, (int, float)):
                celda.number_format = '"$"#,##0.00'
        if l.detalle:
            ws.cell(row=r, column=12, value=l.detalle).font = Font(
                name="Calibri", size=9, color="9C0006")
        r += 1

    # Totales
    r += 1
    ws.cell(row=r, column=8, value="Subtotal").font = Font(name="Calibri", size=12, bold=True)
    celda = ws.cell(row=r, column=9, value=presupuesto.subtotal)
    celda.font = Font(name="Calibri", size=12, bold=True)
    celda.number_format = '"$"#,##0.00'

    r += 1
    ws.cell(row=r, column=8, value="IVA 16%").font = Font(name="Calibri", size=12)
    celda = ws.cell(row=r, column=9, value=presupuesto.iva)
    celda.font = Font(name="Calibri", size=12)
    celda.number_format = '"$"#,##0.00'

    r += 1
    ws.cell(row=r, column=8, value="TOTAL").font = Font(name="Calibri", size=13, bold=True)
    celda = ws.cell(row=r, column=9, value=presupuesto.total)
    celda.font = Font(name="Calibri", size=13, bold=True)
    celda.number_format = '"$"#,##0.00'

    # Si el total esta incompleto, se marca en la MISMA fila del total.
    # Un total parcial sin marcar en la fila es indistinguible de uno bueno.
    if presupuesto.total_incompleto:
        celda.font = Font(name="Calibri", size=13, bold=True, color="9C0006")
        ws.cell(row=r, column=1, value="⚠ TOTAL INCOMPLETO").font = Font(
            name="Calibri", size=13, bold=True, color="9C0006")
        marca = ws.cell(row=r, column=11, value=(
            "NO ES UN PRESUPUESTO ENVIABLE: {}/{} lineas excluidas. "
            "Ver ADVERTENCIAS.".format(len(presupuesto.excluidas),
                                      len(presupuesto.lineas))))
        marca.font = Font(name="Calibri", size=10, bold=True, color="9C0006")

    # Bloque de advertencias: obligatorio, no opcional.
    r += 2
    ws.cell(row=r, column=1, value="ADVERTENCIAS").font = Font(
        name="Calibri", size=12, bold=True, color="9C0006")
    r += 1
    avisos = presupuesto.advertencias()
    for a in takeoff.get("diagnostico", {}).get("advertencias", []):
        ws.cell(row=r, column=1, value="! " + a).font = Font(name="Calibri", size=10, color="9C0006")
        r += 1
    for a in avisos:
        ws.cell(row=r, column=1, value="! " + a).font = Font(name="Calibri", size=10, color="9C0006")
        r += 1
    if not avisos:
        ws.cell(row=r, column=1, value="Sin advertencias: todas las lineas son OK.").font = Font(
            name="Calibri", size=10, color="1B5E20")
        r += 1

    if takeoff["entidades_incompatibles"]:
        r += 1
        ws.cell(row=r, column=1, value="ENTIDADES DESCARTADAS POR INCOMPATIBILIDAD").font = Font(
            name="Calibri", size=11, bold=True, color="9C0006")
        r += 1
        for i in takeoff["entidades_incompatibles"]:
            ws.cell(row=r, column=1, value=i["capa"]).font = Font(name="Calibri", size=9)
            ws.cell(row=r, column=2, value=i["handle"]).font = Font(name="Calibri", size=9)
            ws.cell(row=r, column=3, value=i["tipo"]).font = Font(name="Calibri", size=9)
            ws.cell(row=r, column=4, value=i["forma_detectada"]).font = Font(name="Calibri", size=9)
            ws.cell(row=r, column=5, value=i["unidad_concepto"]).font = Font(name="Calibri", size=9)
            r += 1

    if takeoff["entidades_omitidas"]:
        r += 1
        ws.cell(row=r, column=1, value="ENTIDADES OMITIDAS (no son geometria de obra)").font = Font(
            name="Calibri", size=11, bold=True)
        r += 1
        for o in takeoff["entidades_omitidas"]:
            ws.cell(row=r, column=1, value=o["capa"]).font = Font(name="Calibri", size=9)
            ws.cell(row=r, column=2, value=o["handle"]).font = Font(name="Calibri", size=9)
            ws.cell(row=r, column=3, value=o["tipo"]).font = Font(name="Calibri", size=9)
            ws.cell(row=r, column=4, value=o["motivo"]).font = Font(name="Calibri", size=9)
            r += 1

    for col, ancho in zip("ABCDEFGHIJKL",
                          [22, 22, 34, 26, 11, 7, 8, 15, 15, 11, 34, 60]):
        ws.column_dimensions[col].width = ancho

    return wb


def exportar_pdf_bytes(presupuesto, takeoff) -> bytes:
    """Genera el PDF en memoria, sin tocar el disco."""
    import io

    buf = io.BytesIO()
    _construir_pdf(presupuesto, takeoff, buf)
    return buf.getvalue()


def exportar_pdf(presupuesto, takeoff, ruta: str | Path) -> Path:
    ruta = Path(ruta)
    _construir_pdf(presupuesto, takeoff, ruta)
    return ruta


def _construir_pdf(presupuesto, takeoff, destino) -> None:
    """Arma el PDF y lo escribe en `destino` (ruta o file-like)."""
    doc = SimpleDocTemplate(
        str(destino) if isinstance(destino, (str, Path)) else destino,
        pagesize=letter,
        leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
    )
    ss = getSampleStyleSheet()
    st_titulo = ParagraphStyle("t", parent=ss["Title"], fontSize=16,
                               textColor=colors.HexColor("#" + AZUL))
    st_small = ParagraphStyle("s", parent=ss["BodyText"], fontSize=7.5,
                              textColor=colors.grey)
    st_aviso = ParagraphStyle("a", parent=ss["BodyText"], fontSize=8,
                              textColor=colors.HexColor("#9C0006"))
    st_celda = ParagraphStyle("c", parent=ss["BodyText"], fontSize=7.5)

    filas = [["Concepto", "Cant.", "Und.", "P. unit.", "Importe", "Estado"]]
    for l in presupuesto.lineas:
        filas.append([
            Paragraph("{}<br/><font size='6.5' color='#888888'>{}</font>".format(
                l.concepto, l.capa), st_celda),
            "{:,.4f}".format(l.cantidad_ajustada),
            l.unidad,
            "{:,.2f}".format(l.precio_unitario) if l.precio_unitario else "sin precio",
            "{:,.2f}".format(l.importe) if l.importe is not None else "EXCLUIDA",
            l.estado,
        ])

    tabla = Table(filas, colWidths=[62 * mm, 18 * mm, 11 * mm, 20 * mm, 22 * mm, 26 * mm],
                  repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#" + AZUL)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7.5),
        ("FONTSIZE", (0, 1), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (1, 1), (4, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
    ]))

    story = [
        Paragraph("Presupuesto de obra", st_titulo),
        Paragraph("Plano: {} &nbsp;|&nbsp; Moneda: {} &nbsp;|&nbsp; "
                  "Unidades DXF: {} &nbsp;|&nbsp; Escala: {}".format(
                      takeoff["archivo"], presupuesto.moneda,
                      takeoff["diagnostico"]["unidades_nombre"],
                      takeoff["escala_aplicada"]), st_small),
        Spacer(1, 6 * mm),
        tabla,
        Spacer(1, 4 * mm),
        Paragraph("Subtotal: {:,.2f} &nbsp;&nbsp; IVA 16%: {:,.2f} &nbsp;&nbsp; "
                  "<b>TOTAL: {:,.2f} {}</b>".format(
                      presupuesto.subtotal, presupuesto.iva,
                      presupuesto.total, presupuesto.moneda), ss["BodyText"]),
    ]

    if presupuesto.total_incompleto:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph(
            "<b>⚠ TOTAL INCOMPLETO — NO ENVIAR AL CLIENTE.</b> "
            "{} de {} lineas quedaron excluidas. Este importe NO cubre toda "
            "la obra del plano.".format(len(presupuesto.excluidas),
                                        len(presupuesto.lineas)),
            ParagraphStyle("w", parent=ss["BodyText"], fontSize=11,
                           textColor=colors.HexColor("#9C0006"),
                           borderColor=colors.HexColor("#9C0006"),
                           borderWidth=1, borderPadding=5)))

    avisos = list(takeoff.get("diagnostico", {}).get("advertencias", []))
    avisos += presupuesto.advertencias()
    if takeoff["entidades_incompatibles"]:
        avisos.append("{} entidad(es) descartada(s) por unidad incompatible con su "
                      "concepto (ver detalle en el Excel).".format(
                          len(takeoff["entidades_incompatibles"])))
    if takeoff["entidades_omitidas"]:
        avisos.append("{} entidad(es) omitida(s) por ser anotacion (textos, cotas).".format(
            len(takeoff["entidades_omitidas"])))

    if avisos:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>ADVERTENCIAS</b>", st_aviso))
        for a in avisos:
            story.append(Paragraph("&#8226; " + a, st_aviso))
    else:
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("Sin advertencias: todas las lineas son OK.", st_small))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Las partidas en estado EXCLUIDA no forman parte del total. "
        "La columna Handles permite rastrear cada cantidad hasta las entidades "
        "del plano. Rendimientos incrementan por merma de corte y material.",
        st_small))
    doc.build(story)