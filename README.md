# Medir planos — takeoff y presupuesto de obra

> **Versión 0.1.0, candidata a publicación. No está validada con planos de obra
> reales.**
> Licencia MIT. No hay garantía de estabilidad ni de disponibilidad. Lee las
> [limitaciones](#limitaciones--léelas-antes-de-confiar-en-un-número) antes de
> usar un número de esta herramienta en algo que importe.

Herramienta **libre, gratuita y sin cuentas** para medir planos y generar
presupuestos de obra en pesos mexicanos. Cada cifra del presupuesto muestra el
**handle** de la entidad del plano que la produjo, para que puedas comprobarla
hasta el original.

> **No es un software de certificación ni sustituye el criterio de un estimador.**
> Úsala para calcular y para revisar; la decisión de qué cotizar y a qué precio
> es tuya.

---

## Limitaciones — léelas antes de confiar en un número

| Limitación | Detalle |
|---|---|
| **PDF escaneado no se mide** | Si el plano llega rasterizado no hay geometría. La app lo detecta y avisa; no intenta medir. |
| **DWG requiere ODA File Converter** | Hay que instalarlo aparte. Sin él, la app dice exactamente qué falta y dónde está. La conversión **no está verificada**: ODA no se pudo instalar en el entorno de desarrollo. |
| **Un PDF no tiene capas** | Se agrupa por color de trazo. Es una heurística, no una reconstrucción de CAD. |
| **Un PDF no guarda la escala** | Tienes que indicar cuántos puntos del PDF equivalen a un metro. Con 1.0 salen puntos, no metros, y la app lo dice. |
| **Precios aparte** | No hay precios incluidos ni estimados. Los pones tú. Sin ellos el total queda marcado como incompleto. |
| **Un trazo repetido** | Tres copias idénticas de un rectángulo se miden como una superficie, no tres. Se avisa. |
| **Dos conceptos en una capa** | Si tu capa de puertas y ventanas está junta, solo se cuenta una. Se reporta como ambigua. |
| **Sin validación en obra real** | **No se ha procesado ningún plano de obra real.** Todo lo verificado usa planos sintéticos y dos planos reales de archivo público. |

---

## Requisitos

- **Python 3.12 o superior.** Verificado en **3.12.10** y **3.15.0**.
- Sin base de datos, sin Redis, sin servicios externos.
- Opcional: [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)
  para leer DWG. No se incluye ni se distribuye.

## Poner en marcha

Estos comandos se ejecutaron de verdad, en Windows, en un directorio limpio.
`PYTHONPATH` es necesario porque el proyecto no se instala como paquete.

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "."
python -m uvicorn app.web:app --host 127.0.0.1 --port 8000
```

Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH="."
python -m uvicorn app.web:app --host 127.0.0.1 --port 8000
```

Abre `http://127.0.0.1:8000`.

## Probar desde cero

```bash
pip install -r requirements.txt
python -m pytest tests -q                  # toda la suite
python scripts/comprobar_temporal.py       # no deja basura en TEMP
python scripts/auditar_catalogo.py         # coherencia de los catálogos
python scripts/verificar_fuentes.py        # docs/FUENTES.md vs. los archivos
```

Salida esperada: **197 pruebas en verde**. Si baja, algo se rompió; la suite no
es decorativa.

Los generadores de planos de prueba y de fixtures solo hacen falta si quieres
reconstruirlos:

```bash
python scripts/generar_planos.py          # planos de prueba
python scripts/generar_casos.py           # casos limite
python scripts/generar_pdf_vectorial.py   # PDF vectorial con verdad conocida
python scripts/generar_demo.py            # demo pública
python scripts/generar_publico.py         # landing y kit
python scripts/auditar_capas.py           # qué capas cubre el catálogo
```

### Verificación en navegador

```bash
pip install playwright
python -m playwright install chromium
python scripts/verificar_navegador.py
```

Abre la app en Chromium a 1280 px y 390 px, sube un plano, edita precios,
descarga Excel y PDF, provoca los cuatro errores y corre axe-core. Deja las
capturas en `docs/capturas/` y el resultado en `docs/VERIFICACION.md`.

---

## Cómo se usa

1. **Carga un plano** (DXF, PDF vectorial o DWG).
2. **Revisa el takeoff.** Cada cantidad trae los handles de origen.
3. **Lee las advertencias.** Si algo no se pudo medir, aparece por qué.
4. **Pon tus precios** en la misma pantalla.
5. **Descarga** el Excel o el PDF.

El total queda marcado como **INCOMPLETO** en rojo mientras falte alguna partida
por precio, por unidad incompatible o por capa sin concepto.

### Desde la terminal

```bash
python -m app.pipeline planos/plano_realista.dxf \
    --catalogo catalogo/mi_precios.json --salida salida/
```

Opciones: `--catalogo`, `--escala`, `--iva`, `--pt-por-metro` (solo PDF).

---

## Precios

`catalogo/conceptos.json` viene **sin precios**, a propósito. Un precio
inventado en un presupuesto es un número que le mandas a un cliente.

```bash
python scripts/generar_plantilla_precios.py   # genera catalogo/mi_precios.json
```

Edita `precio_unitario` en cada concepto y usa esa plantilla.

`catalogo/demo_precios.json` tiene precios **de ejemplo** para probar el
formato. **No son precios de mercado** y no deben usarse con clientes.

---

## Privacidad

Cada promesa de esta lista tiene una prueba que la comprueba. Si alguien
cambia el código y rompe una, la suite falla.

| Lo que dice | Cómo se comprueba |
|---|---|
| Se procesa **en memoria**, no se escribe a disco | `test_el_archivo_subido_no_se_conserva`, `test_la_unica_escritura_es_el_temporal_del_archivo_subido` |
| Si algo falla, el archivo temporal se borra igual | `test_el_temporal_se_borra_si_falla` |
| Los resultados solo viven en memoria | `test_la_sesion_no_guarda_el_archivo_original` |
| Sin cuentas ni base de datos | `test_no_hay_persistencia_de_sesiones` |
| Nada sale a otros servidores | `test_sin_imports_de_red_en_la_app`, `test_sin_imports_de_red_en_la_interfaz` |
| Sin analítica ni scripts de terceros | `test_no_hay_analitica_ni_scripts_de_terceros` |
| Nada del plano se escribe en los logs | `test_no_hay_logs_del_contenido_del_plano` |
| El archivo subido se cierra aunque la salida sea un error | `test_el_subir_cierra_el_archivo_en_todas_las_salidas`, `test_el_subir_usa_el_finally_para_cerrar` |
| No queda nada en TEMP | `python scripts/comprobar_temporal.py` |

**Si la app está publicada en un servidor compartido**, la interfaz lo advierte
antes de subir nada y dice que un plano confidencial no debe subirse ahí. Para
eso está la opción local: con `uvicorn` en tu máquina, el archivo nunca sale de
tu equipo.

---

## Reportar un problema

Cada pantalla de trabajo tiene **«¿Algo salió mal?»**. Genera un texto con los
datos técnicos de esa corrida y lo copia al portapapeles. **No envía nada a
ningún servidor y no adjunta el plano.**

El botón abre una incidencia en <https://github.com/LuisF/medir-planos/issues/new>,
que es el repositorio de `app/identidad.py`. La URL no está escrita a mano en
ninguna pantalla: sale de ahí, para que no puedan diferir.

---

## Publicación

### Opción A — Sitio estático (GitHub Pages, gratis) — **la predeterminada**

Publica la demo, el caso de estudio y el kit. **No incluye la app**: eso
necesita ejecutar Python.

El workflow `.github/workflows/pages.yml` hace todo solo en cada push a
`main`:

```bash
python scripts/generar_publico.py   # landing y kit
python scripts/generar_demo.py      # demo
```

Pasos una sola vez en el repositorio:

1. *Settings → Pages → Source* = **GitHub Actions**.
2. Confirmar que `ci.yml` corre en verde.
3. Abrir `https://USUARIO.github.io/REPO/`.

**Sin verificar.** No se ha ejecutado contra un repositorio real: no hay
ninguno. El YAML es válido y los comandos que corre sí se ejecutaron localmente,
pero el despliegue en sí está sin probar.

### Opción B — La app completa en un servicio gratuito

**No está configurada.** Se documenta para decidir, no para dar por hecho.

| Servicio | Plan gratuito | Límite real |
|---|---|---|
| **Render** | Web service | Se duerme tras 15 min sin uso; el arranque en frío hace lento el primer plano. |
| **Fly.io** | Máquinas pequeñas con crédito mensual | Se puede suspender; el límite mensual se agota. |
| **Railway** | Crédito de prueba | Se apaga sin uso y el crédito se acaba. |

Lo que hay que saber antes de elegir:

- **Es una instancia compartida.** Quien tenga la URL la puede usar. La
  interfaz lo advierte antes de subir un archivo.
- **El servidor se duerme o se suspende.** No hay promesa de disponibilidad.
- **El límite de la plataforma manda.** 80 MB es el valor del proyecto; si la
  plataforma acepta menos, hay que bajar `TAMANO_MAX_MB`.
- **El plano pasa por una máquina ajena** mientras se procesa, aunque no se
  guarde. Para planos confidenciales, la opción local.

#### Sobre el límite de 80 MB

**80 MB es un supuesto, no un dato.** No hay fuente para ese número: se eligió
por ser cómodo para planos típicos de obra. Se aplica en el servidor, se
declara en el formulario y se declara como supuesto en la interfaz. Se cambia
en `TAMANO_MAX_MB`, en `app/identidad.py`.

---

## Lo que no está verificado

En una sola línea, para que nadie lo lea en otro orden:

> **No está validado con planos de obra reales.**

Además:

- La conversión **DWG → DXF con ODA nunca se ejecutó**. ODA File Converter no se
  pudo instalar en el entorno de desarrollo. El camino da un error claro, no un
  resultado vacío, pero el resultado correcto nunca se vio.
- Los dos planos reales usados son de archivo público y **los dos llegan
  rasterizados**, así que no ejercitan la ruta vectorial. Esa ruta se prueba con
  un PDF generado cuyo contenido se conoce exactamente.
- **La escala de un PDF la pone el usuario.** El motor no la adivina.
- **Los precios de `catalogo/demo_precios.json` son inventados** para que la
  demo se vea completa. No son precios de mercado.

## Estructura

```
app/
  identidad.py      nombre, versión, licencia y avisos en un solo lugar
  entidades.py      lectura DXF, bloques, hatches, handles
  medidor.py        agrega por capa, respeta la unidad del concepto
  pdf_entrada.py    PDF vectorial con pdfplumber
  presupuesto.py    catálogo, conceptos, IVA, estados
  exportar.py       Excel y PDF
  pipeline.py       DXF/DWG/PDF → takeoff → presupuesto
  web.py            interfaz de una pantalla
catalogo/           conceptos (sin precios), plantilla y precios de demo
docs/               decisiones, casos, formatos, fuentes, verificación
publico/            demo, landing y kit (sitio estático)
scripts/            generadores, auditorías y verificación
tests/              197 pruebas
```

### Lo que se puede cambiar en un solo sitio

`app/identidad.py` concentrationombre, versión, licencia, URL del
repositorio, avisos fijos y el límite de tamaño. La interfaz, el pie de
página, el botón de reporte y este README leen de ahí. Cambia ahí el nombre,
la versión, la licencia, la URL del repositorio, los avisos fijos o el límite
de tamaño, y el resto se entera solo.

---

## Documentación

- `docs/DECISIONES.md` — qué se eligió y qué se descartó
- `docs/CASOS.md` — lista de pruebas con su estado
- `docs/CASO_ESTUDIO.md` — tres partidas calculadas a mano
- `docs/FORMATOS_ENTRADA.md` — investigación sobre PDF y DWG
- `docs/FUENTES.md` — fuentes y licencias de los planos de ejemplo
- `docs/VERIFICACION.md` — capturas, consola, accesibilidad y contraste

---

## Licencia y créditos

**MIT.** Titular **LuisF**, 2026. Texto completo en `LICENSE`. La interfaz, el
pie de página y este README salen de `LICENCIA` en `app/identidad.py`, así que
no pueden divergir.

### Créditos de las librerías

Las licencias se leen de los metadatos de los paquetes instalados, no de
memoria (`python scripts/generar_lock.py` las vuelve a imprimir).

| Librería | Versión | Licencia | Para qué |
|---|---|---|---|
| ezdxf | 1.4.5 | MIT | Lectura y escritura de DXF |
| shapely | 2.2.0 | BSD-3-Clause | Geometría, unión, área |
| pdfplumber | 0.11.10 | MIT | Entrada PDF vectorial |
| pdfminer.six | 20260107 | MIT | Dependencia de pdfplumber |
| openpyxl | 3.1.5 | MIT | Exportación a Excel |
| reportlab | 5.0.1 | BSD | Exportación a PDF |
| pypdf | 6.21.1 | BSD-3-Clause | Verificación de PDF en pruebas |
| fastapi | 0.143.3 | MIT | Interfaz web |
| uvicorn | 0.54.0 | BSD-3-Clause | Servidor ASGI |
| python-multipart | 0.0.32 | Apache-2.0 | Parsing de formularios |
| pytest | 9.1.1 | MIT | Pruebas |
| matplotlib | 3.11.2 | PSF | Solo para generar fixtures |

Todas las directas son permisivas. La única copyleft es **`certifi` (MPL-2.0)**,
que llega por `httpx`, que a su vez entra solo por `starlette.testclient`, usado
únicamente en las pruebas: la aplicación no importa ninguno de los dos
(`tests/test_privacidad.py::test_sin_imports_de_red_en_la_app`). MPL-2.0 es
copyleft de archivo, no de proyecto.

Los planos de ejemplo tienen licencia propia: uno es **dominio público** (obra
del gobierno de EE. UU.) y otro es **CC BY-SA 4.0**. Fuentes completas en
`docs/FUENTES.md`.

---

## Cómo subirlo a GitHub

El repositorio local está listo. Lo que falta es crearlo en GitHub y conectar
los dos.

### 1. Los marcadores ya están resueltos

| Marcador | Estado |
|---|---|
| `REPO_URL` | `https://github.com/LuisF/medir-planos`, con `REPO_CONFIRMADO = True` |
| `LICENCIA_CONFIRMADA` | `True`. MIT, titular LuisF, 2026 |

`python -m pytest tests -q` lo comprueba: si se cambia uno sin el otro, la
suite falla.

### 2. Crear el repositorio en GitHub

En <https://github.com/new>, **sin** marcar "Initialize with a README": el
repositorio local ya tiene todo. Usa el nombre y usuario del encabezado de
este README.

Sobre la visibilidad: si lo creas como **privado**, después puedes cambiarlo
a público en *Settings → Danger Zone → Change visibility*. **Al revés no se
puede sin borrarlo**, así que crear en privado es la opción reversible.

### 3. Conectar y subir

```bash
git remote add origin https://github.com/LuisF/medir-planos.git
git push -u origin main
```

Eso es todo. Si `git push` pide credenciales: usa un **token personal**
(*Settings → Developer settings → Personal access tokens*), no tu contraseña
de GitHub.

### 4. Después de subir

1. **Activar GitHub Pages** (opción A): *Settings → Pages → Source* =
   **GitHub Actions**. El workflow `.github/workflows/pages.yml` publica la
   demo, la landing y el kit. Está **sin verificar en ejecución real**: nadie
   lo ha corrido contra un repositorio de verdad.
2. **Activar las incidencias**: *Settings → General → Features → Issues*.
   Las plantillas de `.github/ISSUE_TEMPLATE/` se usan en cuanto se activen.

### 5. Si prefieres empezar en privado

```bash
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
# luego: Settings → Danger Zone → Change visibility → Change to public
```

Recomendación: **empieza en privado**. En el repositorio hay planos de
ejemplo y capturas de pantalla; conviene verlos una vez en la interfaz de
GitHub antes de que los vea el mundo.