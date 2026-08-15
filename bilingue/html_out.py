"""Salida HTML: tabla bilingüe de dos columnas con CSS embebido (decisión 4).

Un único fichero `<original>.bilingue.html` junto al de entrada. Original a
la izquierda (conservando <i>/<b>/<em>/<strong>), traducción a la derecha en
texto plano; encabezados y marcas de omisión como filas a ancho completo.
CSS para pantalla e impresión (el navegador lo pasa a PDF). Sin fechas ni
datos volátiles: misma entrada → mismo fichero.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from bilingue.model import Document, Kind

_CSS = """
:root {
  --tinta: #1c1b18;
  --tinta-suave: #6d675e;
  --borde: #ddd6c9;
  --fondo: #faf8f3;
}
* { box-sizing: border-box; }
body {
  font-family: Georgia, "Times New Roman", serif;
  color: var(--tinta);
  background: var(--fondo);
  line-height: 1.55;
  margin: 2.5rem auto;
  max-width: 72rem;
  padding: 0 1.25rem;
}
header { margin-bottom: 1.75rem; }
header h1 { font-size: 1.6rem; margin: 0 0 .25rem; }
header .meta { color: var(--tinta-suave); font-size: .9rem; margin: 0; }
table { width: 100%; border-collapse: collapse; }
col.col-mitad { width: 50%; }
thead th {
  text-align: left;
  font-size: .8rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--tinta-suave);
  border-bottom: 2px solid var(--tinta);
  padding: 0 .9rem .35rem 0;
}
thead th + th { padding: 0 0 .35rem .9rem; }
td {
  vertical-align: top;
  border-top: 1px solid var(--borde);
  padding: .5rem .9rem .5rem 0;
}
td + td { border-left: 1px solid var(--borde); padding: .5rem 0 .5rem .9rem; }
tr.fila-encabezado td {
  border-top: none;
  padding: 1.9rem 0 .45rem;
}
tr.fila-encabezado + tr td { border-top: 2px solid var(--tinta); }
.enc-orig { display: block; font-weight: bold; }
.enc-trad { display: block; color: var(--tinta-suave); }
tr.nivel-1 .enc-orig { font-size: 1.45rem; }
tr.nivel-1 .enc-trad { font-size: 1.15rem; }
tr.nivel-2 .enc-orig { font-size: 1.25rem; }
tr.nivel-2 .enc-trad { font-size: 1.05rem; }
tr.nivel-3 .enc-orig, tr.nivel-4 .enc-orig, tr.nivel-5 .enc-orig, tr.nivel-6 .enc-orig { font-size: 1.1rem; }
tr.fila-marca td {
  color: var(--tinta-suave);
  font-style: italic;
  text-align: center;
  font-size: .9rem;
}
@media print {
  body { background: #fff; margin: 0; max-width: none; font-size: 10.5pt; }
  tr { break-inside: avoid; }
  thead { display: table-header-group; }
  @page { margin: 16mm 13mm; }
}
"""


def _rows(doc: Document, source: str, target: str) -> list[str]:
    rows: list[str] = []
    for chapter in doc.chapters:
        for block in chapter.blocks:
            if block.kind is Kind.MARKER:
                rows.append(
                    f'<tr class="fila-marca"><td colspan="2">{escape(block.text)}</td></tr>'
                )
                continue
            original = block.html or escape(block.text)
            translated = escape(block.translation or "")
            if block.kind is Kind.HEADING:
                level = min(max(block.level, 1), 6)
                rows.append(
                    f'<tr class="fila-encabezado nivel-{level}"><td colspan="2">'
                    f'<span class="enc-orig" lang="{escape(source)}">{original}</span>'
                    f'<span class="enc-trad" lang="{escape(target)}">{translated}</span>'
                    f"</td></tr>"
                )
            else:
                rows.append(
                    f'<tr><td lang="{escape(source)}">{original}</td>'
                    f'<td lang="{escape(target)}">{translated}</td></tr>'
                )
    return rows


def write_html(
    doc: Document,
    out_path: Path,
    source: str,
    target: str,
    title: str,
    pivot: bool = False,
) -> None:
    pivot_note = " · pivote por inglés" if pivot else ""
    meta = (
        f"Edición bilingüe {escape(source.upper())} → {escape(target.upper())}"
        f"{pivot_note} · traducción local con Argos Translate"
    )
    rows = "\n".join(_rows(doc, source, target))
    html = f"""<!DOCTYPE html>
<html lang="{escape(source)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} — edición bilingüe</title>
<style>{_CSS}</style>
</head>
<body>
<header>
<h1>{escape(title)}</h1>
<p class="meta">{meta}</p>
</header>
<table>
<colgroup><col class="col-mitad"><col class="col-mitad"></colgroup>
<thead><tr><th>Original ({escape(source)})</th><th>Traducción ({escape(target)})</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8", newline="\n")
