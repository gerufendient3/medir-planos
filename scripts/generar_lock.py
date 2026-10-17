#!/usr/bin/env python
"""Genera requirements.lock.txt desde el entorno instalado.

Se ejecuta dentro del venv. Las licencias se leen de los metadatos de las
distribuciones instaladas, no de memoria: para no afirmar una licencia que
no se ha comprobado.

Uso:  python scripts/generar_lock.py
"""
from __future__ import annotations

import sys
from importlib import metadata

RAIZ = sys.path[0].rsplit("scripts", 1)[0].rstrip("\\/")
SALIDA = RAIZ + r"\requirements.lock.txt"

EXCLUIR = {"pip", "setuptools", "wheel", "relaykit"}

# Solo se documentan las dependencias directas. El lock lleva todas.
DIRECTAS = [
    ("ezdxf", "Lectura y escritura de DXF"),
    ("shapely", "Geometría: área, unión de superficies"),
    ("pdfplumber", "Extracción de geometría vectorial de PDF"),
    ("pdfminer.six", "Dependencia de pdfplumber"),
    ("openpyxl", "Exportación a Excel"),
    ("reportlab", "Exportación a PDF"),
    ("pypdf", "Verificación de PDF en pruebas"),
    ("fastapi", "Interfaz web"),
    ("uvicorn", "Servidor ASGI"),
    ("python-multipart", "Parsing de formularios"),
    ("pytest", "Pruebas"),
    ("matplotlib", "Render de planos a PNG (fixtures)"),
]


def licencia(dist) -> str:
    m = dist.metadata
    # Formato moderno
    v = m.get("License-Expression")
    if v:
        return v
    v = m.get("License")
    if v and len(v) < 40:
        return v
    # Clasificadores de licencia (formato clasico)
    for c in m.get_all("Classifier") or []:
        if c.startswith("License ::"):
            return c.replace("License :: ", "").replace(" OSI Approved :: ", "")
    return "NO DECLARADA en los metadatos"


def main() -> int:
    lineas = [
        "# Lock exacto del entorno verificado. Generado con:",
        "#   python scripts/generar_lock.py",
        "#",
        "# No editar a mano. Para cambiar una version: cambia requirements.txt,",
        "# reinstala en un entorno limpio, corre la suite y regenera este archivo.",
        "",
    ]
    for nombre, _ in DIRECTAS:
        try:
            dist = metadata.distribution(nombre)
        except metadata.PackageNotFoundError:
            lineas.append(f"# FALTA: {nombre} no esta instalado")
            continue
        lineas.append(f"{dist.metadata['Name']}=={dist.version}")

    todos = sorted(
        (d for d in metadata.distributions()
         if (d.metadata["Name"] or "").lower() not in EXCLUIR),
        key=lambda d: (d.metadata["Name"] or "").lower())

    lineas += ["", "# --- Todas las instaladas ---"]
    for d in todos:
        lineas.append(f"{d.metadata['Name']}=={d.version}")

    with open(SALIDA, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lineas) + "\n")

    # Tabla de licencias para pegarla en el README
    print("\n| Paquete | Versión | Licencia | Para qué |")
    print("|---|---|---|---|")
    for nombre, uso in DIRECTAS:
        try:
            dist = metadata.distribution(nombre)
        except metadata.PackageNotFoundError:
            print(f"| {nombre} | — | NO INSTALADO | {uso} |")
            continue
        print(f"| {dist.metadata['Name']} | {dist.version} | "
              f"{licencia(dist)} | {uso} |")

    # Alertar si alguna dependencia es copyleft. Se lee de los metadatos.
    copYLEFT = ("GPL", "AGPL", "MPL", "CDDL")
    print("\n# CopYLEFT detectado en dependencias:")
    encontrados = []
    for d in todos:
        lic = licencia(d)
        if any(c in lic.upper() for c in copYLEFT):
            encontrados.append((d.metadata["Name"], lic))
    for nombre, lic in encontrados:
        print(f"  {nombre}: {lic}")
    if not encontrados:
        print("  (ninguno)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())