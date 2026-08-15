"""Prueba de extremo a extremo (requisito «Prueba mínima incluida»).

Ejecuta el CLI real como subproceso alimentando las preguntas por stdin y
verifica el HTML: nº de filas de dos celdas == nº de párrafos, encabezados a
ancho completo y marcas de omisión presentes. Necesita el par en→es de Argos
(en la primera ejecución se descarga, con red).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

DATA = Path(__file__).parent / "data"

# Verdad de referencia de los ficheros de muestra (ver data/).
TXT_PARAGRAPHS = 8
TXT_HEADINGS = 3
EPUB_PARAGRAPHS = 7
EPUB_HEADINGS = 3


def run_cli(input_file: Path, answers: str = "en\nes\n") -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "-m", "bilingue", str(input_file)],
        input=answers,
        capture_output=True,
        text=True,
        encoding="utf-8",
        # En CI un cuelgue no debe comerse el timeout del job entero.
        timeout=int(os.environ.get("BILINGUE_TEST_TIMEOUT", "900")),
    )
    assert result.returncode == 0, (
        f"exit={result.returncode}\n--- stdout ---\n{result.stdout}"
        f"\n--- stderr ---\n{result.stderr}"
    )
    return result


def parse_rows(html_path: Path):
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
    rows = soup.find("tbody").find_all("tr")
    two_cell = [r for r in rows if len(r.find_all("td")) == 2]
    headings = [r for r in rows if "fila-encabezado" in (r.get("class") or [])]
    markers = [r for r in rows if "fila-marca" in (r.get("class") or [])]
    return soup, two_cell, headings, markers


@pytest.fixture()
def workdir(tmp_path: Path) -> Path:
    """Copia de trabajo: no ensucia tests/data con HTML ni caché."""
    return tmp_path


def test_e2e_txt(workdir: Path) -> None:
    source = workdir / "sample-en.txt"
    shutil.copy(DATA / "sample-en.txt", source)

    result = run_cli(source)

    # La pregunta de origen muestra el idioma detectado como defecto.
    assert "Idioma de origen [en]" in result.stdout
    assert "Idioma de destino" in result.stdout

    html_path = workdir / "sample-en.bilingue.html"
    assert html_path.exists(), result.stdout

    _, two_cell, headings, markers = parse_rows(html_path)
    assert len(two_cell) == TXT_PARAGRAPHS  # nº de filas == nº de párrafos
    assert len(headings) == TXT_HEADINGS  # encabezados a ancho completo
    assert not markers
    for row in two_cell:
        cells = row.find_all("td")
        assert cells[1].get_text(strip=True), "columna traducida vacía"
    for row in headings:
        cell = row.find("td")
        assert cell.get("colspan") == "2"
        assert row.find("span", class_="enc-trad").get_text(strip=True)

    # Al completar, la caché de checkpoints se borra.
    assert not (workdir / ".bilingue-cache").exists()


def test_e2e_epub(workdir: Path) -> None:
    source = workdir / "sample-en.epub"
    shutil.copy(DATA / "sample-en.epub", source)

    run_cli(source)

    html_path = workdir / "sample-en.bilingue.html"
    assert html_path.exists()

    soup, two_cell, headings, markers = parse_rows(html_path)
    assert len(two_cell) == EPUB_PARAGRAPHS
    assert len(headings) == EPUB_HEADINGS
    marker_texts = [m.get_text(strip=True) for m in markers]
    assert marker_texts.count("[imagen omitida]") == 1
    assert marker_texts.count("[tabla omitida]") == 1
    assert marker_texts.count("[nota omitida]") == 1

    # Las cursivas y negritas del original se conservan en la columna izquierda.
    assert soup.find("td").find_parent("table").find("i") is not None
    assert soup.find("b") is not None
