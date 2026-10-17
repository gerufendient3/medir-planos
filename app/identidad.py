"""Identidad del proyecto en un solo lugar.

Si el nombre, la versión, la licencia o la URL del repositorio cambian, se
cambian aqui y en ningun otro sitio. La interfaz, el footer, el boton de
reporte, el README y los metadatos leen de este modulo.

REPO_URL esta marcado como PENDIENTE a proposito: no se invento un nombre de
usuario ni de repositorio. Hasta que se confirme, el boton de reporte avisa
que el destino no esta configurado en vez de llevar a una URL inventada.
"""
from __future__ import annotations

# --- Identidad ---------------------------------------------------------

NOMBRE = "Medir planos"
# Version inicial. Semantica: 0.x = en desarrollo, sin promesa de estabilidad.
VERSION = "0.1.0"

DESCRIPCION = (
    "Herramienta libre para medir planos y generar presupuestos de obra."
)

# --- Licencia ----------------------------------------------------------

# MIT, confirmada por quien publica el proyecto el 2026-10-17.
# Titular y año en el archivo LICENSE. Si se cambia de licencia hay que
# cambiar los tres sitios a la vez: aquí, LICENSE y el README.
LICENCIA = "MIT"
LICENCIA_CONFIRMADA = True
AVISO_LICENCIA = (
    LICENCIA if LICENCIA_CONFIRMADA
    else f"{LICENCIA} (propuesta, pendiente de confirmación)"
)

# --- Repositorio -------------------------------------------------------

# Confirmado antes de publicar. La interfaz y el README salen de aquí: si
# algún día cambia de nombre o de dueño, se cambia en este archivo y en
# ningún otro.
REPO_URL = "https://github.com/LuisF/medir-planos"
REPO_ISSUE = f"{REPO_URL}/issues/new"


# --- Avisos fijos ------------------------------------------------------

# Se usan tal cual en la interfaz, en el README y en la landing para que
# no puedan divergir.
AVISO_SIN_VALIDACION = (
    "No está validado con planos de obra reales."
)
AVISO_NO_ES_CERTIFICACION = (
    "No es un software de certificación ni sustituye el criterio de un estimador."
)
AVISO_PRECIOS_EJEMPLO = (
    "Los precios de ejemplo no son precios de mercado: no existe fuente "
    "pública verificada de precios de obra en México."
)

# --- Limite de tamano --------------------------------------------------

# SUPUESTO, no dato. 80 MB es un numero redondo que se eligio sin fuente.
# Se aplica en cliente (servidor) y se declara en la interfaz.
TAMANO_MAX_MB = 80
TAMANO_MAX_MB_ES_SUPUESTO = True
NOTA_TAMANO = (
    f"Límite de {TAMANO_MAX_MB} MB por archivo. Es un supuesto, no un dato: "
    "se eligió por ser cómodo para planos típicos de obra. Se cambia en "
    "TAMANO_MAX_MB en app/identidad.py."
)