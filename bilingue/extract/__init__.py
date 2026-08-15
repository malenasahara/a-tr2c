"""Extracción de texto por formato de entrada (decisión 2 de la especificación)."""

from __future__ import annotations

from pathlib import Path

from bilingue.model import BilingueError, Document

SUPPORTED = (".epub", ".txt", ".md", ".docx", ".pdf")


def extract(path: Path) -> Document:
    """Extrae el documento según la extensión del fichero.

    Los imports son perezosos: cada formato carga solo sus dependencias.
    """
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        from bilingue.extract.textmd import extract_textmd

        return extract_textmd(path)
    if suffix == ".epub":
        from bilingue.extract.epub import extract_epub

        return extract_epub(path)
    if suffix == ".docx":
        from bilingue.extract.docx import extract_docx

        return extract_docx(path)
    if suffix == ".pdf":
        from bilingue.extract.pdf import extract_pdf

        return extract_pdf(path)
    raise BilingueError(
        f"Formato no soportado: «{path.suffix or path.name}». "
        f"Formatos admitidos: {', '.join(SUPPORTED)}."
    )
