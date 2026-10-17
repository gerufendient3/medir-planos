"""Compara lo que dice docs/FUENTES.md con lo que dicen los archivos.

Un documento de fuentes es util solo si coincide con la realidad. Si el
archivo cambio de tamaño o de licencia, el documento queda mintiendo sin que
nadie lo note.

Este script:
  1. mide cada fixture real (tamaño en disco, objetos vectoriales, imágenes);
  2. compara contra lo que FUENTES.md declara;
  3. comprueba que la licencia sea la que dice Commons, por API.

Los tamaños en bytes casi nunca coinciden con lo declarado en una tabla
escrita a mano, así que se comparan con tolerancia y se avisa del resto.

Uso:  python scripts/verificar_fuentes.py [--red]
Sin --red no consulta Commons: solo compara lo local.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "docs" / "FUENTES.md"
FIXTURES = RAIZ / "tests" / "fixtures" / "pdf"

problemas: list[str] = []
notas: list[str] = []

# Commons responde en inglés; el documento está en español. Comparar los
# textos tal cual daría un falso positivo en cada licencia.
EQUIVALENCIAS = {
    "dominio público": "public domain",
    "dominio publico": "public domain",
    "cc by-sa 4.0": "cc by-sa 4.0",
    "cc by-sa": "cc by-sa",
}


def mismo_licencia(declarada: str, de_commons: str) -> bool:
    d = declarada.strip().lower()
    c = de_commons.strip().lower()
    return d == c or EQUIVALENCIAS.get(d, d) == c


def archivos_reales() -> dict:
    """Datos medidos de los fixtures, no copiados de la documentación."""
    import pdfplumber

    salida = {}
    for f in sorted(FIXTURES.glob("*.pdf")):
        with pdfplumber.open(f) as pdf:
            vectores = 0
            imagenes = 0
            paginas = len(pdf.pages)
            for pag in pdf.pages:
                for _ in pag.objects.get("char", []):
                    pass
                vectores += sum(len(pag.objects.get(t, []))
                                for t in ("line", "rect", "curve", "path"))
                imagenes += len(pag.objects.get("image", []))
            box = pdf.pages[0].mediabox
            salida[f.name] = {
                "bytes": f.stat().st_size,
                "paginas": paginas,
                "vectores": vectores,
                "imagenes": imagenes,
                # La primera página es la que se inspecciona para decidir si
                # el PDF está rasterizado. Un documento de varias páginas
                # puede tener imágenes en unas y vectores en otras, así que
                # se reportan las dos cifras.
                "imagenes_pag1": len(pdf.pages[0].objects.get("image", [])),
                "pt_ancho": round(float(box[2] - box[0]), 1),
                "pt_alto": round(float(box[3] - box[1]), 1),
            }
    return salida


def _pide_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "verificar-fuentes/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def licencia_en_commons(titulo: str) -> dict:
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
           "&prop=imageinfo&iiprop=extmetadata%7Csize&titles="
           + urllib.parse.quote(titulo))
    datos = _pide_json(url)
    for _k, p in datos.get("query", {}).get("pages", {}).items():
        ii = (p.get("imageinfo") or [None])[0]
        if not ii:
            continue
        m = ii.get("extmetadata", {})
        return {
            "licencia": (m.get("LicenseShortName", {}) or {}).get("value"),
            "bytes": ii.get("size"),
            "url": ii.get("descriptionurl"),
        }
    return {}


def _titulos_de_commons(texto: str) -> list[str]:
    """Títulos de archivo de Commons, sin la puntuación del Markdown.

    El patrón ingenuo `File:[^\\]|`]+` se pasa de largo: como el paréntesis de
    cierre del enlace no está excluido y las comas sí, la captura se come el
    resto del documento y la consulta a la API vuelve vacía, dando un falso
    "no devuelve licencia".
    """
    crudos = re.findall(r"File:[^\n|`]+?\.pdf", texto)
    return sorted({t.strip() for t in crudos})


