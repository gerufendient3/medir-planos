import math
import sys
from pathlib import Path

from app.medidor import medir
from app.presupuesto import Catalogo

CAPAS = [
    "PISO-LOSETA", "LAMPARA-PENDIENTE", "ELEC-CONTACTO",
    "MURO-BLOCK-15CM", "Muro de Block 15 cm", "cielo de  yeso",
    "TUBO-HID", "cANALización eléctrica",
]

cat = Catalogo.cargar()
um = cat.unidades_por_capa(CAPAS)

for f in sorted(Path("planos/casos").glob("*.dxf")):
    r = medir(f, unidades_por_capa=um)
    ms = " | ".join("{} {}".format(m["cantidad"], m["unidades"]) for m in r["mediciones"]) or "SIN MEDICION"
    print("{:24} {}".format(f.name, ms))
    for i in r["entidades_incompatibles"]:
        print("      INCOMPAT  {} {} aporta {} vs {}".format(
            i["capa"], i["tipo"], i["forma_detectada"], i["unidad_concepto"]))
    for o in r["entidades_omitidas"]:
        print("      OMITIDA   {} {}".format(o["tipo"], o["motivo"]))
    for a in r["diagnostico"]["advertencias"]:
        print("      DIAG      {}".format(a))

print()
print("bulge  area esperada  ", round(12 + math.pi * 1.5 ** 2 / 2, 4))
print("bulge  perimetro espdo", round(11 + math.pi * 1.5, 4))