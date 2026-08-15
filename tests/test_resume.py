"""Reanudación desde checkpoint (decisión 7), de forma determinista.

En lugar de matar el proceso a media traducción (frágil en CI), se siembra un
checkpoint parcial con una «traducción» centinela y se comprueba que el CLI
la reutiliza tal cual (no retraduce) y completa el resto. La interrupción
real con Ctrl+C se prueba a mano (SMOKE_TEST.md).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from bilingue.checkpoint import CACHE_DIR_NAME, Checkpoint, file_sha256

from test_e2e import DATA, parse_rows, run_cli

SENTINEL = "FAKE-RESUME-MARKER-98765"


def test_resume_uses_checkpoint(tmp_path: Path) -> None:
    source = tmp_path / "sample-en.txt"
    shutil.copy(DATA / "sample-en.txt", source)

    # Siembra: el primer bloque (capítulo 0, bloque 0) ya «traducido».
    checkpoint = Checkpoint(source, file_sha256(source), "en", "es")
    checkpoint.record(0, 0, SENTINEL)
    checkpoint.close()
    assert (tmp_path / CACHE_DIR_NAME).exists()

    result = run_cli(source)
    assert "Reanudando desde el checkpoint" in result.stdout

    html_path = tmp_path / "sample-en.bilingue.html"
    content = html_path.read_text(encoding="utf-8")
    assert SENTINEL in content, "no reutilizó la traducción del checkpoint"

    # El resto se tradujo de verdad y la caché se borró al completar.
    _, two_cell, headings, _ = parse_rows(html_path)
    assert len(two_cell) == 8
    assert len(headings) == 3
    assert not (tmp_path / CACHE_DIR_NAME).exists()