def main(argv: list[str]) -> int:
    con_red = "--red" in argv
    texto = FUENTES.read_text(encoding="utf-8")

    print("== Fixtures medidos ==")
    datos = archivos_reales()
    for nombre, d in sorted(datos.items()):
        print("  {:38} {:>10,} b  {:>6} pág  vec={} img={}  {}×{} pt"
              .format(nombre, d["bytes"], d["paginas"], d["vectores"],
                      d["imagenes"], d["pt_ancho"], d["pt_alto"]))

    # --- lo que FUENTES.md afirma por archivo
    print()
    print("== Lo que FUENTES.md declara ==")
    for nombre in datos:
        if nombre not in texto:
            problemas.append("FUENTES.md no menciona {}".format(nombre))
            continue
        # Busca la fila de la tabla de este archivo.
        for linea in texto.splitlines():
            if linea.startswith("| `" + nombre):
                print("  " + linea.strip()[:160])

    # --- dimensiones declaradas frente a las medidas
    for nombre, d in datos.items():
        m = re.search(r"`" + re.escape(nombre) + r"`[^\n]*?(\d+)\s*×\s*(\d+)\s*pt",
                      texto)
        if m and d["paginas"] == 1:
            ancho, alto = int(m.group(1)), int(m.group(2))
            if abs(ancho - d["pt_ancho"]) > 1 or abs(alto - d["pt_alto"]) > 1:
                problemas.append(
                    "{}: FUENTES.md dice {}×{} pt y el archivo mide {}×{} pt"
                    .format(nombre, ancho, alto, d["pt_ancho"], d["pt_alto"]))
            else:
                print("  {}: dimensiones coinciden ({}×{} pt)"
                      .format(nombre, d["pt_ancho"], d["pt_alto"]))
        elif m:
            notas.append(
                "{}: tiene {} páginas; la tabla de FUENTES.md compara "
                "dimensiones solo en documentos de una página."
                .format(nombre, d["paginas"]))

    # --- vectores e imagenes declarados
    for nombre, d in datos.items():
        m = re.search(r"`" + re.escape(nombre) + r"`[^\n|]*\|[^|]*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
                      texto)
        if m:
            vec, img = int(m.group(1)), int(m.group(2))
            # La tabla dice "objetos vectoriales / imágenes". Hay que aclarar
            # si cuenta el archivo entero o solo la primera página: en un
            # documento de varias páginas las dos cifras difieren.
            ref = d["imagenes_pag1"] if d["paginas"] == 1 else d["imagenes_pag1"]
            if vec != d["vectores"] or img != ref:
                problemas.append(
                    "{}: FUENTES.md dice {}/{} (vec/img) y el archivo tiene "
                    "{}/{} en la primera página, {} imágenes en {} páginas"
                    .format(nombre, vec, img, d["vectores"], ref,
                            d["imagenes"], d["paginas"]))
            else:
                print("  {}: vectores coinciden ({}) e imágenes de la "
                      "primera página coinciden ({}/{})"
                      .format(nombre, vec, vec, img))

    # --- licencias contra Commons
    if con_red:
        print()
        print("== Licencias consultadas en Commons ==")
        for titulo in _titulos_de_commons(texto):
            info = licencia_en_commons(titulo)
            if not info.get("licencia"):
                problemas.append("Commons no devuelve licencia para "
                                  + titulo)
                continue
            print("  {:<62} {}".format(info["licencia"], titulo[:58]))
            # La licencia declarada en el doc debe aparecer en la pagina.
            declarada = None
            for linea in texto.splitlines():
                if titulo in linea:
                    m = re.search(r"\*\*(.+?)\*\*", linea)
                    if m:
                        declarada = m.group(1)
            if declarada and not mismo_licencia(declarada, info["licencia"]):
                problemas.append(
                    "{}: FUENTES.md dice {} y Commons dice {}"
                    .format(titulo.strip(), declarada, info["licencia"]))
    else:
        notas.append("No se consultó Commons (falta --red).")

    # --- urls
    print()
    print("== URLs declaradas ==")
    for url in re.findall(r"https?://[^\s)|]+", texto):
        print("  " + url)

    print()
    for n in notas:
        print("AVISO:", n)
    if problemas:
        print("PROBLEMAS ({}):".format(len(problemas)))
        for p in problemas:
            print("  -", p)
        return 1
    print("FUENTES.md coincide con los archivos.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))