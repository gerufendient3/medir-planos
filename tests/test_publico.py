"""Comprueba que las piezas publicas no contienen afirmaciones no verificadas.

Este es el guardarrail de la regla de oro. Si alguien pega un testimonio o un
numero de usuarios en el HTML, esta prueba falla.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "publico"

LANDING = PUBLICO / "landing.html"
KIT = PUBLICO / "kit.html"
DEMO = PUBLICO / "demo.html"


@pytest.fixture(scope="module")
def landing() -> str:
    return LANDING.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def kit() -> str:
    return KIT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def demo() -> str:
    return DEMO.read_text(encoding="utf-8")


# ------------------------------------------- las tres piezas existen

def test_las_tres_piezas_existen():
    for f in (LANDING, KIT, DEMO):
        assert f.exists(), f
        assert f.stat().st_size > 3000, "{} parece vacio".format(f.name)


# --------------------------------- prohibiciones: nada de tracción inventada

def test_no_hay_testimonios(landing: str, demo: str):
    """No puede haber citas de clientes, porque no hay clientes."""
    prohibido = ["testimonio", "cliente dice", "nos dice", "resultados de",
                 "ahorra 40%", "más de 100", "clientes felices"]
    for term in prohibido:
        assert term not in landing.lower(), "landing menciona '{}'".format(term)
        assert term not in demo.lower(), "demo menciona '{}'".format(term)


def test_no_hay_numeros_de_usuarios(landing: str, demo: str):
    """Cero usuarios registrados. Ningún número de usuarios puede aparecer."""
    patrones = [
        r"\d+\s*(?:contratistas|estimadores|usuarios|empresas)\s+(?:ya\s+)?(?:usan|utilizan|confían)",
        r"(?:mas|más)\s+de\s+\d+\s+(?:usuarios|clientes|empresas)",
        r"\d+\s*usuarios\s+registrados",
    ]
    for p in patrones:
        assert not re.search(p, landing.lower(), re.IGNORECASE), \
            "landing tiene un numero de usuarios: {}".format(p)
        assert not re.search(p, demo.lower(), re.IGNORECASE), \
            "demo tiene un numero de usuarios: {}".format(p)


def test_no_se_declara_validado_con_planos_reales(landing: str, demo: str):
    """Es la prohibido por ley propia: no se ha probado con planos reales."""
    prohibido = ["validado con planos reales", "probado con planos reales",
                 "planes reales de mexico", "con clientes reales"]
    for term in prohibido:
        assert term not in landing.lower(), "landing: '{}'".format(term)
        assert term not in demo.lower(), "demo: '{}'".format(term)


def test_no_comparaciones_con_competidores(landing: str):
    """No se nombran competidores: sin fuente verificada es propaganda."""
    competidores = ["bluebeam", "planswift", "costx", "onscreen takeoff"]
    for c in competidores:
        assert c not in landing.lower(), \
            "la landing menciona a {} sin fuente".format(c)


# ------------------------------------------------- los precios como hipótesis

def test_no_hay_precio_en_la_landing(landing: str):
    """Es una herramienta gratuita: no hay precio en ninguna forma."""
    for term in ["$149", "$299", "149 - 299", "hipotesis de precio",
                 "precio de lanzamiento", "USD"]:
        assert term.lower() not in landing.lower(), "landing menciona '{}'".format(term)
    assert "Software libre, gratuito y sin cuentas" in landing or \
           "Software libre y gratuito" in landing


def test_no_hay_formulario_de_captacion(landing: str):
    """Nada que parezca guardar datos si no guarda nada."""
    assert "<form" not in landing.lower(), "la landing no debe tener formularios"
    for term in ["action=\"#\"", "type=\"email\"", "correo para avisarte"]:
        assert term.lower() not in landing.lower(), "landing tiene '{}'".format(term)


def test_no_hay_checkout_ni_pago(landing: str):
    for term in ["comprar ahora", "añadir al carrito", "contratar ahora",
                 "tarjeta", "credit card", "paypal", "suscripción"]:
        assert term.lower() not in landing.lower(), "landing tiene '{}'".format(term)


def test_la_landing_declara_su_no_validacion(landing: str):
    assert "No se ha procesado ningún plano de obra real" in landing
    assert "No es un software de certificación" in landing
    assert "de ejemplo" in landing


def test_la_landing_dice_que_el_reporte_no_se_envia(landing: str):
    assert "No envía nada a ningún servidor" in landing
    assert "no adjunta el plano" in landing


def test_la_landing_licencia_mit():
    landing = (PUBLICO / "landing.html").read_text(encoding="utf-8")
    assert "MIT" in landing
    assert (PUBLICO.parent / "LICENSE").exists()


def test_la_landing_explica_la_uso():
    landing = (PUBLICO / "landing.html").read_text(encoding="utf-8")
    assert "uvicorn app.web:app" in landing
    assert "requirements.txt" in landing


def test_no_hay_campos_de_tarjeta_o_pago():
    for f in (LANDING, DEMO):
        t = f.read_text(encoding="utf-8").lower()
        for term in ["tarjeta", "credit card", "paypal", "cvv"]:
            assert term not in t, "{} menciona pago: {}".format(f.name, term)


def test_los_precios_del_presupuesto_son_de_ejemplo(demo: str):
    assert "EJEMPLO" in demo or "ejemplo" in demo
    assert "no son precios de mercado" in demo.lower()


# ------------------------------------------------------- honestidad del demo

def test_el_demo_dice_que_no_puede_medir_un_plano_real(demo: str):
    """El riesgo principal esta a la vista, no escondido."""
    assert "NO se puede medir" in demo or "no puede medir" in demo.lower()
    assert "ESCANEADO" in demo or "escaneado" in demo.lower()


def test_el_demo_muestra_las_tres_partidas_manuales(demo: str):
    assert "Cálculo manual" in demo
    # Al menos tres filas con la estructura: calculo, importe, herramienta
    assert demo.count("</td><td><b>") >= 3


def test_el_demo_muestra_los_handles(demo: str):
    """La trazabilidad es la propuesta de valor central."""
    assert "handle" in demo.lower()
    assert "class='handles'" in demo or "class=\"handles\"" in demo


def test_el_demo_tiene_seccion_de_limitaciones(demo: str):
    assert "NO sabe hacer" in demo


def test_el_demo_declara_las_fuentes(demo: str):
    assert "Fuentes y licencias" in demo
    assert "Dominio publico" in demo or "Dominio público" in demo
    assert "CC BY-SA 4.0" in demo


def test_el_demo_avisa_que_no_hay_validacion_real(demo: str):
    assert "planos de obra reales" in demo.lower()


# ------------------------------------------------------ formulario honesto

def test_el_reporte_explica_que_no_se_envia(landing: str):
    """El boton de reporte copia un texto; no hay backend detras."""
    assert "No envía nada a ningún servidor" in landing


# ------------------------------------------- catalogo y precios de ejemplo

def test_los_precios_de_demo_no_cuentan_dos_veces():
    """La demo y el catalogo de ejemplo deben decir los mismos numeros.

    Antes cada uno tenia su propia copia y podian divergir sin que nada lo
    notara: la pagina mostraba un total que el catalogo no justificaba.
    """
    import json
    import sys

    sys.path.insert(0, str(RAIZ / "scripts"))
    import generar_demo

    datos = json.loads(
        (RAIZ / "catalogo" / "demo_precios.json").read_text(encoding="utf-8"))
    desde_archivo = {
        c["clave"]: c["precio_unitario"] for c in datos["conceptos"]
        if c.get("precio_unitario") not in (None, "")
    }
    assert generar_demo.PRECIOS_EJEMPLO == desde_archivo


def test_el_catalogo_del_proyecto_no_trae_precios():
    """conceptos.json nunca debe traer precios: no hay fuente para ellos."""
    import json

    datos = json.loads(
        (RAIZ / "catalogo" / "conceptos.json").read_text(encoding="utf-8"))
    assert datos["conceptos"], "el catálogo no puede estar vacío"
    for c in datos["conceptos"]:
        assert c.get("precio_unitario") is None, \
            "{} trae precio sin fuente".format(c["clave"])


def test_los_precios_de_ejemplo_dicen_no_ser_de_mercado():
    """El archivo de precios de ejemplo debe decirlo en su propio _meta."""
    import json

    datos = json.loads(
        (RAIZ / "catalogo" / "demo_precios.json").read_text(encoding="utf-8"))
    texto = " ".join(datos["_meta"]["avisos"]).lower()
    assert "no son precios de mercado" in texto
    assert "ejemplo" in texto


def test_los_catalogos_no_traen_texto_de_otro_idioma():
    """Chinese, cirilico o hebreo en un catalogo es texto sin traducir."""
    import re

    rangos = [r"[\u4e00-\u9fff]", r"[\u0400-\u04ff]", r"[\u0590-\u05ff]",
              r"[\u0600-\u06ff]", r"[\u0900-\u097f]"]
    for f in sorted((RAIZ / "catalogo").glob("*.json")):
        texto = f.read_text(encoding="utf-8")
        for patron in rangos:
            m = re.search(patron, texto)
            assert m is None, "{} tiene texto sin traducir: {}".format(
                f.name, texto[max(0, m.start() - 40):m.end() + 40]
                if m else "")


def test_el_auditor_de_catalogo_pasa():
    """El script de auditoria debe salir con codigo 0 sobre el arbol real."""
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "auditar_catalogo.py")],
        cwd=str(RAIZ), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_las_fuentes_coinciden_con_los_archivos():
    """FUENTES.md debe describir los archivos que estan en el arbol.

    Sin --red: las licencias de Commons se comprobaron a mano con la API y
    quedan en FUENTES.md. En CI no hay red y una prueba que dependa de ella
    fallaria sola.
    """
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "verificar_fuentes.py")],
        cwd=str(RAIZ), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_toda_url_de_fuentes_esta_verificada():
    """Ninguna URL puede quedar marcada como no verificada sin decirlo.

    Si alguien agrega una fuente nueva, tiene que anotarlo. Este test
    comprueba que la lista de URLs del documento no crezca en silencio.
    """
    texto = (RAIZ / "docs" / "FUENTES.md").read_text(encoding="utf-8")
    # Los paréntesis son parte de estos títulos de archivo ("(2).pdf"), así
    # que un patrón que corte en ')' trunca la URL. Se toma hasta el espacio
    # y solo se quita la puntuación final de frase.
    urls = {u.rstrip(".,;:") for u in re.findall(r"https?://[^\s|]+", texto)}
    declaradas = {
        "https://creativecommons.org/licenses/by-sa/4.0",
        "https://commons.wikimedia.org/wiki/"
        "File:Harlem_Meer_Restaurant_Dwg_-2_-_1990-08-01_-_"
        "First_Floor_Plan_(2).pdf",
        "https://commons.wikimedia.org/wiki/"
        "File:Floor_plan_of_a_5-bedroom_house_(IA_CAT31371083).pdf",
        "https://archive.org/details/CAT31371083",
    }
    nuevas = urls - declaradas
    assert not nuevas, (
        "URLs nuevas sin verificar en FUENTES.md: {}. Ábrelas, confirma que "
        "dicen lo que el documento afirma y añádelas a la lista de "
        "verificadas en el test.".format(nuevas))


def test_el_indice_de_casos_coincide_con_la_suite():
    """docs/CASOS.md no debe prometer tests que no existen.

    Pasó: el documento declaraba 7 casos en PASA cuyos tests no estaban en
    la suite. El índice se escribe a mano y se queda viejo sin avisar.
    """
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "verificar_casos.py")],
        cwd=str(RAIZ), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


# ------------------------------------------------------------------ varios

def test_no_hay_placeholders_sin_reemplazar(demo: str, landing: str, kit: str):
    """Un '{' suelto en el cuerpo significa que una plantilla no se renderizó.

    Se excluyen <style> (CSS legitimo) y <code> (ejemplos de texto).
    """
    import re as _re

    for nombre, texto in (("demo", demo), ("landing", landing), ("kit", kit)):
        limpio = _re.sub(r"<style>.*?</style>", "", texto, flags=_re.S)
        limpio = _re.sub(r"<code>.*?</code>", "", limpio, flags=_re.S)
        limpio = _re.sub(r"<script>.*?</script>", "", limpio, flags=_re.S)
        assert "{" not in limpio, "{} tiene una llave sin resolver".format(nombre)
        assert "}" not in limpio, "{} tiene una llave sin resolver".format(nombre)


# ------------------------------------------------------------- kit de entrevista

def test_el_kit_no_presupone_el_precio(kit: str):
    """Como es gratuita, lo importante es aclararlo de entrada."""
    assert "Abre aclarando que es gratuita" in kit
    assert "No presumas el rango" in kit or "No hay precio" in kit
    # El rango viejo ya no debe aparecer por ningun lado.
    assert "149" not in kit and "299" not in kit


def test_el_kit_tiene_preguntas_de_disposicion_a_pagar(kit: str):
    assert "cuánto valdría" in kit.lower()
    assert "Disposición a pagar" in kit


def test_el_kit_dice_que_es_gratuito(kit: str):
    """El guion debe abrir aclarando que no hay nada que comprar."""
    assert "gratuit" in kit.lower() or "no hay nada que comprar" in kit.lower()


# ------------------------------------------------- reproducibilidad

def test_los_datos_crudos_de_la_demo_se_guardan():
    datos = PUBLICO / "demo_datos.json"
    assert datos.exists(), "sin datos crudos no se puede verificar la demo"
    import json

    d = json.loads(datos.read_text(encoding="utf-8"))
    assert "caso_a_rasterizado" in d
    assert d["caso_a_rasterizado"]["objetos_vectoriales"] == 0
    assert len(d["fuentes"]) >= 3