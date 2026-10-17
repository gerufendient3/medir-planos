# Ideas futuras — ninguna implementada

Esta es **solo una lista**. Nada de lo que está aquí está hecho, comprometido
ni previsto para ninguna versión. La versión 0.1.0 está cerrada y documentada
en `CIERRE.md`.

Si algo de aquí te sirve, hace falta una **solicitud nueva** con su alcance,
sus pruebas y su propio documento de cierre. Nada se arrastra de este archivo
al código.

---

## Antes de cualquiera de estas

Tres cosas seguirían faltando aunque se hiciera todo lo de abajo:

1. **Un plano de obra real procesado.** Es lo que más desmarca el riesgo. Sin
   eso, cualquier función nueva se añade sobre un motor que nunca ha visto
   trabajo real.
2. **La conversión DWG ejecutada de verdad**, con ODA instalado.
3. **Las decisiones de publicación cerradas**: licencia, repositorio,
   visibilidad.

---

## Medición

- **Escala automática en PDF.** Ahora la indica el usuario y nada la comprueba.
  Es la limitación que más molesta en la práctica. También es difícil: exige
  reconocer una cota conocida o un símbolo de escala en el dibujo.
- **OCR, o vectorizar antes de medir.** Muchos planos llegan rasterizados y hoy
  solo producen un aviso. Convertirlos a vectores sería el mayor avance
  posible, y también el más caro.
- **Unir entidades que se tocan.** Hoy dos polilíneas que comparten un borde
  cuentan el solape de más o de menos según el caso.
- **Arreglos de inserción de bloques.** Los `INSERT` con parámetros de
  arreglo son habituales en AutoCAD y no se tratan.

## Catálogo y presupuesto

- **Precios por región y por año, con la fuente declarada.** Hoy no hay ninguno
  y no se inventa.
- **Conceptos compuestos**, con su propio desglose: un concepto de "piso
  terminado" que separe acabado, base y umbral de desperdicio.
- **Descuentos e indirectos como líneas explícitas**, no como un multiplicador
  oculto en el total.
- **Redondeo de la cantidad a la unidad de compra** (medio milímetro, milímetro).

## Interfaz

- **Comparar dos corridas** del mismo plano, para ver qué cambió.
- **Editar una capa desde la interfaz**, sin tocar el DXF.
- **Vista previa del plano** con las cantidades superpuestas.

## Formatos

- **Shapefile y GeoJSON** como salida.
- **Importar precios desde Excel**, que es donde muchos los tienen.

---

## Lo que deliberadamente no se va a hacer

Se listan para que quede escrito que la ausencia es una decisión y no un
olvido:

- **Un servicio en la nube con cuentas y almacenamiento.** Rompe la promesa de
  privacidad del proyecto.
- **Un motor de precios propio.** No hay fuente pública verificada. Preferimos
  que la herramienta se lo deje al usuario.
- **Detectar la escala "aproximadamente".** Un número que aparenta ser un metro
  y no lo es es peor que pedirla.