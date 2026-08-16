"""Runtime hook de PyInstaller: stub de stanza.

El paquete autocontenido no incluye stanza (el segmentador por defecto es
MiniSBD), pero `argostranslate.sbd` hace `import stanza` incondicional. Este
hook registra un módulo sustituto antes de que arranque la app, de modo que
ese import resuelva sin traer los ~600 MB de la pila stanza/torch.
"""

import sys
import types

_stub = types.ModuleType("stanza")


def _sin_stanza(*_args, **_kwargs):
    raise RuntimeError(
        "el paquete autocontenido no incluye stanza; usa el segmentador "
        "MiniSBD (modo por defecto) o una instalación con pip si necesitas "
        "ARGOS_CHUNK_TYPE=STANZA."
    )


_stub.Pipeline = _sin_stanza
sys.modules["stanza"] = _stub
