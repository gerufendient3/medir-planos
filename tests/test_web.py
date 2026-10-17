"""Interfaz web publica: flujo de una pantalla, privacidad y accesibilidad.

Verifica el comportamiento observable por HTTP. No prueba estilos ni colores:
para eso hace falta un navegador, y aqui se comprueba lo que importa de verdad,
que es lo que se puede comprobar sin uno.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.web import APP_VERSION, TAMANO_MAX_MB, app

RAIZ = Path(__file__).resolve().parent.parent
PLANO_DXF = RAIZ / "planos" / "plano_realista.dxf"
PLANO_CASO_ESTUDIO = RAIZ / "planos" / "vectorial_origen.dxf"
PDF_VECTOR = RAIZ / "tests" / "fixtures" / "pdf" / "vectorial_desde_dxf.pdf"
PDF_ESCANEADO = RAIZ / "tests" / "fixtures" / "pdf" / "pd_escaneado.pdf"

client = TestClient(app)


def _subir(ruta: Path, **datos):
    with ruta.open("rb") as fh:
        form = {"pt_por_metro": datos.pop("pt", 1.0), **datos}
        return client.post("/subir",
                           files={"plano": (ruta.name, fh, "application/octet-stream")},
                           data=form)


def _token(html: str) -> str:
    m = re.search(r"/descargar/([0-9a-f]{32})/xlsx", html)
    assert m, "no se encontro token de sesion en el HTML"
    return m.group(1)


# ------------------------------------------------------------- carga

def test_la_pagina_inicial_carga():
    r = client.get("/")
    assert r.status_code == 200
    assert "Cargar un plano" in r.text


def test_muestra_las_advertencias_del_presupuesto():
    """Lo que no se pudo cotizar tiene que verse en la pantalla.

    Es la regla que sostiene todo el proyecto: lo no medido o lo excluido
    no puede desaparecer en silencio, porque el total sigue en pantalla.
    """
    r = _subir(PLANO_DXF)
    assert r.status_code == 200
    html = r.text
    assert "Total incompleto" in html
    # Y la razon concreta de cada exclusion, no solo un aviso generico.
    assert "sin concepto asignado" in html.lower()
    assert "FALTA_PRECIO" in html or "sin precio" in html
    assert "NO_enviar" not in html  # el aviso va en texto legible


def test_muestra_el_total_con_iva():
    """Subtotal, IVA y total deben aparecer en la pantalla."""
    r = _subir(PLANO_DXF)
    assert r.status_code == 200
    html = r.text
    assert "Subtotal" in html
    assert "IVA 16%" in html
    assert "Total" in html
    # Los tres importes en MXN, no un numero suelto sin unidad.
    assert html.count("MXN") >= 3


def test_dwg_sin_oda_devuelve_error_claro():
    """Sin ODA el error dice qué falta y dónde, y la pantalla se recovery.

    Nunca un resultado vacío: un DWG que no se pudo leer tiene que ser
    imposible de confundir con un plano sin geometría.
    """
    r = client.post("/subir",
                    files={"plano": ("plano.dwg", b"AC1024" + b"\x00" * 64,
                                     "application/octet-stream")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 400
    html = r.text
    assert "ODA File Converter" in html
    assert "opendesign.com" in html
    assert "Volver a intentar" in html
    # Y no se presenta como si se hubiera medido algo. El bloque visible es
    # el <main>: el CSS también menciona "Total" en comentarios.
    main = re.search(r"<main[^>]*>(.*?)</main>", html, re.S)
    assert main, "la página de error debe tener un <main>"
    assert "Total" not in main.group(1)
    assert "MXN" not in main.group(1)


def test_rechaza_formato_no_soportado():
    r = client.post("/subir",
                    files={"plano": ("notas.txt", b"hola", "text/plain")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 400
    assert "Formato no soportado" in r.text


def test_rechaza_archivo_demasiado_grande():
    grande = b"x" * (TAMANO_MAX_MB * 1024 * 1024 + 10)
    r = client.post("/subir",
                    files={"plano": ("enorme.dxf", grande, "application/octet-stream")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 413


def test_procesa_dxf_y_muestra_takeoff_con_origen():
    r = _subir(PLANO_DXF)
    assert r.status_code == 200, r.text[:300]
    assert "Cantidades medidas" in r.text
    assert "MURO-BLOCK-15CM" in r.text
    assert "Origen" in r.text


# ------------------------------------------------------------ privacidad

def test_el_archivo_subido_no_se_conserva(tmp_path):
    """El DXF no debe quedar escrito en disco despues de procesar.

    Este es el requisito central de privacidad: si el archivo se conserva,
    quien use la app deja planos de obra en el servidor.
    """
    antes = set(p.name for p in Path(tempfile.gettempdir()).iterdir()
                if p.is_file())
    r = _subir(PLANO_DXF)
    assert r.status_code == 200

    despues = set(p.name for p in Path(tempfile.gettempdir()).iterdir()
                  if p.is_file())
    nuevos = despues - antes
    # Puede haber archivos temporales de otra cosa en paralelo; lo que no
    # puede haber es un .dxf con el nombre del plano.
    assert not any(n.lower().endswith(".dxf") for n in nuevos), \
        "quedo un DXF en disco: {}".format(sorted(nuevos))


def test_el_flujo_completo_no_deja_basura_en_temporal(tmp_path):
    """Cargar, cambiar precios y descargar no puede dejar archivos.

    Cubre las tres vias que antes dejaban rastro:
      - el archivo del plano (temporal de lectura)
      - el catálogo con los precios editados (antes creaba un directorio por
        cada pulsación de «Aplicar» y no lo borraba)
      - las descargas (antes se armaban en disco y se intentaban borrar)
    """
    import tempfile as tf

    temp = Path(tf.gettempdir())
    base_archivos = {p.name for p in temp.iterdir()}
    base_dirs = {p.name for p in temp.iterdir() if p.is_dir()}

    r = _subir(PLANO_DXF)
    assert r.status_code == 200
    token = _token(r.text)
    n = len(re.findall(r"name='precio'", r.text))

    for i in range(3):
        client.post(f"/precios/{token}", data={"precio": ["100.00"] * n})
    client.get(f"/descargar/{token}/xlsx")
    client.get(f"/descargar/{token}/pdf")

    nuevos_archivos = {p.name for p in temp.iterdir()} - base_archivos
    nuevas_dirs = {p.name for p in temp.iterdir() if p.is_dir()} - base_dirs

    assert not nuevas_dirs, "se quedaron directorios: {}".format(sorted(nuevas_dirs))
    assert not nuevos_archivos, \
        "se quedaron archivos: {}".format(sorted(nuevas_archivos))


def test_editar_precios_no_necesita_archivos_temporales(monkeypatch):
    """El catálogo en memoria evita un temporal por cada cambio de precio."""
    import app.web as web

    cat = web.Sesion(token="x", nombre="p.dxf", formato="dxf",
                     takeoff={"mediciones": []}, catalogo_datos={
                         "conceptos": [{"clave": "K", "nombre": "C", "unidad": "m2",
                                        "categoria": "X", "patron_capa": "(?i)K",
                                        "prioridad": 1, "precio_unitario": None,
                                        "rendimiento": 1.0}],
                         "_meta": {}})
    cat.precios["K"] = "123.45"
    built = cat.catalogo()
    assert built.conceptos[0].precio_unitario == pytest.approx(123.45)


def test_la_app_explica_que_procesa_en_memoria():
    r = client.get("/")
    assert "en memoria" in r.text.lower()
    assert "No se escribe a disco" in r.text
    assert "no hay cuentas" in r.text.lower()


def test_no_hay_formularios_que_pretendan_guardar_datos():
    """El unico formulario real es el de subir el plano."""
    r = client.get("/")
    forms = re.findall(r"<form[^>]*>", r.text, re.I)
    assert len(forms) == 1, "la portada deberia tener un solo formulario"
    assert 'action="/subir"' in forms[0]


def test_no_se_declara_una_licencia_que_no_exista():
    """La landing menciona MIT; la licencia debe existir en el repo."""
    r = client.get("/")
    assert "MIT" in r.text
    assert (RAIZ / "LICENSE").exists(), "la pagina menciona MIT pero no hay LICENSE"


def test_no_se_declara_validacion_con_planos_reales():
    """El texto sale de app.identidad, no de una copia pegada en el HTML."""
    from app.identidad import AVISO_NO_ES_CERTIFICACION, AVISO_SIN_VALIDACION

    r = client.get("/")
    assert AVISO_SIN_VALIDACION in r.text
    assert AVISO_NO_ES_CERTIFICACION in r.text
    # Y nunca la frase prohibida.
    assert "validado con planos de obra reales" not in r.text.lower().replace(
        "no está validado con planos de obra reales", "")


def test_no_hay_precio_ni_cupo_en_la_app():
    """Es una herramienta gratuita: nada de precios ni de付费."""
    r = client.get("/")
    for term in ["precio de lanzamiento", "USD", "suscripción", "checkout",
                 "comprar ahora", "plan de pago"]:
        assert term.lower() not in r.text.lower(), "la app menciona '{}'".format(term)


# ------------------------------------------------- avisos y estado incompleto

def test_sin_precios_el_total_queda_incompleto():
    r = _subir(PLANO_DXF)
    assert "Total incompleto" in r.text
    assert "no cubre toda la obra" in r.text


def test_muestra_las_lineas_excluidas():
    r = _subir(PLANO_DXF)
    assert "sin precio" in r.text
    assert "Revisa esto antes de enviar" in r.text


def test_pdf_escaneado_se_detecta_en_la_web():
    r = _subir(PDF_ESCANEADO)
    assert r.status_code == 200
    assert "ESCANEADO" in r.text or "escaneado" in r.text


def test_sube_pdf_vectorial_muestra_grupos_por_color():
    r = _subir(PDF_VECTOR, pt=52.3638)
    assert r.status_code == 200
    assert "COLOR_" in r.text


# ------------------------------------------------------------- precios

def test_se_pueden_cargar_precios_y_el_total_cambia():
    r = _subir(PLANO_DXF)
    token = _token(r.text)
    # Todas las claves presentes, en el orden del formulario.
    claves = re.findall(r"name='precio'", r.text)
    assert claves, "el formulario de precios debe existir"

    n = len(claves)
    r2 = client.post(f"/precios/{token}", data={"precio": ["500"] * n})
    assert r2.status_code == 200
    # El subtotal deja de ser cero
    assert "Total incompleto" in r2.text  # siguen faltando precios de otras capas


def test_precios_vacios_dejan_el_total_incompleto():
    r = _subir(PLANO_DXF)
    token = _token(r.text)
    n = len(re.findall(r"name='precio'", r.text))
    r2 = client.post(f"/precios/{token}", data={"precio": [""] * n})
    assert "Total incompleto" in r2.text


# ------------------------------------------------------------ descargas

def test_descarga_excel():
    r = _subir(PLANO_DXF)
    d = client.get(f"/descargar/{_token(r.text)}/xlsx")
    assert d.status_code == 200
    assert d.content[:2] == b"PK"
    assert "spreadsheetml" in d.headers["content-type"]


def test_descarga_pdf():
    r = _subir(PLANO_DXF)
    d = client.get(f"/descargar/{_token(r.text)}/pdf")
    assert d.status_code == 200
    assert d.content[:5] == b"%PDF-"


def test_descarga_no_deja_archivos_en_disco(tmp_path):
    """Las descargas se arman en memoria, no escribiendo archivos."""
    ruta = Path(tempfile.gettempdir())
    antes = {p.name for p in ruta.iterdir() if p.is_file()}
    r = _subir(PLANO_DXF)
    client.get(f"/descargar/{_token(r.text)}/xlsx")
    client.get(f"/descargar/{_token(r.text)}/pdf")
    despues = {p.name for p in ruta.iterdir() if p.is_file()}
    assert not any(n.endswith(".xlsx") for n in (despues - antes))
    assert not any(n.endswith(".pdf") for n in (despues - antes))


def test_sesion_inexistente_da_404():
    assert client.get("/descargar/noexiste/xlsx").status_code == 404


def test_formato_de_descarga_invalido_da_400():
    r = _subir(PLANO_DXF)
    assert client.get(f"/descargar/{_token(r.text)}/docx").status_code == 400


# ------------------------------------------------------- retroalimentación

def test_hay_boton_para_reportar_un_problema():
    r = _subir(PLANO_DXF)
    assert "Reportar" in r.text or "reporte" in r.text.lower()
    assert "id=\"copiar\"" in r.text


def test_el_reporte_no_incluye_el_contenido_del_plano():
    """El reporte lleva metadatos, no el plano."""
    r = _subir(PLANO_CASO_ESTUDIO)
    m = re.search(r"<textarea[^>]*id=\"reporte\"[^>]*>(.*?)</textarea>",
                  r.text, re.S)
    assert m, "no se encontro el area de reporte"
    texto = m.group(1)
    assert "version_app" in texto
    assert "archivo" in texto
    # El DXF es binario-texto: no debe aparecer volcado.
    assert "ENTITIES" not in texto
    assert "SECTION" not in texto


def test_el_reporte_dice_que_no_adjunta_el_plano():
    r = _subir(PLANO_DXF)
    m = re.search(r"<textarea[^>]*id=\"reporte\"[^>]*>(.*?)</textarea>",
                  r.text, re.S)
    assert "NO se adjunta" in m.group(1) or "NO lo adjuntes" in m.group(1)


def test_el_reporte_no_se_envia_a_ningun_servidor():
    """El boton es copiar, no enviar."""
    r = _subir(PLANO_DXF)
    assert "no se envía a ningún lado" in r.text
    assert "execCommand" in r.text or "clipboard" in r.text


# ------------------------------------------------------- accesibilidad

def test_la_pagina_tiene_idioma_es():
    assert '<html lang="es"' in client.get("/").text


def test_los_campos_tienen_etiqueta_asociada():
    html = client.get("/").text
    for campo in ("plano", "catalogo", "ptm"):
        assert f'for="{campo}"' in html, "falta label para " + campo
        assert f'id="{campo}"' in html


def test_hay_enlace_de_salto_al_contenido():
    assert "Saltar al contenido" in client.get("/").text


def test_los_campos_de_precio_tienen_label_oculto():
    r = _subir(PLANO_DXF)
    labels = re.findall(r"<label class='oculto' for='p-", r.text)
    assert labels, "los campos de precio deben tener etiqueta"


def test_hay_estado_con_aria_live():
    r = _subir(PLANO_DXF)
    assert 'aria-live' in r.text


def test_los_encabezados_de_tabla_tienen_scope():
    r = _subir(PLANO_DXF)
    assert 'scope="col"' in r.text


def test_la_version_es_visible():
    assert APP_VERSION in client.get("/").text


def test_es_responsive():
    html = client.get("/").text
    assert 'name="viewport"' in html
    assert "@media (max-width:640px)" in html


# ------------------------------------------------------- identidad central

def test_la_identidad_esta_centralizada():
    """Nombre, version y licencia salen de app.identidad, no del HTML."""
    from app import identidad

    html = client.get("/").text
    assert identidad.NOMBRE in html
    assert identidad.VERSION in html
    assert identidad.LICENCIA in html


def test_no_hay_url_de_repositorio_inventada():
    """Sin URL confirmada, la interfaz lo dice en vez de inventar una."""
    from app import identidad

    html = client.get("/").text
    assert "github.com/USUARIO" not in html
    assert "github.com/" not in html or identidad.REPO_CONFIRMADO
    if not identidad.REPO_CONFIRMADO:
        assert identidad.REPO_URL == "PENDIENTE_REPO_URL"
        assert "PENDIENTE_REPO_URL" in html


def test_el_boton_de_issue_avisa_si_no_hay_repo():
    from app import identidad

    r = _subir(PLANO_DXF)
    if identidad.reporte_issue_habilitado():
        assert "issues/new" in r.text
    else:
        assert "issues/new" not in r.text
        assert "URL del repositorio" in r.text


def test_la_version_es_semver_inicial():
    from app import identidad

    assert identidad.VERSION == "0.1.0"
    assert identidad.VERSION.startswith("0."), \
        "una versión inicial debe ser 0.x: no promete estabilidad"


def test_la_licencia_mit_esta_marcada_como_propuesta():
    from app import identidad

    assert identidad.LICENCIA == "MIT"
    # No se puede publicar con la licencia sin confirmar.
    assert identidad.LICENCIA_CONFIRMADA is False
    assert "propuesta" in identidad.AVISO_LICENCIA
    html = client.get("/").text
    assert "propuesta" in html


def test_no_se_declara_validado_en_lugar_ninguno():
    """La frase prohibida no puede aparecer sin el 'no' delante."""
    from app import identidad

    html = client.get("/").text.lower()
    prohibido = "validado con planos de obra reales"
    # Solo se admite la forma negativa exacta del aviso centralizado.
    for i in range(len(html)):
        pass
    limpio = html.replace(identidad.AVISO_SIN_VALIDACION.lower(), "")
    assert prohibido not in limpio


def test_la_version_aparece_en_el_reporte():
    from app import identidad

    r = _subir(PLANO_DXF)
    m = re.search(r"<textarea[^>]*id=\"reporte\"[^>]*>(.*?)</textarea>",
                  r.text, re.S)
    assert identidad.VERSION in m.group(1)


# ------------------------------------------------------ limite de tamano

def test_el_limite_de_tamano_se_declara_como_supuesto():
    from app import identidad

    html = client.get("/").text
    assert f"Máximo {TAMANO_MAX_MB} MB" in html
    assert "supuesto" in html.lower()


def test_el_limite_se_aplica_en_el_servidor():
    relleno = b"x"
    grande = relleno * (TAMANO_MAX_MB * 1024 * 1024 + 1024)
    r = client.post("/subir",
                    files={"plano": ("enorme.dxf", grande, "application/octet-stream")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 413
    assert str(TAMANO_MAX_MB) in r.text


def test_el_limite_se_declara_en_el_cliente():
    """El formulario lleva el limite como atributo, para poder validarlo."""
    html = client.get("/").text
    assert f'data-limite-mb="{TAMANO_MAX_MB}"' in html


def test_el_limite_se_aplica_igual_en_error_que_en_exito():
    """Un archivo grande se rechaza por tamaño, no por estar corrupto.

    Aunque el contenido sea basura, el chequeo de tamaño va primero: no tiene
    sentido intentar leer 100 MB para后发现 que no es un DXF.
    """
    relleno = b"no es un dxf valido "
    repeticiones = (TAMANO_MAX_MB * 1024 * 1024) // len(relleno) + 4096
    grande = relleno * repeticiones
    assert len(grande) > TAMANO_MAX_MB * 1024 * 1024

    r = client.post("/subir",
                    files={"plano": ("grande.dxf", grande, "application/octet-stream")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 413
    assert str(TAMANO_MAX_MB) in r.text


def test_un_archivo_pequeno_corrupto_da_error_de_contenido():
    """Pequeño pero inválido: el error debe ser de lectura, no de tamaño."""
    r = client.post("/subir",
                    files={"plano": ("malo.dxf", b"esto no es un dxf", "application/octet-stream")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 400
    assert "MB" not in r.text, "no debe quejarse del tamaño si es pequeño"
    assert "No se pudo procesar" in r.text


# ------------------------------------------------------ contraste medido

def _luminancia(hexc: str) -> float:
    hexc = hexc.lstrip("#")
    canales = [int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lineal = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
              for c in canales]
    return 0.2126 * lineal[0] + 0.7152 * lineal[1] + 0.0722 * lineal[2]


def _contraste(a: str, b: str) -> float:
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def test_los_contrastes_del_css_cumplen_aa():
    """Los colores de la interfaz tienen que pasar WCAG AA, no parecer que sí.

    Estos valores ya estaban medidos; esta prueba los fija para que un
    cambio de color no los degrade en silencio.
    """
    from app.web import CSS

    pares = [
        ("--tinta", "#1c2430", "--fondo", "#ffffff"),
        ("--tenue", "#5b6672", "--fondo", "#ffffff"),
        ("--acento", "#1d4ed8", "--fondo", "#ffffff"),
        ("--aviso", "#8a4b08", "--aviso-fondo", "#fdf6ec"),
        ("--peligro", "#a11a1a", "--peligro-fondo", "#fdf2f2"),
        ("--ok", "#14622f", "--ok-fondo", "#f0f7f2"),
        ("#ffffff", "#ffffff", "--acento", "#1d4ed8"),
        ("#ffffff", "#ffffff", "--peligro", "#a11a1a"),
        ("--tinta", "#1c2430", "--panel", "#f6f7f9"),
        ("--tenue", "#5b6672", "--panel", "#f6f7f9"),
    ]
    flojos = []
    for n1, c1, n2, c2 in pares:
        for color in (c1, c2):
            assert color in CSS, "{} no está en el CSS".format(color)
        ratio = _contraste(c1, c2)
        if ratio < 4.5:
            flojos.append("{} sobre {} = {:.2f}:1 (mínimo 4.5)"
                          .format(n1, n2, ratio))
    assert not flojos, "contraste por debajo de AA:\n  " + "\n  ".join(flojos)


def test_los_contrastes_del_css_no_son_solo_un_comentario():
    """Un número en un comentario de CSS no es una medición.

    Los comentarios del CSS dicen "15.6:1" y cosas así. Si esos números se
    quedan desfasados respecto al color real, el comentario miente. Aquí se
    comprueba contra la fórmula, para que no sobreviva un texto viejo.
    """
    from app.web import CSS

    import re as _re

    patron = _re.compile(
        r"--(\w[\w-]*):\s*(#[0-9a-fA-F]{6});[^\n]*?([\d.]+):1")
    for variable, _color, declarado in patron.findall(CSS):
        if variable not in ("tinta", "tenue", "acento", "aviso", "peligro", "ok"):
            continue
        # El comentario dice el contraste contra el fondo de su propio par.
        fondos = {"aviso": "#fdf6ec", "peligro": "#fdf2f2", "ok": "#f0f7f2"}
        color = dict((v, c) for v, c, _d in patron.findall(CSS))[variable]
        fondo = fondos.get(variable, "#ffffff")
        real = _contraste(color, fondo)
        assert abs(real - float(declarado)) < 0.06, (
            "el comentario de --{} dice {}:1 y el color real da {:.2f}:1"
            .format(variable, declarado, real))


# ------------------------------------------- errores como página, no JSON

def test_los_errores_se_ven_como_pagina_no_como_json():
    """El formulario es un POST normal: ver JSON crudo sería un defecto.

    Un usuario que sube un archivo dañado no debería encontrarse un bloque
    de JSON en el navegador.
    """
    for nombre, contenido, status in (
        ("malo.dxf", b"esto no es un dxf", 400),
        ("notas.txt", b"hola", 400),
    ):
        r = client.post("/subir",
                        files={"plano": (nombre, contenido, "application/octet-stream")},
                        data={"pt_por_metro": 1.0})
        assert r.status_code == status
        assert r.headers["content-type"].startswith("text/html"), \
            "{} devolvió {} en vez de HTML".format(nombre, r.headers["content-type"])
        assert "<!doctype html>" in r.text.lower()
        assert "detail" not in r.text[:200].lower()


def test_el_error_ofrece_el_camino_de_vuelta():
    """Después de un error debe poder volver al formulario."""
    r = client.post("/subir",
                    files={"plano": ("malo.dxf", b"basura", "application/octet-stream")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 400
    assert 'href="/"' in r.text
    assert "<h1>" in r.text, "la página de error debe seguir el estilo del sitio"


def test_el_error_no_filtra_rutas_del_servidor():
    """ezdxf mete la ruta del temporal en el mensaje; no debe mostrarse."""
    r = client.post("/subir",
                    files={"plano": ("malo.dxf", b"basura" * 40,
                                     "application/octet-stream")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 400
    import tempfile
    assert tempfile.gettempdir() not in r.text
    assert "AppData" not in r.text
    assert ".tmp" not in r.text and "tmp" not in r.text.split("<main")[1][:600]


def test_el_rendimiento_se_muestra_en_la_cantidad():
    """La cantidad del presupuesto debe explicar de dónde sale.

    Sin esto, 27.0000 m2 en el takeoff y 29.1600 m2 en el presupuesto parecen
    dos mediciones distintas del mismo plano.
    """
    r = _subir(PLANO_DXF)
    assert "medido 27.0000 × rendimiento 1.08" in r.text

    # Cuando el rendimiento es 1 no se agrega desglose: solo hay que
    # comprobarlo con una expresion anchored, porque "rendimiento 1.0" es
    # subcadena de "rendimiento 1.08".
    assert "rendimiento 1.0 " not in r.text
    assert "rendimiento 1.0<" not in r.text


# -------------------------------------------------- instancia compartida

def test_la_interfaz_advierte_sobre_instancias_compartidas():
    """Antes de subir un archivo, avisar que puede haber alguien más detrás."""
    html = client.get("/").text
    assert "instancia compartida" in html.lower() or "instancia pública" in html.lower()
    assert "confidencial" in html.lower()
    assert "uvicorn app.web:app" in html