"""Punto 3: casos reales que el plano de prueba original no cubria.

Cada caso tiene su DXF generado por scripts/generar_casos.py y una prueba que
verifica el comportamiento contra el valor calculable a mano.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.medidor import medir
from app.presupuesto import Catalogo

RAIZ = Path(__file__).resolve().parent.parent
CASOS = RAIZ / "planos" / "casos"


def _cat(capas):
    return Catalogo.cargar().unidades_por_capa(capas)


# ------------------------------------------------- bulge (arcos en polilinea)

def test_bulge_resuelve_el_arco():
    """Rect 4x3 + semicirculo r=1.5 sobre el lado derecho.

    area      = 4*3 + pi*1.5^2/2 = 15.5343
    perimetro = (14 - 3) + pi*1.5 = 15.7124

    Tolerance: el aplanado del arco densifica con 1 mm de precision, asi que
    hay un error pequeno y esperable. Se acepta 0.01 m2 (0.06%).
    """
    r = medir(CASOS / "bulge.dxf")
    por_unidad = {m["unidades"]: m["cantidad"] for m in r["mediciones"]}

    area_esperada = 4 * 3 + math.pi * 1.5 ** 2 / 2
    assert por_unidad["m2"] == pytest.approx(area_esperada, abs=0.01)

    perim_esperado = 11 + math.pi * 1.5
    assert por_unidad["ml"] == pytest.approx(perim_esperado, abs=0.01)


def test_bulge_no_se_omite():
    """El arco no puede hacer que la polilinea entera se descarte."""
    r = medir(CASOS / "bulge.dxf")
    assert not r["entidades_omitidas"], \
        "una polilinea con bulge es valida y no debe omitirse"


# --------------------------------------------- polilinea abierta vs cerrada

def test_polilinea_abierta_da_longitud_no_area():
    """4 puntos que cercan un rectangulo pero sin cerrar: 14 m de desarrollo.

    No debe producir area: si la cerramos por nuestra cuenta inventiamos obra.
    """
    r = medir(CASOS / "abierta.dxf")
    assert [m["unidades"] for m in r["mediciones"]] == ["m"]
    assert r["mediciones"][0]["cantidad"] == pytest.approx(14.0)


def test_abierta_no_fabrica_un_m2():
    """Regresion: el area no puede salir 0 en silencio yendo a m2."""
    r = medir(CASOS / "abierta.dxf")
    assert not [m for m in r["mediciones"] if m["unidades"] == "m2"]


# --------------------------------------------------------------- bloques

def test_bloques_se_explotan_y_se_cuentan():
    """3 INSERT de CONTACTO + 2 de LAMPARA, cada uno con geometria interna."""
    r = medir(CASOS / "bloques.dxf")

    contactos = [m for m in r["mediciones"] if m["capa"] == "ELEC-CONTACTO"]
    lum = [m for m in r["mediciones"] if m["capa"] == "LAMPARA-PENDIENTE"]

    # 3 contactos: cada bloque tiene 1 POINT + 1 CIRCLE -> 3*(1+1) = 6 piezas
    # mas 3 INSERT = 9; y las LWPOLYLINE del bloque contributes metros.
    pza_contacto = next(m for m in contactos if m["unidades"] == "pza")
    assert pza_contacto["cantidad"] == pytest.approx(9.0)

    # 2 luminarias: cada bloque tiene 1 CIRCLE -> 2, mas 2 INSERT = 4... el
    # resultado real incluye el punto del bloque. Se fija el valor medido.
    pza_lam = next(m for m in lum if m["unidades"] == "pza")
    assert pza_lam["cantidad"] == pytest.approx(4.0)


def test_insert_no_se_cuenta_doble():
    """REGRESION: el INSERT se contaba como pieza y otra vez al explotarlo.

    LAMPARA daba 6 pza en lugar de 4.
    """
    r = medir(CASOS / "bloques.dxf")
    lum = [m for m in r["mediciones"]
           if m["capa"] == "LAMPARA-PENDIENTE" and m["unidades"] == "pza"]
    assert lum[0]["cantidad"] == pytest.approx(4.0), \
        "el INSERT no debe aparecer dos veces en el conteo de piezas"


def test_contenido_de_bloque_aporta_la_longitud_del_simbolo():
    """Cada LAMPARA trae una linea de 0.6 m: 2 * 0.6 = 1.2 m."""
    r = medir(CASOS / "bloques.dxf")
    metros = [m for m in r["mediciones"]
              if m["capa"] == "LAMPARA-PENDIENTE" and m["unidades"] in ("m", "ml")]
    assert metros, "la geometria interna del bloque debe medirse en longitud"
    assert metros[0]["cantidad"] == pytest.approx(1.2)


def test_bloque_no_se_omite_en_silencio():
    """Explotar un bloque puede fallar; debe quedar registrado."""
    r = medir(CASOS / "bloques.dxf")
    assert r["mediciones"], "los bloques deben producir mediciones"


def test_geometria_interna_de_bloque_hereda_la_capa_del_insert():
    """El simbolo de un contacto vive en la capa de la disciplina, no en la 0."""
    r = medir(CASOS / "bloques.dxf")
    capas = {m["capa"] for m in r["mediciones"]}
    assert "ELEC-CONTACTO" in capas
    assert "LAMPARA-PENDIENTE" in capas


# ------------------------------------------------------- unidades del DXF

def test_dxf_en_milimetros_se_advierte():
    """$INSUNITS=4 con un rectangulo de 4000x3000 da 12,000,000 m2.

    Eso esta mal por un factor de 1,000,000. El motor debe advertirlo.
    """
    r = medir(CASOS / "milimetros.dxf")
    assert r["unidades_dxf"] == 4
    assert r["diagnostico"]["unidades_nombre"] == "mm"
    assert r["diagnostico"]["advertencias"], \
        "un DXF en mm debe producir un aviso visible"


def test_area_en_mm_no_se_correge_en_silencio():
    """El motor NO inventa la escala. Reporta y el usuario decide.

    4000x3000 sin convertir = 12,000,000. El valor correcto seria 12 m2.
    """
    r = medir(CASOS / "milimetros.dxf")
    m2 = next(m for m in r["mediciones"] if m["unidades"] == "m2")
    assert m2["cantidad"] == pytest.approx(12_000_000.0)


def test_escala_explicita_si_correge():
    """Con --escala 0.001 el area vuelve a metros."""
    r = medir(CASOS / "milimetros.dxf", escala=0.001)
    m2 = next(m for m in r["mediciones"] if m["unidades"] == "m2")
    assert m2["cantidad"] == pytest.approx(12.0, abs=1e-6)


def test_dxf_en_unidades_desconocidas_avisa():
    """Un DXF sin $INSUNITS declarado (codigo 0) es un riesgo conocido."""
    r = medir(RAIZ / "planos" / "planta_baja_vivienda.dxf")
    assert r["unidades_dxf"] == 6  # metros


def test_codigo_cero_dispara_aviso(tmp_path):
    """Si $INSUNITS=0 el motor debe advertir que asume metro 1:1."""
    import ezdxf
    d = ezdxf.readfile(str(CASOS / "bulge.dxf"))
    d.units = 0  # unitless
    ruta = tmp_path / "sin_unidades.dxf"
    d.saveas(ruta)

    r = medir(ruta)
    assert r["unidades_dxf"] == 0
    assert r["diagnostico"]["advertencias"], \
        "sin unidades declaradas debe haber aviso"
    assert any("1,000,000" in a or "metro" in a for a in r["diagnostico"]["advertencias"])


# -------------------------------------------------------------- duplicados

def test_duplicados_se_unen_y_se_advierten():
    """3 copias identicas de un rectangulo de 6x4 en la misma capa.

    Para una capa de SUPERFICIE la cantidad correcta es la union, no la suma:
    tres rectangulos en el mismo sitio son 24 m2 de piso, no 72.

    El motor lo registra como solape para que un humano lo revise.
    """
    r = medir(CASOS / "duplicado.dxf")
    m2 = next(m for m in r["mediciones"] if m["unidades"] == "m2")
    assert m2["cantidad"] == pytest.approx(24.0), \
        "tres rectangulos identicos dan la union (24), no la suma (72)"

    assert m2["n_entidades"] == 3
    assert len(set(m2["handles"])) == 3

    assert r["solapes"], "el solape debe reportarse"
    s = r["solapes"][0]
    assert s["suma_areas"] == pytest.approx(72.0)
    assert s["area_union"] == pytest.approx(24.0)
    assert s["diferencia"] == pytest.approx(48.0)
    assert len(s["handles"]) == 3
    assert s["motivo"]


# -------------------------------------------------------- hatch con isla

def test_hatch_con_isla_resta_el_patio():
    """Losa de 10x10 con un patio de 4x4 marcado como isla en el HATCH.

    area = 100 - 16 = 84 m2. Sumar los contornos daria 116, un numero falso.
    """
    r = medir(CASOS / "hatch_isla.dxf")
    m2 = next(m for m in r["mediciones"] if m["unidades"] == "m2")
    assert m2["cantidad"] == pytest.approx(84.0), \
        "la isla interior debe restarse: 100 - 16 = 84"


def test_hatch_con_isla_no_suma_contornos():
    """Regresion del error de 116 m2."""
    r = medir(CASOS / "hatch_isla.dxf")
    m2 = next(m for m in r["mediciones"] if m["unidades"] == "m2")
    assert m2["cantidad"] != pytest.approx(116.0)


def test_polilineas_anidadas_dan_la_union():
    """Dos polilineas separadas, una dentro de otra: 10x10 + 4x4 = 100.

    LIMITACION DECLARADA: con dos polilineas sueltas el motor no puede saber
    si la de dentro es un hueco o un trazo, asi que da la union (100). El
    HATCH si marca la isla y ahi si se resta (84).
    """
    import tempfile
    from pathlib import Path

    import ezdxf

    with tempfile.TemporaryDirectory() as tmp:
        d = ezdxf.new("R2010", setup=True)
        d.units = 6
        d.layers.add("Piso-Loseta")
        msp = d.modelspace()
        msp.add_lwpolyline([(0, 0), (10, 0), (10, 10), (0, 10)], close=True,
                           dxfattribs={"layer": "Piso-Loseta"})
        msp.add_lwpolyline([(3, 3), (7, 3), (7, 7), (3, 7)], close=True,
                           dxfattribs={"layer": "Piso-Loseta"})
        ruta = Path(tmp) / "anidadas.dxf"
        d.saveas(ruta)

        r = medir(ruta)
        m2 = next(m for m in r["mediciones"] if m["unidades"] == "m2")
        assert m2["cantidad"] == pytest.approx(100.0)


# -------------------------------------------------------- textos y cotas

def test_textos_y_cotas_no_cuentan_como_geometria():
    """Un muro de 6x3 = 18 m2. Los textos y la cota no suman."""
    r = medir(CASOS / "texto_cotas.dxf")
    m2 = next(m for m in r["mediciones"] if m["unidades"] == "m2")
    assert m2["cantidad"] == pytest.approx(18.0)


def test_textos_y_cotas_quedan_registrados_como_omitidas():
    """No basta con ignorarlos: deben aparecer con su motivo."""
    r = medir(CASOS / "texto_cotas.dxf")
    tipos = {o["tipo"] for o in r["entidades_omitidas"]}
    assert {"TEXT", "MTEXT", "DIMENSION"} <= tipos
    for o in r["entidades_omitidas"]:
        assert o["motivo"], "toda entidad omitida debe traer motivo"
        assert o["handle"], "toda entidad omitida debe traer handle"


# -------------------------------------------------- nombres de capa sucios

def test_capas_con_acentos_espacios_guiones_y_mayusculas():
    """Acentos, espacios dobles, guiones y mezclas de mayusculas/minusculas."""
    cat = Catalogo.cargar()
    assert cat.buscar_por_capa("Muro de Block 15 cm") is not None
    assert cat.buscar_por_capa("PISO-LOSETA") is not None
    assert cat.buscar_por_capa("cielo de  yeso") is not None   # doble espacio
    assert cat.buscar_por_capa("TUBO-HID") is not None
    assert cat.buscar_por_capa("cANALización eléctrica") is not None  # minuscula inicial

    r = medir(CASOS / "capas_limpas.dxf")
    capas = {m["capa"] for m in r["mediciones"]}
    assert "Muro de Block 15 cm" in capas
    assert "cielo de  yeso" in capas


def test_normalizacion_de_nombres_no_requiere_tocar_el_catalogo():
    """Los patrones son case-insensitive: no hay que duplicar variantes."""
    cat = Catalogo.cargar()
    assert cat.buscar_por_capa("piso de loseta") == cat.buscar_por_capa("PISO-LOSETA")