"""Punto 4: verificacion de totales.

El subtotal, el IVA y el total deben coincidir AL CENTAVO entre el resultado de
Python, la celda del Excel y el texto del PDF. Si divergen, el presupuesto no
es confiable.
"""
from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from openpyxl import load_workbook

from app.exportar import exportar_excel, exportar_pdf
from app.pipeline import ejecutar
from app.presupuesto import calcular_iva

RAIZ = Path(__file__).resolve().parent.parent
REALISTA = RAIZ / "planos" / "plano_realista.dxf"


def _catalogo_demo(tmp_path: Path) -> Path:
    """PRECIOS DE EJEMPLO. No son precios de mercado, solo validan el flujo."""
    datos = json.loads((RAIZ / "catalogo" / "conceptos.json").read_text(encoding="utf-8"))
    precios = {"MUR_BLOCK_15": 900.0, "LOSETA": 320.0, "VINI": 450.0,
               "CIELO_YESO": 280.0, "TUBO_ELEC": 95.0, "LAMPARA": 850.0,
               "TUBO_HIDRO": 130.0, "VENTANA": 2400.0}
    for c in datos["conceptos"]:
        if c["clave"] in precios:
            c["precio_unitario"] = precios[c["clave"]]
    ruta = tmp_path / "demo.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


def _texto_pdf(ruta: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(ruta))
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def _numero_en_texto(texto: str, valor: float) -> bool:
    """Busca el importe con separador de miles o sin el."""
    n = f"{valor:,.2f}"
    return n in texto or f"{valor:.2f}" in texto


# --------------------------------------------------------------- IVA

def test_iva_es_dieciseis_por_ciento():
    assert calcular_iva(1000.0) == pytest.approx(160.00)
    # Numero generico a proposito. Antes era un importe real de una corrida
    # de prueba, y un total de ese tipo no tiene por que quedar en un
    # repositorio publico aunque sea solo como operando.
    #   12345.67 * 0.16 = 1975.3072 -> 1975.31
    assert calcular_iva(12345.67) == pytest.approx(1975.31)


def test_total_es_subtotal_mas_iva(tmp_path):
    r = ejecutar(REALISTA, _catalogo_demo(tmp_path))
    p = r["presupuesto"]
    assert p.total == pytest.approx(p.subtotal + p.iva)
    assert p.iva == pytest.approx(p.subtotal * 0.16, abs=0.01)


def test_iva_usa_redondeo_a_dos_decimales():
    """El redondeo debe ser half-up, no binario.

    1234.565 * 0.16 = 197.5304 -> 197.53
    """
    assert calcular_iva(1234.565) == 197.53


def test_subtotal_es_la_suma_de_las_lineas_ok(tmp_path):
    r = ejecutar(REALISTA, _catalogo_demo(tmp_path))
    p = r["presupuesto"]
    suma = sum(l.importe for l in p.lineas if l.importe is not None)
    assert p.subtotal == pytest.approx(suma, abs=0.01)
    # Las lineas excluidas no aportan nada al subtotal.
    assert all(l.importe is None for l in p.excluidas)


# -------------------------------------------- los tres coinciden al centavo

