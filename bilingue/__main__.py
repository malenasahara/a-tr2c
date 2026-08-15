"""Permite `python -m bilingue <fichero>` (imprescindible para la prueba offline en CI)."""

from bilingue.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
