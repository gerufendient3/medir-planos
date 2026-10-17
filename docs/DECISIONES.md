# Registro de decisiones

Fecha: 17 de octubre de 2026. Cada decisión dice qué se eligió, por qué, y qué
se descartó.

---

## 1. Medir por entidad, no agregar y luego validar

**Elegido:** `app/entidades.py` convierte cada entidad DXF en una
`EntidadMedida` con handle, tipo, capa y sus contribuciones (área, longitud,
piezas). `app/medidor.py` valida la compatibilidad **antes** de agregar.

**Por qué:** el diseño anterior agregaba por capa y decidía después, que es
exactamente donde el bug de luminarias se coló: el `0.14 m²` ya estaba dentro de
la suma cuando se intentaba recuperar. Además, sin handle no hay forma de que un
estimador rastro una cifra hasta el plano.

**Descartado:** validar la compatibilidad post-agregación (el diseño previo). No
puede recuperar una cantidad ya contaminada.

---

## 2. La compatibilidad es tabla explícita por unidad

**Elegido:** `FORMAS_ACEPTADAS` en `app/presupuesto.py` y `COMPATIBLE` en
`app/medidor.py`:

| Unidad | Formas admitidas |
|---|---|
| m2 | m2 |
| m | m |
| ml | ml, m |
| pza | pza, m |

**Por qué:** hace la regla auditable. Se puede leer y discutir. `pza` acepta `m`
porque un contacto se cuenta por metro de muro; `ml` acepta `m` porque un
rodapié en un trazo recto es metro lineal igual que en una polilínea.

**Descartado:** deducir la compatibilidad del nombre de la unidad. Era implícito
y por eso falló.

---

## 3. Una entidad puede aportar más de una forma

**Elegido:** `EntidadMedida.contribuciones()` devuelve una lista. Una polilínea
cerrada aporta m2 **y** ml.

**Por qué:** al principio devolvía solo una unidad y el perímetro se perdía. Un
concepto `ml` (rodapié, cornisa,Development) habría reportado cero en silencio.
Lo detecté al revisar el caso bulge.

**Descartado:** elegir una "unidad dominante" por entidad. information loss.

---

## 4. El bulge se resuelve con `ezdxf.path.make_path`

**Elegido:** `make_path(entity).flattening(0.001)`.

**Por qué:** `get_points()` de una LWPOLYLINE **ignora el bulge**: devuelve solo
los vértices y pierde el arco. Eso da un perímetro y un área falsos, que es peor
que no medir.

El aplanado a 1 mm introduce un error del 0.003% en el caso bulge verificado
(15.5339 medido contra 15.5343 exacto).

**Descartado:** `get_points()` (pérdida silenciosa del arco). Descartado también
`ezdxf.path.vertices_to_polyline_2d`, que **no existe** en ezdxf 1.4.5 — lo
implementé mal la primera vez y omisió todas las polilíneas cerradas.

---

## 5. El INSERT se cuenta una vez

**Elegido:** `extraer()` cuenta el INSERT como pieza. `extraer_bloques()` mide
**solo el contenido** del bloque, no el INSERT otra vez.

**Por qué:** encontré que las luminarias daban 6 pza en vez de 4. El INSERT se
contaba como pieza y luego volvía a contarse al explotar. En un plano de
instalaciones con 200 luminarias eso es +50% en la partida.

**Descartado:** `virtual_entities()` sobre el propio INSERT contado como pieza.

---

## 6. El texto se aparta desde el principio

**Elegido:** `NO_GEOMETRICO = {TEXT, MTEXT, LEADER, DIMENSION, TOLERANCE}` se
rechaza antes de medir, pero **se registra** en `entidades_omitidas` con su
handle y su motivo.

**Por qué:** un plano real tiene rótulos y cotas dentro de la capa de muros.
Ignorarlos en silencio hace imposible saber si faltó algo o si era anotación.

**Descartado:** ignorarlos sin registro.

---

## 7. Nada se omite en silencio, en consola ni en el entregable

