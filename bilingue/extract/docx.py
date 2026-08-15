"""Extractor de DOCX vía python-docx.

Recorre el cuerpo del documento en orden real (párrafos y tablas
intercalados). Estilos de encabezado → filas a ancho completo; tablas,
imágenes y referencias de nota al pie → marcas de omisión; negrita y cursiva
de los runs → etiquetas inline.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

from docx import Document as open_docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.hyperlink import Hyperlink
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from bilingue.model import (
    MARK_IMAGE,
    MARK_NOTE,
    MARK_TABLE,
    BilingueError,
    Block,
    Chapter,
    Document,
    Kind,
)

_HEADING_STYLE_RE = re.compile(r"(?i)^(?:heading|t[íi]tulo)\s*(\d)?")


def _heading_level(par: Paragraph) -> int | None:
    """Nivel del encabezado según el estilo, o None si es un párrafo normal."""
    style = par.style
    for candidate in ((style.name or ""), (style.style_id or "")) if style else ():
        m = _HEADING_STYLE_RE.match(candidate.replace("Title", "Heading 1"))
        if m:
            level = int(m.group(1)) if m.group(1) else 1
            return min(level, 6)
    return None


def _iter_runs(par: Paragraph):
    for item in par.iter_inner_content():
        if isinstance(item, Run):
            yield item
        elif isinstance(item, Hyperlink):
            yield from item.runs


def _inline(par: Paragraph) -> tuple[str, str]:
    plain_parts: list[str] = []
    marked_parts: list[str] = []
    for run in _iter_runs(par):
        text = run.text
        if not text:
            continue
        plain_parts.append(text)
        chunk = escape(text, quote=False)
        if run.italic:
            chunk = f"<i>{chunk}</i>"
        if run.bold:
            chunk = f"<b>{chunk}</b>"
        marked_parts.append(chunk)
    plain = re.sub(r"\s+", " ", "".join(plain_parts)).strip()
    marked = re.sub(r"\s+", " ", "".join(marked_parts)).strip()
    return plain, marked


def extract_docx(path: Path) -> Document:
    doc = Document(format="DOCX")
    try:
        source = open_docx(str(path))
    except Exception as exc:  # python-docx lanza tipos variados con zips corruptos
        raise BilingueError(f"«{path.name}» no se puede abrir como DOCX: {exc}") from exc

    blocks: list[Block] = []
    for item in source.iter_inner_content():
        if isinstance(item, Table):
            blocks.append(Block(Kind.MARKER, MARK_TABLE))
            continue
        if not isinstance(item, Paragraph):
            continue

        element = item._p
        for _ in element.findall(".//" + qn("w:drawing")) + element.findall(
            ".//" + qn("w:pict")
        ):
            blocks.append(Block(Kind.MARKER, MARK_IMAGE))
        for _ in element.findall(".//" + qn("w:footnoteReference")) + element.findall(
            ".//" + qn("w:endnoteReference")
        ):
            blocks.append(Block(Kind.MARKER, MARK_NOTE))

        plain, marked = _inline(item)
        if not plain:
            continue
        level = _heading_level(item)
        if level is not None:
            blocks.append(Block(Kind.HEADING, plain, marked, level=level))
        else:
            blocks.append(Block(Kind.PARAGRAPH, plain, marked))

    if not blocks:
        raise BilingueError(f"«{path.name}»: el DOCX no contiene texto.")
    doc.chapters.append(Chapter(title=path.stem, blocks=blocks))
    return doc
