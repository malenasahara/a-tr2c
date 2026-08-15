"""Funcionamiento sin conexión (requisito de la especificación).

El segmentador de frases stanza, que argostranslate usa por debajo, intenta
descargar `resources.json` de raw.githubusercontent.com en cada arranque de
proceso y rompe sin red aunque todo esté cacheado. Este módulo lo inicializa
sin descargas con el parche que detalla la especificación; debe importarse
antes de usar `argostranslate.translate`.
"""

from __future__ import annotations

import functools

import stanza

import argostranslate.sbd as sbd

_patched = False


def patch_stanza() -> None:
    """Aplica el parche (idempotente): stanza sin download_method."""
    global _patched
    if _patched:
        return
    sbd.stanza.Pipeline = functools.partial(stanza.Pipeline, download_method=None)
    _patched = True


patch_stanza()
