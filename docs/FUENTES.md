# Fuentes de los archivos de prueba

Todos los archivos de fixture de terceros, con su licencia y origen. Se usan
solo para pruebas automatizadas, nunca como producto ni dato de cliente.

| Archivo | Origen | Licencia | Uso |
|---|---|---|---|
| `tests/fixtures/pdf/harlem_meer_planta.pdf` | Wikimedia Commons, `File:Harlem Meer Restaurant Dwg -2 - 1990-08-01 - First Floor Plan (2).pdf` | **CC BY-SA 4.0**, autor MMDA-Photos | Probar que un plano real de CAD ploteado puede venir rasterizado |
| `tests/fixtures/pdf/pd_escaneado.pdf` | Wikimedia Commons, `File:Floor plan of a 5-bedroom house (IA CAT31371083).pdf`, Internet Archive CAT31371083 | **Dominio público** (obra del gobierno de EE. UU., *Division of Home Economics*) | Probar la detección de PDF escaneado |
| `tests/fixtures/pdf/vectorial_desde_dxf.pdf` | Generado por `scripts/generar_pdf_vectorial.py` desde `planos/vectorial_origen.dxf` | Ours, Dominio público de las pruebas | Probar la ruta vectorial con verdad conocida |

## Páginas fuente

- CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0
- Commons (archivo CC BY-SA): https://commons.wikimedia.org/wiki/File:Harlem_Meer_Restaurant_Dwg_-2_-_1990-08-01_-_First_Floor_Plan_(2).pdf
- Commons (archivo de dominio público): https://commons.wikimedia.org/wiki/File:Floor_plan_of_a_5-bedroom_house_(IA_CAT31371083).pdf
- Internet Archive, ítem original: https://archive.org/details/CAT31371083

## Hallazgo relevante sobre estos archivos

**Los dos PDFs reales de planos son imágenes rasterizadas.** Ninguno contiene
trazados vectoriales recuperables:

| Archivo | Objetos vectoriales | Imágenes en la página 1 |
|---|---|---|
| `harlem_meer_planta.pdf` (CC BY-SA, 4760 × 2160 pt, 1 página) | 0 | 1 |
| `pd_escaneado.pdf` (dominio público, 5 páginas) | 0 | 2 |

El conteo es **de la primera página**, que es la que el motor inspecciona para
decidir si el PDF está rasterizado. `pd_escaneado.pdf` tiene 6 imágenes en
total repartidas en sus 5 páginas; el archivo entero tampoco tiene vectores.

`vectorial_desde_dxf.pdf` sí es vectorial: 4 objetos vectoriales (rectángulos y
líneas), 0 imágenes, 1 página de 460.8 × 345.6 pt.

Estas cifras las mide `scripts/verificar_fuentes.py`, que también consulta la
API de Commons para comprobar que la licencia de cada archivo sea la que este
documento declara:

```
python scripts/verificar_fuentes.py --red
```

Esto es evidencia, no un problema del fixture: un plano entregado por una
oficina puede llegar como PDF con la geometría rasterizada aunque el original
sea CAD. El motor lo detecta y avisa en vez de medir basura
(`test_pdf_real_de_plano_resulta_escaneado`).

Para cubrir la ruta vectorial se generó un PDF cuyo contenido se conoce
exactamente: rectángulo de 8 × 6 m, tabique de 6 m y rectángulo de 4 × 3 m. El
test `test_escala_explicita_convierte_a_metros` verifica que el motor devuelve
12 m² para el rectángulo de 4 × 3 m.

## Licencias de las librerías

Se leen de los metadatos de las distribuciones instaladas, no de memoria, con
`scripts/generar_lock.py`:

| Librería | Licencia | Uso |
|---|---|---|
| `ezdxf` | MIT | Lectura y escritura de DXF |
| `shapely` | BSD-3-Clause | Geometría, unión, área |
| `pdfplumber` | MIT | Entrada PDF vectorial |
| `pdfminer.six` | MIT | Dependencia de pdfplumber |
| `openpyxl` | MIT | Exportación Excel |
| `reportlab` | BSD | Exportación PDF |
| `pypdf` | BSD-3-Clause | Verificación de PDF en pruebas |
| `fastapi` | MIT | Interfaz web |
| `uvicorn` | BSD-3-Clause | Servidor ASGI |
| `python-multipart` | Apache-2.0 | Parsing de formularios |
| `pytest` | MIT | Pruebas |
| `matplotlib` | PSF | Solo para generar el fixture vectorial |

**Dependencia transitiva copyleft:** `certifi` es MPL-2.0. Llega por `httpx`,
que a su vez entra solo por `starlette.testclient`, que se usa únicamente en
las pruebas. La aplicación en sí no importa `httpx` ni `certifi`: se
comprueba en `tests/test_privacidad.py::test_sin_imports_de_red_en_la_app`.
MPL-2.0 es copyleft de archivo, no de proyecto, y no obliga a nada aquí.

**Descartado por licencia:** PyMuPDF es AGPL o de pago comercial. Se usa
pdfplumber (MIT).

**Descartado por riesgo:** ODA File Converter es un binario externo
propietario. No se incluye ni se distribuye: se usa solo si el usuario lo
instala en su máquina. Si no está, el motor falla con un mensaje que dice qué
instalar y dónde, y nunca devuelve un resultado vacío.