def test_python_excel_y_pdf_coinciden(tmp_path):
    cat = _catalogo_demo(tmp_path)
    r = ejecutar(REALISTA, cat)
    p = r["presupuesto"]

    xlsx = exportar_excel(p, r["takeoff"], tmp_path / "p.xlsx")
    pdf = exportar_pdf(p, r["takeoff"], tmp_path / "p.pdf")

    # Excel
    wb = load_workbook(xlsx)
    ws = wb.active
    fila_subtotal = fila_iva = fila_total = None
    for row in range(1, ws.max_row + 1):
        etiqueta = ws.cell(row=row, column=8).value
        if etiqueta == "Subtotal":
            fila_subtotal = ws.cell(row=row, column=9).value
        elif etiqueta == "IVA 16%":
            fila_iva = ws.cell(row=row, column=9).value
        elif etiqueta == "TOTAL":
            fila_total = ws.cell(row=row, column=9).value

    assert fila_subtotal is not None and fila_iva is not None and fila_total is not None

    # Centavo exacto entre Python y Excel
    assert Decimal(str(fila_subtotal)) == Decimal(str(p.subtotal))
    assert Decimal(str(fila_iva)) == Decimal(str(p.iva))
    assert Decimal(str(fila_total)) == Decimal(str(p.total))

    # Centavo exacto entre Python y PDF
    texto = _texto_pdf(pdf)
    assert _numero_en_texto(texto, p.subtotal), f"subtotal {p.subtotal} no aparece en el PDF"
    assert _numero_en_texto(texto, p.iva), f"IVA {p.iva} no aparece en el PDF"
    assert _numero_en_texto(texto, p.total), f"total {p.total} no aparece en el PDF"


def test_cada_linea_ok_se_calcula_como_cantidad_por_precio(tmp_path):
    """Importe == cantidad_ajustada * precio_unitario, redondeado a 2."""
    r = ejecutar(REALISTA, _catalogo_demo(tmp_path))
    for l in r["presupuesto"].lineas:
        if l.estado != "OK":
            continue
        esperado = Decimal(str(l.cantidad_ajustada)) * Decimal(str(l.precio_unitario))
        esperado = esperado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert Decimal(str(l.importe)) == esperado, f"linea {l.clave}"


# --------------------------------------- caso manual documentado a mano

def test_caso_manual_tres_lineas_calculadas_a_mano(tmp_path):
    """Verificacion manual de tres lineas del plano realista.

    Calculo a mano, sin usar el motor para el importe:

    1) Muro de block 15 cm, 108.00 m2 medidos, rendimiento 1.0,
       precio de EJEMPLO 900.00
       108.00 * 1.0 * 900.00 = 97,200.00

    2) Piso de loseta, 27.00 m2 medidos, rendimiento 1.08 (merma),
       precio de EJEMPLO 320.00
       27.00 * 1.08 = 29.16 m2
       29.16 * 320.00 = 9,331.20

    3) Luminaria, 2 pza medidas (dos circulos de r=0.15 en el plano),
       rendimiento 1.0, precio de EJEMPLO 850.00
       2 * 1.0 * 850.00 = 1,700.00
    """
    r = ejecutar(REALISTA, _catalogo_demo(tmp_path))
    lineas = {(l.clave, l.unidad): l for l in r["presupuesto"].lineas}

    muro = lineas[("MUR_BLOCK_15", "m2")]
    assert muro.estado == "OK"
    assert muro.cantidad_medida == pytest.approx(108.0)
    assert muro.rendimiento == 1.0
    assert muro.importe == pytest.approx(97200.00)

    loseta = lineas[("LOSETA", "m2")]
    assert loseta.estado == "OK"
    assert loseta.cantidad_medida == pytest.approx(27.0)
    assert loseta.cantidad_ajustada == pytest.approx(29.16)
    assert loseta.importe == pytest.approx(9331.20)

    lam = lineas[("LAMPARA", "pza")]
    assert lam.estado == "OK"
    assert lam.cantidad_ajustada == pytest.approx(2.0)
    assert lam.importe == pytest.approx(1700.00)


def test_caso_manual_los_mismos_importes_aparecen_en_el_excel(tmp_path):
    """Los tres importes del calculo manual deben estar en las filas del Excel."""
    cat = _catalogo_demo(tmp_path)
    r = ejecutar(REALISTA, cat)
    xlsx = exportar_excel(r["presupuesto"], r["takeoff"], tmp_path / "p.xlsx")

    wb = load_workbook(xlsx)
    ws = wb.active
    importes = []
    for row in range(7, ws.max_row + 1):
        v = ws.cell(row=row, column=9).value
        if isinstance(v, (int, float)):
            importes.append(round(float(v), 2))

    assert 97200.00 in importes
    assert 9331.20 in importes
    assert 1700.00 in importes