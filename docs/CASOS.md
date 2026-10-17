# Lista de casos de prueba y su estado

Fecha: 17 de octubre de 2026. Ejecutar: `python -m pytest tests -v`

Resultado global: **99 casos, 99 pasan, 0 fallan.**

Este documento es un **índice curado** de los casos que importan, no el
inventario completo. La suite tiene más tests de los que aparecen aquí
(identidad, privacidad, contraste, catalogs, fuentes); se comprueba con:

```bash
python scripts/verificar_casos.py
```

Ese script falla si algún test nombrado aquí no existe, si un caso no está en
estado PASA, o si la cifra de la cabecera no corresponde a las filas listadas.

Estado por caso: **PASA** / **FALLA** / **NO IMPLEMENTADO**

---

## Punto 1 — Compatibilidad entidad–concepto (punto 1)

| # | Caso | Estado | Test |
|---|---|---|---|
| 1.1 | Cada unidad declara sus formas admitidas | PASA | `test_cada_unidad_declara_sus_formas` |
| 1.2 | m2 no admite m ni pza | PASA | `test_m2_no_admite_m` |
| 1.3 | pza admite m (piezas en eje) | PASA | `test_pza_admite_m_para_piezas_en_eje` |
| 1.4 | Unidad inválida es error de catálogo | PASA | `test_unidad_invalida_es_error_de_catalogo` |
| 1.5 | **REGRESIÓN luminarias**: no se cobran como m² | PASA | `test_regresion_luminarias_no_se_cobran_como_m2` |
| 1.6 | **REGRESIÓN luminarias**: importe = piezas × precio | PASA | `test_regresion_luminarias_importe_es_precio_por_pieza` |
| 1.7 | Entidad incompatible se reporta con handle | PASA | `test_entidad_incompatible_se_reporta_con_handle` |
| 1.8 | Una capa incompatible no contamina a las demás | PASA | `test_incompatibilidad_no_contamina_el_resto` |
| 1.9 | Polilínea cerrada aporta área y perímetro | PASA | `test_polilinea_cerrada_aporta_area_y_perimetro` |

## Punto 3 — Casos reales (punto 3)

### Bulge / arcos
| # | Caso | Estado | Test |
|---|---|---|---|
| 3.1 | El arco se resuelve: área 15.5339 (exacta 15.5343) | PASA | `test_bulge_resuelve_el_arco` |
| 3.2 | Una polilínea con bulge no se omite | PASA | `test_bulge_no_se_omite` |

### Polilínea abierta
| # | Caso | Estado | Test |
|---|---|---|---|
| 3.3 | Abierta da longitud, no área (14 m) | PASA | `test_polilinea_abierta_da_longitud_no_area` |
| 3.4 | Abierta no fabrica un m² | PASA | `test_abierta_no_fabrica_un_m2` |

### Bloques
| # | Caso | Estado | Test |
|---|---|---|---|
| 3.5 | Bloques se explotan y se cuentan (4 y 9 pza) | PASA | `test_bloques_se_explotan_y_se_cuentan` |
| 3.6 | **REGRESIÓN**: el INSERT no se cuenta doble | PASA | `test_insert_no_se_cuenta_doble` |
| 3.7 | Contenido del bloque aporta longitud del símbolo | PASA | `test_contenido_de_bloque_aporta_la_longitud_del_simbolo` |
| 3.8 | Bloque no se omite en silencio | PASA | `test_bloque_no_se_omite_en_silencio` |
| 3.9 | Geometría interna hereda la capa del INSERT | PASA | `test_geometria_interna_de_bloque_hereda_la_capa_del_insert` |

### Unidades del DXF
| # | Caso | Estado | Test |
|---|---|---|---|
| 3.10 | DXF en mm produce aviso | PASA | `test_dxf_en_milimetros_se_advierte` |
| 3.11 | El área en mm **no** se corrige sola | PASA | `test_area_en_mm_no_se_correge_en_silencio` |
| 3.12 | `--escala 0.001` sí corrige a m² | PASA | `test_escala_explicita_si_correge` |
| 3.13 | DXF en metros se identifica | PASA | `test_dxf_en_unidades_desconocidas_avisa` |
| 3.14 | `$INSUNITS=0` dispara aviso | PASA | `test_codigo_cero_dispara_aviso` |

### Duplicados y solapes
| # | Caso | Estado | Test |
|---|---|---|---|
| 3.15 | 3 copias idénticas = unión 24 m², con aviso de solape | PASA | `test_duplicados_se_unen_y_se_advierten` |

