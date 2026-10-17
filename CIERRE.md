# Cierre — versión 0.1.0

> **Estado: versión 0.1.0, candidata a publicación.**
> **No está validada con planos de obra reales.**

Este documento resume en un solo lugar qué se verificó, qué no, qué falta
decidir y qué hay que hacer para publicar. No declara la versión como final ni
la herramienta como lista para usar: no hay base para decirlo.

- Versión declarada en `app/identidad.py`: `VERSION = "0.1.0"`
- Commit de esta versión: `54b397f` (rama `main`, 97 archivos versionados)
- Suite: **197 pruebas en verde**
- Sin remoto configurado. **No se ha publicado nada.**

---

## 1. Qué funciona, y qué prueba lo respalda

Cada línea de esta tabla está comprobada por una prueba con nombre. No es una
lista de intenciones: si la prueba deja de pasar, la afirmación deja de ser
cierta.

| Comportamiento | Prueba que lo demuestra |
|---|---|
| Mide áreas, longitudes y conteos por capa, con unidad comprobada | `test_compatibilidad.py` (9 pruebas) |
| Una luminaria se cobra por pieza, nunca por m² | `test_regresion_luminarias_no_se_cobran_como_m2` |
| Una capa incompatible no contamina a las demás | `test_incompatibilidad_no_contamina_el_resto` |
| El solape de superficies se une: 10×10 con patio 4×4 da 84 m², no 116 | `test_casos_reales.py` |
| El bulge (arcos) se resuelve geométricamente | `test_bulge_resuelve_el_arco` |
| Las islas de un HATCH se restan | `test_hatch_con_isla_resta_el_patio` |
| Cada cantidad conserva el handle de la entidad DXF de origen | `test_todas_las_omisiones_llevan_handle_y_motivo` |
| Una entidad con unidad incompatible se reporta y se excluye | `test_entidad_incompatible_se_reporta_con_handle` |
| Sin precio, la línea se excluye y el subtotal no la cuenta | `test_cada_concepto_sin_precio_queda_marcado`, `test_catalogo_de_sin_precio_da_subtotal_cero` |
| El total se marca incompleto si alguna línea quedó fuera | `test_el_total_se_marca_incompleto`, `test_excel_marca_el_total_como_incompleto` |
| IVA 16 % con redondeo a dos decimales, y Python = Excel = PDF al centavo | `test_total_es_subtotal_mas_iva`, `test_totales.py` (8) |
| El catálogo cubre las capas del plano de referencia | `test_catalogo_capas_reales.py` (12) |
| Un PDF escaneado se detecta y **no** se mide | `test_pdf_real_de_plano_resulta_escaneado` |
| Un DXF corrupto da error legible, no resultado vacío | `test_un_archivo_pequeno_corrupto_da_error_de_contenido` |
| DWG sin ODA da error que dice qué instalar y dónde | `test_sin_oda_el_dwg_no_se_omite_en_silencio` |
| El archivo se procesa en memoria y no se escribe a disco | `test_el_archivo_subido_no_se_conserva` |
| Si el procesamiento falla, el temporal se borra igual | `test_el_temporal_se_borra_si_falla` |
| El archivo subido se cierra aunque la salida sea un error | `test_el_subir_cierra_el_archivo_en_todas_las_salidas` |
| No hay base de datos ni persistencia de sesión | `test_no_hay_persistencia_de_sesiones` |
| Nada sale a otros servidores | `test_sin_imports_de_red_en_la_app` |
| Sin analítica ni scripts de terceros | `test_no_hay_analitica_ni_scripts_de_terceros` |
| Nada del plano aparece en los logs | `test_no_hay_logs_del_contenido_del_plano` |
| No quedan archivos en TEMP tras procesar | `python scripts/comprobar_temporal.py` |
| El límite de 80 MB se aplica en servidor y se declara en el formulario | `test_el_limite_se_aplica_en_el_servidor`, `test_el_limite_se_declara_en_el_cliente` |
| Los errores se ven como página HTML, no como JSON crudo | `test_los_errores_se_ven_como_pagina_no_como_json` |
| El error no filtra rutas del servidor | `test_el_error_no_filtra_rutas_del_servidor` |
| La interfaz no muestra un enlace a un repositorio inventado | `test_no_hay_url_de_repositorio_inventada` |
| Contraste por encima de AA en todos los pares de color | `test_los_contrastes_del_css_cumplen_aa` |
| Los comentarios de contraste del CSS son ciertos | `test_los_contrastes_del_css_no_son_solo_un_comentario` |
| Sin violaciones de accesibilidad (axe-core) en portada y resultados | `docs/VERIFICACION.md` |
| El sitio público no inventa tracción, precios ni usuarios | `test_publico.py` (26+) |
| La documentación no se queda vieja | `test_el_indice_de_casos_coincide_con_la_suite`, `test_las_fuentes_coinciden_con_los_archivos` |

---

## 2. Qué no funciona o no está verificado

