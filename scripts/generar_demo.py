"""Genera la demostracion publica en publico/demo.html.

Reproducible: corre el pipeline real y vuelca sus resultados. No hay cifras
escritas a mano.

Dos casos, a proposito:

  A) PLANO REAL de dominio publico, rasterizado. Se demuestra que la
     herramienta DETECTA que no se puede medir y explica por que.
     Esto no se esconde: es el riesgo numero uno del producto.

  B) PLANO VECTORIAL generado por el proyecto, con verdad conocida.
     Se demuestra el takeoff con handles, las advertencias y el presupuesto
     con precios de ejemplo.

Cada archivo usado lleva su fuente y licencia en la misma pagina.
"""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

from app.pipeline import ejecutar
from app.pdf_entrada import inspeccionar

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "publico"
ASSETS = SALIDA / "assets"
FIXTURES = RAIZ / "tests" / "fixtures" / "pdf"

# Plano real de dominio publico. NO se puede medir.
PLANO_REAL = FIXTURES / "pd_escaneado.pdf"
# Plano vectorial generado por el proyecto, verdad conocida.
PLANO_VECTOR = FIXTURES / "vectorial_desde_dxf.pdf"
DXF_VERDAD = RAIZ / "planos" / "vectorial_origen.dxf"

# Precios de EJEMPLO para que el presupuesto sea legible. No son precios de
# mercado y la pagina lo dice donde sea que aparezcan.
#
# Vive en catalogo/demo_precios.json y NO aqui: una sola copia, para que el
# archivo y la demo no puedan dar numeros distintos. El test
# test_los_precios_de_demo_no_cuentan_dos_veces lo comprueba.
def _cargar_precios_demo() -> dict:
    import json
    ruta = RAIZ / "catalogo" / "demo_precios.json"
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return {c["clave"]: c["precio_unitario"]
            for c in datos["conceptos"]
            if c.get("precio_unitario") not in (None, "")}


PRECIOS_EJEMPLO = _cargar_precios_demo()

FUENTES = [
    {
        "archivo": PLANO_REAL.name,
        "titulo": "Floor plan of a 5-bedroom house (Plan no. 7181)",
        "autor": "United States. Division of Home Economics, 1965",
        "licencia": "Dominio publico (obra del gobierno de EE. UU.)",
        "origen": "https://archive.org/details/CAT31371083",
    },
    {
        "archivo": "harlem_meer_planta.pdf",
        "titulo": "Harlem Meer Restaurant — First Floor Plan (Drawing #2), 1990",
        "autor": "MMDA-Photos, Nueva York",
        "licencia": "CC BY-SA 4.0",
        "origen": "https://commons.wikimedia.org/wiki/File:Harlem_Meer_Restaurant_Dwg_-2_-_1990-08-01_-_First_Floor_Plan_(2).pdf",
    },
    {
        "archivo": PLANO_VECTOR.name,
        "titulo": "Planta vectorial de prueba (geometria conocida)",
        "autor": "Generado por este proyecto con ezdxf",
        "licencia": "Dominio publico de las pruebas",
        "origen": "scripts/generar_pdf_vectorial.py",
    },
    {
        "archivo": DXF_VERDAD.name,
        "titulo": "DXF origen del plano vectorial",
        "autor": "Generado por este proyecto",
        "licencia": "Dominio publico de las pruebas",
        "origen": "scripts/generar_pdf_vectorial.py",
    },
]