### HATCH con isla
| # | Caso | Estado | Test |
|---|---|---|---|
| 3.16 | Losa 10×10 con patio 4×4 = **84 m²** (no 116) | PASA | `test_hatch_con_isla_resta_el_patio` |
| 3.17 | No suma contornos | PASA | `test_hatch_con_isla_no_suma_contornos` |
| 3.18 | Polilíneas anidadas sueltas dan la unión (limitación declarada) | PASA | `test_polilineas_anidadas_dan_la_union` |

### Textos y cotas
| # | Caso | Estado | Test |
|---|---|---|---|
| 3.17 | Textos y cotas no cuentan como geometría | PASA | `test_textos_y_cotas_no_cuentan_como_geometria` |
| 3.18 | Se registran como omitidas con motivo y handle | PASA | `test_textos_y_cotas_quedan_registrados_como_omitidas` |

### Nombres de capa
| # | Caso | Estado | Test |
|---|---|---|---|
| 3.19 | Acentos, espacios dobles, guiones, minúsculas | PASA | `test_capas_con_acentos_espacios_guiones_y_mayusculas` |
| 3.20 | No hace falta duplicar variantes en el catálogo | PASA | `test_normalizacion_de_nombres_no_requiere_tocar_el_catalogo` |

## Punto 2 — Visibilidad (punto 2)

| # | Caso | Estado | Test |
|---|---|---|---|
| 2.1 | Toda omisión lleva handle y motivo | PASA | `test_todas_las_omisiones_llevan_handle_y_motivo` |
| 2.2 | El total reporta partidas excluidas | PASA | `test_el_total_reporta_partidas_excluidas` |
| 2.3 | El aviso de unidades llega al presupuesto | PASA | `test_advertencia_de_unidades_llega_al_presupuesto` |
| 2.4 | Excel muestra bloque ADVERTENCIAS | PASA | `test_excel_muestra_la_bloque_de_advertencias` |
| 2.5 | Excel muestra las líneas excluidas | PASA | `test_excel_muestra_las_lineas_excluidas` |
| 2.6 | Excel muestra entidades descartadas | PASA | `test_excel_muestra_entidades_descartadas` |
| 2.7 | Excel incluye handles de procedencia | PASA | `test_excel_incluye_handles_de_procedencia` |
| 2.8 | PDF muestra las advertencias | PASA | `test_pdf_muestra_las_advertencias` |
| 2.9 | PDF muestra subtotal, IVA y total | PASA | `test_pdf_muestra_subtotal_iva_y_total` |
| 2.10 | PDF dice cuando no hay advertencias | PASA | `test_pdf_dice_cuando_no_hay_advertencias` |

## Punto 4 — Totales (punto 4)

| # | Caso | Estado | Test |
|---|---|---|---|
| 4.1 | IVA = subtotal × 0.16 | PASA | `test_iva_es_dieciseis_por_ciento` |
| 4.2 | Total = subtotal + IVA | PASA | `test_total_es_subtotal_mas_iva` |
| 4.3 | Redondeo half-up a 2 decimales | PASA | `test_iva_usa_redondeo_a_dos_decimales` |
| 4.4 | Subtotal = suma de las líneas OK | PASA | `test_subtotal_es_la_suma_de_las_lineas_ok` |
| 4.5 | **Python = Excel = PDF al centavo** | PASA | `test_python_excel_y_pdf_coinciden` |
| 4.6 | Cada línea OK = cantidad × precio | PASA | `test_cada_linea_ok_se_calcula_como_cantidad_por_precio` |
| 4.7 | Caso manual de 3 líneas a mano | PASA | `test_caso_manual_tres_lineas_calculadas_a_mano` |
| 4.8 | Esos importes aparecen en el Excel | PASA | `test_caso_manual_los_mismos_importes_aparecen_en_el_excel` |

## Casos manuales documentados

En `test_totales.py`, `test_caso_manual_tres_lineas_calculadas_a_mano`. Precios
**de ejemplo**, calculados a mano sin usar el motor para el importe:

| Concepto | Cantidad | Rend. | Precio ejemplo | Importe a mano |
|---|---|---|---|---|
| Muro block 15 cm | 108.00 m² | 1.00 | 900.00 | **97,200.00** |
| Piso de loseta | 27.00 m² | 1.08 | 320.00 | 29.16 × 320 = **9,331.20** |
| Luminaria | 2 pza | 1.00 | 850.00 | **1,700.00** |

