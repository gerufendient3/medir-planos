# Formatos de entrada: investigación (sin implementar)

Fecha: 17 de octubre de 2026. Este documento **no implementa nada**. Solo
establish qué es viable y qué no.

## El riesgo

`ezdxf` lee DXF. No lee PDF ni escaneos. Si el plano que entrega un contratista
llega en PDF —que es el formato en que se reparten planos en buena parte de
Latinoamérica— el motor actual no tiene entrada.

Esto puede invalidar el enfoque completo o convertirlo en un producto de
servicio, no de software. **No lo sé y no puedo saberlo sin un plano real.**

## DWG: viable, con una dependencia externa

DWG es un formato binario propietario. No hay lectura nativa en Python.

Ruta: **ODA File Converter**, gratuito, de Open Design Alliance, convierte
DWG → DXF, y `ezdxf` tiene un addon oficial `odafc` que lo invoca
automáticamente.

- Documentación del addon: https://ezdxf.readthedocs.io/en/stable/addons/odafc.html
- Conversor: https://www.opendesign.com/guestfiles/oda_file_converter

Versiones soportadas por ODAFileConverter: de ACAD12 (R12) a ACAD2018 (R2018).
ACAD9 y ACAD10 **no** están soportadas.

Consecuencias honestas:
- Sí es viable para DWG, pero **el usuario debe instalar ODA File Converter**.
- ezdxf advierte explícitamente que ejecutar una aplicación externa es un
  riesgo de seguridad, y recomienda borrar el módulo si el PATH es modificable.
- En Linux, la GUI puede requerir `xvfb`.
- Multiplataforma, pero añade un paso de instalación a un producto que
  aspiremos a que sea simple.

Alternativa descartada: **LibreDWG** (GPL, sin dependencias externas). No la
evalué a fondo y ezdxf no tiene integración directa. Reversible si se necesita:
es una dependencia distinta, no un cambio de arquitectura.

## PDF vectorial: viable con reservas

Un PDF generado por CAD conserva la geometría como vectores, no como mapa de
bits. Eso significa que sí se puede medir.

Herramientas evaluadas:

| Opción | Qué da | Licencia |
|---|---|---|
| **pdfplumber** | `.lines`, `.rects`, `.curves`, `.chars` con coordenadas. `.edges` combinado. Depende de `pdfminer.six`. | MIT |
| **PyMuPDF** | Extracción de vectores y matrices de transformación. AGPL o comercial. | AGPL/comercial |
| **pypdf** | Extracción de texto. Ya se usa para verificar los PDF que generamos. No extrae geometría. | BSD |

Fuente: https://github.com/jsvine/pdfplumber

**Mi recomendación: pdfplumber.** Es MIT (el AGPL de PyMuPDF contaminaría el
proyecto y es una razón real para descartarlo en un producto comercial).

### Las reservas serias

pdfplumber **no tiene soporte de OCR**. Su README lo lista explícitamente entre
lo que no provee, y dice que funciona mejor en PDFs generados por máquina que
en escaneados.

Consecuencia directa y no negociable: **un plano escaneado o rasterizado no se
puede medir con esta ruta.** Un contratista que reciba el plano en PDF escaneado
—y en obra eso pasa— necesita o bien el DXF de origen, o bien una ruta de OCR +
vectorización que es un proyecto aparte y con tasa de error desconocida.

Si se eligiera PyMuPDF (AGPL) habría que evaluar la licencia con cuidado antes
de distribuir comercialmente.

## Alternativa no evaluada: PDF → SVG → DXF

Convertir el PDF a SVG y luego a DXF. Existe la ruta técnica pero **no la
evalué y no puedo afirmar que sea viable**. Un SVG de plano CAD pierde las capas,
que es exactamente la información que necesita nuestro mapeo capa → concepto.
Lo descarto por ahora sin evidencia, no por descarte confirmado.

## Decisión y reversibilidad

**No implemento nada de esto todavía.** La decisión depende de un dato que solo
tú tienes: **¿en qué formato te llegan los planos?**

| Si el formato es… | Entonces |
|---|---|
| DXF | El motor actual sirve. PDF es mejora, no urgencia. |
| DWG | Vía ODAFileConverter es viable. Añade instalación. |
| PDF vectorial | pdfplumber viable. Trabajo grande: reconstruir capas desde color/grosor. |
| PDF escaneado | **El enfoque no sirve.** Hay que hablar de otra cosa. |

Todo esto es reversible: la entrada se resuelve en `app/pipeline.py` en un solo
punto (`ejecutar()`). Añadir un lector más no obliga a reescribir el motor de
medición, porque `extraer()` ya recibe un objeto con `.modelspace()`.

## Lo que no sé

- Qué proporción de planos en México llega en cada formato. **No tengo fuente.**
- Si los PDF que circulan son vectoriales o escaneados. Sin fuente.
- Cuánto se pierde al reconstruir "capas" a partir de color y grosor de línea
  en un PDF. No lo he medido.