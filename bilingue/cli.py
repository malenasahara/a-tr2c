"""Punto de entrada de consola: `bilingue <fichero>`."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bilingue",
        description=(
            "Genera una edición bilingüe en HTML (dos columnas alineadas por "
            "párrafo) traduciendo localmente con Argos Translate."
        ),
    )
    parser.add_argument("fichero", help="fichero de entrada (EPUB, TXT, MD, DOCX o PDF)")
    args = parser.parse_args(argv)

    print(f"bilingue: aún en construcción ({args.fichero})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
