"""bilingue: edición bilingüe en dos columnas con traducción local (Argos Translate)."""

import os
import platform
import sys

__version__ = "0.1.0"

if sys.platform == "darwin" and platform.machine() == "x86_64":
    # torch (vía stanza) y ctranslate2 empaquetan cada uno su propio libomp;
    # en macOS Intel esa duplicación segfaultea al construir el Translator de
    # ctranslate2 (verificado con faulthandler en CI, translate.py:189).
    # Un solo hilo OpenMP lo evita; exporta OMP_NUM_THREADS para forzar otro
    # valor bajo tu responsabilidad.
    os.environ.setdefault("OMP_NUM_THREADS", "1")
