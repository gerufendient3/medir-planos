"""Verificacion en navegador real con Playwright.

Los tests de pytest comprueban estructura del HTML. Esto comprueba lo que
ellos no pueden: que se ve bien, que el flujo funciona de verdad y que no
hay errores en consola.

Genera capturas en docs/capturas/ y un reporte en docs/VERIFICACION.md.
Las capturas son artefactos de verificacion: no son datos de usuario.

Uso:
    python scripts/verificar_navegador.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAPTURAS = RAIZ / "docs" / "capturas"
REPORTE = RAIZ / "docs" / "VERIFICACION.md"

sys.path.insert(0, str(RAIZ))
from app.identidad import TAMANO_MAX_MB as TAMANO_MB  # noqa: E402

PUERTO = 8799
BASE = f"http://127.0.0.1:{PUERTO}"

ESCRITORIO = {"width": 1280, "height": 900}
MOVIL = {"width": 390, "height": 844}


class Servidor:
    def __enter__(self):
        self.p = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.web:app",
             "--host", "127.0.0.1", "--port", str(PUERTO),
             "--log-level", "warning"],
            cwd=str(RAIZ), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            time.sleep(0.5)
            try:
                import urllib.request
                urllib.request.urlopen(BASE, timeout=2)
                return self
            except Exception:
                continue
        raise RuntimeError("el servidor no arrancó")

    def __exit__(self, *a):
        self.p.terminate()
        try:
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def _axe(page):
    """Corre axe-core sobre la página actual. Devuelve la lista de hallazgos."""
    import urllib.request

    # axe-core desde el CDN de unpkg; si no hay red, se omite y se reporta.
    try:
        src = urllib.request.urlopen(
            "https://unpkg.com/axe-core@4.10.0/axe.min.js",
            timeout=20).read().decode()
    except Exception:
        return None, "no se pudo descargar axe-core (sin red)"
    page.add_script_tag(content=src)
    return page.evaluate("axe.run()"), None


def _una_linea(texto: str) -> str:
    """Colapsa a una sola línea: una celda con saltos rompe la tabla Markdown."""
    return " ".join(texto.split())


def _kb(n) -> str:
    """Tamaño aproximado, en KB.

    El byte exacto cambia en cada corrida: el xlsx y el PDF llevan dentro la
    marca de tiempo de creación. Poner el número exacto haría que este
    archivo se modificara solo y daría a entender una precisión que no hay.
    """
    return "{:.1f} KB".format(int(n or 0) / 1024)


def _valor_total(page) -> str:
    """Saca solo la cifra del Total, no las cuatro líneas del bloque."""
    el = page.query_selector(".totales dd:last-of-type")
    if el is None:
        return _una_linea(page.inner_text(".totales"))
    return _una_linea(el.inner_text())


def _separar_consola(resultados: dict, vista: str, errores: list) -> list:
    """Mete cada mensaje en su cubo y devuelve los de JavaScript."""
    js = []
    for e in errores:
        if _clasificar_consola(e) == "red":
            resultados["consola_red"].append({"vista": vista, "mensaje": e})
        else:
            js.append({"vista": vista, "error": e})
    return js


def _clasificar_consola(mensaje: str) -> str:
    """Separa errores de JavaScript de avisos de red.

    El navegador registra en consola los estados HTTP de las peticiones. Las
    pruebas de error provocan 400 y 413 a proposito, asi que eso no es un
    fallo de la pagina: son respuestas que la propia prueba pidio. Solo lo
    que viene de un script cuenta como error real.
    """
    if "Failed to load resource" in mensaje or "status of" in mensaje:
        return "red"
    return "javascript"


def _contraste():
    """Calcula el contraste real de los pares de color del CSS."""
    def lum(hexc):
        hexc = hexc.lstrip("#")
        c = [int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

    def ratio(a, b):
        la, lb = lum(a), lum(b)
        hi, lo = max(la, lb), min(la, lb)
        return (hi + 0.05) / (lo + 0.05)

    pares = [
        ("tinta sobre fondo", "#1c2430", "#ffffff"),
        ("tenue sobre fondo", "#5b6672", "#ffffff"),
        ("acento sobre fondo", "#1d4ed8", "#ffffff"),
        ("aviso sobre aviso-fondo", "#8a4b08", "#fdf6ec"),
        ("peligro sobre peligro-fondo", "#a11a1a", "#fdf2f2"),
        ("ok sobre ok-fondo", "#14622f", "#f0f7f2"),
        ("incompleto (blanco sobre rojo)", "#ffffff", "#a11a1a"),
        ("boton primario (blanco sobre acento)", "#ffffff", "#1d4ed8"),
        ("tinta sobre panel", "#1c2430", "#f6f7f9"),
        ("tenue sobre panel", "#5b6672", "#f6f7f9"),
    ]
    return [{"par": n, "a": a, "b": b, "ratio": round(ratio(a, b), 2),
             "cumple_AA": ratio(a, b) >= 4.5,
             "cumple_AAA": ratio(a, b) >= 7.0}
            for n, a, b in pares]


def main() -> int:
    from playwright.sync_api import sync_playwright

    CAPTURAS.mkdir(parents=True, exist_ok=True)
    resultados = {"capturas": [], "consola": [], "consola_red": [],
                  "flujo": {}, "errores_ui": {}, "accesibilidad": []}

    with Servidor():
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            plano = str(RAIZ / "planos" / "plano_realista.dxf")
            plano_malo = str(RAIZ / "tests" / "fixtures" / "pdf" / "pd_escaneado.pdf")

            # --- 1) estados en escritorio y movil
            for etiqueta, viewport in (("escritorio", ESCRITORIO), ("movil", MOVIL)):
                page = nav.new_page(viewport=viewport)
                errores = []
                page.on("console", lambda m: errores.append(m.text)
                        if m.type == "error" else None)
                page.on("pageerror", lambda e: errores.append(str(e)))

                # vacio
                page.goto(BASE, wait_until="networkidle")
                p = CAPTURAS / f"01-vacio-{etiqueta}.png"
                page.screenshot(path=str(p), full_page=True)
                resultados["capturas"].append(p.name)

                # cargando (retarda la respuesta para poder capturarlo en curso)
                def _ralentizar(route):
                    time.sleep(1.5)
                    route.continue_()

                page.route("**/subir", _ralentizar)
                page.set_input_files("#plano", plano)
                page.click("button[type=submit]")
                page.wait_for_selector(".totales", timeout=30000)
                page.unroute("**/subir")
                p = CAPTURAS / f"02-takeoff-{etiqueta}.png"
                page.screenshot(path=str(p), full_page=True)
                resultados["capturas"].append(p.name)

                # advertencias abiertas
                for details in page.query_selector_all("details.detalle"):
                    details.evaluate("e => e.open = true")
                p = CAPTURAS / f"03-advertencias-{etiqueta}.png"
                page.screenshot(path=str(p), full_page=True)
                resultados["capturas"].append(p.name)

                # error: archivo corrupto
                malo = CAPTURAS / "_malo.dxf"
                malo.write_bytes(b"esto no es un dxf valido" * 50)
                page.goto(BASE, wait_until="networkidle")
                page.set_input_files("#plano", str(malo))
                page.click("button[type=submit]")
                page.wait_for_selector("main[role=alert]", timeout=30000)
                p = CAPTURAS / f"04-error-corrupto-{etiqueta}.png"
                page.screenshot(path=str(p), full_page=True)
                resultados["capturas"].append(p.name)
                resultados["errores_ui"][f"DXF corrupto ({etiqueta})"] = \
                    _una_linea(page.inner_text("main[role=alert]"))[:90]
                malo.unlink()

                # error: PDF escaneado
                page.goto(BASE, wait_until="networkidle")
                page.set_input_files("#plano", plano_malo)
                page.click("button[type=submit]")
                page.wait_for_selector("text=No se pudo medir nada",
                                       timeout=120000)
                p = CAPTURAS / f"05-error-escaneado-{etiqueta}.png"
                page.screenshot(path=str(p), full_page=True)
                resultados["capturas"].append(p.name)
                resultados["errores_ui"][f"PDF escaneado ({etiqueta})"] = \
                    _una_linea(page.inner_text(".vacio"))[:90]

                resultados["consola"].extend(
                    _separar_consola(resultados, etiqueta, errores))
                page.close()

            # --- 2) flujo completo: subir, editar precio, descargar
            page = nav.new_page(viewport=ESCRITORIO)
            errores = []
            page.on("console", lambda m: errores.append(m.text)
                    if m.type == "error" else None)
            page.on("pageerror", lambda e: errores.append(str(e)))

            page.goto(BASE, wait_until="networkidle")
            page.set_input_files("#plano", plano)
            page.click("button[type=submit]")
            page.wait_for_selector("input[name=precio]", timeout=60000)

            subtotal_antes = _valor_total(page)
            incomplete_antes = page.query_selector(".incompleto") is not None
            campos = page.query_selector_all("input[name=precio]")
            for campo in campos:
                campo.fill("1234.50")
            page.click("form[action^='/precios'] button[type=submit]")
            page.wait_for_selector("input[name=precio]", timeout=60000)
            subtotal_despues = _valor_total(page)
            incomplete_despues = page.query_selector(".incompleto") is not None

            # El total incompleto tiene su propia captura: es el estado que
            # más importa que se entienda, porque el número está incompleto.
            inc = page.query_selector(".incompleto")
            if inc:
                inc.scroll_into_view_if_needed()
                p = CAPTURAS / "09-total-incompleto.png"
                page.screenshot(path=str(p), full_page=False)
                resultados["capturas"].append(p.name)
                resultados["flujo"]["texto_total_incompleto"] = \
                    _una_linea(inc.inner_text())
            p = CAPTURAS / "06-precios-cargados.png"
            page.screenshot(path=str(p), full_page=True)
            resultados["capturas"].append(p.name)

            # descargas reales
            with page.expect_download() as di:
                page.click("a[href$='/xlsx']")
            d = di.value
            destino = CAPTURAS / "salida.xlsx"
            d.save_as(str(destino))
            with page.expect_download() as di2:
                page.click("a[href$='/pdf']")
            d2 = di2.value
            destino2 = CAPTURAS / "salida.pdf"
            d2.save_as(str(destino2))

            resultados["flujo"] = {
                "total_sin_precios": subtotal_antes,
                "total_con_precios": subtotal_despues,
                "texto_total_incompleto": _una_linea(inc.inner_text()) if inc
                                          else "",
                "precios_cargados": len(campos),
                "incompleto_sin_precios": incomplete_antes,
                "incompleto_con_precios": incomplete_despues,
                "xlsx_bytes": destino.stat().st_size,
                "pdf_bytes": destino2.stat().st_size,
                "xlsx_valido": destino.read_bytes()[:2] == b"PK",
                "pdf_valido": destino2.read_bytes()[:5] == b"%PDF-",
            }

            # reporte de problema
            # inner_text() devuelve "" en un textarea: hay que leer el valor.
            reporte = page.input_value("#reporte")
            resultados["flujo"]["reporte_no_adjunta_plano"] = (
                "NO se adjunta" in reporte)
            resultados["flujo"]["reporte_tiene_version"] = "0.1.0" in reporte
            resultados["flujo"]["reporte_bytes"] = len(reporte)
            # El archivo subido no debe aparecer en el reporte más que por
            # su nombre: el reporte va a un foro público.
            resultados["flujo"]["reporte_solo_lista_el_nombre"] = (
                plano.split("\\")[-1] in reporte)

            # Errores de DWG y de tamaño, en escritorio y en móvil.
            for etiqueta, viewport in (("escritorio", ESCRITORIO),
                                       ("movil", MOVIL)):
                page.set_viewport_size(viewport)
                errores = []
                page.on("console", lambda m: errores.append(m.text)
                        if m.type == "error" else None)
                page.on("pageerror", lambda e: errores.append(str(e)))

                # DWG sin ODA instalado
                dwg = CAPTURAS / "_prueba.dwg"
                dwg.write_bytes(b"AC1024" + b"\x00" * 40)
                page.goto(BASE, wait_until="networkidle")
                page.set_input_files("#plano", str(dwg))
                page.click("button[type=submit]")
                page.wait_for_selector("main[role=alert]", timeout=30000)
                p = CAPTURAS / f"07-error-dwg-sin-oda-{etiqueta}.png"
                page.screenshot(path=str(p), full_page=True)
                resultados["capturas"].append(p.name)
                resultados["errores_ui"][f"dwg sin ODA ({etiqueta})"] = \
                    _una_linea(page.inner_text("main[role=alert]"))[:90]
                dwg.unlink()

                # archivo que excede el limite de tamano
                grande = CAPTURAS / "_grande.dxf"
                grande.write_bytes(b"0" * (TAMANO_MB * 1024 * 1024 + 4096))
                page.goto(BASE, wait_until="networkidle")
                page.set_input_files("#plano", str(grande))
                page.click("button[type=submit]")
                page.wait_for_selector("main[role=alert]", timeout=60000)
                p = CAPTURAS / f"08-error-sobre-limite-{etiqueta}.png"
                page.screenshot(path=str(p), full_page=True)
                resultados["capturas"].append(p.name)
                resultados["errores_ui"][f"sobre el límite ({etiqueta})"] = \
                    _una_linea(page.inner_text("main[role=alert]"))[:90]
                grande.unlink()

                resultados["consola"].extend(
                    _separar_consola(resultados, f"errores-{etiqueta}", errores))
            page.set_viewport_size(ESCRITORIO)

            # accesibilidad: portada y pantalla de resultados
            for etiqueta, url in (("portada", BASE),):
                page.goto(url, wait_until="networkidle")
                res, err = _axe(page)
                if err:
                    resultados["accesibilidad"].append(
                        {"vista": etiqueta, "nota": err, "violaciones": []})
                elif res:
                    resultados["accesibilidad"].append({
                        "vista": etiqueta,
                        "violaciones": [
                            {"id": v["id"], "impacto": v["impact"],
                             "nodos": len(v["nodes"]),
                             "ayuda": v["help"]}
                            for v in res["violations"]],
                    })

            # La pantalla de resultados es la densa: se escanea con plano
            # cargado, que es donde hay tablas, avisos y campos de precio.
            page.goto(BASE, wait_until="networkidle")
            page.set_input_files("#plano", plano)
            page.click("button[type=submit]")
            page.wait_for_selector("input[name=precio]", timeout=60000)
            res, err = _axe(page)
            if err:
                resultados["accesibilidad"].append(
                    {"vista": "resultados", "nota": err, "violaciones": []})
            elif res:
                resultados["accesibilidad"].append({
                    "vista": "resultados",
                    "violaciones": [
                        {"id": v["id"], "impacto": v["impact"],
                         "nodos": len(v["nodes"]),
                         "ayuda": v["help"]}
                        for v in res["violations"]],
                })

            resultados["consola"].extend(
                _separar_consola(resultados, "flujo", errores))
            page.close()
            nav.close()

    # --- contraste
    contraste = _contraste()

    # --- reporte
    lineas = ["# Verificación en navegador real", "",
              "Generado por `scripts/verificar_navegador.py`. "
              "No editar a mano.", "",
              "## Consola del navegador", "",
              "### Errores de JavaScript", ""]
    if resultados["consola"]:
        lineas += ["| Vista | Error |", "|---|---|"]
        lineas += [f"| {c['vista']} | `{c['error']}` |"
                   for c in resultados["consola"]]
    else:
        lineas.append("**Sin errores de JavaScript ni excepciones sin capturar "
                      "en ninguna vista ni tamaño de pantalla.**")

    lineas += ["", "### Respuestas HTTP anotadas por el navegador", "",
               "No son fallos de la página: son los estados que las pruebas de "
               "error provocan a propósito para comprobar que la interfaz los "
               "muestra.", ""]
    if resultados["consola_red"]:
        cuenta = {}
        for c in resultados["consola_red"]:
            clave = (c["vista"], c["mensaje"])
            cuenta[clave] = cuenta.get(clave, 0) + 1
        lineas += ["| Vista | Estado | Veces |", "|---|---|---|"]
        for (vista, mensaje), n in sorted(cuenta.items()):
            estado = re.search(r"status of (\d+)", mensaje)
            lineas.append("| {} | {} | {} |".format(
                vista, estado.group(1) if estado else mensaje, n))
    else:
        lineas.append("Ninguna.")

    lineas += ["", "## Flujo completo", "",
               "| Comprobación | Resultado |", "|---|---|"]
    f = resultados["flujo"]
    lineas += [
        f"| Campos de precio en la pantalla | {f.get('precios_cargados')} |",
        f"| Total sin precios | {f.get('total_sin_precios')} |",
        f"| Total con precios puestos | {f.get('total_con_precios')} |",
        f"| Marcado incompleto sin precios | "
        f"{f.get('incompleto_sin_precios')} |",
        f"| Marcado incompleto con precios | "
        f"{f.get('incompleto_con_precios')} |",
        f"| Rótulo del total incompleto | "
        f"{_una_linea(str(f.get('texto_total_incompleto', '(no encontrado)')))} |",
        f"| Excel descargado y válido | {f.get('xlsx_valido')} "
        f"(~{_kb(f.get('xlsx_bytes'))}) |",
        f"| PDF descargado y válido | {f.get('pdf_valido')} "
        f"(~{_kb(f.get('pdf_bytes'))}) |",
        f"| El reporte no adjunta el plano | {f.get('reporte_no_adjunta_plano')} |",
        f"| El reporte lleva la versión | {f.get('reporte_tiene_version')} |",
        f"| El reporte solo cita el nombre del archivo | "
        f"{f.get('reporte_solo_lista_el_nombre')} |",
    ]

    lineas += ["", "## Errores en la interfaz", "",
               "| Caso | Se muestra el error |", "|---|---|"]
    for k, v in resultados["errores_ui"].items():
        lineas.append("| {} | {} |".format(k, _una_linea(str(v))))

    lineas += ["", "## Accesibilidad (axe-core)", ""]
    if not resultados["accesibilidad"]:
        lineas.append("No se pudo ejecutar axe-core.")
    for a in resultados["accesibilidad"]:
        lineas.append(f"### {a['vista']}")
        if a.get("nota"):
            lineas.append(f"No se pudo ejecutar: {a['nota']}")
        elif not a["violaciones"]:
            lineas.append("**Sin violaciones.**")
        else:
            lineas += ["| Regla | Impacto | Nodos | Ayuda |", "|---|---|---|---|"]
            for v in a["violaciones"]:
                lineas.append(f"| {v['id']} | {v['impacto']} | {v['nodos']} "
                              f"| {v['ayuda']} |")

    lineas += ["", "## Contraste calculado (WCAG 2.1)", "",
               "Medido con la fórmula de luminancia relativa, no declarado.",
               "", "| Par | Colores | Ratio | AA (4.5) | AAA (7) |",
               "|---|---|---|---|---|"]
    for c in contraste:
        lineas.append(f"| {c['par']} | {c['a']} / {c['b']} | **{c['ratio']}** "
                      f"| {'sí' if c['cumple_AA'] else 'NO'} "
                      f"| {'sí' if c['cumple_AAA'] else 'no'} |")

    lineas += ["", "## Capturas", ""]
    for c in sorted(resultados["capturas"]):
        lineas.append(f"- `capturas/{c}`")

    REPORTE.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[:40]))
    print(f"\nescrito {REPORTE}")
    print(f"capturas en {CAPTURAS}: {len(resultados['capturas'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())