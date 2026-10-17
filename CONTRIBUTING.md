# Cómo contribuir

Gracias por mirar esto. Antes de nada, el estado real del proyecto:

> **Prototipo en revisión (0.1.0). No está validado con planos de obra reales.**
> La licencia MIT es una propuesta sin confirmar.

Si vas a usar un número de esta herramienta para cotizar a un cliente, lee
antes la sección de [limitaciones del README](README.md#limitaciones--léelas-antes-de-confiar-en-un-número).

## Qué hace esta herramienta

Mide geometría de planos DXF y de PDF vectorial, y arma un presupuesto en
pesos con el detalle de qué entidad del plano produjo cada cantidad.

## Qué no hace

- **No lee planos escaneados.** Si el PDF viene rasterizado, lo detecta y lo
  dice. No hay OCR.
- **No lee DWG sin instalar** [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)
  aparte. Y esa conversión **nunca se ha ejecutado en pruebas reales**.
- **No adivina la escala.** Para un PDF, tú dices cuántos puntos equivalen a
  un metro.
- **No trae precios.** No existe fuente pública verificada de precios de obra
  en México. Los pones tú; lo que quede vacío se marca como total incompleto.

## Correr las pruebas

Hace falta Python 3.12 o superior. Verificado en 3.12 y 3.15.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
export PYTHONPATH="."            # Windows: $env:PYTHONPATH = "."
python -m pytest tests -q
```

Deben pasar **194 pruebas**. Si pasa menos o más, algo se rompió.

Los cuatro verificadores que la suite usa por dentro, por si quieres
correrlos sueltos:

```bash
python scripts/auditar_catalogo.py    # coherencia de los catálogos
python scripts/verificar_fuentes.py   # docs/FUENTES.md contra los archivos
python scripts/verificar_casos.py     # docs/CASOS.md contra la suite
python scripts/comprobar_temporal.py  # que no queden archivos en TEMP
```

Para la verificación en navegador hace falta Chromium:

```bash
pip install playwright
python -m playwright install chromium
python scripts/verificar_navegador.py
```

## Qué **no** enviar

Esto es lo más importante de esta página.

- **Ningún plano de cliente.** Ni aunque sea "un ejemplo rápido". Pueden ser
  confidenciales y casi nunca se pueden borrar de verdad de un historial de
  Git. El `.gitignore` ya bloquea `*.dxf`, `*.dwg` y `*.pdf` fuera de las
  carpetas del proyecto, pero no es una red de seguridad: **mira `git status`
  antes de confirmar.**
- **Ningún precio real.** `catalogo/conceptos.json` va sin precios a
  propósito. No pongas los tuyos ahí.
- **Ningún archivo generado**: nada de `salida/`, `.xlsx`, `.pdf` sueltos,
  `*.log`, `.bak`.
- **Ningún `.env`, clave ni token.** El proyecto no los necesita.

Si ya commiteaste algo que no debía, no basta con borrarlo del último commit.
Hay que reescribir el historial (`git filter-repo`) o, si aún no se ha
subido, empezar de cero.

## Cómo reportar un problema

Usa el enlace **New issue** y elige la plantilla **"Un plano no se midió"**.

**No adjuntes el plano.** No hace falta y no se debe. La plantilla pide solo
lo que hace falta para reproducir:

- **formato** del archivo (DXF, PDF, DWG),
- **software de origen** con el que se hizo (AutoCAD, Revit, Civil 3D, escaneo…),
- **qué capas** tiene el plano y cómo se llaman,
- **escala**: para DXF, las unidades del archivo; para PDF, cuántos puntos
  equivalen a un metro.

Si el plano es confidencial, puedes describir la estructura sin el archivo. Un
nombre de capa y una captura recortada bastan la mayoría de las veces.

Si prefieres no abrir una incidencia pública, la app tiene un botón **"¿Algo
salió mal?"** que genera un reporte con los datos técnicos de la corrida. Se
copia al portapapeles y **no envía nada a ningún servidor**; el texto no lleva
el plano adjunto, solo su nombre y las cifras que se midieron.

## Cómo va a quedar la pull request

1. Un tema por PR, o el trabajo se vuelve imposible de revisar.
2. Si cambia el motor, **añade o ajusta la prueba** que lo demuestra. Aquí no
   se acepta "esto lo probé yo a mano" como evidencia.
3. Si cambias un texto del README, `docs/` o del sitio público, corre los
   verificadores: hay pruebas que fallan si la documentación se queda vieja.
4. **No declares que el proyecto está validado con planos reales** mientras siga
   sin estarlo. Es la restricción que más se cuela por descuido.

## Si quieres cambiar algo grande

Antes de escribir código, abre una incidencia y describe el problema. Es más
barato que descubrir a medias que el enfoque no era el que buscabas.

El motor de medición y el catálogo son el corazón del proyecto. Si tu cambio
altera cómo se mide un área, un longitud o un conteo, o cómo se decide si una
línea entra al total, trátalo como cambio de comportamiento: necesita prueba
de regresión y una nota en `docs/DECISIONES.md`.