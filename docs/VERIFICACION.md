# Verificación en navegador real

Generado por `scripts/verificar_navegador.py`. No editar a mano.

## Consola del navegador

### Errores de JavaScript

**Sin errores de JavaScript ni excepciones sin capturar en ninguna vista ni tamaño de pantalla.**

### Respuestas HTTP anotadas por el navegador

No son fallos de la página: son los estados que las pruebas de error provocan a propósito para comprobar que la interfaz los muestra.

| Vista | Estado | Veces |
|---|---|---|
| errores-escritorio | 400 | 2 |
| errores-escritorio | 413 | 2 |
| errores-movil | 400 | 3 |
| errores-movil | 413 | 3 |
| escritorio | 400 | 1 |
| flujo | 400 | 3 |
| flujo | 413 | 3 |
| movil | 400 | 1 |

## Flujo completo

| Comprobación | Resultado |
|---|---|
| Campos de precio en la pantalla | 10 |
| Total sin precios | 0.00 MXN |
| Total con precios puestos | 498,715.29 MXN |
| Marcado incompleto sin precios | True |
| Marcado incompleto con precios | True |
| Rótulo del total incompleto | Total incompleto: 2 de 12 líneas quedaron fuera. Este importe no cubre toda la obra del plano. |
| Excel descargado y válido | True (~7.0 KB) |
| PDF descargado y válido | True (~4.0 KB) |
| El reporte no adjunta el plano | True |
| El reporte lleva la versión | True |
| El reporte solo cita el nombre del archivo | True |

## Errores en la interfaz

| Caso | Se muestra el error |
|---|---|
| DXF corrupto (escritorio) | No se pudo procesar el archivo No se pudo procesar el plano: File '<archivo>' is not a DXF |
| PDF escaneado (escritorio) | No se pudo medir nada de este archivo. Si es un PDF escaneado, no hay geometría que medir. |
| DXF corrupto (movil) | No se pudo procesar el archivo No se pudo procesar el plano: File '<archivo>' is not a DXF |
| PDF escaneado (movil) | No se pudo medir nada de este archivo. Si es un PDF escaneado, no hay geometría que medir. |
| dwg sin ODA (escritorio) | No se pudo procesar el archivo Para leer archivos DWG hace falta ODA File Converter. ODA F |
| sobre el límite (escritorio) | No se pudo procesar el archivo El archivo supera 80 MB. El límite es un supuesto, no un da |
| dwg sin ODA (movil) | No se pudo procesar el archivo Para leer archivos DWG hace falta ODA File Converter. ODA F |
| sobre el límite (movil) | No se pudo procesar el archivo El archivo supera 80 MB. El límite es un supuesto, no un da |

## Accesibilidad (axe-core)

### portada
**Sin violaciones.**
### resultados
**Sin violaciones.**

## Contraste calculado (WCAG 2.1)

Medido con la fórmula de luminancia relativa, no declarado.

| Par | Colores | Ratio | AA (4.5) | AAA (7) |
|---|---|---|---|---|
| tinta sobre fondo | #1c2430 / #ffffff | **15.62** | sí | sí |
| tenue sobre fondo | #5b6672 / #ffffff | **5.85** | sí | no |
| acento sobre fondo | #1d4ed8 / #ffffff | **6.7** | sí | no |
| aviso sobre aviso-fondo | #8a4b08 / #fdf6ec | **6.33** | sí | no |
| peligro sobre peligro-fondo | #a11a1a / #fdf2f2 | **7.15** | sí | sí |
| ok sobre ok-fondo | #14622f / #f0f7f2 | **6.85** | sí | no |
| incompleto (blanco sobre rojo) | #ffffff / #a11a1a | **7.84** | sí | sí |
| boton primario (blanco sobre acento) | #ffffff / #1d4ed8 | **6.7** | sí | no |
| tinta sobre panel | #1c2430 / #f6f7f9 | **14.57** | sí | sí |
| tenue sobre panel | #5b6672 / #f6f7f9 | **5.46** | sí | no |

## Capturas

- `capturas/01-vacio-escritorio.png`
- `capturas/01-vacio-movil.png`
- `capturas/02-takeoff-escritorio.png`
- `capturas/02-takeoff-movil.png`
- `capturas/03-advertencias-escritorio.png`
- `capturas/03-advertencias-movil.png`
- `capturas/04-error-corrupto-escritorio.png`
- `capturas/04-error-corrupto-movil.png`
- `capturas/05-error-escaneado-escritorio.png`
- `capturas/05-error-escaneado-movil.png`
- `capturas/06-precios-cargados.png`
- `capturas/07-error-dwg-sin-oda-escritorio.png`
- `capturas/07-error-dwg-sin-oda-movil.png`
- `capturas/08-error-sobre-limite-escritorio.png`
- `capturas/08-error-sobre-limite-movil.png`
- `capturas/09-total-incompleto.png`