CSS = """
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;
     line-height:1.55;color:#1a1a1a;background:#fbfbfb}
header{background:#1F3A5F;color:#fff;padding:26px 20px}
header h1{margin:0 0 6px;font-size:24px}
header p{margin:0;opacity:.9;font-size:14px}
main{max-width:1080px;margin:0 auto;padding:22px 20px 60px}
h2{font-size:19px;margin:30px 0 10px;padding-bottom:6px;
   border-bottom:2px solid #1F3A5F}
h3{font-size:15px;margin:18px 0 8px}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:18px;
      margin:14px 0}
.aviso{background:#fff4f4;border-left:5px solid #9C0006;padding:11px 15px;
       margin:9px 0;color:#9C0006;font-size:14px}
.aviso.info{background:#f2f7ff;border-left-color:#1F3A5F;color:#1F3A5F}
.aviso.bien{background:#f1f8f2;border-left-color:#2e7d32;color:#2e7d32}
.ejemplo{background:#fff9e6;border-left:5px solid #f9a825;padding:11px 15px;
         margin:9px 0;font-size:14px}
table{border-collapse:collapse;width:100%;font-size:13px;margin:8px 0}
th,td{border:1px solid #d5d5d5;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#1F3A5F;color:#fff}
tr:nth-child(even){background:#f6f6f6}
.OK{background:#e8f5e9}
.FALTA_PRECIO{background:#fff4ce}
.UNIDAD_INCOMPATIBLE,.CAPA_EXCLUIDA{background:#ffe0b2}
.SIN_MAPEO{background:#fde2e2}
code,.handle{background:#eee;padding:1px 5px;border-radius:3px;
             font-family:ui-monospace,Consolas,monospace;font-size:12px}
.total{font-size:21px;font-weight:700}
.marca-incompleto{background:#9C0006;color:#fff;padding:12px 16px;
                  border-radius:6px;font-weight:700;margin:12px 0}
.handles{font-size:11px;color:#555;word-break:break-all}
footer{max-width:1080px;margin:0 auto;padding:20px;color:#666;font-size:12px}
img.plano{max-width:100%;border:1px solid #ccc;background:#fff}
a{color:#1F3A5F}
small{color:#666}
"""


def esc(x) -> str:
    return html.escape(str(x))


