"""Punto 3: el catalogo contra capas reales de despacho.

El plano planos/capas_reales.dxf reproduce la nomenclatura habitual de una
oficina de arquitectura: prefijos de disciplina, sufijos de tipo, abreviaturas
y capas de anotacion mezcladas.

Objetivo: medir la cobertura real del catalogo y fijar las brechas en tests
para que no se regrezen.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.presupuesto import Catalogo

RAIZ = Path(__file__).resolve().parent.parent
PLANO = RAIZ / "planos" / "capas_reales.dxf"


def _cat() -> Catalogo:
    return Catalogo.cargar()


# ------------------------------------------------- exclusiones obligatorias

def test_capa_de_anotacion_no_se_mapea_a_muro():
    """REGRESION DE RIESGO ALTO.

    'NOTAS-MUROS' contiene la palabra MUROS. Un patron la mapearia a muro de
    block de 15 cm y cobraria metros cuadrados de una capa de texto.
    """
    cat = _cat()
    assert cat.es_no_medible("NOTAS-MUROS") is not None
    assert cat.buscar_por_capa("NOTAS-MUROS") is None


def test_estructura_no_se_confunde_con_acabado():
    """Columnas y cimentacion se cotizan aparte, no como concepto de acabado."""
    cat = _cat()
    assert cat.es_no_medible("A-ESTRUCT-COLUMNAS") is not None
    assert cat.buscar_por_capa("A-ESTRUCT-COLUMNAS") is None


def test_capa_organizativa_por_planta_se_excluye():
    cat = _cat()
    assert cat.es_no_medible("PLANTA_ALTA") is not None
    assert cat.buscar_por_capa("PLANTA_ALTA") is None


def test_planos_de_apoyo_se_excluyen():
    cat = _cat()
    for capa in ("PERIMETRO", "CORTE-AA", "ESTIMADO-REVISADO", "TEXTOS-NOTAS"):
        assert cat.es_no_medible(capa) is not None, capa


# --------------------------------------------------------- cobertura real

def test_cubre_las_capas_reales_de_despacho():
    """Las capas con prefijo de disciplina deben mapear a un concepto."""
    cat = _cat()
    esperados = {
        "A-ESTRUCT-MUROS": "MURO_GENERICO",
        "A-PLANTA-MUROS-TAB": "MUR_BLOCK_15",
        "A-PLANTA-PISOS-LOSETA": "LOSETA",
        "A-PLANTA-PISOS-PORCELANATO": "PORCELANATO",
        "A-PLANTA-CIELOS-YESO": "CIELO_YESO",
        "ELE-TAB-DIST": "TABLERO",
        "ELE-TUBO-CONDUIT": "TUBO_ELEC",
        "ELE-CABLE-AL": "CABLE_ELEC",
        "ELE-LAMP-TIPO-A": "LAMPARA",
        "ELE-CONTACTO-DUPLEX": "CONTACTO",
        "HID-TUBO-AGUA-FRIA": "TUBO_HIDRO",
        "HID-TUBO-AGUA-CALIENTE": "TUBO_HIDRO",
        "HID-COLADERA-BANO": "COLADERA",
        "MEC-DUCTO-SUP": "DUCTO",
    }
    for capa, clave in esperados.items():
        c = cat.buscar_por_capa(capa)
        assert c is not None, "{} no mapea a nada".format(capa)
        assert c.clave == clave, "{} mapea a {} y se esperaba {}".format(
            capa, c.clave, clave)


def test_cobertura_del_plano_real_supera_el_90():
    """Criterio de cierre del punto 3: la cobertura debe quedar por encima de 90%.

    Las capas excluidas (anotacion, estructura, organizativas) NO cuentan como
    brecha: no son conceptos de acabado.
    """
    import sys
    sys.path.insert(0, str(RAIZ / "scripts"))
    from auditar_capas import auditar

    r = auditar(PLANO, _cat())
    assert r["cobertura_pct"] >= 90.0, \
        "cobertura cayo a {}%: {}".format(r["cobertura_pct"],
                                         [f["capa"] for f in r["capas"]
                                          if f["estado"] == "SIN_MAPEO"])


def test_todas_las_capas_medibles_del_plano_estan_auditadas():
    """Ninguna capa del plano debe quedar sin clasificacion."""
    import sys
    sys.path.insert(0, str(RAIZ / "scripts"))
    from auditar_capas import auditar

    r = auditar(PLANO, _cat())
    estados = {f["estado"] for f in r["capas"]}
    assert estados <= {"MAPEADO", "AMBIGUO", "SIN_MAPEO", "CAPA_EXCLUIDA"}


def test_capa_mixta_de_puerta_y_ventana_se_reporta_ambigua():
    """BRECHA CONOCIDA: 'ARQ-PUERTAS-VENTANAS' mezcla dos conceptos.

    Se resuelve por prioridad a Ventana, lo que cuenta las puertas como
    ventanas. No hay forma de separarlas sin que el usuario divida la capa.
    Se documenta como brecha, no se esconde.
    """
    import sys
    sys.path.insert(0, str(RAIZ / "scripts"))
    from auditar_capas import auditar

    r = auditar(PLANO, _cat())
    ambigua = [f for f in r["capas"] if f["capa"] == "ARQ-PUERTAS-VENTANAS"]
    assert ambigua
    assert ambigua[0]["estado"] == "AMBIGUO"
    assert "PUERTA" in ambigua[0]["otros_patrones"]


# -------------------------------------------------- en el presupuesto

def test_capa_excluida_aparece_como_tal_en_el_presupuesto():
    """Una capa excluida no es una brecha: debe decir POR QUE se excluyo."""
    from app.medidor import medir
    from app.presupuesto import construir_presupuesto

    cat = _cat()
    r = medir(PLANO, unidades_por_capa=cat.unidades_por_capa(
        ["PLANTA_ALTA", "A-ESTRUCT-COLUMNAS", "A-PLANTA-CIELOS-YESO"]))
    p = construir_presupuesto(r["mediciones"], cat)

    excluidas = p.excluidas_por_patron
    capas = {l.capa for l in excluidas}
    # Estas dos tienen geometria real y estan excluidas por catalogo.
    assert "PLANTA_ALTA" in capas
    assert "A-ESTRUCT-COLUMNAS" in capas
    assert all(l.detalle for l in excluidas), "toda capa excluida debe explicar el motivo"
    assert all(l.importe is None for l in excluidas)


def test_capa_de_anotacion_no_produce_medicion():
    """'NOTAS-MUROS' solo tiene texto: no genera cantidad, y el texto queda
    registrado en entidades_omitidas. No hay linea que cotizar."""
    from app.medidor import medir

    r = medir(PLANO)
    capas_omitidas = {o["capa"] for o in r["entidades_omitidas"]}
    assert "NOTAS-MUROS" in capas_omitidas
    assert not [m for m in r["mediciones"] if m["capa"] == "NOTAS-MUROS"]


def test_el_presupuesto_avisa_sobre_capas_excluidas():
    from app.medidor import medir
    from app.presupuesto import construir_presupuesto

    cat = _cat()
    r = medir(PLANO, unidades_por_capa=cat.unidades_por_capa(["PLANTA_ALTA"]))
    p = construir_presupuesto(r["mediciones"], cat)
    assert any("excluidas por catalogo" in a for a in p.advertencias())


def test_muro_generico_es_de_prioridad_menor_que_el_especifico():
    """'MUROS' a secas cae en el concepto generico, no en muro de block."""
    cat = _cat()
    assert cat.buscar_por_capa("MUROS").clave == "MURO_GENERICO"
    assert cat.buscar_por_capa("MURO-BLOCK-15CM").clave == "MUR_BLOCK_15"
    assert cat.buscar_por_capa("MURO-TABIQUE").clave == "TABA_10"