**Elegido:** las incompatibilidades y omisiones van al Excel (bloque propio con
handle y tipo), al PDF (sección ADVERTENCIAS) y a la consola. El presupuesto
emite `TOTAL PARCIAL` cuando hay líneas excluidas.

**Por qué:** un total que no explica qué le falta es peor que no entregar total.
Un estimador que pone su nombre necesita saber si el número cubre todo.

**Descartado:** advertencias solo en consola.

---

## 8. El IVA vive en el presupuesto, no en el exportador

**Elegido:** `Presupuesto` lleva `subtotal`, `iva` y `total`, calculados una vez
con redondeo half-up a dos decimales.

**Por qué:** si el IVA se calculara en cada exportador, Excel y PDF podrían
divergir. Se centraliza y se prueba que los tres coinciden al centavo.

**Descartado:** calcular IVA en el Excel.

---

## 9. La procedencia se conserva hasta el entregable

**Elegido:** cada `Linea` guarda `handles` y `n_entidades`, y el Excel incluye
una columna **Handles**.

**Por qué:** el requisito es que un estimador pueda comprobar cada cifra hasta
la entidad original del plano. Sin la columna de handles eso no es posible.

**Descartado:** solo guardar el agregado.

---

## 10. Los precios viven fuera del código

**Elegido:** `catalogo/conceptos.json` con `precio_unitario: null` por defecto.
El motor marca `FALTA_PRECIO` y **excluye la línea del subtotal**.

**Por qué:** no hay fuente de precios de obra en México. Un precio inventado en
un presupuesto es un número que un contratista manda a su cliente. Es peor que
una línea faltante y señalada.

`catalogo/demo_precios.json` tiene precios **de ejemplo** para probar el flujo.
No son precios de mercado y no deben usarse con clientes.

**Descartado:** precios por defecto "razonables". Inventa precisión que no existe.

---

## 11. Las unidades del DXF se reportan, no se corrigen

**Elegido:** si `$INSUNITS=4` (milímetros), el motor **avisa** y deja la
escala en 1.0 salvo que se pase `--escala`.

**Por qué:** convertir automáticamente requiere adivinar la intención. Un plano
en mm con geometría de 4000×3000 da 12,000,000 m² si se interpreta mal: el
factor de error es de un millón. Prefiero un número obviamente absurdamente
grande con una advertencia que un número plausible y falso.

**Descartado:** convertir automáticamente según `$INSUNITS`.

---

## 12. Las superficies se unen; las longitudes se suman

**Elegido:** para `m2` el motor calcula la **unión geométrica** con shapely, no
la suma de áreas. Para `m`, `ml` y `pza` sí suma.

**Por qué:** lo descubrí verificando un caso que ya sabía mal. Una losa de
10×10 con un patio de 4×4 daba **116 m²** (100 + 16) cuando el área correcta es
**84**. Sumar contornos produce un número falso y plausible, que es lo peor.

Tres copias idénticas de un rectangulo de 6×4 dan 24 m², no 72: son el mismo
piso tres veces, no tres pisos.

Las longitudes sí se suman porque dos tuberías paralelas sí son 2 metros lineales
de tubo, aunque sus trazos no se unan.

Cada unión que difiere de la suma se registra en `solapes` con la diferencia, el
número de entidades y los handles.

**Descartado:** sumar sin más (producía 116 m²). Descartado también usar la
unión para longitudes (sumar 2 tubos paralelos como 1 es incorrecto).

**Limitación declarada:** con **dos polilíneas sueltas** anidadas el motor no
puede saber si la de dentro es un hueco o un trazo, y da la unión (100 m²).
Con un **HATCH** la isla sí se resta (84 m²) porque DXF marca el bit `external`.
Ver `test_polilineas_anidadas_dan_la_union`.

---

## 13. PDF: pdfplumber (MIT), no PyMuPDF (AGPL)

**Elegido:** `pdfplumber` en `app/pdf_entrada.py`.

**Por qué:** PyMuPDF es AGPL o comercial. Un AGPL en un producto comercial
comercial es una obligación de licencia, no un detalle. pdfplumber es MIT y da
lo necesario: `.lines`, `.rects`, `.curves` con coordenadas.

