"""Punto de entrada de consola: `bilingue <fichero>` (decisión 8).

Muestra formato y volumen, pregunta idioma de origen (con el detectado como
defecto) y de destino, valida el par local-primero, traduce con barra de
progreso y checkpoint reanudable, y escribe `<original>.bilingue.html`.
Las preguntas se leen con input(), por lo que pueden alimentarse por stdin
(p. ej. en CI): `printf 'en\\nes\\n' | bilingue fichero`.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from pathlib import Path

from bilingue.model import MARK_IMAGE, MARK_NOTE, MARK_TABLE, BilingueError, Document, Kind


def _force_utf8_console() -> None:
    """Consola UTF-8 en Windows (requisito de la sección «Plataformas»)."""
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr, sys.stdin):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                try:
                    reconfigure(encoding="utf-8")
                except Exception:
                    pass


def _install_signal_handlers() -> None:
    """Trata Ctrl+Break (Windows) y SIGTERM como la interrupción de Ctrl+C,
    para que cualquier cierre ordenado deje el mensaje de reanudación."""

    def _raise_keyboard_interrupt(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    for name in ("SIGBREAK", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, _raise_keyboard_interrupt)
            except (ValueError, OSError):
                pass


def _num(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    minutes, rest = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {rest} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min"


def _ask_language(
    label: str, default: str | None, known_names: dict[str, str]
) -> str:
    from bilingue.langs import parse_language

    while True:
        prompt = f"{label} [{default}]: " if default else f"{label}: "
        try:
            answer = input(prompt)
        except EOFError:
            raise BilingueError(
                "no se pudo leer la respuesta (fin de la entrada). En uso no "
                "interactivo, alimenta las dos respuestas por stdin, por ejemplo: "
                "printf 'en\\nes\\n' | bilingue fichero"
            ) from None
        answer = answer.strip()
        if not answer and default:
            return default
        code = parse_language(answer, known_names)
        if code:
            return code
        print(
            "  No reconozco ese idioma. Escribe un código ISO 639-1 (en, es, fr…) "
            "o el nombre del idioma (p. ej. «inglés», «español»)."
        )


def _omitted_summary(doc: Document) -> str | None:
    counts = {MARK_IMAGE: 0, MARK_TABLE: 0, MARK_NOTE: 0}
    for block in doc.blocks:
        if block.kind is Kind.MARKER and block.text in counts:
            counts[block.text] += 1
    parts = []
    if counts[MARK_IMAGE]:
        parts.append(f"{counts[MARK_IMAGE]} imagen(es)")
    if counts[MARK_TABLE]:
        parts.append(f"{counts[MARK_TABLE]} tabla(s)")
    if counts[MARK_NOTE]:
        parts.append(f"{counts[MARK_NOTE]} nota(s)")
    if not parts:
        return None
    return f"elementos omitidos con marca en el HTML: {', '.join(parts)}"


def _run(path: Path) -> int:
    start = time.monotonic()
    if not path.exists():
        raise BilingueError(f"no existe el fichero «{path}».")
    if not path.is_file():
        raise BilingueError(f"«{path}» no es un fichero.")

    from bilingue.extract import extract

    doc = extract(path)
    avisos: list[str] = list(doc.warnings)

    chapters = len(doc.chapters)
    print(f"Fichero: {path.name} ({doc.format})")
    print(
        f"Volumen: {_num(doc.word_count)} palabras · {_num(doc.paragraph_count)} "
        f"párrafos · {chapters} capítulo{'s' if chapters != 1 else ''}"
    )
    for warning in doc.warnings:
        print(f"Aviso: {warning}")

    from bilingue.langs import (
        detect_source_language,
        ensure_installed,
        get_translation,
        known_language_names,
        resolve_pair,
    )

    detected = detect_source_language(doc.sample_text())
    known_names = known_language_names()
    source = _ask_language("Idioma de origen", detected, known_names)
    target = _ask_language("Idioma de destino", None, known_names)

    plan = resolve_pair(source, target)
    if plan.pivot:
        aviso_pivote = (
            f"no hay paquete directo {source}→{target}; se traduce por pivote "
            f"({source}→en→{target}), que duplica el tiempo de cómputo y puede "
            "acumular errores de dos traducciones"
        )
        print(f"Aviso: {aviso_pivote}.")
        avisos.append(aviso_pivote)
    ensure_installed(plan)

    print("Cargando el motor de traducción…")
    translation = get_translation(plan)

    from bilingue.checkpoint import Checkpoint, file_sha256
    from bilingue.translate import run_translation

    checkpoint = Checkpoint(path, file_sha256(path), source, target)
    resumed = min(checkpoint.load(), doc.translatable_count)
    if resumed:
        print(
            f"Reanudando desde el checkpoint: {_num(resumed)}/"
            f"{_num(doc.translatable_count)} bloques ya traducidos."
        )

    from tqdm import tqdm

    bar = tqdm(
        total=doc.translatable_count,
        initial=resumed,
        unit="párr.",
        dynamic_ncols=True,
    )
    try:
        run_translation(doc, translation, checkpoint, on_progress=lambda: bar.update(1))
    finally:
        bar.close()
        checkpoint.close()

    out_path = path.with_suffix(".bilingue.html")
    from bilingue.html_out import write_html

    write_html(doc, out_path, source, target, title=path.stem, pivot=plan.pivot)
    checkpoint.discard()

    omitted = _omitted_summary(doc)
    if omitted:
        avisos.append(omitted)

    print()
    print(f"Completado en {_fmt_duration(time.monotonic() - start)}.")
    print(f"  Párrafos: {_num(doc.paragraph_count)} · Palabras: {_num(doc.word_count)}")
    print(f"  HTML: {out_path}")
    if avisos:
        print("  Avisos:")
        for aviso in avisos:
            print(f"    - {aviso}")
    else:
        print("  Avisos: ninguno")
    return 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8_console()
    _install_signal_handlers()
    parser = argparse.ArgumentParser(
        prog="bilingue",
        description=(
            "Genera una edición bilingüe en HTML (dos columnas alineadas por "
            "párrafo) traduciendo localmente con Argos Translate."
        ),
    )
    parser.add_argument("fichero", help="fichero de entrada (EPUB, TXT, MD, DOCX o PDF)")
    args = parser.parse_args(argv)

    try:
        return _run(Path(args.fichero))
    except BilingueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "\nInterrumpido. El progreso queda guardado en .bilingue-cache/; "
            "relanza el mismo comando para reanudar donde quedó.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