---

# Ruta crítica 2026-10-17 (puntos 1 a 5)

## Punto 1 — Entrada PDF vectorial (`tests/test_entradas.py`)

| # | Caso | Estado | Test |
|---|---|---|---|
| 1.1 | Plano real de CAD (4760×2160 pt) resulta rasterizado | PASA | `test_pdf_real_de_plano_resulta_escaneado` |
| 1.2 | Escaneado avisa que no se puede medir | PASA | `test_escaneado_avisa_que_no_se_puede_medir` |
| 1.3 | Escaneado devuelve cero mediciones sin explotar | PASA | `test_escaneado_devuelve_cero_mediciones_sin_explotar` |
| 1.4 | PDF vectorial se detecta como tal | PASA | `test_pdf_vectorial_generado_si_se_detecta_como_tal` |
| 1.5 | Escala 1.0 avisa que son puntos, no metros | PASA | `test_escala_uno_avisa_que_no_son_metros` |
| 1.6 | Avisa que el PDF no tiene capas | PASA | `test_pdf_avisa_que_no_tiene_capas` |
| 1.7 | Escala explícita convierte a metros (12 m² exactos) | PASA | `test_escala_explicita_convierte_a_metros` |
| 1.8 | Sin escala se conservan proporciones | PASA | `test_proporcion_se_conserva_aunque_no_haya_escala` |
| 1.9 | Agrupamiento separa por color de trazo | PASA | `test_agrupamiento_separa_por_color` |
| 1.10 | La envoltura de página se excluye | PASA | `test_agrupamiento_excluye_la_envoltura_de_pagina` |
| 1.11 | Los grupos se nombran COLOR_*, nunca como capas | PASA | `test_capas_pdf_se_llaman_por_color` |
| 1.12 | Los PDF traen procedencia | PASA | `test_manejadores_de_procedencia_presentes` |

## Punto 2 — DWG (`tests/test_entradas.py`)

| # | Caso | Estado | Test |
|---|---|---|---|
| 2.1 | Detección de ODA no lanza | PASA | `test_odafc_reporta_si_esta_o_no_disponible` |
| 2.2 | Sin ODA: error con qué instalar y dónde | PASA | `test_leer_dwg_sin_oda_da_error_claro` |
| 2.3 | Se rechaza extensión no-DWG | PASA | `test_leer_dwg_rechaza_extension_no_dwg` |
| 2.4 | Sin ODA el DWG **no** se omite en silencio | PASA | `test_sin_oda_el_dwg_no_se_omite_en_silencio` |
| 2.5 | Conversión real DWG→DXF | **NO IMPLEMENTADO** | ODA File Converter no está instalado en esta máquina |

## Punto 3 — Catálogo contra capas reales (`tests/test_catalogo_capas_reales.py`)

| # | Caso | Estado | Test |
|---|---|---|---|
| 3.1 | `NOTAS-MUROS` no se mapea a muro de block | PASA | `test_capa_de_anotacion_no_se_mapea_a_muro` |
| 3.2 | Estructura no se confunde con acabado | PASA | `test_estructura_no_se_confunde_con_acabado` |
| 3.3 | Capa organizativa por planta se excluye | PASA | `test_capa_organizativa_por_planta_se_excluye` |
| 3.4 | Planos de apoyo se excluyen | PASA | `test_planos_de_apoyo_se_excluyen` |
| 3.5 | 14 capas de despacho mapean al concepto correcto | PASA | `test_cubre_las_capas_reales_de_despacho` |
| 3.6 | Cobertura del plano real ≥ 90% (actual 94.4%) | PASA | `test_cobertura_del_plano_real_supera_el_90` |
| 3.7 | Toda capa queda clasificada | PASA | `test_todas_las_capas_medibles_del_plano_estan_auditadas` |
| 3.8 | Capa mixta puerta+ventana se reporta ambigua | PASA | `test_capa_mixta_de_puerta_y_ventana_se_reporta_ambigua` |
| 3.9 | Capa excluida aparece con su motivo | PASA | `test_capa_excluida_aparece_como_tal_en_el_presupuesto` |
| 3.10 | Capa de anotación no produce medición | PASA | `test_capa_de_anotacion_no_produce_medicion` |
| 3.11 | Se avisa sobre las capas excluidas | PASA | `test_el_presupuesto_avisa_sobre_capas_excluidas` |
| 3.12 | El muro genérico tiene menor prioridad que el específico | PASA | `test_muro_generico_es_de_prioridad_menor_que_el_especifico` |

