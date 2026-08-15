"""Extractor de TXT y Markdown.

Ambos formatos comparten parser: párrafos separados por línea en blanco y
líneas `#` como encabezados (también en TXT, de modo que un TXT con
encabezados produzca filas a ancho completo). Del resto de sintaxis Markdown
se cubre lo básico: listas (cada ítem, un párrafo), citas, imágenes, tablas y
notas al pie —estos tres últimos se omiten con su marca—, y la negrita y la
cursiva se conservan como etiquetas inline en la columna original.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from bilingue.model import (
    MARK_IMAGE,
    MARK_NOTE,
    MARK_TABLE,
    Block,
    Chapter,
    Document,
    Kind,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_ITEM_RE = re.compile(r"^\s{0,3}(?:[-*+]|\d{1,3}[.)])\s+(.*)$")
_HR_RE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*\|?\s*$")
_QUOTE_RE = re.compile(r"^\s{0,3}>\s?")
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")
_CODE_RE = re.compile(r"`([^`]*)`")
_FOOTNOTE_DEF_RE = re.compile(r"^\s{0,3}\[\^[^\]]+\]:")
_FOOTNOTE_REF_RE = re.compile(r"\[\^[^\]]+\]")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)")


def _inline(text: str) -> tuple[str, str]:
    """Convierte el marcado inline: devuelve (texto plano, HTML seguro)."""
    text = _FOOTNOTE_REF_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _CODE_RE.sub(r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()

    def _first_group(m: re.Match[str]) -> str:
        return m.group(1) or m.group(2) or ""

    plain = _BOLD_RE.sub(_first_group, text)
    plain = _ITALIC_RE.sub(_first_group, plain)

    escaped = html.escape(text, quote=False)
    marked = _BOLD_RE.sub(lambda m: f"<b>{_first_group(m)}</b>", escaped)
    marked = _ITALIC_RE.sub(lambda m: f"<i>{_first_group(m)}</i>", marked)
    return plain, marked


def _is_table_start(lines: list[str], idx: int) -> bool:
    return (
        "|" in lines[idx]
        and idx + 1 < len(lines)
        and "|" in lines[idx + 1]
        and bool(_TABLE_SEP_RE.match(lines[idx + 1]))
    )


def extract_textmd(path: Path) -> Document:
    doc = Document(format=path.suffix.lstrip(".").upper() or "TXT")
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="cp1252", errors="replace")
        doc.warnings.append(
            "El fichero no está en UTF-8; se ha leído como cp1252 y puede haber "
            "caracteres sustituidos."
        )

    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[Block] = []
    para_lines: list[str] = []

    def emit_paragraph(md_text: str) -> None:
        for _ in _IMAGE_RE.findall(md_text):
            blocks.append(Block(Kind.MARKER, MARK_IMAGE))
        md_text = _IMAGE_RE.sub("", md_text)
        plain, marked = _inline(md_text)
        if plain:
            blocks.append(Block(Kind.PARAGRAPH, plain, marked))

    def flush() -> None:
        if para_lines:
            emit_paragraph(" ".join(para_lines))
            para_lines.clear()

    idx = 0
    total = len(lines)
    while idx < total:
        line = _QUOTE_RE.sub("", lines[idx])
        stripped = line.strip()

        if not stripped:
            flush()
            idx += 1
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            flush()
            plain, marked = _inline(heading.group(2))
            if plain:
                blocks.append(
                    Block(Kind.HEADING, plain, marked, level=len(heading.group(1)))
                )
            idx += 1
            continue

        if _HR_RE.match(line):
            flush()
            idx += 1
            continue

        if _FOOTNOTE_DEF_RE.match(line):
            flush()
            blocks.append(Block(Kind.MARKER, MARK_NOTE))
            idx += 1
            while idx < total and lines[idx].strip():
                idx += 1
            continue

        if _is_table_start(lines, idx):
            flush()
            blocks.append(Block(Kind.MARKER, MARK_TABLE))
            while idx < total and "|" in lines[idx] and lines[idx].strip():
                idx += 1
            continue

        item = _LIST_ITEM_RE.match(line)
        if item:
            flush()
            item_lines = [item.group(1).strip()]
            idx += 1
            while idx < total:
                cont = _QUOTE_RE.sub("", lines[idx])
                if (
                    not cont.strip()
                    or _LIST_ITEM_RE.match(cont)
                    or _HEADING_RE.match(cont)
                    or _HR_RE.match(cont)
                    or _is_table_start(lines, idx)
                ):
                    break
                item_lines.append(cont.strip())
                idx += 1
            emit_paragraph(" ".join(item_lines))
            continue

        para_lines.append(stripped)
        idx += 1

    flush()
    doc.chapters.append(Chapter(title=path.stem, blocks=blocks))
    return doc
