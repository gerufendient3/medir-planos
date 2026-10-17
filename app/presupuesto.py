"""Catalogo de conceptos y motor de presupuesto.

Reglas:
- El motor NUNCA inventa precios. Sin precio_unitario la linea queda
  FALTA_PRECIO y se excluye del subtotal.
- El motor NUNCA inventa cantidades. Una medicion incompatible con la unidad
  del concepto se excluye y se reporta.
- Toda linea guarda los handles de origen para que un estimador pueda
  rastroar la cifra hasta la entidad del plano.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

CATALOGO_POR_DEFECTO = Path(__file__).resolve().parent.parent / "catalogo" / "conceptos.json"

UNIDADES = {"m2", "m", "ml", "pza"}

# El concepto se cotiza por esta unidad y solo admite mediciones de esta forma
# natural de entidad.
FORMAS_ACEPTADAS = {
    "m2": {"m2"},
    "m": {"m"},
    "ml": {"ml", "m"},
    "pza": {"pza", "m"},  # piezas por metro (contactos, luminarias en un eje)
}


class ErrorCatalogo(ValueError):
    """El catalogo es invalido."""


def unidades_compatibles(unidad_concepto: str, unidad_medicion: str) -> bool:
    return unidad_medicion in FORMAS_ACEPTADAS.get(unidad_concepto, set())


@dataclass
class Concepto:
    clave: str
    nombre: str
    unidad: str
    categoria: str
    patron_capa: str
    prioridad: int = 0
    precio_unitario: float | None = None
    rendimiento: float = 1.0
    notas: str = ""
    _regex: re.Pattern | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.unidad not in UNIDADES:
            raise ErrorCatalogo(f"{self.clave}: unidad invalida '{self.unidad}'. Use {sorted(UNIDADES)}")
        self._regex = re.compile(self.patron_capa)

    @property
    def tiene_precio(self) -> bool:
        return self.precio_unitario is not None and self.precio_unitario > 0

    @property
    def formas_admitidas(self) -> set[str]:
        return FORMAS_ACEPTADAS.get(self.unidad, set())


class CapaNoMedible(Exception):
    """La capa esta en la lista de exclusion: no se debe cotizar.

    Existe para evitar falsos positivos. 'NOTAS-MUROS' contiene la palabra
    MUROS y un patron la mapea a muro de block, lo cual es incorrecto.
    """


class Catalogo:
    def __init__(self, conceptos: list[Concepto], meta: dict | None = None) -> None:
        self.conceptos = sorted(conceptos, key=lambda c: -c.prioridad)
        self.meta = meta or {}
        claves = [c.clave for c in self.conceptos]
        if len(claves) != len(set(claves)):
            raise ErrorCatalogo("Hay claves de concepto duplicadas")

        # Lista de exclusion: patrones de capas que nunca son conceptos de obra.
        self.no_medibles: list[tuple[re.Pattern, str]] = []
        for entrada in self.meta.get("capas_no_medibles", []):
            self.no_medibles.append(
                (re.compile(entrada["patron"]), entrada.get("motivo", "excluida"))
            )

    @classmethod
    def desde_dict(cls, datos: dict) -> Catalogo:
        """Construye el catálogo desde datos ya en memoria.

        Existe para que quien edita precios en caliente (la interfaz web) no
        tenga que escribir un archivo temporal por cada pulsación de «Aplicar».
        """
        conceptos = [
            Concepto(
                clave=c["clave"],
                nombre=c["nombre"],
                unidad=c.get("unidad") or c.get(" unidad"),
                categoria=c.get("categoria", "Sin categoría"),
                patron_capa=c["patron_capa"],
                prioridad=c.get("prioridad", 0),
                precio_unitario=c.get("precio_unitario"),
                rendimiento=float(c.get("rendimiento", 1.0)),
                notas=c.get("notas", ""),
            )
            for c in datos["conceptos"]
        ]
        return cls(conceptos, datos.get("_meta", {}))

    @classmethod
    def cargar(cls, ruta: str | Path | None = None) -> Catalogo:
        """Carga el catálogo de un JSON en disco."""
        ruta = Path(ruta) if ruta else CATALOGO_POR_DEFECTO
        return cls.desde_dict(json.loads(ruta.read_text(encoding="utf-8")))

    def es_no_medible(self, nombre_capa: str) -> str | None:
        """Devuelve el motivo si la capa esta excluida, o None si no lo esta."""
        for regex, motivo in self.no_medibles:
            if regex.search(nombre_capa):
                return motivo
        return None

    def buscar_por_capa(self, nombre_capa: str) -> Concepto | None:
        # Las exclusiones ganan a cualquier patron.
        if self.es_no_medible(nombre_capa) is not None:
            return None
        for c in self.conceptos:
            assert c._regex is not None
            if c._regex.search(nombre_capa):
                return c
        return None

    def unidades_por_capa(self, capas: list[str]) -> dict[str, str]:
        """Mapa capa -> unidad del concepto.

        Lo usa el motor para DESCARTAR entidades incompatibles antes de
        agregar. Las capas excluidas y sin concepto no aparecen en el mapa,
        por lo que el motor las mide sin filtrar y el presupuesto las reporta
        como excluidas o sin mapear.
        """
        out: dict[str, str] = {}
        for capa in capas:
            if self.es_no_medible(capa) is not None:
                continue
            c = self.buscar_por_capa(capa)
            if c is not None:
                out[capa] = c.unidad
        return out


@dataclass
class Linea:
    capa: str
    clave: str
    concepto: str
    unidad: str
    cantidad_medida: float
    rendimiento: float
    cantidad_ajustada: float
    precio_unitario: float | None
    importe: float | None
    categoria: str
    estado: str  # OK | FALTA_PRECIO | SIN_MAPEO | UNIDAD_INCOMPATIBLE
    detalle: str = ""
    handles: list[str] = field(default_factory=list)
    n_entidades: int = 0

    @property
    def facturable(self) -> bool:
        return self.estado == "OK"


UNIDAD_INCOMPATIBLE = "UNIDAD_INCOMPATIBLE"


@dataclass
class Presupuesto:
    lineas: list[Linea]
    subtotal: float
    moneda: str = "MXN"
    iva: float = 0.0
    total: float = 0.0

    @property
    def falta_precio(self) -> list[Linea]:
        return [l for l in self.lineas if l.estado == "FALTA_PRECIO"]

    @property
    def sin_mapeo(self) -> list[Linea]:
        return [l for l in self.lineas if l.estado == "SIN_MAPEO"]

    @property
    def excluidas_por_patron(self) -> list[Linea]:
        return [l for l in self.lineas if l.estado == "CAPA_EXCLUIDA"]

    @property
    def incompatibles(self) -> list[Linea]:
        return [l for l in self.lineas if l.estado == UNIDAD_INCOMPATIBLE]

    @property
    def excluidas(self) -> list[Linea]:
        return [l for l in self.lineas if not l.facturable]

    @property
    def completo(self) -> bool:
        return (not self.falta_precio and not self.incompatibles
                and not self.sin_mapeo and not self.excluidas_por_patron)

    @property
    def total_incompleto(self) -> bool:
        """El total NO cubre toda la obra del plano.

        Es una propiedad distinta de 'completo': ademas de los precios, una
        linea puede quedar fuera por incompatibilidad de unidad o por una capa
        sin concepto. Enviarle al cliente un total parcial sin decirlo es el
        peor resultado posible.
        """
        return bool(self.excluidas)

    def advertencias(self) -> list[str]:
        avisos = []
        if self.falta_precio:
            claves = ", ".join(sorted({l.clave for l in self.falta_precio}))
            avisos.append(
                f"{len(self.falta_precio)} concepto(s) sin precio_unitario ({claves}). "
                "NO incluidos en el subtotal."
            )
        if self.incompatibles:
            capas = ", ".join(sorted({l.capa for l in self.incompatibles}))
            avisos.append(
                f"{len(self.incompatibles)} medicion(es) con unidad incompatible con su "
                f"concepto ({capas}). NO incluidas: revisa si son piezas o superficies."
            )
        if self.sin_mapeo:
            capas = ", ".join(sorted({l.capa for l in self.sin_mapeo}))
            avisos.append(f"{len(self.sin_mapeo)} capa(s) sin concepto asignado: {capas}")
        if self.excluidas_por_patron:
            capas = ", ".join(sorted({l.capa for l in self.excluidas_por_patron}))
            avisos.append(
                f"{len(self.excluidas_por_patron)} capa(s) excluidas por catalogo "
                f"(anotacion, estructura o planos de apoyo): {capas}. NO cotizadas."
            )
        if self.excluidas:
            avisos.append(
                f"TOTAL PARCIAL: {len(self.excluidas)} de {len(self.lineas)} lineas "
                f"excluidas por advertencias. El total NO cubre toda la obra del plano."
            )
        if self.total_incompleto:
            avisos.append(
                "NO ENVIAR ESTE PRESUPUESTO AL CLIENTE TODAVIA: el total esta "
                "incompleto. Revisa las advertencias y recarga las partidas "
                "excluidas antes de cotizar."
            )
        return avisos


def calcular_iva(subtotal: float, tasa: float = 0.16) -> float:
    return round(subtotal * tasa, 2)


def construir_presupuesto(mediciones: list[dict], catalogo: Catalogo,
                          tasa_iva: float = 0.16) -> Presupuesto:
    """Convierte mediciones del motor en lineas de presupuesto.

    mediciones: lista de dicts con 'capa', 'unidades', 'cantidad' y
    opcionalmente 'handles' y 'n_entidades'.
    """
    lineas: list[Linea] = []
    subtotal = 0.0

    for m in mediciones:
        capa = m["capa"]
        unidad_medida = m["unidades"]
        cantidad = float(m["cantidad"])
        handles = m.get("handles", [])
        n_ent = m.get("n_entidades", len(handles))

        concepto = catalogo.buscar_por_capa(capa)

        if concepto is None:
            motivo_exclusion = catalogo.es_no_medible(capa)
            if motivo_exclusion:
                lineas.append(Linea(
                    capa=capa, clave="", concepto="(capa excluida)",
                    unidad=unidad_medida, cantidad_medida=cantidad, rendimiento=1.0,
                    cantidad_ajustada=cantidad, precio_unitario=None, importe=None,
                    categoria="Excluida", estado="CAPA_EXCLUIDA",
                    detalle="Excluida por catalogo: " + motivo_exclusion,
                    handles=handles, n_entidades=n_ent,
                ))
            else:
                lineas.append(Linea(
                    capa=capa, clave="", concepto="(sin concepto asignado)",
                    unidad=unidad_medida, cantidad_medida=cantidad, rendimiento=1.0,
                    cantidad_ajustada=cantidad, precio_unitario=None, importe=None,
                    categoria="Sin mapear", estado="SIN_MAPEO",
                    detalle="Ningun concepto del catalogo coincide con el nombre de esta capa.",
                    handles=handles, n_entidades=n_ent,
                ))
            continue

        if not unidades_compatibles(concepto.unidad, unidad_medida):
            lineas.append(Linea(
                capa=capa, clave=concepto.clave, concepto=concepto.nombre,
                unidad=unidad_medida, cantidad_medida=cantidad, rendimiento=1.0,
                cantidad_ajustada=cantidad, precio_unitario=concepto.precio_unitario,
                importe=None, categoria=concepto.categoria,
                estado=UNIDAD_INCOMPATIBLE,
                detalle=(
                    f"El concepto se cotiza por {concepto.unidad} (acepta "
                    f"{sorted(concepto.formas_admitidas)}) pero la capa produjo "
                    f"{cantidad:.4f} {unidad_medida}. Linea EXCLUIDA."
                ),
                handles=handles, n_entidades=n_ent,
            ))
            continue

        cantidad_ajustada = cantidad * concepto.rendimiento

        if concepto.tiene_precio:
            importe = round(cantidad_ajustada * concepto.precio_unitario, 2)
            subtotal += importe
            estado = "OK"
        else:
            importe = None
            estado = "FALTA_PRECIO"

        lineas.append(Linea(
            capa=capa, clave=concepto.clave, concepto=concepto.nombre,
            unidad=unidad_medida, cantidad_medida=cantidad,
            rendimiento=concepto.rendimiento,
            cantidad_ajustada=round(cantidad_ajustada, 4),
            precio_unitario=concepto.precio_unitario,
            importe=importe, categoria=concepto.categoria, estado=estado,
            handles=handles, n_entidades=n_ent,
        ))

    subtotal = round(subtotal, 2)
    iva = calcular_iva(subtotal, tasa_iva)
    return Presupuesto(
        lineas=lineas, subtotal=subtotal, iva=iva,
        total=round(subtotal + iva, 2),
    )