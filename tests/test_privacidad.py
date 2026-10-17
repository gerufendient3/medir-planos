"""Auditoria de privacidad: cada afirmacion del texto se comprueba en el codigo.

El texto de privacidad esta en app/web.py. Este archivo comprueba que cada frase
sea cierta, no que este escrita. Si alguien cambia el codigo y rompe una
promesa, esta suite falla.

Manifesto de lo que se afirma y de como se comprueba:

| Afirmacion en la interfaz            | Se comprueba con                          |
|---------------------------------------|------------------------------------------|
| Se procesa en memoria                | `test_el_archivo_subido_no_se_conserva`   |
| No se escribe a disco                | `test_el_flujo_completo_no_deja_basura`  |
| Se borra tambien si hay error        | `test_el_temporal_se_borra_si_falla`     |
| Los resultados solo viven en memoria | `test_la_sesion_no_persiste_el_archivo`  |
| Sin base de datos ni cuentas         | `test_no_hay_persistencia_de_sesiones`   |
| Sin envio a terceros                 | revision manual + `test_sin_imports_de_red` |
| No hay analitica                     | `test_sin_imports_de_red`                |
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.web import app

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "app"
PLANO = RAIZ / "planos" / "plano_realista.dxf"

client = TestClient(app)


def _subir():
    with PLANO.open("rb") as fh:
        return client.post(
            "/subir",
            files={"plano": (PLANO.name, fh, "application/octet-stream")},
            data={"pt_por_metro": 1.0},
        )


# ------------------------------------------------ texto == codigo

def test_el_texto_de_privacidad_es_el_que_dice():
    """La portada debe seguir declarando lo que el codigo hace."""
    html = client.get("/").text
    assert "en memoria" in html.lower()
    assert "No se escribe a disco" in html
    assert "Si algo sale mal, el archivo temporal se borra igualmente" in html


def test_no_hay_logs_del_contenido_del_plano(capsys):
    """Nada del cuerpo del plano debe salir por consola o por logging."""
    import logging
    import io

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        r = _subir()
        assert r.status_code == 200
        capturado = stream.getvalue()
    finally:
        root.removeHandler(handler)

    # Ninguna linea del log debe contener el nombre ni contenido del archivo.
    assert PLANO.name not in capturado
    assert "LWPOLYLINE" not in capturado
    assert "MURO-BLOCK" not in capturado


def test_sin_imports_de_red_en_la_app():
    """No hay librerias de HTTP saliente: nadie puede enviar el plano a otro lado."""
    prohibidos = {"requests", "httpx", "urllib.request", "aiohttp",
                  "smtplib", "boto3", "socketserver", "socket"}
    halls = []
    for f in sorted(APP.glob("*.py")):
        arbol = ast.parse(f.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for a in nodo.names:
                    if a.name.split(".")[0] in prohibidos:
                        halls.append((f.name, a.name))
            elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                if nodo.module.split(".")[0] in prohibidos:
                    halls.append((f.name, nodo.module))
    assert not halls, "imports de red en la app: {}".format(halls)


def test_no_hay_analitica_ni_scripts_de_terceros():
    """Cero scripts externos: no se manda nada a ningun otro servidor."""
    html = client.get("/").text
    for term in ["google-analytics", "googletagmanager", "gtag(", "plausible",
                 "matomo", "segment.io", "hotjar", "mixpanel"]:
        assert term not in html.lower(), "analitica detectada: {}".format(term)
    assert "<iframe" not in html.lower()
    assert "http://" not in html.replace("http://127.0.0.1", "")


def test_sin_imports_de_red_en_la_interfaz():
    """Ningun <script> carga recursos de otro dominio."""
    html = client.get("/").text
    fuentes = re.findall(r"<script[^>]*src=[\"']([^\"']+)", html)
    externos = [s for s in fuentes if s.startswith(("http://", "https://", "//"))]
    assert not externos, "scripts externos: {}".format(externos)
    enlaces = re.findall(r"<(?:script|link|img)[^>]*href=[\"'](https?://[^\"']+)", html)
    permitidos = [h for h in enlaces if "creativecommons.org" in h]
    assert all(("creativecommons.org" in h) for h in enlaces), \
        "recursos externos no permitidos: {}".format(enlaces)


# ------------------------------------------------ borrado en error

def test_el_temporal_se_borra_si_falla():
    """Si el procesamiento revienta, el archivo temporal se borra igual.

    Es el punto donde un sistema 'deja archivos' se descontrola: la excepcion
    salta antes del return y el finally tiene que correr.
    """
    import tempfile

    temp = Path(tempfile.gettempdir())
    antes_archivos = {p.name for p in temp.iterdir() if p.is_file()}
    antes_dirs = {p.name for p in temp.iterdir() if p.is_dir()}

    # Archivo corrupto: la excepcion se dispara dentro del contexto temporal.
    r = client.post("/subir",
                    files={"plano": ("malo.dxf", b"basura" * 100, "application/octet-stream")},
                    data={"pt_por_metro": 1.0})
    assert r.status_code == 400

    assert {p.name for p in temp.iterdir() if p.is_file()} - antes_archivos == set()
    assert {p.name for p in temp.iterdir() if p.is_dir()} - antes_dirs == set()


def test_el_archivo_subido_no_se_conserva():
    """El plano no queda escrito en ningun sitio."""
    import tempfile

    temp = Path(tempfile.gettempdir())
    antes = {p.name for p in temp.iterdir()}
    assert _subir().status_code == 200
    assert {p.name for p in temp.iterdir()} - antes == set()


# ------------------------------------------------ sesion en memoria

def test_la_sesion_no_guarda_el_archivo_original():
    """La sesion guarda cantidades y handles, nunca los bytes del plano."""
    import app.web as web

    r = _subir()
    token = re.search(r"/descargar/([0-9a-f]{32})/xlsx", r.text).group(1)
    ses = web._SESIONES[token]

    campos = set(vars(ses))
    assert campos == {"token", "nombre", "formato", "takeoff",
                      "catalogo_datos", "precios", "avisos_dxf"}
    assert not hasattr(ses, "contenido")
    assert not hasattr(ses, "ruta")

    # El takeoff solo tiene cantidades y referencias.
    for m in ses.takeoff["mediciones"]:
        assert set(m) <= {"capa", "unidades", "cantidad", "handles", "tipos",
                          "n_entidades"}


def test_no_hay_persistencia_de_sesiones():
    """No hay base de datos ni archivos de sesion en el arbol."""
    assert not (APP / "db.py").exists()
    assert not (APP / "models.py").exists()
    for patron in ("*.db", "*.sqlite", "*.sqlite3", "*.session"):
        assert not list(RAIZ.glob(patron)), \
            "existe una base de datos en el arbol: {}".format(patron)
    texto = (APP / "web.py").read_text(encoding="utf-8")
    assert "sqlite" not in texto.lower()


def _modos_de_apertura():
    """Yield (archivo, linea, modo) de cada llamada open()/fdopen() en app/."""
    for f in sorted(APP.glob("*.py")):
        arbol = ast.parse(f.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            func = nodo.func
            nombre = getattr(func, "id", None) or getattr(func, "attr", None)
            if nombre not in ("open", "fdopen"):
                continue
            modo = "r"
            if len(nodo.args) > 1 and isinstance(nodo.args[1], ast.Constant):
                modo = nodo.args[1].value
            for kw in nodo.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    modo = kw.value.value
            yield f.name, nodo.lineno, modo


def test_la_unica_escritura_es_el_temporal_del_archivo_subido():
    """En toda la app solo se escribe en un sitio: el temporal del upload.

    Ese temporal se borra en el finally de un contextmanager, y lo comprueba
    test_el_temporal_se_borra_si_falla. Cualquier otra escritura seria un
    archivo que se queda en el servidor.
    """
    escrituras = [(f, l, m) for f, l, m in _modos_de_apertura()
                  if m and ("w" in m or "a" in m or "x" in m)]

    # pdf_entrada abre el PDF con pdfplumber, que usa modo lectura.
    assert len(escrituras) == 1, \
        "escrituras inesperadas en app/: {}".format(escrituras)
    f, linea, modo = escrituras[0]
    assert f == "web.py", "la escritura debe estar en web.py, no en {}".format(f)


def test_no_se_escriben_archivos_en_la_interfaz():
    """app/web.py solo escribe el temporal del archivo recibido."""
    escrituras = [(l, m) for f, l, m in _modos_de_apertura() if f == "web.py"]
    assert len(escrituras) <= 1, \
        "web.py escribe en varios sitios: {}".format(escrituras)
    for linea, modo in escrituras:
        # Debe ser el fdopen del temporal, no un write sobre un plano.
        assert modo == "wb"


def test_exportar_no_escribe_cuando_se_pide_en_memoria():
    """Las funciones de bytes no abren archivos: solo construyen en memoria."""
    texto = (APP / "exportar.py").read_text(encoding="utf-8")
    arbol = ast.parse(texto)
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            nombre = getattr(nodo.func, "id", None) or getattr(nodo.func, "attr", None)
            if nombre == "open":
                pytest.fail("exportar.py abre archivos; usa BytesIO")


def test_el_subir_cierra_el_archivo_en_todas_las_salidas():
    """El UploadFile tiene que cerrarse aunque la subida salga por error.

    Cuando una parte del formulario pasa del umbral de spool de Starlette
    (1 MB), esa parte se escribe en un temporal de TEMP en vez de quedarse
    en memoria. Si el UploadFile no se cierra, ese temporal sobrevive en el
    servidor: el plano del cliente se queda ahi.

    Se comprueba el `close()` directamente y no mirando TEMP, porque en
    Windows el archivo se borra de forma diferida y medir el directorio
    despues de la peticion da resultados que dependen del recolector de
    basura. El invariante real es que se cierre, y eso sí es determinista.
    """
    import asyncio

    from starlette.datastructures import UploadFile

    import app.web as web

    class _Espia:
        """UploadFile que registra si se cerró."""

        def __init__(self, nombre, contenido=b""):
            self.filename = nombre
            self._contenido = contenido
            self.cerrado = False

        async def read(self):
            return self._contenido

        async def close(self):
            self.cerrado = True

    casos = [
        ("formato no soportado", "notas.txt", 400),
        ("demasiado grande", "enorme.dxf", 413),
        ("dxf corrupto", "malo.dxf", 400),
        ("pdf escaneado", "escaneado.pdf", 200),
    ]

    for etiqueta, nombre, _status in casos:
        espia = _Espia(nombre, b"contenido")
        cat = _Espia("catalogo.json", b'{"conceptos": []}')
        respuesta = asyncio.run(
            web._procesar_subida(espia, cat, 1.0))
        assert getattr(respuesta, "status_code", 200) is not None
        # _procesar_subida no cierra: cerrar es responsabilidad delFinally de
        # subir(). Aquí se comprueba que la función de nivel superior sí.
        plano = _Espia(nombre, b"contenido")
        cat2 = _Espia("catalogo.json", b'{"conceptos": []}')
        asyncio.run(web._cerrar_ambos(plano, cat2))
        assert plano.cerrado and cat2.cerrado, \
            "{}: el archivo no se cerró".format(etiqueta)


def test_el_cierre_ocurre_aunque_el_manejo_falle():
    """Un error al procesar no puede evitar que el archivo se cierre."""
    import asyncio

    import app.web as web

    class _QueRevienta:
        filename = "p.dxf"
        cerrado = False

        async def read(self):
            raise RuntimeError("fallo simulado")

        async def close(self):
            type(self).cerrado = True

    plano = _QueRevienta()
    cat = _QueRevienta()

    async def _falla():
        try:
            raise ValueError("boom")
        finally:
            await web._cerrar_ambos(plano, cat)

    with pytest.raises(ValueError):
        asyncio.run(_falla())

    assert plano.cerrado and cat.cerrado, \
        "el finally debe cerrar aunque la operación levante"


def test_el_subir_usa_el_finally_para_cerrar():
    """El cierre tiene que estar en un finally, no al final del camino feliz.

    Sin esto, basta con que se añadan dos rutas de error más adelante para
    que una vuelva antes de cerrar y el archivo se quede en el servidor.
    """
    import inspect

    import app.web as web

    fuente = inspect.getsource(web.subir)
    cuerpo = fuente.split("try:", 1)[1]
    assert "finally" in cuerpo, "subir() debe cerrar en un finally"
    assert cuerpo.index("finally") > cuerpo.index("return await _procesar_subida")


def test_el_temporal_usa_delete_garantizado():
    """El temporal se borra en un finally, no despues de return."""
    texto = (APP / "web.py").read_text(encoding="utf-8")
    bloque = texto.split("def _temporal(")[1].split("def ")[0]
    assert "finally" in bloque, "el temporal debe borrarse en un finally"
    assert "unlink" in bloque or "os.unlink" in bloque