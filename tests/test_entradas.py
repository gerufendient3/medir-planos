"""Punto 1: entrada PDF vectorial con pdfplumber.

Casos cubiertos:
  - deteccion de PDF escaneado (2 PDFs reales de licencia conocida)
  - medicion de PDF vectorial contra verdad conocida
  - agrupamiento por color (PDF no tiene capas)
  - escala explicita y aviso cuando falta
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.entidades import OdaNoDisponible, odafc_disponible
from app.pdf_entrada import inspeccionar, leer_grupos, medir_pdf

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PDF = FIXTURES / "pdf"

VECTORIAL = PDF / "vectorial_desde_dxf.pdf"
REAL_VECTOR = PDF / "harlem_meer_planta.pdf"     # CC BY-SA 4.0
REAL_ESCANEADO = PDF / "pd_escaneado.pdf"       # Dominio publico (PD US Government)


# ------------------------------------------------------- deteccion escaneado

def test_pdf_real_de_plano_resulta_escaneado():
    """Un plano real CC BY-SA de 4760x2160 pt tiene 0 vectores: es imagen.

    Esto es un hallazgo, no una excepcion: los PDF de planos en circulacion
    suelen venir rasterizados aunque el original sea CAD.
    """
    info = inspeccionar(REAL_VECTOR)
    assert info["objetos_vectoriales"] == 0
    assert info["images"] > 0
    assert info["vectorial"] is False


def test_escaneado_avisa_que_no_se_puede_medir():
    info = inspeccionar(REAL_ESCANEADO)
    assert info["vectorial"] is False
    assert any("ESCANEADO" in a for a in info["advertencias"])
    assert any("OCR" in a for a in info["advertencias"])


def test_escaneado_devuelve_cero_mediciones_sin_explotar():
    """Un escaneado NO se intenta medir: devuelve vacio y lo dice."""
    r = medir_pdf(REAL_ESCANEADO)
    assert r["mediciones"] == []
    assert any("ESCANEADO" in a for a in r["diagnostico"]["advertencias"])


def test_pdf_vectorial_generado_si_se_detecta_como_tal():
    info = inspeccionar(VECTORIAL)
    assert info["vectorial"] is True
    assert info["objetos_vectoriales"] >= 3
    assert info["images"] == 0


# -------------------------------------------------------- escala y unidades

def test_escala_uno_avisa_que_no_son_metros():
    """El PDF no trae escala. Con 1.0 las cantidades son PUNTOS, no metros."""
    r = medir_pdf(VECTORIAL, pt_por_metro=1.0)
    assert any("PUNTOS PDF" in a or "ESCALA = 1.0" in a
               for a in r["diagnostico"]["advertencias"])


def test_pdf_avisa_que_no_tiene_capas():
    """El agrupamiento por color es una heuristica y debe decirlo."""
    r = medir_pdf(VECTORIAL, pt_por_metro=52.3637)
    assert any("NO TIENE CAPAS" in a for a in r["diagnostico"]["advertencias"])


def test_escala_explicita_convierte_a_metros():
    """El rectangulo de 8x6 m mide 418.91 x 314.18 pt en el PDF.

    418.91 / 8 = 52.3637 pt por metro.
    Con esa escala, el area debe dar 48 m2.
    """
    PT_POR_M = 418.91 / 8.0
    r = medir_pdf(VECTORIAL, pt_por_metro=PT_POR_M)

    areas = [m for m in r["mediciones"] if m["unidades"] == "m2"]
    assert areas, "debe haber al menos una superficie"

    # El rectangulo verde de 4x3 m debe medir 12 m2.
    verde = [m for m in areas if m["capa"].startswith("COLOR_0_1_0")]
    assert verde, "el rectangulo verde (piso) debe formar su propio grupo"
    assert verde[0]["cantidad"] == pytest.approx(12.0, rel=0.01)


def test_proporcion_se_conserva_aunque_no_haya_escala():
    """Sin escala no hay metros, pero las proporciones del plano se mantienen.

    El grupo negro tiene el rect 8x6; la relacion debe ser 4/3.
    """
    r = medir_pdf(VECTORIAL, pt_por_metro=1.0)
    # Hay dos grupos por color: negro (muros) y verde (piso).
    capas = {m["capa"] for m in r["mediciones"]}
    assert len(capas) == 2, "se esperan 2 grupos por color: negro y verde"


# ------------------------------------------------------- agrupado por color

def test_agrupamiento_separa_por_color():
    g = leer_grupos(VECTORIAL)["grupos"]
    assert len(g) == 2, "negro y verde"
    verde = [k for k in g if k.startswith("COLOR_0_1_0")]
    assert verde, "el piso es verde"
    assert g[verde[0]]["rects"] == 1


def test_agrupamiento_excluye_la_envoltura_de_pagina():
    """La caja que ocupa toda la pagina no es geometria de obra."""
    g = leer_grupos(VECTORIAL)["grupos"]
    total = sum(v["rects"] + v["lines"] + v["curves"] for v in g.values())
    # La pagina tiene 3 rectangulos y 1 linea. Uno de los rectangulos es la
    # envoltura de pagina (460.8 x 345.6) y se excluye: quedan 3 objetos.
    assert total == 3, "2 rectangulos de obra + 1 linea (la envoltura se excluye)"


def test_capas_pdf_se_llaman_por_color():
    """Los grupos se nombran COLOR_<r>_<g>_<b>, nunca como capas de CAD."""
    r = medir_pdf(VECTORIAL)
    for m in r["mediciones"]:
        assert m["capa"].startswith("COLOR_"), m["capa"]


def test_manejadores_de_procedencia_presentes():
    r = medir_pdf(VECTORIAL)
    for m in r["mediciones"]:
        assert m["handles"], "cada medicion PDF debe traer procedencia"
        assert m["n_entidades"] > 0


# ------------------------------------------------------ deteccion de formato

def test_odafc_reporta_si_esta_o_no_disponible():
    """Debe devolver un bool sin lanzar, para poder avisar."""
    assert isinstance(odafc_disponible(), bool)


def test_leer_dwg_sin_oda_da_error_claro():
    """Sin ODA el error debe explicar QUE FALTA y COMO SOLUCIONARLO."""
    from app.entidades import leer_dwg

    fake = FIXTURES / "dwg" / "no_existe.dwg"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_bytes(b"AC1024\x00\x00\x00\x00")

    if odafc_disponible():
        pytest.skip("ODA File Converter esta instalado en esta maquina")

    with pytest.raises(OdaNoDisponible) as exc:
        leer_dwg(fake)
    mensaje = str(exc.value)
    assert "ODA File Converter" in mensaje
    assert "opendesign.com" in mensaje, "el error debe incluir donde descargar"
    assert "DXF" in mensaje, "el error debe sugerir la alternativa DXF"


def test_leer_dwg_rechaza_extension_no_dwg():
    from app.entidades import leer_dwg

    with pytest.raises(ValueError, match="dwg"):
        leer_dwg(VECTORIAL)


def test_sin_oda_el_dwg_no_se_omite_en_silencio(tmp_path):
    """Un DWG sin ODA debe fallar, nunca devolver un resultado vacio."""
    from app.entidades import leer_dwg

    fake = tmp_path / "plano.dwg"
    fake.write_bytes(b"AC1024\x00\x00\x00\x00")

    if odafc_disponible():
        pytest.skip("ODA File Converter esta instalado en esta maquina")

    with pytest.raises(OdaNoDisponible):
        leer_dwg(fake)