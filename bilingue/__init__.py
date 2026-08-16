"""bilingue: edición bilingüe en dos columnas con traducción local (Argos Translate)."""

import os
import platform
import sys

__version__ = "0.2.0"

# Segmentador de frases: MiniSBD (modelos ONNX de ~0,2 MB por idioma) en vez
# de la pila stanza/torch. Debe fijarse ANTES de cualquier import de
# argostranslate: settings lee ARGOS_CHUNK_TYPE en el momento del import (los
# imports pesados del paquete son perezosos, así que basta con hacerlo aquí).
# setdefault permite forzar otro modo por entorno, p. ej.
# ARGOS_CHUNK_TYPE=STANZA en una instalación con pip.
os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")

if sys.platform == "darwin" and platform.machine() == "x86_64":
    # torch (vía stanza) y ctranslate2 empaquetan cada uno su propio libomp;
    # en macOS Intel esa duplicación segfaultea al construir el Translator de
    # ctranslate2 (verificado con faulthandler en CI, translate.py:189).
    # Un solo hilo OpenMP lo evita; exporta OMP_NUM_THREADS para forzar otro
    # valor bajo tu responsabilidad. Sin torch (paquete autocontenido) solo
    # queda la libomp de ctranslate2 y no hace falta el tope: multihilo.
    import importlib.util

    if importlib.util.find_spec("torch") is not None:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
