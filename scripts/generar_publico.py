"""Genera publico/landing.html y publico/kit.html.

El precio de lanzamiento es una HIPOTESIS con rango, no un precio validado.
No hay testimonios, ni numeros de usuarios, ni logos. Nada de eso existe.
"""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path

SALIDA = Path(__file__).resolve().parent.parent / "publico"

CSS = """
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;
     line-height:1.6;color:#1a1a1a;background:#fff}
header{background:#1F3A5F;color:#fff;padding:44px 20px}
header .wrap{max-width:900px;margin:0 auto}
header h1{font-size:30px;margin:0 0 12px;line-height:1.25}
header p{font-size:17px;margin:0;opacity:.92}
main{max-width:900px;margin:0 auto;padding:30px 20px 70px}
h2{font-size:21px;margin:34px 0 12px;padding-bottom:6px;
   border-bottom:2px solid #1F3A5F}
h3{font-size:16px;margin:20px 0 8px}
ul,ol{padding-left:22px}
li{margin:5px 0}
.card{background:#fafafa;border:1px solid #ddd;border-radius:8px;
      padding:18px;margin:14px 0}
.aviso{background:#fff9e6;border-left:5px solid #f9a825;padding:12px 16px;
       margin:12px 0;font-size:14px}
.bien{background:#f1f8f2;border-left:5px solid #2e7d32;padding:12px 16px;
      margin:12px 0;font-size:14px}
.no{background:#fff4f4;border-left:5px solid #9C0006;padding:12px 16px;
    margin:12px 0;font-size:14px}
.hiptesis{background:#f3e8ff;border:2px dashed #7c3aed;padding:16px 18px;
          border-radius:8px;margin:16px 0}
.hiptesis .precio{font-size:30px;font-weight:800;color:#5b21b6}
table{border-collapse:collapse;width:100%;font-size:14px;margin:10px 0}
th,td{border:1px solid #d5d5d5;padding:8px 10px;text-align:left}
th{background:#1F3A5F;color:#fff}
form{background:#fafafa;border:1px solid #ddd;border-radius:8px;padding:20px}
label{display:block;font-weight:600;margin:14px 0 5px;font-size:14px}
input,textarea,select{width:100%;padding:9px;border:1px solid #bbb;
                      border-radius:4px;font-size:14px;font-family:inherit}
textarea{min-height:80px}
button{background:#1F3A5F;color:#fff;border:0;padding:12px 22px;
       border-radius:5px;font-size:15px;cursor:pointer;margin-top:16px;
       font-weight:600}
button:hover{background:#152c47}
footer{max-width:900px;margin:0 auto;padding:24px;color:#666;font-size:12px;
       border-top:1px solid #ddd}
a{color:#1F3A5F}
small{color:#666}
code{background:#eee;padding:1px 5px;border-radius:3px;
     font-family:ui-monospace,Consolas,monospace;font-size:13px}
.demo{background:#eef4fb;border:1px solid #c3d7ee;border-radius:8px;
      padding:16px;margin:14px 0}
"""


def esc(x) -> str:
    return html.escape(str(x))


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cotiza planos en minutos, con la cuenta a la vista</title>
<style>{css}</style></head><body>
<header><div class="wrap">
<h1>Cotiza planos en minutos, con la cuenta a la vista</h1>
<p>Herramienta de takeoff y presupuesto de obra para contratistas y
estimadores en México. Cada cifra muestra de qué entidad del plano salió.</p>
</div></header>
<main>

<h2>El problema</h2>
<div class="card">
<p>Medir planos cuesta tiempo y los errores salen caros. Hoy se mide a ojo, con
regla y calculadora, o con un programa que cuesta más de lo que justifica el
trabajo.</p>
<p>Peor: cuando una herramienta se equivoca, el error es invisible. Un total
que parece correcto y está mal no genera ninguna duda. La pérdida aparece meses
después, en la obra.</p>
<p>Esta herramienta está construida al revés: <b>muestra cuándo no sabe</b>.</p>
</div>

<h2>Qué hace</h2>
<ul>
<li>Lee planos <b>DXF</b> y <b>PDF vectorial</b>, clasifica por capa y calcula
áreas, longitudes y conteos.</li>
<li>Mapea las capas a conceptos de obra con un catálogo que <b>editas tú</b>.</li>
<li>Marca cada partida con el <b>handle</b> de la entidad DXF que la produjo, para
rastroarla hasta el plano.</li>
<li>Exporta a <b>Excel y PDF</b> con subtotal, IVA y el detalle de lo que no pudo
medir.</li>
</ul>

<div class="demo">
<b>Ver la demostración pública</b><br>
Un plano real que <b>no</b> se puede medir y por qué, un plano que sí, el cálculo
a mano de partidas comparado contra la salida de la herramienta, y la lista de
lo que no sabe hacer.<br>
<a href="demo.html">→ Abrir la demostración</a>
</div>

