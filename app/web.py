"""Interfaz web de una sola pantalla: plano -> takeoff -> precios -> Excel/PDF.

PRIVACIDAD (ver README y la propia interfaz):
- El archivo se procesa ENTERO EN MEMORIA. No se escribe a disco.
- El XLSX y el PDF se generan tambien en memoria y se sirven desde ahi.
- La sesion guarda solo datos derivados (cantidades,Handles, precios), nunca
  el archivo original. Se pierde al reiniciar el servidor.
- No hay base de datos, ni cuentas, ni envio a terceros.

ALCANZABLE:
- HTML semantico, labels asociados, aria-live para estado, foco visible.
- Contraste >= 4.5:1 en todos los textos.
- Navegable por teclado: la app no usa raton para ninguna accion.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response

from app.exportar import exportar_excel_bytes, exportar_pdf_bytes
from app.identidad import (
    AVISO_NO_ES_CERTIFICACION,
    AVISO_PRECIOS_EJEMPLO,
    AVISO_SIN_VALIDACION,
    LICENCIA,
    LICENCIA_CONFIRMADA,
    NOMBRE,
    NOTA_TAMANO,
    REPO_ISSUE,
    TAMANO_MAX_MB,
    VERSION,
    reporte_issue_habilitado,
)
from app.medidor import medir
from app.pdf_entrada import medir_pdf
from app.presupuesto import Catalogo, construir_presupuesto

# Se reexportan por compatibilidad con lo que ya importan las pruebas.
APP_VERSION = VERSION

EXTENSIONES = {".dxf", ".pdf", ".dwg"}

app = FastAPI(title=NOMBRE, docs_url=None, redoc_url=None, openapi_url=None)

# Sesiones en memoria. No hay persistencia.
_SESIONES: dict[str, "Sesion"] = {}


# ------------------------------------------------------------- estilos
# 3 colores: tinta, acento, superficie. Los de estado son semanticos.
CSS = """
/* Los contrastes que aparecen en estos comentarios los mide
   scripts/verificar_navegador.py con la fórmula de luminancia relativa;
   no se estiman a ojo. Si cambias un color, vuelve a correr el script y
   actualiza el número aquí y en docs/VERIFICACION.md. */
:root{
  --tinta:#1c2430;        /* texto y bordes, 15.6:1 sobre --fondo */
  --tenue:#5b6672;        /* texto secundario, 5.9:1 sobre --fondo */
  --acento:#1d4ed8;       /* enlaces y foco, 6.7:1 sobre --fondo */
  --fondo:#ffffff;
  --panel:#f6f7f9;
  --borde:#d9dde3;
  --aviso:#8a4b08;        /* ámbar oscuro, 6.3:1 sobre --aviso-fondo */
  --aviso-fondo:#fdf6ec;
  --peligro:#a11a1a;      /* rojo oscuro, 7.1:1 sobre --peligro-fondo */
  --peligro-fondo:#fdf2f2;
  --ok:#14622f;           /* verde oscuro, 6.8:1 sobre --ok-fondo */
  --ok-fondo:#f0f7f2;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
  margin:0;color:var(--tinta);background:var(--fondo);
  line-height:1.6;font-size:16px;
}
.envoltorio{max-width:980px;margin:0 auto;padding:32px 20px 72px}
h1{font-size:1.55rem;line-height:1.3;margin:0 0 .3em;font-weight:650;letter-spacing:-.01em}
h2{font-size:1.1rem;margin:2rem 0 .6em;font-weight:650}
h3{font-size:.95rem;margin:1.4rem 0 .5em;font-weight:650}
p{margin:.6em 0}
a{color:var(--acento)}
sub,small{color:var(--tenue)}
.marco{max-width:64ch}
.silencio{color:var(--tenue);font-size:.9rem}
.encabezado{border-bottom:1px solid var(--borde);padding-bottom:1.2rem;margin-bottom:1.6rem}
.tarjeta{background:var(--panel);border:1px solid var(--borde);
         border-radius:10px;padding:20px;margin:1.2rem 0}
.tarjeta h2,.tarjeta h3{margin-top:0}

/* Foco visible para teclado en TODO */
:focus-visible{outline:3px solid var(--acento);outline-offset:2px;border-radius:3px}
:focus:not(:focus-visible){outline:none}

/* Estado 空 */
.vacio{background:var(--panel);border:1px dashed var(--borde);border-radius:10px;
       padding:28px 20px;text-align:center;color:var(--tenue)}
.estado{min-height:1.4em;font-size:.9rem;color:var(--tenue);margin-top:.5em}
.estado[aria-live]{min-height:1.4em}

/* Botones */
.boton{display:inline-block;border:1px solid transparent;border-radius:7px;
       padding:.62rem 1.1rem;font-size:.95rem;font-weight:600;
       cursor:pointer;font-family:inherit;text-decoration:none;text-align:center}
