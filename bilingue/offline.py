"""Funcionamiento sin conexión (requisito de la especificación).

El segmentador por defecto de la app es MiniSBD (ARGOS_CHUNK_TYPE=MINISBD,
fijado en bilingue/__init__.py): modelos ONNX diminutos que argostranslate
descarga al primer uso de cada par dentro de su directorio de datos y
reutiliza sin red después. En este modo no hay nada que parchear.

La ruta stanza sigue disponible para quien la fuerce por entorno (p. ej.
ARGOS_CHUNK_TYPE=STANZA en una instalación con pip). El segmentador stanza
intenta descargar `resources.json` de raw.githubusercontent.com en cada
arranque de proceso y rompe sin red aunque todo esté cacheado; en modo stanza
este módulo lo inicializa sin descargas con el parche que detalla la
especificación, antes de usar `argostranslate.translate`.

Se conserva una referencia al Pipeline original (con descargas) para el
aprovisionamiento único del segmentador en la primera traducción de un par:
los paquetes de Argos empaquetan recursos de stanza de una versión antigua
(p. ej. `resources.json` sin la clave «packages» que espera stanza moderno) y
hay que actualizarlos una vez, con red, dentro del directorio del paquete.
"""

from __future__ import annotations

import functools
import logging


def _stanza_activo() -> bool:
    """True si el segmentador efectivo es stanza: forzado por entorno o
    argostranslate antiguo, sin selector de segmentador."""
    import argostranslate.settings as argos_settings

    chunk = getattr(argos_settings, "chunk_type", None)
    if chunk is None:  # argostranslate sin ChunkType: stanza era el único modo
        return True
    # Comparación por nombre para no importar ChunkType (las versiones
    # antiguas no lo tienen). DEFAULT/ARGOSTRANSLATE eligen por paquete, y los
    # paquetes de Argos traen recursos de stanza: cuentan como modo stanza.
    return getattr(chunk, "name", "") in ("DEFAULT", "ARGOSTRANSLATE", "STANZA")


STANZA_ACTIVE = _stanza_activo()

# Pipeline original, ANTES del parche: descarga recursos (solo se usa en el
# aprovisionamiento online de la primera traducción). None en modo MiniSBD o
# si stanza no está instalado (paquete autocontenido).
ORIGINAL_PIPELINE = None

_patched = False

if STANZA_ACTIVE:
    try:
        import stanza
    except ImportError:
        stanza = None

    if stanza is not None:
        # stanza avisa por consola de ajustes internos de sus procesadores
        # (p. ej. «package default expects mwt»); no aportan nada al usuario
        # de bilingue. Un filtro y no setLevel: stanza resetea el nivel de su
        # logger en cada construcción del Pipeline, pero los filtros
        # sobreviven.
        class _SoloErrores(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                return record.levelno >= logging.ERROR

        logging.getLogger("stanza").addFilter(_SoloErrores())
        ORIGINAL_PIPELINE = stanza.Pipeline


def patch_stanza() -> None:
    """Aplica el parche (idempotente): stanza sin download_method."""
    global _patched
    if _patched or ORIGINAL_PIPELINE is None:
        return
    import argostranslate.sbd as sbd

    sbd.stanza.Pipeline = functools.partial(ORIGINAL_PIPELINE, download_method=None)
    _patched = True


if STANZA_ACTIVE:
    patch_stanza()