## Punto 4 — Precios (`tests/test_precios.py`)

| # | Caso | Estado | Test |
|---|---|---|---|
| 4.1 | La plantilla sale con todos los precios en `null` | PASA | `test_la_plantilla_se_genera_con_todos_los_precios_en_null` |
| 4.2 | **REGRESIÓN**: la plantilla no filtra precios | PASA | `test_la_plantilla_no_contiene_precios_numericos` |
| 4.3 | Sin precios el subtotal es 0.00 | PASA | `test_catalogo_de_sin_precio_da_subtotal_cero` |
| 4.4 | Cada concepto sin precio queda marcado | PASA | `test_cada_concepto_sin_precio_queda_marcado` |
| 4.5 | El total se marca incompleto | PASA | `test_el_total_se_marca_incompleto` |
| 4.6 | El Excel marca TOTAL INCOMPLETO | PASA | `test_excel_marca_el_total_como_incompleto` |
| 4.7 | El PDF avisa que no se envíe al cliente | PASA | `test_pdf_avisa_que_no_se_envie_al_cliente` |
| 4.8 | Con todos los precios no queda FALTA_PRECIO | PASA | `test_con_todos_los_precios_no_quedan_lineas_sin_precio` |
| 4.9 | El total incompleto distingue su causa | PASA | `test_el_total_incompleto_tiene_causa_distinta_a_los_precios` |
| 4.10 | El total no es cero si hay precios | PASA | `test_el_total_no_es_cero_si_hay_precios` |

## Punto 5 — Interfaz web (`tests/test_web.py`)

| # | Caso | Estado | Test |
|---|---|---|---|
| 5.1 | La página inicial carga | PASA | `test_la_pagina_inicial_carga` |
| 5.2 | Rechaza formato no soportado | PASA | `test_rechaza_formato_no_soportado` |
| 5.3 | Procesa un DXF y muestra el takeoff | PASA | `test_procesa_dxf_y_muestra_takeoff_con_origen` |
| 5.4 | Muestra las advertencias del presupuesto | PASA | `test_muestra_las_advertencias_del_presupuesto` |
| 5.5 | Muestra el total con IVA | PASA | `test_muestra_el_total_con_iva` |
| 5.6 | Descarga de Excel válida | PASA | `test_descarga_excel` |
| 5.7 | Descarga de PDF válida | PASA | `test_descarga_pdf` |
| 5.8 | Sesión inexistente da 404 | PASA | `test_sesion_inexistente_da_404` |
| 5.9 | Formato de descarga inválido da 400 | PASA | `test_formato_de_descarga_invalido_da_400` |
| 5.10 | Sube un PDF vectorial y muestra grupos por color | PASA | `test_sube_pdf_vectorial_muestra_grupos_por_color` |
| 5.11 | PDF escaneado se detecta en la web | PASA | `test_pdf_escaneado_se_detecta_en_la_web` |
| 5.12 | DWG sin ODA da error claro en la web | PASA | `test_dwg_sin_oda_devuelve_error_claro` |

## Brechas de la ruta crítica

| Brecha | Estado |
|---|---|
| Conversión real DWG→DXF con ODA | **NO VERIFICADO** — ODA no está instalado aquí |
| Separar `ARQ-PUERTAS-VENTANAS` en dos conceptos | **NO IMPLEMENTADO** — una capa con dos conceptos se resuelve por prioridad y cuenta las puertas como ventanas |
| Reconstruir capas de CAD a partir del color de un PDF | **FUERA DE ALCANCE** — el PDF no las tiene; se agrupa por color como heurística |
| OCR de planos escaneados | **NO IMPLEMENTADO** y no se intenta |

## No implementado (declarado, no omitido)

| Caso | Por qué |
|---|---|
| Resolución de XREF | Las referencias externas no se resuelven. |
| Hueco en polilíneas sueltas anidadas | Dos polilíneas separadas no marcan cuál es el hueco; se da la unión. El HATCH sí lo marca y sí se resta. |
| Escalas mixtas dentro de un mismo plano | Se asume un factor global por documento. |
| Sesiones persistentes en la web | Son en memoria; pierden el resultado al reiniciar. Suficiente para MVP local. |