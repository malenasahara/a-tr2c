"""Extractor de EPUB: documentos HTML del zip en orden de spine.

Cada documento del spine es un capítulo. Encabezados h1–h6 → filas a ancho
completo; párrafos y elementos de lista → filas normales; imágenes, tablas y
notas al pie → marcas de omisión (decisión 6). Las cursivas y negritas del
original se conservan como etiquetas inline.
"""

from __future__ import annotations

import posixpath
import re
import warnings
import zipfile
from html import escape
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup, NavigableString, Tag, XMLParsedAsHTMLWarning
from lxml import etree

# Los documentos de un EPUB son XHTML; el parser HTML de lxml los trata bien
# y es más tolerante con ficheros reales imperfectos que el parser XML.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

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

_CONTAINER_NS = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
_OPF_NS = {"opf": "http://www.idpf.org/2007/opf"}

_INLINE_KEEP = {"i", "em", "b", "strong"}
_SKIP_TAGS = {"script", "style", "head", "hr", "title", "meta", "link"}
_NOTE_MARK_RE = re.compile(r"^[\d*†‡§]+$")
_BLOCKISH = [
    "p", "div", "section", "article", "blockquote", "ul", "ol", "li", "dl",
    "table", "figure", "figcaption", "img", "image", "svg", "pre",
    "h1", "h2", "h3", "h4", "h5", "h6",
]


def _attr(tag: Tag, name: str) -> str:
    value = tag.get(name)
    if isinstance(value, list):
        return " ".join(value)
    return value or ""


def _is_noteref(tag: Tag) -> bool:
    """Referencia en el texto a una nota al pie: se elimina (decisión 6)."""
    if tag.name == "a":
        if "noteref" in _attr(tag, "epub:type") or "doc-noteref" in _attr(tag, "role"):
            return True
    if tag.name == "sup":
        text = tag.get_text(strip=True)
        if tag.find("a") is not None and _NOTE_MARK_RE.match(text or ""):
            return True
    return False


def _is_note_container(tag: Tag) -> bool:
    """Cuerpo de una nota al pie o final: se sustituye por su marca."""
    ept = _attr(tag, "epub:type")
    role = _attr(tag, "role")
    return any(k in ept for k in ("footnote", "endnote", "rearnote")) or any(
        k in role for k in ("doc-footnote", "doc-endnote")
    )


def _inline_parts(el: Tag, plain: list[str], marked: list[str]) -> None:
    for child in el.children:
        if isinstance(child, NavigableString):
            text = str(child)
            plain.append(text)
            marked.append(escape(text, quote=False))
        elif isinstance(child, Tag):
            if child.name in _SKIP_TAGS or child.name in ("img", "image", "svg"):
                continue
            if _is_noteref(child):
                continue
            if child.name == "br":
                plain.append(" ")
                marked.append(" ")
                continue
            keep = child.name in _INLINE_KEEP
            if keep:
                marked.append(f"<{child.name}>")
            _inline_parts(child, plain, marked)
            if keep:
                marked.append(f"</{child.name}>")


def _inline(el: Tag) -> tuple[str, str]:
    plain_parts: list[str] = []
    marked_parts: list[str] = []
    _inline_parts(el, plain_parts, marked_parts)
    plain = re.sub(r"\s+", " ", "".join(plain_parts)).strip()
    marked = re.sub(r"\s+", " ", "".join(marked_parts)).strip()
    return plain, marked


class _ChapterBuilder:
    def __init__(self) -> None:
        self.blocks: list[Block] = []

    def _emit_paragraph(self, el: Tag) -> None:
        for _ in el.find_all(["img", "image", "svg"]):
            self.blocks.append(Block(Kind.MARKER, MARK_IMAGE))
        plain, marked = _inline(el)
        if plain:
            self.blocks.append(Block(Kind.PARAGRAPH, plain, marked))

    def _walk_list(self, el: Tag) -> None:
        for li in el.find_all("li", recursive=False):
            nested = li.find_all(["ul", "ol"], recursive=False)
            for sub in nested:
                sub.extract()
            self._emit_paragraph(li)
            for sub in nested:
                self._walk_list(sub)

    def walk(self, el: Tag) -> None:
        for child in el.children:
            if not isinstance(child, Tag):
                continue
            name = (child.name or "").lower()
            if name in _SKIP_TAGS:
                continue
            if _is_note_container(child):
                self.blocks.append(Block(Kind.MARKER, MARK_NOTE))
                continue
            if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                plain, marked = _inline(child)
                if plain:
                    self.blocks.append(
                        Block(Kind.HEADING, plain, marked, level=int(name[1]))
                    )
            elif name == "table":
                self.blocks.append(Block(Kind.MARKER, MARK_TABLE))
            elif name in ("img", "image", "svg"):
                self.blocks.append(Block(Kind.MARKER, MARK_IMAGE))
            elif name in ("ul", "ol"):
                self._walk_list(child)
            elif name in ("p", "dt", "dd", "pre", "figcaption"):
                self._emit_paragraph(child)
            else:
                # Contenedor (div, section, blockquote, figure…): si dentro hay
                # estructura de bloques se desciende; si solo hay texto e
                # inline, es de facto un párrafo.
                if child.find(_BLOCKISH) is not None:
                    self.walk(child)
                else:
                    self._emit_paragraph(child)


def extract_epub(path: Path) -> Document:
    doc = Document(format="EPUB")
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise BilingueError(f"«{path.name}» no es un EPUB válido (zip corrupto).") from exc

    with zf:
        try:
            container = etree.fromstring(zf.read("META-INF/container.xml"))
            rootfile_el = container.find(".//c:rootfile", _CONTAINER_NS)
            if rootfile_el is None:
                raise KeyError("rootfile")
            opf_path = rootfile_el.get("full-path", "")
            opf = etree.fromstring(zf.read(opf_path))
        except (KeyError, etree.XMLSyntaxError) as exc:
            raise BilingueError(
                f"«{path.name}» no es un EPUB válido (falta o no se puede leer el OPF)."
            ) from exc

        manifest = {
            item.get("id"): item.get("href")
            for item in opf.findall(".//opf:manifest/opf:item", _OPF_NS)
        }
        opf_dir = posixpath.dirname(opf_path)
        spine = opf.findall(".//opf:spine/opf:itemref", _OPF_NS)
        if not spine:
            raise BilingueError(f"«{path.name}»: el EPUB no tiene spine (sin contenido).")

        for itemref in spine:
            if (itemref.get("linear") or "yes").lower() == "no":
                continue
            href = manifest.get(itemref.get("idref") or "")
            if not href:
                continue
            full = posixpath.normpath(posixpath.join(opf_dir, unquote(href)))
            try:
                data = zf.read(full)
            except KeyError:
                doc.warnings.append(
                    f"EPUB: el documento «{href}» aparece en el spine pero no está en el zip; se omite."
                )
                continue

            soup = BeautifulSoup(data, "lxml")
            body = soup.body or soup
            builder = _ChapterBuilder()
            builder.walk(body)
            if not builder.blocks:
                continue
            first_heading = next(
                (b.text for b in builder.blocks if b.kind is Kind.HEADING), None
            )
            title = first_heading or Path(unquote(href)).stem
            doc.chapters.append(Chapter(title=title, blocks=builder.blocks))

    if not doc.chapters:
        raise BilingueError(f"«{path.name}»: no se ha encontrado texto en el EPUB.")
    return doc
