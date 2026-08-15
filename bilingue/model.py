"""Modelo de documento común a todos los formatos de entrada.

La extracción de cada formato produce un `Document`: lista de capítulos, cada
uno con una lista de bloques. Un bloque es un párrafo, un encabezado o una
marca de elemento omitido (decisión 6 de la especificación).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

MARK_IMAGE = "[imagen omitida]"
MARK_TABLE = "[tabla omitida]"
MARK_NOTE = "[nota omitida]"


class BilingueError(Exception):
    """Error con mensaje pensado para mostrarse tal cual al usuario."""


class Kind(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    MARKER = "marker"


@dataclass
class Block:
    kind: Kind
    text: str
    """Texto plano: lo que se traduce. En las marcas, el literal fijo en español."""

    html: str = ""
    """HTML seguro para la columna original: texto escapado conservando las
    etiquetas inline <i>/<b>/<em>/<strong> del original. Vacío → se usa `text`
    escapado."""

    level: int = 2
    """Solo encabezados: nivel 1-6."""

    @property
    def translatable(self) -> bool:
        return self.kind in (Kind.PARAGRAPH, Kind.HEADING)


@dataclass
class Chapter:
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Document:
    format: str
    chapters: list[Chapter] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def blocks(self) -> list[Block]:
        return [b for c in self.chapters for b in c.blocks]

    @property
    def paragraph_count(self) -> int:
        return sum(1 for b in self.blocks if b.kind is Kind.PARAGRAPH)

    @property
    def translatable_count(self) -> int:
        return sum(1 for b in self.blocks if b.translatable)

    @property
    def word_count(self) -> int:
        return sum(len(b.text.split()) for b in self.blocks if b.translatable)

    def sample_text(self, max_chars: int = 4000) -> str:
        """Texto inicial del documento, para la detección del idioma de origen."""
        parts: list[str] = []
        total = 0
        for block in self.blocks:
            if not block.translatable:
                continue
            parts.append(block.text)
            total += len(block.text)
            if total >= max_chars:
                break
        return "\n".join(parts)[:max_chars]
