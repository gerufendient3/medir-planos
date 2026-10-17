# Caso de estudio: así mide la herramienta un plano

**Fecha:** 17 de octubre de 2026
**Reproducible:** `python scripts/generar_demo.py` genera `publico/demo.html`
con estos mismos números. Ninguna cifra de aquí está escrita a mano.

---

## 1. Por qué este caso

Un estimador va a poner su nombre en un presupuesto. Para que confíe no le
basta ver una captura bonita: necesita **poder comprobar la cuenta**. Este caso
es exactamente eso: tres partidas calculadas a mano y contrastadas con lo que la
herramienta escribió.

Los dos planos del caso están en `tests/fixtures/pdf/` y sus licencias en
`docs/FUENTES.md`.

---

## 2. El plano: `plano_realista.dxf`

Generado por `scripts/generar_plano_realista.py`. **No es un plano de obra
real**, es un plano sintético construido a propósito con lasibatallas típicas
de los planos reales:

| Característica | Detalle |
|---|---|
| Envolvente | 12 × 9 m |
| Capas con nombres inconsistentes | `MURO-BLOCK-15CM`, `Muro_Bloque_Interior`, `A-C-01` |
| Tablero nombrado con código opaco | `A-C-01` |
| Espacios dobles y acentos | `CIELO DE YESO`, `cANALización eléctrica` |
| Capa sin concepto en el catálogo | `REFORZADOS-ESTRURA` |
| Variedad de unidades | m², m, ml, pza |

Es deliberadamente hostile. Un plano que uno mismo genera ordenado no prueba
nada.

---

## 3. Las tres partidas, calculadas a mano

Precios de **ejemplo**. No son precios de mercado: no existe fuente pública
verificada de precios de obra en México. Los precios los pone el usuario.

### Partida 1 — Muro de block de 15 cm

| | |
|---|---|
| Capa | `MURO-BLOCK-15CM` |
| Entidades | 1 polilínea cerrada, handle `98` |
| Cantidad medida | 12 × 9 = **108.00 m²** |
| Rendimiento | 1.00 (sin merma declarada) |
| Precio de ejemplo | **$900.00** por m² |
| **Cálculo** | `108.00 × 1.00 × 900.00` |
| **Importe** | **$97,200.00** |
| Lo que escribió la herramienta | **$97,200.00** ✓ |

### Partida 2 — Piso de loseta

| | |
|---|---|
| Capa | `Piso-Loseta` |
| Entidades | 1 polilínea cerrada, handle `9B` |
| Cantidad medida | 6 × 4.5 = **27.00 m²** |
| Rendimiento | 1.08 (merma de corte) |
| Cantidad ajustada | `27.00 × 1.08` = **29.16 m²** |
| Precio de ejemplo | **$320.00** por m² |
| **Cálculo** | `29.16 × 320.00` |
| **Importe** | **$9,331.20** |
| Lo que escribió la herramienta | **$9,331.20** ✓ |

### Partida 3 — Luminarias

| | |
|---|---|
| Capa | `LAMPARA-PENDIENTE` |
| Entidades | 2 círculos de radio 0.15 m, handles `A2`, `A3` |
| Cantidad medida | **2 pza** |
| Precio de ejemplo | **$850.00** por pieza |
| **Cálculo** | `2 × 1.00 × 850.00` |
| **Importe** | **$1,700.00** |
| Lo que escribió la herramienta | **$1,700.00** ✓ |

### Suma de estas tres partidas

`97,200.00 + 9,331.20 + 1,700.00` = **$108,231.20**

El subtotal completo del plano es mayor porque hay más partidas; la tabla del
presupuesto las trae todas.

---

## 4. Verificación automática

Estas tres cifras no están comprobadas solo en este documento. Están fijadas en
pruebas que fallan si algo cambia:

