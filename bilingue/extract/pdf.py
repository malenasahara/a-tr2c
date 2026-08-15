"""Extractor de PDF: capa de texto vía PyMuPDF, párrafos por heurística.

Adaptación propia (decisión 2): se extraen los bloques de texto de cada
página en orden de lectura; los bloques partidos por columna o página se
funden cuando el anterior no cierra frase y el siguiente empieza en
minúscula (o el anterior termina en guión). Las imágenes y las tablas
detectadas se sustituyen por su marca. Páginas sin capa de texto (¿escaneadas?)
se omiten con aviso; OCR fuera del alcance. La menor fidelidad del PDF se
avisa siempre: división en párrafos heurística, bloques de número de página
descartados y sin detección de encabezados.
"""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

import pymupdf

# Evita el mensaje publicitario "Consider using the pymupdf_layout package…"
# que PyMuPDF imprime en stdout al analizar tablas.
if hasattr(pymupdf, "no_recommend_layout"):
    pymupdf.no_recommend_layout()

from bilingue.model import (
    MARK_IMAGE,
    MARK_TABLE,
    BilingueError,
    Block,
    Chapter,
    Document,
    Kind,
)

_ITALIC_FLAG = 2
_BOLD_FLAG = 16
_PAGE_NUMBER_RE = re.compile(r"^\d{1,4}$")
_SENTENCE_END_RE = re.compile(r"[.!?:;…»”\"']\s*$")
_STARTS_LOWER_RE = re.compile(r"^[a-záéíóúüñàèìòùâêîôûäëïöç]")


def _span_chunks(line: dict) -> tuple[str, str]:
    plain_parts: list[str] = []
    marked_parts: list[str] = []
    for span in line.get("spans", []):
        text = span.get("text", "")
        if not text:
            continue
        plain_parts.append(text)
        chunk = escape(text, quote=False)
        flags = span.get("flags", 0)
        if flags & _ITALIC_FLAG:
            chunk = f"<i>{chunk}</i>"
        if flags & _BOLD_FLAG:
            chunk = f"<b>{chunk}</b>"
        marked_parts.append(chunk)
    return "".join(plain_parts), "".join(marked_parts)


def _join_lines(parts: list[tuple[str, str]]) -> tuple[str, str]:
    """Une las líneas de un bloque deshaciendo la separación silábica con guión."""
    plain = ""
    marked = ""
    for line_plain, line_marked in parts:
        if plain.endswith("-") and _STARTS_LOWER_RE.match(line_plain.strip()):
            plain = plain[:-1] + line_plain.strip()
            marked = re.sub(r"-((?:</[bi]>)*)$", r"\1", marked) + line_marked.strip()
        else:
            plain = (plain + " " + line_plain).strip()
            marked = (marked + " " + line_marked).strip()
    marked = marked.replace("</i> <i>", " ").replace("</b> <b>", " ")
    plain = re.sub(r"\s+", " ", plain).strip()
    marked = re.sub(r"\s+", " ", marked).strip()
    return plain, marked


def _table_bboxes(page: pymupdf.Page) -> list[pymupdf.Rect]:
    try:
        return [pymupdf.Rect(t.bbox) for t in page.find_tables().tables]
    except Exception:
        return []


def _merge_paragraphs(blocks: list[Block]) -> list[Block]:
    """Funde párrafos partidos por columna o salto de página."""
    merged: list[Block] = []
    for block in blocks:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and prev.kind is Kind.PARAGRAPH
            and block.kind is Kind.PARAGRAPH
        ):
            hyphen = prev.text.endswith("-")
            continues = not _SENTENCE_END_RE.search(prev.text) and _STARTS_LOWER_RE.match(
                block.text
            )
            if hyphen or continues:
                if hyphen:
                    prev.text = prev.text[:-1] + block.text
                    prev.html = re.sub(r"-((?:</[bi]>)*)$", r"\1", prev.html) + block.html
                else:
                    prev.text = prev.text + " " + block.text
                    prev.html = prev.html + " " + block.html
                continue
        merged.append(block)
    return merged


def extract_pdf(path: Path) -> Document:
    doc = Document(format="PDF")
    try:
        pdf = pymupdf.open(path)
    except Exception as exc:
        raise BilingueError(f"«{path.name}» no se puede abrir como PDF: {exc}") from exc

    if pdf.needs_pass:
        raise BilingueError(f"«{path.name}» está cifrado con contraseña; no soportado.")

    blocks: list[Block] = []
    scanned_pages: list[int] = []
    with pdf:
        for page in pdf:
            tables = _table_bboxes(page)
            emitted_tables = [False] * len(tables)
            data = page.get_text("dict", sort=True)
            page_blocks = data.get("blocks", [])
            has_text = False
            has_image = False

            for raw in page_blocks:
                if raw.get("type") == 1:
                    has_image = True
                    blocks.append(Block(Kind.MARKER, MARK_IMAGE))
                    continue

                bbox = pymupdf.Rect(raw.get("bbox", (0, 0, 0, 0)))
                in_table = None
                for idx, rect in enumerate(tables):
                    if rect.intersects(bbox) and (bbox & rect).get_area() > 0.5 * bbox.get_area():
                        in_table = idx
                        break
                if in_table is not None:
                    has_text = True
                    if not emitted_tables[in_table]:
                        emitted_tables[in_table] = True
                        blocks.append(Block(Kind.MARKER, MARK_TABLE))
                    continue

                parts = [_span_chunks(line) for line in raw.get("lines", [])]
                plain, marked = _join_lines([p for p in parts if p[0].strip()])
                if not plain:
                    continue
                has_text = True
                if _PAGE_NUMBER_RE.match(plain):
                    continue
                blocks.append(Block(Kind.PARAGRAPH, plain, marked))

            if not has_text and has_image:
                scanned_pages.append(page.number + 1)

    blocks = _merge_paragraphs(blocks)

    doc.warnings.append(
        "PDF: fidelidad limitada — la división en párrafos es heurística, no se "
        "detectan encabezados y las imágenes y tablas se pierden (quedan sus marcas)."
    )
    if scanned_pages:
        listed = ", ".join(str(n) for n in scanned_pages[:10])
        extra = "…" if len(scanned_pages) > 10 else ""
        doc.warnings.append(
            f"PDF: {len(scanned_pages)} página(s) sin capa de texto omitida(s) "
            f"(¿escaneadas?): {listed}{extra}. OCR fuera del alcance."
        )

    if not any(b.translatable for b in blocks):
        raise BilingueError(
            f"«{path.name}»: el PDF no tiene capa de texto extraíble"
            + (" (parece escaneado; OCR fuera del alcance)." if scanned_pages else ".")
        )

    doc.chapters.append(Chapter(title=path.stem, blocks=blocks))
    return doc