**Consecuencias asumidas y documentadas:**

- **PDF no tiene capas.** Se agrupa por color de TRAZO y los grupos se llaman
  `COLOR_<r>_<g>_<b>`. Se usa `stroking_color` y no `non_stroking_color`
  porque en un plano ploteado el relleno siempre vale 1.0 y el trazo es lo que
  codifica la capa. Aun así es una heurística y el motor lo avisa.
- **PDF no trae escala.** Se exige `pt_por_metro`. Con 1.0 devuelve puntos y
  avisa. Convertir a la ligera significa inventar un factor.
- **PDF escaneado no se mide.** Si la página es imagen, se devuelve vacío con
  aviso. No hay OCR y no se intenta.

**Descartado:** PyMuPDF (AGPL), OCR (pdfplumber no lo trae y reconstruir
geometría desde píxeles con error desconocido es peor que no medir).

## 14. DWG: ODA File Converter como paso opcional

**Elegido:** `app.entidades.leer_dwg()` usa el addon `odafc` de ezdxf. Si ODA
no está instalado, lanza `OdaNoDisponible` con el mensaje completo: qué es,
dónde se descarga, cómo se configura y que la alternativa es abrir el DXF.

**Por qué:** DWG es binario propietario, no hay lectura nativa. ODAFileConverter
es la vía estándar y ezdxf la soporta oficialmente.

**Por qué falla en vez de degradar:** un DWG que se lee como "cero
mediciones" es el peor resultado posible: el usuario creería que el plano no
tenía muros. `test_sin_oda_el_dwg_no_se_omite_en_silencio` fija ese
comportamiento.

**Pendiente:** la conversión real no está verificada porque ODA no está
instalado en esta máquina. Declarado, no comprobado.

## 15. El catálogo excluye capas, no solo mapea

**Elegido:** `capas_no_medibles` en `_meta`, con patrón y motivo. Antes de
buscar concepto, `buscar_por_capa` consulta las exclusiones.

**Por qué:** la auditoría con nomenclatura real dio 12 de 20 capas sin mapear.
Al aflojar patrones para cubrirlas apareció el riesgo contrario: `NOTAS-MUROS`
contiene "MUROS" y se habría mapeado a muro de block de 15 cm. Eso es un
falso positivo que cobra metros cuadrados de una capa de texto.

La lista de exclusión separa tres cosas que antes se mezclaban en "sin mapear":
- **brecha real**: falta un concepto (p.ej. porcelanato)
- **exclusión deliberada**: la capa no es un concepto de acabado (columnas,
  notas, capas por planta)

Solo la primera es una brecha. Fijar esa distinción bajó las brechas reales de
12 a 1 sin tapar nada.

**Descartado:** solo ampliar patrones (creaba falsos positivos).

## 16. `MURO_GENERICO` de baja prioridad

**Elegido:** concepto de reserva con prioridad 20, patrón `MURO|MUR`.

**Por qué:** `A-ESTRUCT-MUROS` y `A-PLANTA-MUROS-PT` son muros reales que no
dicen material. Mapearlos a "muro de block" sería inventar. Mapearlos a
"muero por definir" es honesto y el usuario lo corrige.

La prioridad 20 garantiza que cualquier patrón específico (block, tabique)
gane siempre. `test_muro_generico_es_de_prioridad_menor_que_el_especifico`
fija que `MUROS` cae en el genérico y `MURO-BLOCK-15CM` en el específico.

## 17. El total incompleto se marca en la fila del total

**Elegido:** `Presupuesto.total_incompleto` y una marca en rojo en la misma
fila del total, en Excel y en PDF.

**Por qué:** un total parcial en una hoja de cálculo es indistinguible de uno
completo a menos que se mire la letra chiquita. El estimador lo va a mandar al
cliente.

`total_incompleto` es más amplio que `completo`: cubre falta de precio,
unidad incompatible, capa sin concepto y capa excluida. Son causas distintas
y cada una tiene su aviso.

**Descartado:** solo poner las advertencias en una sección aparte.