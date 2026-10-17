"""Revisa que el _meta de los catalogos sea cierto y no traiga texto raro.

Un catalogo es un archivo que el usuario edita a mano. Si su _meta dice algo
falso, el usuario toma decisiones sobre una base equivocada: por ejemplo,
creer que no trae precios cuando si los trae.

Este script revisa tres cosas:
  1. que los avisos del _meta no se contradigan con el contenido real;
  2. que no queden caracteres fuera del rango latino habitual, que suelen
     ser texto de otro idioma que se coló al traducir;
  3. que el archivo sea JSON valido y tenga la forma que espera la app.

Uso:  python scripts/auditar_catalogo.py
Sale con codigo 1 si encuentra algo, para poder usarlo en CI.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "catalogo"

# Rangos que no deberian aparecer en un catalogo en espanol.
# CJK, cirilico, hebreo, arabe, devanagari, tailandes, coreano.
RAROS = [
    (r"[\u4e00-\u9fff]", "caracteres chinos"),
    (r"[\u0400-\u04ff]", "cirilico"),
    (r"[\u0590-\u05ff]", "hebreo"),
    (r"[\u0600-\u06ff]", "arabe"),
    (r"[\u0900-\u097f]", "devanagari"),
    (r"[\u0e00-\u0e7f]", "tailandes"),
    (r"[\uac00-\ud7af]", "coreano"),
]

problemas: list[str] = []


def revisar(nombre: str) -> None:
    ruta = CATALOGO / nombre
    if not ruta.exists():
        problemas.append("{}: no existe".format(nombre))
        return

    texto = ruta.read_text(encoding="utf-8")

    # --- 2. texto que se coló de otro idioma
    for patron, nombre_rango in RAROS:
        for m in re.finditer(patron, texto):
            ctx = texto[max(0, m.start() - 30):m.end() + 30].replace("\n", " ")
            problemas.append(
                "{}: {} sin querer: ...{}...".format(nombre, nombre_rango, ctx))

    # --- 1. forma del archivo
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as exc:
        problemas.append("{}: JSON invalido: {}".format(nombre, exc))
        return

    for clave in ("conceptos", "_meta"):
        if clave not in datos:
            problemas.append("{}: falta la clave {!r}".format(nombre, clave))
    if "conceptos" not in datos:
        return

    conceptos = datos["conceptos"]
    sin_precio = [c for c in conceptos
                  if c.get("precio_unitario") in (None, "")]
    con_precio = [c for c in conceptos
                  if c.get("precio_unitario") not in (None, "")]

    avisos = " ".join(datos.get("_meta", {}).get("avisos", []))
    minusculas = avisos.lower()

    # La forma mas comun de mentira: un archivo CON precios que dice que no
    # los trae. Lleva a cargar un catalogo que ya estaba bien y a pensar que
    # falta informacion.
    if con_precio and "no vienen incluidos" in minusculas:
        problemas.append(
            "{}: tiene {} precio(s) pero su _meta dice que 'los precios NO "
            "vienen incluidos'. Contradiccion.".format(nombre, len(con_precio)))

    # Y al reves: uno SIN precios que dice que si los trae.
    if not con_precio and "los precios vienen incluidos" in minusculas:
        problemas.append(
            "{}: no tiene precios pero su _meta dice que vienen "
            "incluidos.".format(nombre))

    # Todo concepto necesita clave y unidad, si no la app no puede cotizarlo.
    for c in conceptos:
        if not c.get("clave"):
            problemas.append("{}: concepto sin 'clave': {!r}".format(nombre, c))
        if not c.get("unidad"):
            problemas.append("{}: concepto sin 'unidad': {!r}".format(nombre, c))

    print("{:24} {:>3} conceptos  {:>2} con precio".format(
        nombre, len(conceptos), len(con_precio)))


def main() -> int:
    nombres = sorted(p.name for p in CATALOGO.glob("*.json"))
    if not nombres:
        print("no hay catalogos en", CATALOGO)
        return 1
    for n in nombres:
        revisar(n)

    print()
    if problemas:
        print("PROBLEMAS ({}):".format(len(problemas)))
        for p in problemas:
            print("  -", p)
        return 1
    print("Todos los catalogos son coherentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())