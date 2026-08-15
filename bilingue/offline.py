"""Funcionamiento sin conexión (requisito de la especificación).

El segmentador de frases stanza, que argostranslate usa por debajo, intenta
descargar `resources.json` de raw.githubusercontent.com en cada arranque de
proceso y rompe sin red aunque todo esté cacheado. Este módulo lo inicializa
sin descargas con el parche que detalla la especificación; debe importarse
antes de usar `argostranslate.translate`.

Se conserva una referencia al Pipeline original (con descargas) para el
aprovisionamiento único del segmentador en la primera traducción de un par:
los paquetes de Argos empaquetan recursos de stanza de una versión antigua
(p. ej. `resources.json` sin la clave «packages» que espera stanza moderno) y
hay que actualizarlos una vez, con red, dentro del directorio del paquete.
"""

from __future__ import annotations

import functools
import logging

import stanza

import argostranslate.sbd as sbd

# stanza avisa por consola de ajustes internos de sus procesadores (p. ej.
# «package default expects mwt»); no aportan nada al usuario de bilingue.
logging.getLogger("stanza").setLevel(logging.ERROR)

# Pipeline original, ANTES del parche: descarga recursos (solo se usa en el
# aprovisionamiento online de la primera traducción).
ORIGINAL_PIPELINE = stanza.Pipeline

_patched = False


def patch_stanza() -> None:
    """Aplica el parche (idempotente): stanza sin download_method."""
    global _patched
    if _patched:
        return
    sbd.stanza.Pipeline = functools.partial(ORIGINAL_PIPELINE, download_method=None)
    _patched = True


patch_stanza()
