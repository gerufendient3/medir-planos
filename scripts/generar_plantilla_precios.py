"""Genera una plantilla de catalogo con los precios vacios y guias de uso.

No inventa ni sugiere precios. La plantilla sale con precio_unitario: null y
el motor marcara cada concepto como FALTA_PRECIO hasta que el usuario lo
llene. Ver docs/DECISIONES.md decision 10.
"""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "catalogo" / "conceptos.json"
DESTINO = RAIZ / "catalogo" / "mi_precios.json"

GUIA = """CÓMO USAR ESTA PLANTILLA
========================

1. Llena `precio_unitario` en cada concepto que uses, en pesos mexicanos (MXN),
   con el precio que TÚ cobras. Incluye material y mano de obra como las
   cotices tú.

2. Deja en `null` los conceptos que no apliquen a tu obra. El motor los marca
   como FALTA_PRECIO y los EXCLUYE del subtotal. No son un error: son una
   señal de que el total está incompleto.

3. `rendimiento` es un factor de merma (1.08 = 8% de desperdicio). Ajústalo a tu
   práctica y al material.

4. `patron_capa` mapea el nombre de la capa del plano al concepto. Si tu
   arquitecto nombra las capas distinto, ajusta el patrón; el motor no cambia.

5. Para ver qué capas de tu plano quedan sin cubrir, corre:
       python scripts/auditar_capas.py planos/tu_plano.dxf

NINGÚN PRECIO ESTÁ INCLUIDO. Esta plantilla no propone precios de mercado:
no hay fuente pública verificada de precios de obra en México. Los precios
son tuyos.

Para desarmar el total desglosado y sus advertencias:
       python -m app.pipeline planos/tu_plano.dxf \\
           --catalogo catalogo/mi_precios.json --salida salida/
"""


def main() -> int:
    datos = json.loads(ORIGEN.read_text(encoding="utf-8"))

    for c in datos["conceptos"]:
        c["precio_unitario"] = None  # explicito, aunque ya lo este

    datos["_meta"]["version"] = "plantilla-usuario"
    datos["_meta"]["_plantilla"] = True
    datos["_meta"]["_guia"] = GUIA
    datos["_meta"]["_conceptos_sin_precio"] = [
        {"clave": c["clave"], "nombre": c["nombre"], "unidad": c["unidad"]}
        for c in datos["conceptos"]
    ]

    DESTINO.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print("escrita plantilla: {}".format(DESTINO.name))
    print("conceptos: {}  (todos con precio_unitario = null)".format(len(datos["conceptos"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())