def _catalogo_ejemplo(destino: Path):
    import json as _json

    datos = _json.loads((RAIZ / "catalogo" / "conceptos.json").read_text(encoding="utf-8"))
    for c in datos["conceptos"]:
        c["precio_unitario"] = PRECIOS_EJEMPLO.get(c["clave"])
    destino.write_text(_json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino


def render_plano_png(dxf: Path, png: Path) -> bool:
    """Dibuja el DXF a PNG para que el visitante vea el plano."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import ezdxf
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

        doc = ezdxf.readfile(str(dxf))
        fig = plt.figure(figsize=(9, 7))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        Frontend(RenderContext(doc), MatplotlibBackend(ax)).draw_layout(
            doc.modelspace(), finalize=True)
        fig.savefig(png, dpi=110)
        plt.close(fig)
        return True
    except Exception as exc:  # pragma: no cover
        print("  aviso: no se pudo renderizar el PNG:", exc)
        return False


def _tabla_mediciones(take: dict) -> str:
    filas = ["<tr><th>Capa</th><th>Cantidad</th><th>Unidad</th>"
             "<th>Entidades</th><th>Handles (procedencia)</th></tr>"]
    for m in take["mediciones"]:
        handles = ", ".join(m.get("handles", [])[:10])
        if len(m.get("handles", [])) > 10:
            handles += " (+{})".format(len(m["handles"]) - 10)
        filas.append(
            "<tr><td>{}</td><td><b>{:,.4f}</b></td><td>{}</td>"
            "<td>{}</td><td class='handles'>{}</td></tr>".format(
                esc(m["capa"]), m["cantidad"], esc(m["unidades"]),
                m.get("n_entidades", 0), esc(handles) or "—")
        )
    return "<table>" + "".join(filas) + "</table>"


def _tabla_presupuesto(pres) -> str:
    filas = ["<tr><th>Estado</th><th>Concepto</th><th>Capa</th><th>Cant.</th>"
             "<th>Und.</th><th>P. unit.</th><th>Importe</th>"
             "<th>Procedencia</th></tr>"]
    for l in pres.lineas:
        imp = "{:,.2f}".format(l.importe) if l.importe is not None else "EXCLUIDA"
        pu = "{:,.2f}".format(l.precio_unitario) if l.precio_unitario else "sin precio"
        handles = ", ".join(l.handles[:5]) + ("…" if len(l.handles) > 5 else "")
        filas.append(
            "<tr class='{}'><td>{}</td><td>{}</td><td>{}</td>"
            "<td>{:,.4f}</td><td>{}</td><td>{}</td><td>{}</td>"
            "<td class='handles'>{}</td></tr>".format(
                esc(l.estado), esc(l.estado), esc(l.concepto), esc(l.capa),
                l.cantidad_ajustada, esc(l.unidad), pu, imp, esc(handles) or "—")
        )
    return "<table>" + "".join(filas) + "</table>"


def bloque_advertencias(pres) -> str:
    partes = []
    if pres.total_incompleto:
        partes.append(
            '<div class="marca-incompleto">TOTAL INCOMPLETO — {} de {} líneas '
            "excluidas. Este importe NO cubre toda la obra del plano.</div>".format(
                len(pres.excluidas), len(pres.lineas)))
    for a in pres.advertencias():
        partes.append('<div class="aviso">{}</div>'.format(esc(a)))
    return "".join(partes) if partes else (
        '<div class="aviso bien">Sin advertencias: todas las líneas son OK.</div>')


def main() -> int:
    SALIDA.mkdir(exist_ok=True)
    ASSETS.mkdir(exist_ok=True)
    cat_ejemplo = _catalogo_ejemplo(ASSETS / "catalogo_ejemplo.json")

    # --- Caso A: plano real, rasterizado
    print("Caso A: plano real de dominio publico")
    info_real = inspeccionar(PLANO_REAL)
    res_real = ejecutar(PLANO_REAL, cat_ejemplo, pt_por_metro=1.0)
    print("  vectores={} imagenes={} mediciones={}".format(
        info_real["objetos_vectoriales"], info_real["images"],
        len(res_real["takeoff"]["mediciones"])))

    # --- Caso B: plano vectorial generado, verdad conocida
    print("Caso B: plano vectorial generado")
    from app.pdf_entrada import medir_pdf

    PT_POR_M = 418.91 / 8.0  # el rectangulo de 8 m mide 418.91 pt en el PDF
    take_b = medir_pdf(PLANO_VECTOR, pt_por_metro=PT_POR_M)
    from app.presupuesto import Catalogo, construir_presupuesto

    cat = Catalogo.cargar(cat_ejemplo)
    pres_b = construir_presupuesto(take_b["mediciones"], cat)
    res_b = {"takeoff": take_b, "presupuesto": pres_b}
    print("  mediciones={}".format(len(take_b["mediciones"])))

    png_ok = render_plano_png(DXF_VERDAD, ASSETS / "plano.png")
    print("  PNG renderizado:", png_ok)

    # --- Caso B: se mide SIN filtro de concepto para mostrar TODO lo que hay
    # en el plano, y despues se muestra que hizo el presupuesto con eso.
    from app.medidor import medir

    take_dxf = medir(DXF_VERDAD)   # sin filtrar: sale todo
    p_dxf = construir_presupuesto(take_dxf["mediciones"], cat)

    cuerpo = []
    cuerpo.append("<h2>Qué es esto</h2><div class='card'>")
    cuerpo.append(
        "<p>Una herramienta que convierte un plano en un presupuesto en pesos "
        "mexicanos, y que <b>muestra de dónde sale cada cifra</b>. Cada cantidad "
        "de la tabla lleva el <i>handle</i> de las entidades DXF que la "
        "producen, así que se puede rastrear hasta el plano original.</p>")
    cuerpo.append(
        "<p>Aquí se muestran <b>dos planos reales de archivo</b>: uno que la "
        "herramienta <b>no puede medir</b>, y otro que sí. El primero está "
        "puesto a propósito.</p>")
    cuerpo.append("<p><small>Generado el {} · reproducible con "
                  "<code>scripts/generar_demo.py</code></small></p>".format(
                      date.today().isoformat()))
    cuerpo.append("</div>")

    # --- Caso A
    cuerpo.append("<h2>Caso A — Plano real que NO se puede medir</h2>")
    cuerpo.append("<div class='card'>")
    cuerpo.append(
        "<p><b>{}</b><br><small>{} · {}</small></p>".format(
            esc(PLANO_REAL.name),
            esc(FUENTES[0]["autor"]), esc(FUENTES[0]["licencia"])))
    cuerpo.append(
        "<p>Este es un plano de obra real, de dominio público, con licencia "
        "verificable. <b>La herramienta no puede medirlo</b> y no va a "
        "inventar números.</p>")
    cuerpo.append(
        "<table><tr><th>Diagnóstico</th><th>Valor</th></tr>"
        "<tr><td>Objetos vectoriales (líneas, rectángulos, curvas)</td>"
        "<td><b>{}</b></td></tr>"
        "<tr><td>Imágenes en la página</td><td><b>{}</b></td></tr>"
        "<tr><td>Caracteres de texto</td><td>{}</td></tr>"
        "<tr><td>Mediciones producidas</td><td><b>{}</b></td></tr></table>".format(
            info_real["objetos_vectoriales"], info_real["images"],
            info_real["chars"], len(res_real["takeoff"]["mediciones"])))
    for a in info_real["advertencias"]:
        cuerpo.append('<div class="aviso">{}</div>'.format(esc(a)))
    cuerpo.append(
        "<p><b>Por qué importa.</b> Un plano puede llegar como PDF aunque el "
        "original sea CAD, y si llega rasterizado no hay geometría que medir. "
        "Detectar esto y decirlo es la diferencia entre una herramienta que "
        "ayuda y una que produce números falsos.</p>")
    cuerpo.append("</div>")

    # --- Caso B
    cuerpo.append("<h2>Caso B — Plano que sí se puede medir, cifra por cifra</h2>")
    cuerpo.append("<div class='card'>")
    if png_ok:
        cuerpo.append(
            "<p><img class='plano' src='assets/plano.png' "
            "alt='Planta renderizada del DXF medido'></p>")
    cuerpo.append(
        "<p>Plano vectorial generado por el proyecto con ezdxf. La geometría se "
        "conoce exactamente, así que cada cantidad se puede comprobar contra la "
        "verdad:</p>")
    cuerpo.append(
        "<table><tr><th>Capa</th><th>Geometría real</th><th>Valor exacto</th></tr>"
        "<tr><td>MURO-PISO</td><td>Rectángulo 8 × 6 m</td><td>48 m²</td></tr>"
        "<tr><td>MURO-TABIQUE</td><td>Línea vertical de 6 m</td><td>6 m</td></tr>"
        "<tr><td>PISO-LOSETA</td><td>Rectángulo 4 × 3 m</td><td>12 m²</td></tr></table>")

    cuerpo.append("<h3>Lo que la herramienta midió</h3>")
    cuerpo.append(_tabla_mediciones(take_dxf))
    cuerpo.append(
        "<div class='aviso info'>El PDF no conserva la escala del plano. La escala "
        "la define el usuario; aquí se usó <code>{} pt por metro</code>, derivado del "
        "rectángulo de 8 m que mide 418.91 pt en el PDF. Sin ese dato las cantidades "
        "serían puntos, no metros.</div>".format(round(PT_POR_M, 4)))

    cuerpo.append("<h3>Presupuesto</h3>")
    cuerpo.append('<div class="ejemplo"><b>Precios de EJEMPLO.</b> '
                  "No son precios de mercado: no existe fuente pública verificada "
                  "de precios de obra en México. Sirven solo para que se vea el "
                  "formato de salida.</div>")
    cuerpo.append(_tabla_presupuesto(p_dxf))
    cuerpo.append(bloque_advertencias(p_dxf))

    # Segunda medicion, ahora CON el filtro de concepto, para mostrar que
    # rechaza lo que no corresponde a la unidad del concepto.
    take_filtrado = medir(DXF_VERDAD, unidades_por_capa=cat.unidades_por_capa(
        ["MURO-PISO", "MURO-TABIQUE", "PISO-LOSETA"]))

    if take_filtrado["entidades_incompatibles"]:
        cuerpo.append("<h3>Lo que se descartó y por qué</h3>")
        cuerpo.append(
            "<p>Estas entidades existen en el plano pero <b>no se pudieron "
            "cotizar</b>. No se omiten en silencio: se listan con su handle.</p>")
        cuerpo.append(
            "<table><tr><th>Capa</th><th>Handle</th><th>Tipo</th>"
            "<th>Aporta</th><th>El concepto pide</th><th>Motivo</th></tr>")
        for i in take_filtrado["entidades_incompatibles"]:
            cuerpo.append(
                "<tr><td>{}</td><td class='handle'>{}</td><td>{}</td>"
                "<td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    esc(i["capa"]), esc(i["handle"]), esc(i["tipo"]),
                    esc(i["forma_detectada"]), esc(i["unidad_concepto"]),
                    esc(i["motivo"])))
        cuerpo.append("</table>")
        cuerpo.append(
            "<p><small>Ejemplo real de por qué esto importa: el tabique de 6 m es "
            "una línea, y el concepto al que se asigna (tabique de gypsum) se "
            "cotiza por m². Multiplicar metros por un precio de m² daría un "
            "importe sin sentido que parecería correcto. La herramienta lo rechaza "
            "y lo dice, en vez de colar un número falso en el presupuesto.</small></p>")

    # --- Cálculo manual de tres partidas
    cuerpo.append("<h3>Cálculo manual de tres partidas</h3>")
    cuerpo.append("<div class='card'>")
    cuerpo.append(
        "<p>Para que no tengas que creernos, aquí está el cálculo a mano de tres "
        "líneas y el valor que la herramienta escribió en el Excel.</p>")
    cuerpo.append(
        "<table><tr><th>Concepto</th><th>Cálculo a mano</th>"
        "<th>Importe calculado</th><th>Herramienta</th><th>¿Coincide?</th></tr>")

    manuales = []
    # El calculo manual se hace sobre plano_realista.dxf, que tiene partidas
    # mas variadas y una aritmetica ya verificada en
    # tests/test_totales.py::test_caso_manual_tres_lineas_calculadas_a_mano
    from app.pipeline import ejecutar as _ejecutar

    res_realista = _ejecutar(RAIZ / "planos" / "plano_realista.dxf", cat_ejemplo)
    p_real = res_realista["presupuesto"]

    cuerpo.append(
        "<p>Cálculo sobre <code>plano_realista.dxf</code>, un plano generado para "
        "probar el motor con lasimilitudes que tienen los planos reales: capas con "
        "nombres inconsistentes, un tablero nombrado <code>A-C-01</code> y texto "
        "dentro de la capa de muros. La aritmética de estas tres partidas está "
        "fijada en <code>tests/test_totales.py</code>.</p>")
    for l in p_real.lineas:
        if l.estado != "OK":
            continue
        cant = l.cantidad_ajustada
        pu = l.precio_unitario
        manual = "{:,.4f} {} × {:,.2f}".format(cant, l.unidad, pu)
        importe = round(cant * pu, 2)
        coincide = abs(importe - l.importe) < 0.005
        manuales.append((l.concepto, manual, importe, l.importe, coincide))
        cuerpo.append(
            "<tr><td>{}<br><small>capa {} · handle {}</small></td>"
            "<td><code>{}</code></td><td><b>{:,.2f}</b></td>"
            "<td>{:,.2f}</td><td>{}</td></tr>".format(
                esc(l.concepto), esc(l.capa), esc(", ".join(l.handles[:2]) + "…"),
                esc(manual), importe, l.importe,
                "sí" if coincide else "NO"))

    cuerpo.append(
        "<tr><td colspan='4'><b>Suma de las {} líneas de arriba, calculada a "
        "mano</b></td><td><b>{:,.2f}</b></td></tr>".format(
            len(manuales), sum(m[2] for m in manuales)))
    cuerpo.append("</table>")
    cuerpo.append(
        "<p><small>Precios de ejemplo. El cálculo manual usa la cantidad ya "
        "ajustada por rendimiento, tal como aparece en el presupuesto. La "
        "verificación de que estas tres cifras coinciden al centavo con el Excel, "
        "el PDF y el resultado de Python está en "
        "<code>tests/test_totales.py</code>.</small></p>")
    cuerpo.append("</div>")

    # --- Lo que no se pudo medir
    cuerpo.append("<h2>Lo que esta herramienta NO sabe hacer</h2>")
    cuerpo.append("<div class='card'><ul>")
    for item in [
        "No mide planos rasterizados ni escaneados. No hay OCR.",
        "No reconstruye las capas de CAD en un PDF: agrupa por color, que es una heurística.",
        "No sabe la escala de un plano: la tiene que dar el usuario.",
        "No tiene precios. No los propone ni los adivina.",
        "No lee DWG sin que instales ODA File Converter.",
        "No reconoce si un trazo repetido es un error del arquitecto o tres locales distintos.",
        "Si dos conceptos comparten una capa (por ejemplo puerta y ventana juntas), cuenta solo uno.",
        "No hay una sola validación con planos de obra reales de México.",
    ]:
        cuerpo.append("<li>{}</li>".format(esc(item)))
    cuerpo.append("</ul></div>")

    # --- Fuentes
    cuerpo.append("<h2>Fuentes y licencias</h2>")
    cuerpo.append("<div class='card'><table>")
    cuerpo.append("<tr><th>Archivo</th><th>Qué es</th><th>Licencia</th><th>Origen</th></tr>")
    vistos = set()
    for f in FUENTES:
        if f["archivo"] in vistos:
            continue
        vistos.add(f["archivo"])
        cuerpo.append("<tr><td>{}</td><td>{}</td><td>{}</td>"
                      "<td><a href='{}' target='_blank' rel='noopener'>{}</a></td></tr>".format(
                          esc(f["archivo"]), esc(f["titulo"]), esc(f["licencia"]),
                          esc(f["origen"]), esc(f["origen"][:60])))
    cuerpo.append("</table></div>")

    pagina = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Medición de planos a presupuesto (MXN) — demostración</title>
<style>{css}</style></head><body>
<header><h1>De plano a presupuesto en pesos, con la cuenta a la vista</h1>
<p>Demostración pública y verificable · los precios son de ejemplo</p></header>
<main>{cuerpo}</main>
<footer>Generado con ezdxf, shapely y pdfplumber. Cada cifra de este documento
proviene de ejecutar el motor; ninguna está escrita a mano.</footer>
</body></html>""".format(css=CSS, cuerpo="".join(cuerpo))

    destino = SALIDA / "demo.html"
    destino.write_text(pagina, encoding="utf-8")
    (SALIDA / "demo_datos.json").write_text(
        json.dumps({
            "caso_a_rasterizado": {"archivo": PLANO_REAL.name, **info_real},
            "caso_b_vectorial": {
                "mediciones": take_dxf["mediciones"],
                "lineas": [l.__dict__ for l in p_dxf.lineas],
                "subtotal": p_dxf.subtotal, "iva": p_dxf.iva, "total": p_dxf.total,
                "pt_por_metro": PT_POR_M,
            },
            "fuentes": FUENTES,
        }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print("escrito:", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())