<h2>Lo que incluye y lo que no</h2>
<table>
<tr><th>Sí</th><th>No</th></tr>
<tr><td>
Lectura de DXF<br>
Lectura de PDF vectorial<br>
Clasificación por capa<br>
Áreas, longitudes y conteos<br>
Catálogo de conceptos editable<br>
Trazabilidad por handle<br>
Excel y PDF con IVA<br>
Avisos de lo no medido<br>
Marcado de total incompleto<br>
Interfaz web
</td><td>
Planos escaneados (no hay OCR)<br>
DWG sin instalar ODA File Converter<br>
Precios incluidos<br>
Detección automática de escala<br>
Reconstrucción de capas de CAD en PDF<br>
Gestión de clientes u obras<br>
App móvil
</td></tr>
</table>

<h2>Limitaciones</h2>
<div class="no">
<p><b>No se ha procesado ningún plano de obra real.</b> Todo lo verificado usa
planos sintéticos y dos planos reales de archivo público.</p>
<p>Los precios de la demostración son <b>de ejemplo</b>. No son precios de
mercado: no hay fuente pública verificada de precios de obra en México.</p>
<p><b>No es un software de certificación ni sustituye el criterio de un
estimador.</b> Úsala para calcular y para revisar; la decisión de qué cotizar y
a qué precio es tuya.</p>
</div>

<h2>Cómo se usa</h2>
<div class="card">
<p>Se ejecuta en tu propia máquina. No hay cuentas ni servicios externos.</p>
<pre style="background:#fff;border:1px solid #ddd;border-radius:6px;
     padding:12px;overflow-x:auto;font-size:.85rem"><code>python -m venv .venv
pip install -r requirements.txt
python -m uvicorn app.web:app --port 8000</code></pre>
<p>Y abre <code>http://127.0.0.1:8000</code>.</p>
</div>

<h2>Qué pasa con tu archivo</h2>
<div class="card">
<ul class="silencio" style="padding-left:1.2em">
<li>Se procesa <b>en memoria</b>. No se escribe a disco.</li>
<li>Los resultados se guardan solo en memoria mientras la sesión esté abierta.</li>
<li>No hay cuentas, ni base de datos, ni envío a terceros, ni analítica.</li>
</ul>
</div>

<h2>Reportar un problema</h2>
<div class="card">
<p>En la pantalla de trabajo hay un botón <b>Reportar un problema con este
plano</b>. Genera un texto con los datos técnicos de esa corrida y lo copia al
portapapeles. <b>No envía nada a ningún servidor</b> y <b>no adjunta el plano</b>.</p>
</div>

<h2>Licencia y créditos</h2>
<div class="card">
<p><b>MIT.</b> Puedes leer el código, modificarlo y redistribuirlo.</p>
<p>Los planos de ejemplo tienen licencia propia: uno es de dominio público y
otro es CC BY-SA 4.0. Fuentes en
<a href="../docs/FUENTES.md">docs/FUENTES.md</a>.</p>
<p>Librerías: ezdxf, shapely, pdfplumber, openpyxl, reportlab, fastapi,
uvicorn. Todas MIT o BSD.</p>
</div>

