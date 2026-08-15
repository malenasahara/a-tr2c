"""Bucle de traducción por párrafos: núcleo común de la CLI y la GUI.

Rellena `Block.translation` de cada bloque traducible, recuperando del
checkpoint lo ya hecho y persistiendo cada traducción nueva en el momento.
El progreso y la cancelación se delegan en callbacks para que la CLI (tqdm,
Ctrl+C) y la GUI (Progressbar, botón cancelar) compartan el mismo código.
"""

from __future__ import annotations

from typing import Callable, Protocol

from bilingue.checkpoint import Checkpoint
from bilingue.model import Document


class Translator(Protocol):
    def translate(self, input_text: str) -> str: ...


class TranslationCancelled(Exception):
    """La GUI ha pedido cancelar; el checkpoint queda guardado."""


def run_translation(
    doc: Document,
    translator: Translator,
    checkpoint: Checkpoint,
    on_progress: Callable[[], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> int:
    """Traduce los bloques pendientes. Devuelve cuántos se han traducido ahora."""
    fresh = 0
    for chapter_index, chapter in enumerate(doc.chapters):
        for block_index, block in enumerate(chapter.blocks):
            if not block.translatable:
                continue
            cached = checkpoint.translations.get((chapter_index, block_index))
            if cached is not None:
                block.translation = cached
                continue
            if should_stop is not None and should_stop():
                raise TranslationCancelled()
            block.translation = translator.translate(block.text)
            checkpoint.record(chapter_index, block_index, block.translation)
            fresh += 1
            if on_progress is not None:
                on_progress()
    return fresh
