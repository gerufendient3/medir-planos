"""Extraccion de entidades con procedencia.

Cada entidad conserva su handle, tipo y capa. Nada se agrega todavia: el
motor de medicion decide que hacer con cada una. La procedencia es lo que
permite a un estimador rastroar una cifra del presupuesto hasta el plano.

Decisiones:
- Se usa ezdxf.path.make_path porque resuelve el bulge (arcos) de LWPOLYLINE.
  get_points() ignora el arco y daria un perimetro falso.
- Los bloques (INSERT) se explotan con ezdxf.explode() y se miden como piezas
  del bloque mas la geometria interior. Es el patron real en instalaciones:
  contactos y luminarias vienen como bloques.
- El texto se separa desde el inicio: no es geometria y no debe mezclarse
  con areas ni longitudes de obra.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import ezdxf
from ezdxf.entities import DXFGraphic

# Tipos que son anotacion, nunca cantidad de obra.
NO_GEOMETRICO = {"TEXT", "MTEXT", "LEADER", "DIMENSION", "TOLERANCE", "MTEXT"}

# Tipos que portan arco. make_path los resuelve a una polilinea densa.
CON_ARCO = {"ARC", "CIRCLE", "ELLIPSE"}

# Radio maximo para que un circulo cuente como pieza y no como superficie.
RADIO_MAXIMO_PIEZA_M = 0.5

# Densificacion al aplanar arcos. 1 mm es suficiente para obra: un arco de
# radio 1 m con error de 1 mm subestima el area en menos de 0.1%.
PRECISION_ARCO_M = 0.001


@dataclass
class EntidadMedida:
    """Una entidad del plano, con su procedencia y su contribucion medida."""

    handle: str
    tipo: str            # LINE, LWPOLYLINE, CIRCLE, INSERT...
    capa: str
    forma: str           # "m" | "m2" | "pza"
    longitud: float = 0.0
    area: float = 0.0
    piezas: float = 0.0
    cerrado: bool = False
    origen_bloque: str | None = None
    escala_insert: float = 1.0
    advertencias: list[str] = field(default_factory=list)
    # Geometria 2D completa de la entidad, con sus huecos. Se conserva para
    # resolver solapes y containment con union geometrica. Guardar solo el
    # anillo exterior perderia las islas de un HATCH.
    geometria: object | None = field(default=None, repr=False, compare=False)

    @property
    def unidad_primaria(self) -> str:
        """Unidad dominante. Se conserva por compatibilidad de API."""
        c = self.contribuciones()
        return c[0][0] if c else "ninguna"

    def contribuciones(self) -> list[tuple[str, float]]:
        """Lista (forma, valor) de todo lo que esta entidad aporta.

        Una polilinea cerrada aporta DOS cosas: area (m2) y perimetro (ml).
        Devolver solo una perderia el perimetro, que es justo lo que necesita
        un concepto ml como rodapie o cornisa.

        El orden es fijo para que el comportamiento sea determinista.
        """
        out: list[tuple[str, float]] = []
        if self.piezas:
            out.append(("pza", self.piezas))
        if self.area:
            out.append(("m2", self.area))
        if self.longitud and self.forma != "pza":
            # El perimetro de un poligono se contabiliza como ml, no como m:
            # metro lineal es desarrollo, metro es trazo recto.
            unidad_len = "ml" if self.cerrado or self.forma == "m2" else "m"
            out.append((unidad_len, self.longitud))
        return out


class Insignificante(ValueError):
    """La entidad no aporta cantidad de obra (cota, texto, referencia)."""


def _pts2d(entity) -> list[tuple[float, float]]:
    return [(p[0], p[1]) for p in entity.get_points()]


def _a_camino(entity) -> "object":
    """Convierte la entidad en un path de ezdxf con arcos resueltos.

    make_path es la via correcta: LWPOLYLINE con bulge produce una polilinea
    densa que incluye los arcos. get_points() los pierde.
    """
    from ezdxf.path import make_path

    return make_path(entity)


def medir_entidad(entity: DXFGraphic, origen_bloque: str | None = None,
                  escala_insert: float = 1.0) -> EntidadMedida:
    """Convierte una entidad DXF en su contribucion medida."""
    tipo = entity.dxftype()

    if tipo in NO_GEOMETRICO:
        raise Insignificante(f"{tipo} es anotacion, no geometria de obra")

    em = EntidadMedida(
        handle=str(entity.dxf.handle),
        tipo=tipo,
        capa=entity.dxf.layer,
        forma="ninguna",
        origen_bloque=origen_bloque,
        escala_insert=escala_insert,
    )

    # INSERT: es una pieza por si mismo, mas la geometria que contiene.
    if tipo == "INSERT":
        em.forma = "pza"
        em.piezas = 1.0
        em.advertencias.append("bloque sin explotar medido como 1 pieza")
        return em

    if tipo == "POINT":
        em.forma = "pza"
        em.piezas = 1.0
        return em

    if tipo == "CIRCLE":
        radio = entity.dxf.radius * escala_insert
        if radio <= RADIO_MAXIMO_PIEZA_M:
            em.forma = "pza"
            em.piezas = 1.0
            return em
        em.forma = "m2"
        em.area = 3.141592653589793 * radio ** 2
        em.longitud = 2 * 3.141592653589793 * radio
        return em

    if tipo in {"ARC", "ELLIPSE"}:
        camino = _a_camino(entity)
        em.forma = "m"
        try:
            densa = list(camino.flattening(PRECISION_ARCO_M))
            em.longitud = _longitud_abierta(densa) * escala_insert
        except Exception as exc:
            em.advertencias.append(f"arco ilegible, se usa longitud nominal: {exc}")
            em.longitud = float(getattr(entity.dxf, "radius", 0.0)) * escala_insert
        return em

    if tipo == "LINE":
        s, e = entity.dxf.start, entity.dxf.end
        em.forma = "m"
        em.longitud = ((s[0] - e[0]) ** 2 + (s[1] - e[1]) ** 2) ** 0.5 * escala_insert
        return em

    if tipo in {"LWPOLYLINE", "POLYLINE"}:
        cerrado = bool(getattr(entity, "closed", False))
        pts = _pts2d(entity)
        em.cerrado = cerrado

        if cerrado:
            if len(pts) < 3:
                em.advertencias.append(
                    f"polilinea cerrada con solo {len(pts)} punto(s): area no valida"
                )
                raise Insignificante("polilinea cerrada degenerada")
            em.forma = "m2"
            try:
                camino = _a_camino(entity)
                # flattening() densifica los arcos del bulge. Es la via
                # correcta: get_points() los pierde.
                anillo = list(camino.flattening(PRECISION_ARCO_M))
                if not anillo or len(anillo) < 3:
                    em.advertencias.append("polilinea cerrada sin vertices suficientes")
                    raise Insignificante("polilinea cerrada degenerada")
                em.area = abs(_area(anillo)) * escala_insert ** 2
                em.longitud = _longitud_cerrada(anillo) * escala_insert
                from shapely.geometry import Polygon as _Poly
                em.geometria = _Poly([(p[0], p[1]) for p in anillo])
            except Insignificante:
                raise
            except Exception as exc:
                em.advertencias.append(f"no se pudo calcular area: {exc}")
                raise Insignificante("polilinea con bulge ilegible") from exc
            return em

        if len(pts) < 2:
            em.advertencias.append("polilinea abierta con menos de 2 puntos")
            raise Insignificante("polilinea abierta degenerada")

        em.forma = "m"
        try:
            camino = _a_camino(entity)
            densa = list(camino.flattening(PRECISION_ARCO_M))
            em.longitud = _longitud_abierta(densa) * escala_insert
        except Exception as exc:
            em.advertencias.append(f"longitud con bulge ilegible, se usa get_points: {exc}")
            em.longitud = _longitud_abierta(pts) * escala_insert
        return em

    if tipo == "HATCH":
        em.forma = "m2"
        try:
            from shapely.geometry import Polygon

            # Un HATCH con isla (p.ej. un patio dentro de una losa) NO es la
            # suma de sus contornos. DXF marca cada contorno con un bitfield
            # donde el bit de valor 1 es "exterior"; los demas son islas y se
            # RESTAN. Ignorar ese bit daba 116 m2 en vez de 84.
            #
            # ezdxf anade el bit de polilinea al escribir, asi que un
            # contorno exterior tipico se lee como 3 y una isla como 2.
            exteriores, islas = [], []
            for bp in entity.paths:
                flags = getattr(bp, "path_type_flags", None)
                externo = True if flags is None else bool(flags & 1)
                try:
                    verts = bp.vertices
                    anillo = [(p[0], p[1]) for p in verts]
                except Exception:
                    continue
                if len(anillo) < 3:
                    continue
                try:
                    poligono = Polygon(anillo)
                    if not poligono.is_valid:
                        poligono = poligono.buffer(0)
                    if poligono.is_empty:
                        continue
                except Exception:
                    continue
                if externo:
                    exteriores.append(poligono)
                else:
                    islas.append(poligono)

            if not exteriores:
                # Sin ningun contorno externo: cae al metodo por sub_paths.
                camino = _a_camino(entity)
                total = 0.0
                for sub in camino.sub_paths():
                    anillo = list(sub.flattening(PRECISION_ARCO_M))
                    if len(anillo) >= 3:
                        total += abs(_area(anillo))
                em.area = total * escala_insert ** 2
                if total == 0.0:
                    raise Insignificante("hatch sin contorno utilizable")
                return em

            base = exteriores[0]
            for extra in exteriores[1:]:
                base = base.union(extra)
            for isla in islas:
                base = base.difference(isla)

            em.area = base.area * escala_insert ** 2
            em.geometria = base
            em.longitud = base.exterior.length * escala_insert
            em.cerrado = True
            if base.area <= 0:
                raise Insignificante("hatch con area nula")
        except Insignificante:
            raise
        except Exception as exc:
            em.advertencias.append(f"hatch ilegible: {exc}")
            raise Insignificante("hatch ilegible") from exc
        return em

    em.advertencias.append(f"tipo de entidad '{tipo}' sin soporte")
    raise Insignificante(f"tipo sin soporte: {tipo}")


def _area(pts) -> float:
    """Area por el teorema del cordon (shoelace)."""
    n = len(pts)
    return 0.5 * sum(
        pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
        for i in range(n)
    )


def _longitud_abierta(pts) -> float:
    return sum(
        ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        for a, b in zip(pts, pts[1:])
    )


def _longitud_cerrada(pts) -> float:
    if len(pts) < 3:
        return 0.0
    return _longitud_abierta(list(pts) + [pts[0]])


def extraer(doc, capa_filtro: list[str] | None = None) -> tuple[list[EntidadMedida], list[dict]]:
    """Recorre el modelspace y devuelve (entidades medidas, omitidas con motivo)."""
    msp = doc.modelspace()
    medidas: list[EntidadMedida] = []
    omitidas: list[dict] = []

    for e in msp:
        capa = e.dxf.layer
        if capa_filtro is not None and capa not in capa_filtro:
            continue
        try:
            medidas.append(medir_entidad(e))
        except Insignificante as exc:
            omitidas.append({
                "handle": str(e.dxf.handle),
                "tipo": e.dxftype(),
                "capa": capa,
                "motivo": str(exc),
            })
        except Exception as exc:
            omitidas.append({
                "handle": str(e.dxf.handle),
                "tipo": e.dxftype(),
                "capa": capa,
                "motivo": f"error inesperado: {exc}",
            })

    return medidas, omitidas


def extraer_bloques(doc, capa_filtro: list[str] | None = None) -> tuple[list[EntidadMedida], list[dict]]:
    """Explota los bloques y mide su contenido.

    Decision: un INSERT se contabiliza como 1 pieza del concepto de la capa
    (p.ej. un contacto) y su geometria interior se mide por separado. Es el
    patron mas frecuente en planos de instalaciones.

    El INSERT como pieza ya lo cuenta extraer(). Aqui NO se vuelve a añadir:
    hacerlo duplicaba la partida (6 luminarias en vez de 4).
    """
    msp = doc.modelspace()
    medidas: list[EntidadMedida] = []
    omitidas: list[dict] = []

    for e in msp:
        capa = e.dxf.layer
        if capa_filtro is not None and capa not in capa_filtro:
            continue
        if e.dxftype() != "INSERT":
            continue

        try:
            escala = float(getattr(e.dxf, "xscale", 1.0) or 1.0)
            for sub in e.virtual_entities():
                try:
                    sub_med = medir_entidad(sub, origen_bloque=str(e.dxf.name),
                                            escala_insert=escala)
                    # La geometria interna hereda la capa del INSERT: en un
                    # plano real el bloque vive en la capa de su disciplina.
                    sub_med.capa = capa
                    medidas.append(sub_med)
                except Insignificante:
                    continue
        except Exception as exc:
            omitidas.append({
                "handle": str(e.dxf.handle),
                "tipo": "INSERT",
                "capa": capa,
                "motivo": f"no se pudo explotar el bloque: {exc}",
            })

    return medidas, omitidas


def leer(path: str | Path):
    return ezdxf.readfile(str(path))


class OdaNoDisponible(RuntimeError):
    """ODA File Converter no esta instalado.

    DWG es un formato binario propietario: no hay lectura nativa. La unica via
    soportada es convertirlo con ODA File Converter, que el usuario debe
    instalar. Ver docs/FORMATOS_ENTRADA.md.
    """


def odafc_disponible() -> bool:
    """True si ODA File Converter se puede invocar."""
    try:
        from ezdxf.addons import odafc
    except ImportError:
        return False
    try:
        return bool(odafc.is_installed())
    except Exception:
        return False


def leer_dwg(path: str | Path):
    """Abre un DWG convirtiéndolo a DXF con ODA File Converter.

    Falla con un mensaje claro si ODA no está instalado. Nunca degrada en
    silencio a "no se pudo leer".
    """
    ruta = Path(path)
    if ruta.suffix.lower() != ".dwg":
        raise ValueError(f"leer_dwg espera un .dwg, recibio '{ruta.suffix}'")

    try:
        from ezdxf.addons import odafc
    except ImportError as exc:
        raise OdaNoDisponible(
            "El addon odafc de ezdxf no esta instalado. Instala ezdxf completo."
        ) from exc

    if not odafc_disponible():
        raise OdaNoDisponible(
            "ODA File Converter no esta instalado, y es obligatorio para leer DWG.\n"
            "  Descarga: https://www.opendesign.com/guestfiles/oda_file_converter\n"
            "  Windows: instala y deja la ruta en el PATH, o configurala en\n"
            "           ezdxf.options (seccion odafc-addon, clave win_exec_path).\n"
            "  Linux/macOS: pon ODAFileConverter en el PATH o usa AppImage.\n"
            "  Si tu plano es DXF, no necesitas esto: abre el .dxf directamente."
        )

    try:
        return odafc.readfile(str(ruta))
    except Exception as exc:
        raise OdaNoDisponible(
            f"ODA File Converter fallo leyendo '{ruta.name}': {exc}\n"
            "El archivo puede estar corrupto o ser de una version no soportada "
            "(ODA soporta de ACAD12/R12 a ACAD2018/R2018)."
        ) from exc


def unidades_documento(doc) -> int:
    return int(doc.units or 0)
