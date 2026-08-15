"""Checkpoint reanudable en `.bilingue-cache/` (decisión 7).

Directorio de caché junto al fichero de entrada, ligado al hash del fichero y
al par de idiomas; dentro, un JSONL por capítulo con las traducciones ya
hechas (una línea por bloque, volcada y flusheada al momento). Relanzar el
mismo comando reanuda; al completar, la caché se borra. Sin flags: todo
automático.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import IO

CACHE_DIR_NAME = ".bilingue-cache"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Checkpoint:
    def __init__(
        self, input_path: Path, file_hash: str, source: str, target: str
    ) -> None:
        self.input_path = input_path
        self.file_hash = file_hash
        self.pair = f"{source}-{target}"
        self.job_dir = (
            input_path.parent / CACHE_DIR_NAME / f"{file_hash[:12]}-{source}-{target}"
        )
        self.translations: dict[tuple[int, int], str] = {}
        self._handles: dict[int, IO[str]] = {}

    def _chapter_file(self, chapter: int) -> Path:
        return self.job_dir / f"cap-{chapter:03d}.jsonl"

    def load(self) -> int:
        """Recupera las traducciones ya hechas. Devuelve cuántas hay."""
        meta_path = self.job_dir / "meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = None
            if not meta or meta.get("sha256") != self.file_hash or meta.get("pair") != self.pair:
                # Colisión del prefijo del hash o caché corrupta: se descarta.
                shutil.rmtree(self.job_dir, ignore_errors=True)

        for chapter_file in sorted(self.job_dir.glob("cap-*.jsonl")):
            try:
                chapter = int(chapter_file.stem.split("-")[1])
            except (IndexError, ValueError):
                continue
            with chapter_file.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        self.translations[(chapter, int(entry["b"]))] = str(entry["t"])
                    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                        continue  # línea truncada por una interrupción: se ignora
        return len(self.translations)

    def _ensure_meta(self) -> None:
        self.job_dir.mkdir(parents=True, exist_ok=True)
        meta_path = self.job_dir / "meta.json"
        if not meta_path.exists():
            meta_path.write_text(
                json.dumps(
                    {
                        "fichero": self.input_path.name,
                        "sha256": self.file_hash,
                        "pair": self.pair,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    def record(self, chapter: int, block: int, translation: str) -> None:
        """Apunta una traducción y la deja ya persistida en disco."""
        self.translations[(chapter, block)] = translation
        handle = self._handles.get(chapter)
        if handle is None:
            self._ensure_meta()
            handle = self._chapter_file(chapter).open("a", encoding="utf-8")
            self._handles[chapter] = handle
        handle.write(json.dumps({"b": block, "t": translation}, ensure_ascii=False) + "\n")
        handle.flush()

    def close(self) -> None:
        for handle in self._handles.values():
            try:
                handle.close()
            except OSError:
                pass
        self._handles.clear()

    def discard(self) -> None:
        """Al completar: borra el directorio del trabajo (y `.bilingue-cache/`
        si queda vacío)."""
        self.close()
        shutil.rmtree(self.job_dir, ignore_errors=True)
        cache_root = self.job_dir.parent
        try:
            cache_root.rmdir()  # solo si está vacío
        except OSError:
            pass