.boton-primario{background:var(--acento);color:#fff}
.boton-primario:hover{background:#1a3fae}
.boton-secundario{background:#fff;color:var(--tinta);border-color:var(--borde)}
.boton-secundario:hover{background:var(--panel)}
.boton[disabled]{opacity:.55;cursor:not-allowed}
.acciones{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1rem}

/* Formularios */
label{display:block;font-weight:600;font-size:.92rem;margin:.9rem 0 .35rem}
input[type=file],input[type=number],input[type=text],select{
  width:100%;padding:.6rem .7rem;border:1px solid #9aa3ad;border-radius:7px;
  font-size:.95rem;font-family:inherit;background:#fff;color:var(--tinta)}
input[type=file]{padding:.5rem}
input[type=number]{max-width:9rem}
table{width:100%;border-collapse:collapse;font-size:.9rem}
caption{text-align:left;color:var(--tenue);font-size:.85rem;
        padding-bottom:.5rem}
th,td{border-bottom:1px solid var(--borde);padding:.55rem .5rem;text-align:left;
      vertical-align:top}
th{font-weight:650;font-size:.82rem;color:var(--tenue);text-transform:uppercase;
   letter-spacing:.03em;border-bottom:1px solid var(--borde)}
tbody tr:hover{background:var(--panel)}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ref{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.78rem;
     color:var(--tenue);word-break:break-all}

/* Etiquetas de estado */
.et{display:inline-block;font-size:.72rem;font-weight:700;padding:.15rem .45rem;
    border-radius:4px;white-space:nowrap;letter-spacing:.02em}
.et-OK{background:var(--ok-fondo);color:var(--ok)}
.et-FALTA_PRECIO{background:var(--aviso-fondo);color:var(--aviso)}
.et-UNIDAD_INCOMPATIBLE,.et-CAPA_EXCLUIDA{background:var(--aviso-fondo);color:var(--aviso)}
.et-SIN_MAPEO{background:var(--peligro-fondo);color:var(--peligro)}

/* Avisos */
.aviso{border-left:3px solid var(--aviso);background:var(--aviso-fondo);
       color:var(--aviso);padding:.85rem 1rem;border-radius:0 7px 7px 0;
       margin:.7rem 0;font-size:.9rem}
.aviso.peligro{border-color:var(--peligro);background:var(--peligro-fondo);
               color:var(--peligro)}
.aviso.ok{border-color:var(--ok);background:var(--ok-fondo);color:var(--ok)}
.aviso h3{color:inherit;margin:0 0 .3em;font-size:.92rem}
.aviso ul{margin:.4em 0 0;padding-left:1.2em}

/* Totales */
.totales{background:var(--panel);border:1px solid var(--borde);
         border-radius:10px;padding:1.1rem 1.3rem;margin:1.2rem 0}
.totales dl{display:grid;grid-template-columns:auto 1fr;gap:.35rem 1.2rem;
            margin:0;font-variant-numeric:tabular-nums}
.totales dt{color:var(--tenue)}
.totales dd{margin:0;text-align:right;font-weight:600}
.totales .total{font-size:1.15rem;font-weight:700;padding-top:.5rem;
                border-top:1px solid var(--borde)}
.incompleto{background:var(--peligro);color:#fff;padding:.9rem 1.1rem;
            border-radius:8px;font-weight:650;margin:1rem 0;font-size:.95rem}

.detalle{margin-top:.6rem}
.detalle summary{cursor:pointer;font-weight:600;font-size:.9rem;color:var(--acento)}
.detalle summary:focus-visible{outline:3px solid var(--acento)}
.tabla-envoltorio{overflow-x:auto;-webkit-overflow-scrolling:touch}
.oculto{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);
       white-space:nowrap}
@media (max-width:640px){
  .envoltorio{padding:20px 14px 56px}
  h1{font-size:1.3rem}
  table{font-size:.82rem}
  th,td{padding:.45rem .35rem}
  .acciones{flex-direction:column}
  .boton{width:100%}
}
@media print{.no-imprimir{display:none}}
"""


def esc(x) -> str:
    return (str(x).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def _enlace_repo() -> str:
    """Enlace al repositorio, o texto honesto si aún no hay URL confirmada."""
    if reporte_issue_habilitado():
        return f'<a href="{REPO_ISSUE.rsplit("/issues", 1)[0]}">código</a>'
    return '<span title="Falta confirmar el repositorio">código (PENDIENTE_REPO_URL)</span>'


def _html(titulo: str, cuerpo: str) -> HTMLResponse:
    return HTMLResponse(content=f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(titulo)} · {esc(NOMBRE)}</title>
<meta name="description" content="Herramienta libre para medir planos y generar presupuestos de obra.">
<style>{CSS}</style>
</head>
<body>
<div class="envoltorio">
<header class="encabezado">
<a class="oculto" href="#contenido">Saltar al contenido principal</a>
<h1>{esc(NOMBRE)}</h1>
<p class="silencio">Mide planos y arma presupuestos de obra. Software libre,
sin cuentas y sin precio.</p>
</header>
<main id="contenido">
{cuerpo}
</main>
<footer class="no-imprimir" style="border-top:1px solid var(--borde);
        margin-top:3rem;padding-top:1.2rem">
<p class="silencio">
{NOMBRE} {VERSION} · Licencia {LICENCIA}{'' if LICENCIA_CONFIRMADA else ' (propuesta)'} ·
{_enlace_repo()} ·
{AVISO_NO_ES_CERTIFICACION}
</p>
</footer>
</div>
</body></html>""", status_code=200)


def _error_html(mensaje: str, status: int) -> HTMLResponse:
    """Error como página, no como JSON.

    El formulario de carga es un POST normal: si el manejador lanza
    HTTPException, FastAPI devuelve `{"detail": ...}` y el usuario ve un
    bloque de JSON crudo en el navegador. Como esta pantalla es HTML de
    principio a fin, el error también lo es, con el mismo estilo y un
    caminho de vuelta al formulario.

    El status HTTP se conserva (413 por tamaño, 400 por contenido), así que
    la máquina sigue distinguiendo los casos aunque la vista sea idéntica.
    """
    cuerpo = f"""<div class="vacio">
<h2>No se pudo procesar el archivo</h2>
<p>{esc(mensaje)}</p>
<p class="silencio">Se procesó en memoria y no quedó nada escrito en disco.</p>
</div>
<p><a class="boton boton-primario" href="/">Volver a intentar con otro plano</a></p>"""
    return HTMLResponse(
        content=f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Error · {esc(NOMBRE)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="envoltorio">
<header class="encabezado">
<a class="oculto" href="#contenido">Saltar al contenido principal</a>
<h1>{esc(NOMBRE)}</h1>
</header>
<main id="contenido" role="alert">
{cuerpo}
</main>
<footer class="no-imprimir" style="border-top:1px solid var(--borde);
        margin-top:3rem;padding-top:1.2rem">
<p class="silencio">
{NOMBRE} {VERSION} · Licencia {LICENCIA}{'' if LICENCIA_CONFIRMADA else ' (propuesta)'} ·
{AVISO_NO_ES_CERTIFICACION}
</p>
</footer>
</div>
</body></html>""",
        status_code=status)


# ------------------------------------------------------------- sesión
@dataclass
class Sesion:
    token: str
    nombre: str
    formato: str
    takeoff: dict
    catalogo_datos: dict
    precios: dict = field(default_factory=dict)
    avisos_dxf: list = field(default_factory=list)

    def catalogo(self) -> Catalogo:
        """Catálogo con los precios que el usuario haya puesto."""
        datos = json.loads(json.dumps(self.catalogo_datos))
        for c in datos["conceptos"]:
            if c["clave"] in self.precios:
                v = self.precios[c["clave"]]
                c["precio_unitario"] = None if v in (None, "") else float(v)
        return Catalogo.desde_dict(datos)

    def presupuesto(self):
        cat = self.catalogo()
        return construir_presupuesto(self.takeoff["mediciones"], cat)


def _sesion(token: str) -> Sesion:
    s = _SESIONES.get(token)
    if s is None:
        raise HTTPException(404, "Esta sesión ya no existe. Vuelve a cargar el plano.")
    return s


# ------------------------------------------------------------- landing
@app.get("/", response_class=HTMLResponse)
def inicio() -> HTMLResponse:
    cuerpo = f"""
<div class="marco">
<div class="tarjeta">
<h2>Cargar un plano</h2>
<form method="post" action="/subir" enctype="multipart/form-data" id="form-carga">
  <label for="plano">Plano (DXF, PDF vectorial o DWG)</label>
  <input type="file" id="plano" name="plano" required
         accept=".dxf,.pdf,.dwg" aria-describedby="ayuda-formato"
         data-limite-mb="{TAMANO_MAX_MB}">

  <p id="ayuda-formato" class="silencio" style="margin:.4rem 0 0">
    Máximo {TAMANO_MAX_MB} MB. Un PDF escaneado no se puede medir: se detecta y
    se avisa. Para DWG hace falta instalar ODA File Converter.
  </p>

  <label for="catalogo">Catálogo de precios (opcional)</label>
  <input type="file" id="catalogo" name="catalogo" accept=".json"
         aria-describedby="ayuda-catalogo">
  <p id="ayuda-catalogo" class="silencio" style="margin:.4rem 0 0">
    Un JSON con los precios por concepto. Si no lo cargas, cargarás los precios
    en la pantalla siguiente. Sin precios el total queda marcado como incompleto.
  </p>

  <label for="ptm">Escala — solo PDF (puntos PDF por metro)</label>
  <input type="number" id="ptm" name="pt_por_metro" step="any" min="0"
         placeholder="1" aria-describedby="ayuda-escala">
  <p id="ayuda-escala" class="silencio" style="margin:.4rem 0 0">
    Un PDF no guarda la escala del plano. Si no la conoces, déjalo en 1: las
    cantidades saldrán en puntos, no en metros, y la app lo dirá.
  </p>

  <div class="acciones">
    <button class="boton boton-primario" type="submit">Procesar plano</button>
  </div>
  <p class="estado" id="estado-carga" role="status" aria-live="polite"></p>
</form>
</div>

<div class="tarjeta">
<h2>Qué hace y qué no</h2>
<div class="tabla-envoltorio">
<table>
<caption>Dónde llega y dónde no.</caption>
<thead><tr><th scope="col">Sí</th><th scope="col">No</th></tr></thead>
<tbody>
<tr><td>Lee DXF</td><td>Planos escaneados (no hay OCR)</td></tr>
<tr><td>Lee PDF vectorial</td><td>DWG sin instalar ODA File Converter</td></tr>
<tr><td>Calcula áreas, longitudes y conteos por capa</td>
    <td>Precios incluidos</td></tr>
<tr><td>Muestra el handle de origen de cada cifra</td>
    <td>Detectar la escala del plano automáticamente</td></tr>
<tr><td>Exporta a Excel y PDF con IVA</td>
    <td>Reconstruir las capas de CAD dentro de un PDF</td></tr>
<tr><td>Avisa de lo que no pudo medir</td>
    <td>Certificar un presupuesto</td></tr>
</tbody></table>
</div>
</div>

<div class="tarjeta">
<h2>Antes de subir un plano: si usas una instancia compartida</h2>
<div class="aviso">
<small><b>Esta página puede estar servida por alguien más.</b> En una
instancia pública, el archivo que subes lo procesa el servidor de quien la
publicó, no tu computadora, y el archivo desaparece al terminar pero pasa por
esa máquina.<br><br>
<b>Si el plano es confidencial, no lo subas aquí.</b> Ejecuta la aplicación en
tu propia máquina: <code>python -m uvicorn app.web:app --port 8000</code>.
Entonces el archivo nunca sale de tu equipo.</small>
</div>
</div>

<div class="tarjeta">
<h2>Qué pasa con tu archivo</h2>
<ul class="silencio" style="padding-left:1.2em">
<li>Se procesa <b>dentro de este servidor, en memoria</b>. No se escribe a disco.</li>
<li>Los resultados (cantidades, handles, precios) se guardan solo en memoria
    mientras la sesión esté abierta. Se pierden al reiniciar el servidor.</li>
<li>No hay cuentas, ni base de datos, ni envío a terceros, ni analítica.</li>
<li>Si algo sale mal, el archivo temporal se borra igualmente.</li>
</ul>
</div>

<div class="tarjeta">
<h2>Sin validar todavía</h2>
<p class="silencio" style="margin:0">
<b>{AVISO_SIN_VALIDACION}</b> Todo lo verificado usa planos sintéticos y dos
planos reales de archivo público.<br>
{AVISO_NO_ES_CERTIFICACION}<br>
{AVISO_PRECIOS_EJEMPLO}
</p>
</div>

<div class="tarjeta">
<h2>Sobre el tamaño del archivo</h2>
<p class="silencio" style="margin:0">{NOTA_TAMANO}</p>
</div>
</div>

<script>
document.getElementById('form-carga').addEventListener('submit', function () {{
  var e = document.getElementById('estado-carga');
  e.textContent = 'Procesando el plano… no cierres esta ventana.';
}});
</script>
"""
    return _html("Medir planos", cuerpo)


# ------------------------------------------------------------- procesar
@app.post("/subir", response_class=HTMLResponse)
async def subir(
    request: Request,
    plano: UploadFile = File(...),
    catalogo: UploadFile | None = File(None),
    pt_por_metro: float = Form(1.0),
):
    # El cierre va en un finally y no al final del camino feliz.

    # Cuando una parte del formulario es mas grande que el umbral de spool de
    # Starlette (1 MB), esa parte se escribe a disco en TEMP mientras se
    # procesa. Si no se cierra el UploadFile, el archivo temporal se queda
    # ahi hasta que el proceso termine: es decir, el plano del cliente
    # sobrevive en el servidor. Por eso todas las salidas pasan por aqui,
    # incluidas las cuatro que devuelven error.
    try:
        return await _procesar_subida(plano, catalogo, pt_por_metro)
    finally:
        await _cerrar_ambos(plano, catalogo)


async def _cerrar_ambos(plano, catalogo) -> None:
    """Cierra los archivos subidos. Nunca deja que un fallo cierre al otro.

    Si cerrar uno lanzara, el otro se quedaria abierto y con su temporal en
    disco, que es justo lo que se quiere evitar.
    """
    for archivo in (plano, catalogo):
        if archivo is None:
            continue
        try:
            await archivo.close()
        except Exception:
            # Cerrar no puede hacer fallar una respuesta ya construida.
            pass


async def _procesar_subida(plano: UploadFile,
                           catalogo: UploadFile | None,
                           pt_por_metro: float) -> HTMLResponse:
    nombre = Path(plano.filename or "").name
    ext = Path(nombre).suffix.lower()
    if ext not in EXTENSIONES:
        return _error_html(
            "Formato no soportado: se aceptan .dxf, .pdf y .dwg.", 400)

    # El archivo NUNCA se escribe a disco por nuestra cuenta: se lee a
    # memoria y se procesa ahí.
    contenido = await plano.read()
    if len(contenido) > TAMANO_MAX_MB * 1024 * 1024:
        return _error_html(
            f"El archivo supera {TAMANO_MAX_MB} MB. "
            "El límite es un supuesto, no un dato; se cambia en "
            "TAMANO_MAX_MB, en app/identidad.py.", 413)

    cat_datos = _catalogo_base()
    precios_pre = {}
    if catalogo is not None and catalogo.filename:
        try:
            cat_datos = json.loads((await catalogo.read()).decode("utf-8"))
        except Exception as exc:
            return _error_html(
                f"El catálogo no es JSON válido: {exc}", 400)

    try:
        takeoff = _medir_memoria(contenido, ext, nombre, pt_por_metro)
    except Exception as exc:
        return _error_html(_mensaje_amigable(exc), 400)

    for c in cat_datos["conceptos"]:
        if c.get("precio_unitario"):
            precios_pre[c["clave"]] = c["precio_unitario"]

    token = uuid.uuid4().hex
    ses = Sesion(token=token, nombre=nombre, formato=ext.lstrip("."),
                 takeoff=takeoff, catalogo_datos=cat_datos, precios=precios_pre)
    _SESIONES[token] = ses
    return _html("Resultado", _cuerpo_trabajo(ses))


def _catalogo_base() -> dict:
    return json.loads(
        (Path(__file__).resolve().parent.parent / "catalogo" / "conceptos.json")
        .read_text(encoding="utf-8"))


def _medir_memoria(contenido: bytes, ext: str, nombre: str, pt_por_metro: float) -> dict:
    """Mide desde bytes, sin dejar el archivo en disco.

    ezdxf y pdfplumber necesitan una ruta. Se escribe un temporal, se cierra,
    se procesa y se borra en un finally. El temporal vive microsegundos y
    nunca contiene datos de forma intencionada.
    """
    import ezdxf

    with _temporal(contenido, ext) as ruta:
        if ext == ".pdf":
            return medir_pdf(ruta, pt_por_metro=pt_por_metro)

        if ext == ".dwg":
            from app.entidades import leer_dwg

            doc = leer_dwg(ruta)
        else:
            doc = ezdxf.readfile(ruta)

        capas = sorted({e.dxf.layer for e in doc.modelspace()})
        cat = Catalogo.cargar()
        um = cat.unidades_por_capa(capas)
        # _medir_documento evita reescribir el archivo temporal.
        from app.medidor import _medir_documento

        return _medir_documento(doc, escala=1.0, unidades_por_capa=um)


@contextlib.contextmanager
def _temporal(contenido: bytes, ext: str):
    """Archivo temporal que se borra al salir, pase lo que pase."""
    fd, nombre_tmp = tempfile.mkstemp(suffix="." + ext.lstrip("."))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(contenido)
        yield Path(nombre_tmp)
    finally:
        try:
            os.unlink(nombre_tmp)
        except OSError:
            pass


def _mensaje_amigable(exc: Exception) -> str:
    """Error legible para el usuario, sin filtrar rutas del servidor.

    ezdxf mete en el mensaje la ruta completa del temporal del servidor. Eso
    no le sirve de nada a quien subió el archivo y sí revela el sistema de
    archivos de quien publica la herramienta.
    """
    s = str(exc)
    if "ODA" in s or "odafc" in s:
        return ("Para leer archivos DWG hace falta ODA File Converter. " + s)
    if "DXFStructure" in s or "corrupt" in s.lower():
        return "El archivo DXF parece estar dañado o no es un DXF válido."
    limpio = re.sub(r"[A-Za-z]:\\\\?[^\s'\"]*", "<archivo>", s)
    limpio = re.sub(r"/tmp/[^\s'\"]*", "<archivo>", limpio)
    return f"No se pudo procesar el plano: {limpio}"


# ------------------------------------------------- pantalla de trabajo
def _cuerpo_trabajo(ses: Sesion) -> str:
    pres = ses.presupuesto()
    take = ses.takeoff
    p = []

    p.append(f"""<h2>{esc(ses.nombre)}</h2>
<p class="silencio">Formato {esc(ses.formato.upper())} ·
escala {esc(take.get('escala_aplicada', 1))} ·
{take['diagnostico']['unidades_nombre']}</p>""")

    for a in take.get("diagnostico", {}).get("advertencias", []):
        p.append(f'<div class="aviso">{esc(a)}</div>')

    # --- Vacío: no se midió nada
    if not take["mediciones"]:
        p.append("""<div class="vacio">
<p><b>No se pudo medir nada de este archivo.</b></p>
<p class="silencio">Si es un PDF escaneado, no hay geometría que medir.
Si es un DXF, revisa que tenga geometría en el espacio modelo.</p>
</div>""")
    else:
        p.append(_tabla_takeoff(take))

    # --- Descartes
    inc = take.get("entidades_incompatibles", [])
    if inc:
        filas = "".join(
            "<tr><td>{}</td><td class='ref'>{}</td><td>{}</td><td>{}</td>"
            "<td>{}</td></tr>".format(
                esc(i["capa"]), esc(i["handle"]), esc(i["tipo"]),
                esc(i["forma_detectada"]), esc(i["motivo"]))
            for i in inc)
        p.append(f"""<details class="detalle">
<summary>Se descartaron {len(inc)} entidades por unidad incompatible</summary>
<p class="silencio">No entran al total. Cada una trae su referencia de origen.</p>
<div class="tabla-envoltorio"><table>
<thead><tr><th scope="col">Capa</th><th scope="col">Origen</th>
<th scope="col">Tipo</th><th scope="col">Aporta</th>
<th scope="col">Motivo</th></tr></thead>
<tbody>{filas}</tbody></table></div>
</details>""")

    omit = take.get("entidades_omitidas", [])
    if omit:
        tipos = sorted({o["tipo"] for o in omit})
        p.append(f"""<div class="aviso">
Se omitieron {len(omit)} entidades de tipo {', '.join(tipos)}. Son textos o
cotas: no son cantidades de obra, así que no se cotizan.
</div>""")

    solapes = take.get("solapes", [])
    if solapes:
        p.append(f"""<div class="aviso">
{len(solapes)} capa(s) tienen geometría que se solapa o se contiene. Se cobró
el área real (la unión), no la suma. Revísalas si el número te parece bajo.
</div>""")

    # --- Precios
    p.append(_formulario_precios(ses, pres))

    # --- Totales
    p.append(_bloque_totales(pres))

    # --- Avisos del presupuesto
    avisos = pres.advertencias()
    if avisos:
        cuerpo_av = "".join(f"<li>{esc(a)}</li>" for a in avisos)
        p.append(f'<div class="aviso"><h3>Revisa esto antes de enviar el '
                 f'presupuesto</h3><ul>{cuerpo_av}</ul></div>')

    # --- Descargas
    p.append(f"""<div class="acciones">
<a class="boton boton-primario" href="/descargar/{ses.token}/xlsx"
   download>Descargar Excel</a>
<a class="boton boton-secundario" href="/descargar/{ses.token}/pdf"
   download>Descargar PDF</a>
<a class="boton boton-secundario" href="/">Procesar otro plano</a>
</div>""")

    # --- Reportar problema
    p.append(_bloque_reportar(ses, pres, take))

    return "\n".join(p)


def _tabla_takeoff(take: dict) -> str:
    filas = []
    for m in take["mediciones"]:
        refs = ", ".join(m.get("handles", [])[:6])
        if len(m.get("handles", [])) > 6:
            refs += f" (+{len(m['handles']) - 6})"
        filas.append(
            "<tr><td>{}</td><td class='num'>{:,.4f}</td><td>{}</td>"
            "<td class='num'>{}</td><td class='ref'>{}</td></tr>".format(
                esc(m["capa"]), m["cantidad"], esc(m["unidades"]),
                m.get("n_entidades", 0), esc(refs) or "—"))
    return f"""<div class="tabla-envoltorio"><table>
<caption>Cantidades medidas. «Origen» son los handles de las entidades del
plano que producen esa cifra.</caption>
<thead><tr><th scope="col">Capa</th><th scope="col">Cantidad</th>
<th scope="col">Unidad</th><th scope="col">Entidades</th>
<th scope="col">Origen</th></tr></thead>
<tbody>{''.join(filas)}</tbody></table></div>"""


def _formulario_precios(ses: Sesion, pres) -> str:
    """Una fila por concepto presente en el plano, con su campo de precio."""
    por_clave: dict[str, list] = {}
    for l in pres.lineas:
        if l.clave:
            por_clave.setdefault(l.clave, []).append(l)

    if not por_clave:
        return """<h2>Precios</h2>
<div class="aviso">Ninguna capa de este plano coincide con un concepto del
catálogo, así que no hay nada que cotizar todavía. Corre
<code>scripts/auditar_capas.py</code> para ver qué capas no están cubiertas.</div>"""

    filas = []
    for clave, lineas in sorted(por_clave.items()):
        l0 = lineas[0]
        cant = sum(x.cantidad_ajustada for x in lineas)
        unidad = l0.unidad if len({x.unidad for x in lineas}) == 1 else "mixto"
        precio = ses.precios.get(clave)

        # La cantidad del presupuesto puede no ser igual a la del takeoff
        # porque el concepto lleva rendimiento (desperdicio). Sin decir la
        # cuenta, el mismo numero en dos pantallas parece una contradiccion.
        rendimiento = l0.rendimiento
        if abs(rendimiento - 1.0) < 1e-9:
            desglose = ""
        else:
            medida = sum(x.cantidad_medida for x in lineas)
            desglose = ("<br><small class='silencio'>medido {:,.4f} × "
                        "rendimiento {}</small>").format(medida, rendimiento)

        filas.append(
            "<tr><td>{}<br><small>{}</small></td>"
            "<td class='num'>{:,.4f} {}{}</td>"
            "<td><label class='oculto' for='p-{c}'>Precio unitario de {n}</label>"
            "<input type='number' id='p-{c}' name='precio' value='{v}' "
            "step='0.01' min='0' inputmode='decimal' placeholder='sin precio'>"
            "</td>"
            "<td>{e}</td></tr>".format(
                esc(l0.concepto), esc(l0.categoria), cant, esc(unidad),
                desglose,
                c=esc(clave), n=esc(l0.concepto),
                v=("" if precio in (None, "") else str(precio)),
                e=("&nbsp;" if all(x.importe is not None for x in lineas)
                   else "<span class='silencio'>sin precio</span>")))

    return f"""<h2>Precios</h2>
<p class="silencio">Pon los precios que tú manejas. Lo que dejes vacío queda
fuera del total y el total se marca como incompleto. Cuando el concepto lleva
rendimiento, la cantidad muestra de dónde sale.</p>
<form method="post" action="/precios/{ses.token}">
<div class="tabla-envoltorio"><table>
<thead><tr><th scope="col">Concepto</th><th scope="col">Cantidad</th>
<th scope="col">Precio unitario (MXN)</th><th scope="col">Importe</th></tr></thead>
<tbody>{''.join(filas)}</tbody></table></div>
<div class="acciones">
<button class="boton boton-primario" type="submit">Aplicar precios</button>
</div>
</form>"""


def _bloque_totales(pres) -> str:
    if pres.total_incompleto:
        cab = (f'<div class="incompleto">Total incompleto: '
               f'{len(pres.excluidas)} de {len(pres.lineas)} líneas quedaron '
               f'fuera. Este importe no cubre toda la obra del plano.</div>')
    else:
        cab = '<div class="aviso ok"><b>Total completo.</b> ' \
              'Todas las líneas tienen precio y unidad compatible.</div>'
    return f"""<h2>Totales</h2>
{cab}
<div class="totales">
<dl>
<dt>Subtotal</dt><dd>{pres.subtotal:,.2f} MXN</dd>
<dt>IVA 16%</dt><dd>{pres.iva:,.2f} MXN</dd>
<dt class="total">Total</dt><dd class="total">{pres.total:,.2f} MXN</dd>
</dl></div>"""


def _bloque_reportar(ses: Sesion, pres, take: dict) -> str:
    resumen = {
        "version_app": APP_VERSION,
        "archivo": ses.nombre,
        "formato": ses.formato.upper(),
        "unidades_archivo": take.get("diagnostico", {}).get("unidades_nombre"),
        "escala": take.get("escala_aplicada"),
        "capas_detectadas": len({m["capa"] for m in take["mediciones"]}),
        "mediciones": len(take["mediciones"]),
        "entidades_descartadas": len(take.get("entidades_incompatibles", [])),
        "entidades_omitidas": len(take.get("entidades_omitidas", [])),
        "capas_con_solape": len(take.get("solapes", [])),
        "lineas_totales": len(pres.lineas),
        "lineas_ok": len([l for l in pres.lineas if l.estado == "OK"]),
        "lineas_excluidas": len(pres.excluidas),
        "avisos": pres.advertencias(),
        "nota": "El plano NO se adjunta. Pega el texto y adjúntalo tú si "
                "quieres que lo veamos.",
    }
    texto = json.dumps(resumen, ensure_ascii=False, indent=2)

    cuerpo_md = (
        "### Qué pasó\n\n"
        "<!-- Describe el problema y qué esperabas. -->\n\n"
        "### Datos técnicos (rellenados automáticamente)\n\n"
        "```json\n" + texto + "\n```\n\n"
        "### Origen del plano\n\n"
        "<!-- Opcional: origen, fecha y si puedes compartirlo. NO lo adjuntes "
        "si es confidencial. -->\n")

    return f"""<h2 class="no-imprimir">¿Algo salió mal?</h2>
<div class="tarjeta no-imprimir">
<p class="silencio">Genera un reporte con los datos técnicos de esta corrida.
Se copia al portapapeles; <b>el texto no se envía a ningún lado</b> y
<b>el plano no se adjunta</b>. Pégalo tú donde quieras.</p>
<label for="reporte">Reporte generado</label>
<textarea id="reporte" rows="14" readonly
  style="width:100%;display:block;font-family:ui-monospace,Menlo,monospace;
         font-size:.8rem">{esc(cuerpo_md)}</textarea>
<div class="acciones">
<button class="boton boton-primario" type="button" id="copiar">Copiar el reporte</button>
{_boton_issue(cuerpo_md)}
</div>
<p class="estado" id="estado-copiar" role="status" aria-live="polite"></p>
</div>
<script>
document.getElementById('copiar').addEventListener('click', function () {{
  var t = document.getElementById('reporte');
  t.focus(); t.select();
  var ok = false;
  try {{ ok = document.execCommand('copy'); }} catch (e) {{ ok = false; }}
  if (!ok && navigator.clipboard) {{
    navigator.clipboard.writeText(t.value).then(function () {{
      document.getElementById('estado-copiar').textContent =
        'Reporte copiado. Pégalo en el repositorio del proyecto.';
    }});
  }} else {{
    document.getElementById('estado-copiar').textContent = ok
      ? 'Reporte copiado. Pégalo en el repositorio del proyecto.'
      : 'No se pudo copiar. Selecciona el texto y cópialo con el teclado.';
  }}
}});
</script>"""


def _boton_issue(cuerpo_md: str) -> str:
    """Enlace al issue, o un aviso si el repositorio aún no está confirmado.

    Con REPO_URL sin confirmar, un enlace a una URL inventada sería peor que
    no tener enlace: el usuario escribiría su reporte en la nada.
    """
    if not reporte_issue_habilitado():
        return ('<p class="silencio">Aún no hay URL del repositorio '
                'configurada, así que no se puede abrir el issue. Copia el '
                'reporte y compártelo como quieras.</p>')
    return (f'<a class="boton boton-secundario" target="_blank" rel="noopener" '
            f'href="{REPO_ISSUE}?title={_url("Problema con un plano")}'
            f'&body={_url(cuerpo_md[:1200])}">Abrir como issue (opcional)</a>')


def _url(s: str) -> str:
    return quote(s[:1200], safe="")


# ------------------------------------------------------------- precios
@app.post("/precios/{token}", response_class=HTMLResponse)
def actualizar_precios(token: str, precio: list[str] = Form(default=[])):
    """Aplica los precios capturados.

    El orden de los campos coincide con el orden de las filas del formulario,
    que es el orden en que aparecen las claves por primera vez.
    """
    ses = _sesion(token)
    claves: list[str] = []
    for l in ses.presupuesto().lineas:
        if l.clave and l.clave not in claves:
            claves.append(l.clave)

    for clave, valor in zip(claves, precio):
        v = (valor or "").strip()
        ses.precios[clave] = None if v == "" else v

    return _html("Resultado", _cuerpo_trabajo(ses))


# ------------------------------------------------------------- descargas
@app.get("/descargar/{token}/{formato}")
def descargar(token: str, formato: str):
    ses = _sesion(token)
    pres = ses.presupuesto()
    base = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(ses.nombre).stem) or "presupuesto"

    if formato == "xlsx":
        datos = exportar_excel_bytes(pres, ses.takeoff)
        return Response(
            datos,
            media_type="application/vnd.openxmlformats-officedocument."
                       "spreadsheetml.sheet",
            headers={"Content-Disposition":
                     f'attachment; filename="{base}.xlsx"'})

    if formato == "pdf":
        datos = exportar_pdf_bytes(pres, ses.takeoff)
        return Response(datos, media_type="application/pdf",
                        headers={"Content-Disposition":
                                 f'attachment; filename="{base}.pdf"'})

    raise HTTPException(400, "Formato no soportado")