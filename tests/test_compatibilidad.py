"""Punto 1: compatibilidad entidad-concepto como regla explicita.

Cada concepto declara que formas de entidad acepta. Una entidad incompatible
se reporta con su handle, nunca se agrega en silencio.

Incluye la regresion del bug de luminarias: un concepto pza no puede acabar
facturando metros cuadrados.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.medidor import COMPATIBLE, medir
from app.presupuesto import Catalogo, Concepto, ErrorCatalogo, unidades_compatibles

RAIZ = Path(__file__).resolve().parent.parent
CASOS = RAIZ / "planos" / "casos"
BLOQUES = CASOS / "bloques.dxf"
REALISTA = RAIZ / "planos" / "plano_realista.dxf"


def _cat_precio(tmp_path: Path, precios: dict) -> Catalogo:
    datos = json.loads((RAIZ / "catalogo" / "conceptos.json").read_text(encoding="utf-8"))
    for c in datos["conceptos"]:
        if c["clave"] in precios:
            c["precio_unitario"] = precios[c["clave"]]
    ruta = tmp_path / "cat.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return Catalogo.cargar(ruta)


# ------------------------------------------------- tabla de compatibilidad

def test_cada_unidad_declara_sus_formas():
    assert COMPATIBLE["m2"] == {"m2"}
    assert COMPATIBLE["m"] == {"m"}
    assert "ml" in COMPATIBLE["ml"]
    assert "pza" in COMPATIBLE["pza"]


def test_m2_no_admite_m():
    assert not unidades_compatibles("m2", "m")
    assert not unidades_compatibles("m2", "pza")


def test_pza_admite_m_para_piezas_en_eje():
    """Un contacto por metro de muro es valido; por eso pza acepta m."""
    assert unidades_compatibles("pza", "m")


def test_unidad_invalida_es_error_de_catalogo():
    with pytest.raises(ErrorCatalogo):
        Concepto(clave="X", nombre="x", unidad="pies", categoria="c", patron_capa="(?i)x")


# -------------------------------------------- regresion del bug de luminarias

def test_regresion_luminarias_no_se_cobran_como_m2():
    """REGRESION: el bug original.

    Una luminaria es un circulo de radio pequeno. Antes se contabilizaba como
    superficie y el presupuesto cobraba 0.14 m2 de luminarias.

    Ahora debe contabilizarse como pieza.
    """
    r = medir(BLOQUES)
    lum = [m for m in r["mediciones"]
           if m["capa"] == "LAMPARA-PENDIENTE" and m["unidades"] == "pza"]
    assert lum, "debe existir una medicion en pza para las luminarias"
    assert lum[0]["cantidad"] == pytest.approx(4.0)

    # No debe existir ninguna medicion en m2 para luminarias.
    assert not [m for m in r["mediciones"]
                if m["capa"] == "LAMPARA-PENDIENTE" and m["unidades"] == "m2"]


def test_regresion_luminarias_importe_es_precio_por_pieza(tmp_path):
    """El importe debe ser 4 x precio (piezas), no area x precio.

    Si el bug volviera, la cantidad seria ~0.14 m2 y el importe ~119 MXN.
    """
    cat = _cat_precio(tmp_path, {"LAMPARA": 850.0})
    from app.presupuesto import construir_presupuesto

    r = medir(BLOQUES)
    p = construir_presupuesto(r["mediciones"], cat)
    lum = [l for l in p.lineas if l.clave == "LAMPARA" and l.estado == "OK"
       and l.unidad == "pza"]
    assert lum
    assert lum[0].unidad == "pza"
    assert lum[0].cantidad_ajustada == pytest.approx(4.0)
    assert lum[0].importe == pytest.approx(4 * 850.0)


# ------------------------------- incompatibilidad reportada, no silenciosa

def test_entidad_incompatible_se_reporta_con_handle():
    """Un concepto 'm' no puede absorber el area de una polilinea cerrada."""
    cat = Catalogo.cargar()
    um = cat.unidades_por_capa(["TUBO-HID"])
    assert um["TUBO-HID"] == "m"

    r = medir(CASOS / "capas_limpas.dxf", unidades_por_capa=um)
    inc = [i for i in r["entidades_incompatibles"] if i["capa"] == "TUBO-HID"]
    assert inc, "el area de TUBO-HID debe reportarse como incompatible"
    for i in inc:
        assert i["handle"], "toda incompatibilidad debe traer el handle de origen"
        assert i["motivo"]

    # Y no debe haber creado ninguna medicion m2 en esa capa.
    assert not [m for m in r["mediciones"]
                if m["capa"] == "TUBO-HID" and m["unidades"] == "m2"]


def test_incompatibilidad_no_contamina_el_resto():
    """Una capa incompatible no debe arrastrar a las demas."""
    cat = Catalogo.cargar()
    um = cat.unidades_por_capa(["Muro de Block 15 cm", "PISO-LOSETA", "cielo de  yeso"])
    r = medir(CASOS / "capas_limpas.dxf", unidades_por_capa=um)

    areas = {m["capa"]: m["cantidad"] for m in r["mediciones"] if m["unidades"] == "m2"}
    assert areas["Muro de Block 15 cm"] == pytest.approx(20.0)
    assert areas["PISO-LOSETA"] == pytest.approx(32.0)
    assert areas["cielo de  yeso"] == pytest.approx(48.0)


def test_polilinea_cerrada_aporta_area_y_perimetro():
    """Una polilinea cerrada aporta m2 y ml. Ambas deben existir."""
    r = medir(CASOS / "bulge.dxf")
    units = {m["unidades"] for m in r["mediciones"]}
    assert "m2" in units
    assert "ml" in units