<footer>
Generado el {fecha} · <a href="demo.html">demostración</a> ·
<a href="../docs/CASO_ESTUDIO.md">caso de estudio</a> ·
<a href="../docs/FUENTES.md">fuentes y licencias</a> ·
<a href="../README.md">README</a><br>
Software libre y gratuito. Sin usuarios registrados y sin validación con
planos de obra reales.
</footer>
</body></html>"""

PREGUNTAS = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kit de entrevista y guion de demo (5 min)</title>
<style>{css}</style></head><body>
<header><div class="wrap">
<h1>Kit de entrevista y demo de 5 minutos</h1>
<p>Para hablar con estimadores y contratistas. Guion literal y preguntas.</p>
</div></header>
<main>

<div class="aviso">
<small><b>Abre aclarando que es gratuita.</b> Es software libre: no hay nada
que comprar. Si no lo dices, te van a preguntar el precio y se acaba la
conversación. Pregunta primero cómo cotizan ellos; el valor te lo dicen ellos,
no tú.</small>
</div>

<h2>Guion de demostración — 5 minutos</h2>

<h3>0:00 – 0:30 · Enganche</h3>
<blockquote>Esto es gratuito, es software libre, no hay nada que comprar.
Voy a enseñarte un presupuesto hecho con un plano. Tú dime si el número te
serviría para mandarlo a un cliente.</blockquote>
<p><small>No digas que es una demo ni que es una prueba. Pide una opinión
técnica, no una valoración comercial.</small></p>

<h3>0:30 – 1:30 · El problema, con su vocabulario</h3>
<ul>
<li>¿Cómo se mide un plano hoy? ¿Con regla? ¿A ojo? ¿Software?</li>
<li>¿Cuánto tiempo te toma cotizar uno?</li>
<li>¿Cuántos planos al mes?</li>
</ul>

<h3>1:30 – 3:00 · La demostración (<a href="demo.html">demo.html</a>)</h3>
<ol>
<li>Abre el <b>Caso A</b>: el plano real que no se puede medir.
    <b>Qué decir:</b> "Este es un plano real de dominio público. La herramienta
    dice que no lo puede medir y por qué. No te va a dar un número falso."</li>
<li>Abre el <b>Caso B</b>: las cantidades medidas.
    <b>Qué decir:</b> "Mira la columna de handles. Cada cifra dice de qué
    entidad del plano salió."</li>
<li>Enseña el <b>cálculo manual de las tres partidas</b>.
    <b>Qué decir:</b> "Esta multiplicación la puedes hacer tú en una
    calculadora para comprobarlo."</li>
<li>Enseña <b>lo que se descartó y por qué</b>.
    <b>Qué decir:</b> "Esto es lo que ninguna herramienta te enseña: qué no
    pudo medir."</li>
</ol>

<h3>3:00 – 4:00 · Las preguntas duras</h3>
<ul>
<li>¿En qué formato te llegan los planos? ¿Y quién los produce?</li>
<li>¿Cuántos planos cotizas al mes?</li>
<li>¿Cuánto te cobra hoy lo que usas, o cuánto costaría?</li>
<li>¿Alguna vez mandaste una cotización con un error de cantidad?</li>
</ul>

<h3>4:00 – 5:00 · Cierre</h3>
<ul>
<li>Si esto te ahorrara 4 horas por presupuesto, ¿cuánto valdría al mes?</li>
<li>¿Te lo probarías con un plano real tuyo si funcionara?</li>
<li>¿Puedo volver a contactarte cuando tenga un resultado sobre un plano tuyo?</li>
</ul>

<h2>Preguntas de entrevista</h2>

<h3>Proceso actual</h3>
<ol>
<li>Cuéntame cómo cotizas un presupuesto, de principio a fin.</li>
<li>¿En qué formato te llega el plano? ¿Y quién lo produced?</li>
<li>¿Cómo mides? ¿Con qué herramienta? ¿Y cuánto tiempo te toma?</li>
<li>¿Cómo manejas los cambios de versión de un plano?</li>
<li>¿Quién revisa las cantidades antes de enviar la cotización?</li>
</ol>

<h3>El precio</h3>
<ol start="6">
<li>¿Cuánto te cuesta, en horas, cotizar un presupuesto?</li>
<li>¿Alguna vez has mandasted una cotización con un error de cantidad?
    ¿Qué pasó?</li>
<li>¿Cuánto dinero te ha costado un error así?</li>
</ol>

<h3>Disposición a pagar</h3>
<ol start="9">
<li>Si una herramienta te ahorrara 4 horas por presupuesto, ¿cuánto valdría
    eso al mes?</li>
<li>¿Lo pagarías de una vez o por mes? ¿Por qué?</li>
<li>¿Con quién tendrías que hablar para autorizar una compra así?</li>
</ol>

<div class="aviso">
<small><b>No hay precio.</b> La herramienta es gratuita. Lo que sí conviene
preguntar es cuánto tiempo le ahorraría y si eso valdría dinero: así se sabe si
la herramienta tiene futuro aunque hoy no se cobre.</small>
</div>

<h2>Cómo registrar</h2>
<div class="card">
<p>Por cada entrevista anota textualmente:</p>
<ul>
<li>Formato de plano (la respuesta más valiosa)</li>
<li>Horas por presupuesto</li>
<li>Volumen al mes</li>
<li>Un error que te costó dinero</li>
<li>Respuesta literal a "¿cuánto valdría?"</li>
</ul>
<p><small>No promedies respuestas. Una sola persona que diga "no pagaría" vale
más que cinco que digan "sí, interesante".</small></p>
</div>

<footer>
Generado el {fecha} · <a href="landing.html">landing</a> ·
<a href="demo.html">demostración</a>
</footer>
</body></html>"""


def main() -> int:
    SALIDA.mkdir(exist_ok=True)
    hoy = date.today().isoformat()

    (SALIDA / "landing.html").write_text(
        PAGINA.format(css=CSS, fecha=hoy), encoding="utf-8")
    (SALIDA / "kit.html").write_text(
        PREGUNTAS.format(css=CSS, fecha=hoy), encoding="utf-8")
    (SALIDA / "README.md").write_text(
        "# Piezas públicas\n\n"
        "Generadas por `scripts/generar_demo.py` (demo) y "
        "`scripts/generar_publico.py` (landing y kit).\n\n"
        "| Archivo | Qué es |\n|---|---|\n"
        "| `demo.html` | Demostración: plano que no se mide + plano que sí + "
        "cálculo manual + lo que no sabe hacer |\n"
        "| `landing.html` | Página del proyecto: qué hace, qué no, y "
        "cómo ejecutarlo |\n"
        "| `kit.html` | Guion de demo de 5 min y preguntas de entrevista |\n"
        "| `demo_datos.json` | Datos crudos de la demo, para verificar |\n\n"
        "## Lo que estas piezas NO son\n\n"
        "- **Software libre y gratuito.** No hay precio, ni cuentas, ni pagos.\n"
        "- No hay testimonios. No hay usuarios registrados.\n"
        "- Los precios del presupuesto son de ejemplo, no de mercado.\n"
        "- Ningún plano de obra real ha sido procesado.\n"
        "- No hay formulario de captación: el boton de reporte copia un texto "
        "y no envía nada.\n",
        encoding="utf-8")

    print("escritos: landing.html, kit.html, README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())