| Limitación | Detalle |
|---|---|
| **Ningún plano de obra real se ha procesado** | Todo lo verificado usa planos sintéticos y dos planos reales de archivo público. Es la limitación de la que no hay evidencia para salir. |
| **DWG sin verificar en ejecución** | El camino con ODA File Converter está implementado y da un error claro cuando falta, pero **la conversión nunca se ejecutó**: ODA no se pudo instalar en el entorno de desarrollo. Que funcione con un DWG real es una suposición. |
| **PDF escaneado no se mide** | Se detecta y se avisa. No hay OCR y no se intenta medir. Correcto, pero es una limitación: muchos planos llegan así. |
| **Un PDF no guarda la escala** | La indica el usuario. Con `1.0` salen puntos, no metros. **Nada comprueba que la escala sea correcta.** |
| **Un PDF no tiene capas** | Se agrupa por color de trazo. Es una heurística, no una reconstrucción de CAD. |
| **Precios de ejemplo inventados** | `catalogo/demo_precios.json` trae 11 precios inventados para que la demostración sea legible. **No son precios de mercado**: no existe fuente pública verificada de precios de obra en México. |
| **Los dos planos reales de archivo público llegan rasterizados** | Los dos tienen 0 objetos vectoriales. No ejercitan la ruta vectorial; esa ruta se prueba con un PDF generado de contenido conocido. |
| **El límite de 80 MB es un supuesto** | Sin fuente. Elegido por ser cómodo para planos típicos. |
| **La CI no se ha ejecutado** | `.github/workflows/ci.yml` y `pages.yml` son YAML válido y sus comandos se ejecutaron localmente, pero **nunca han corrido en GitHub**. |

---

## 3. Decisiones aplicadas

Las siete decisiones se recibieron y se aplicaron:

| Decisión | Valor | Dónde vive |
|---|---|---|
| Licencia | **MIT**, confirmada | `LICENSE`, `LICENCIA_CONFIRMADA = True` en `app/identidad.py` |
| Titular y año | **LuisF, 2026** | `LICENSE` |
| Repositorio | **https://github.com/LuisF/medir-planos** | `REPO_URL` y `REPO_CONFIRMADO = True` en `app/identidad.py` |
| Visibilidad | **Pública**, activada a mano por quien publica | No hay nada en el repositorio que la fije: es una acción en GitHub |
| Alojamiento | **Opción A**: GitHub Pages para la demo y la documentación. La app se ejecuta en local clonando el repositorio. | `.github/workflows/pages.yml` |
| Límite de subida | **80 MB**, sin cambios, sigue declarado como supuesto | `TAMANO_MAX_MB` en `app/identidad.py` |
| Plano de obra real | **Ninguno.** Se mantiene el aviso de no validación. | — |

La interfaz ya enlaza al repositorio real y el botón de reportar un problema
abre una incidencia con los datos técnicos de la corrida.

**Lo que sigue sin cerrar: el plano de obra real.** Ninguna de las otras seis
decisiones lo compensa.

---

## 4. Pasos que quedan

Los dos marcadores ya están resueltos y aplicados. Falta la parte que solo se
puede hacer desde GitHub.

### 4.1 Nada que cambiar en el código

`REPO_URL` y `LICENCIA_CONFIRMADA` ya tienen su valor final. La suite lo
comprueba: si alguien los cambia por un valor a medias, falla.

### 4.2 Crear el repositorio

En <https://github.com/new>, **sin** marcar "Initialize with a README": el
repositorio local ya tiene todo. Nombre y usuario: `LuisF/medir-planos`.

### 4.2 Comprobar que nada quedó a medias

```bash
python -m pytest tests -q
```

Hay pruebas que fallan si `REPO_CONFIRMADO` queda a `True` sin URL real, o si
la licencia del código y la de `LICENSE` dejan de coincidir.

### 4.3 Subir

```bash
git remote add origin https://github.com/LuisF/medir-planos.git
git push -u origin main
```

### 4.4 Después de subir

1. Revisar el primer `git status`: si aparece algún plano o salida, hay que
   parar. Lo que está aquí ya pasó la verificación, pero una mirada de más no
   cuesta.
2. **Settings → Pages → Source = GitHub Actions** para activar la opción A.
   Es el paso que más se olvida y sin él no se publica el sitio.
3. **Settings → General → Features → Issues** para habilitar las plantillas de
   `.github/ISSUE_TEMPLATE/`.
4. Esperar a que `ci.yml` termine en verde antes de dar por buena la versión.

Sobre la visibilidad: se eligió **pública**, y eso es una acción en GitHub, no
algo que viva en el repositorio. Si en algún momento quieres volver a privado,
está en *Settings → Danger Zone → Change visibility*. El sentido inverso, de
privado a público, no se puede sin borrar el repositorio.

---

## 5. Condición de reapertura

**Si un plano de obra real falla al procesarse, o produce una cifra incorrecta,
este cierre queda sin efecto y el proyecto vuelve a desarrollo.**

Concretamente, este cierre se reabre si ocurre cualquiera de estas cosas:

- Un plano real produce un total que no cuadra con lo calculado a mano.
- Un plano real se procesa sin error pero midiendo una superficie que no es la
  del plano.
- La conversión DWG falla con un archivo real, o da un resultado que no
  corresponde al dibujo.
- Aparece un plano de cliente en el repositorio o en su historial.
- Se encuentra una cifra o un dato de origen desconocido dando vueltas en el
  código.

Al reabrirse, hay que: bajar el rótulo a desarrollo, corregir, añadir la
prueba de regresión que cubra el fallo, y volver a levantar este documento con
un número de versión nuevo.

---

## 6. Cualquier cambio posterior requiere una nueva solicitud

Este documento cierra la versión 0.1.0. **No lo amplía ni lo sustituye.**

A partir de aquí, cualquier cambio —una función nueva, un catálogo distinto,
otro formato de entrada, un ajuste de la interfaz— **requiere una solicitud
nueva y explícita**, con su propio alcance, sus propias pruebas y su propio
documento de cierre.

Lo que no se ha hecho aquí, y por tanto **no está hecho**: está en
`IDEAS.md`, que es solo una lista. Ninguna de esas ideas está implementada ni
comprometida.