| Qué se verifica | Prueba |
|---|---|
| Las tres cifras a mano coinciden | `test_caso_manual_tres_lineas_calculadas_a_mano` |
| Esos importes aparecen en el Excel | `test_caso_manual_los_mismos_importes_aparecen_en_el_excel` |
| Python = Excel = PDF al centavo | `test_python_excel_y_pdf_coinciden` |
| Cada línea OK = cantidad × precio | `test_cada_linea_ok_se_calcula_como_cantidad_por_precio` |
| IVA = subtotal × 0.16, total = subtotal + IVA | `test_total_es_subtotal_mas_iva` |

---

## 5. Lo que la herramienta NO pudo medir

Esta es la parte que más importa. Un presupuesto que parece completo y no lo
es es peor que no tener presupuesto.

### 5.1 Cuatro partidas quedaron fuera del total

| Partida | Por qué |
|---|---|
| Tablero de distribución (`A-C-01`) | El concepto no tiene precio cargado |
| Coladera (`Coladera`) | El concepto no tiene precio cargado |
| `REFORZADOS-ESTRURA` (m² y ml) | Ningún concepto del catálogo coincide con esa capa |
| Perímetros de `MURO-BLOCK-15CM`, `Muro_Bloque_Interior`, `PISO-LOSETA`, `Piso-Loseta`, `CIELO DE YESO` | Son longitud de una polilínea cerrada y el concepto se cotiza por m² |

El presupuesto emite **TOTAL INCOMPLETO** en rojo sobre la fila del total, en el
Excel y en el PDF, diciendo cuántas líneas quedaron fuera.

### 5.2 Por qué una incompatibilidad de unidad importa tanto

`MURO-TABIQUE` (handle `8E`) es una **línea de 6 m**. El concepto al que se
asigna, *tabique de gypsum*, se cotiza por **m²**.

Si la herramienta multiplicara `6 m × precio de m²`, produciría un importe
numérico, plausible y completamente falso. Un total con ese número no da
ningún aviso de que esté mal.

Lo que hace es rechazarlo, dejarlo fuera del total y reportarlo con su handle.

### 5.3 El bug que causó esto

Este caso reproduce un defecto real que ya está corregido y con prueba de
regresión. En la primera versión, una luminaria (círculo de radio 0.15 m) se
contabilizaba como **0.14 m² de superficie**, y el presupuesto cobraba metros
cuadrados de luminarias: un 92% menos de la partida, un número que salía
perfecto y no significaba nada.

Prueba que lo fija: `test_regresion_luminarias_no_se_cobran_como_m2`.

### 5.4 Otras cosas que no sabe hacer

- No distingue si un trazo repetido tres veces es un error del arquitecto o
  tres locales distintos.
- No separa dos conceptos que compartan capa. Si `ARQ-PUERTAS-VENTANAS` trae
  puertas y ventanas juntas, cuenta solo ventanas.
- No tiene precios. No propone ninguno.
- No ha visto un solo plano de obra real de México.

---

## 6. Fuentes

| Archivo | Qué es | Licencia |
|---|---|---|
| `planos/plano_realista.dxf` | Plano sintético hostil | Generado por el proyecto |
| `tests/fixtures/pdf/pd_escaneado.pdf` | Plano real que **no** se puede medir | Dominio público |
| `tests/fixtures/pdf/harlem_meer_planta.pdf` | Plano real de CAD, también rasterizado | CC BY-SA 4.0 |
| `tests/fixtures/pdf/vectorial_desde_dxf.pdf` | Plano vectorial de verdad conocida | Generado por el proyecto |

Detalles completos en `docs/FUENTES.md`.

---

## 7. Lo que este caso de estudio no demuestra

- Que funcione con planos de obra reales. **No lo hemos probado.**
- Que la escala de un plano se detecte sola. No se detecta: la da el usuario.
- Que los rendimientos de merma sean los correctos para cada material. Son
  editables y el usuario los ajusta.
- Que el catálogo de 21 conceptos cubra la nomenclatura de tu despacho. La
  cobertura medida sobre nomenclatura realista es del 100%, pero eso no es lo
  mismo que tu forma de nombrar.