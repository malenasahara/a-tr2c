"""GUI tkinter opcional (`bilingue-gui`), añadida por decisión del usuario
(15-08-2026) como envoltorio del mismo núcleo que la CLI: extracción,
validación del par local-primero, checkpoint reanudable y salida HTML son
idénticos. La traducción corre en un hilo de fondo; el hilo de interfaz solo
pinta progreso. Cerrar la ventana a media traducción no pierde nada: el
checkpoint queda y la siguiente ejecución (GUI o CLI) reanuda.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from bilingue.model import BilingueError, Document

_FILETYPES = [
    ("Documentos soportados", "*.epub *.txt *.md *.docx *.pdf"),
    ("Todos los ficheros", "*.*"),
]


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("bilingue — edición bilingüe en dos columnas")
        root.minsize(560, 360)

        self.path: Path | None = None
        self.doc: Document | None = None
        self.out_path: Path | None = None
        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        # Estado compartido con el hilo de trabajo; lo pinta _poll() cada 200 ms.
        self.progress = {"done": 0, "total": 0, "start": 0.0, "status": "", "error": "", "finished": False}

        frame = ttk.Frame(root, padding=12)
        frame.grid(sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Button(frame, text="Elegir fichero…", command=self.pick_file).grid(
            row=0, column=0, sticky="w"
        )
        self.file_label = ttk.Label(frame, text="(ningún fichero)")
        self.file_label.grid(row=0, column=1, columnspan=2, sticky="w", padx=8)

        self.info_label = ttk.Label(frame, text="")
        self.info_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.warn_label = ttk.Label(frame, text="", foreground="#8a6d3b", wraplength=520)
        self.warn_label.grid(row=2, column=0, columnspan=3, sticky="w")

        ttk.Label(frame, text="Idioma de origen:").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.source_box = ttk.Combobox(frame, width=28)
        self.source_box.grid(row=3, column=1, sticky="w", pady=(10, 0))

        ttk.Label(frame, text="Idioma de destino:").grid(row=4, column=0, sticky="w", pady=(4, 0))
        self.target_box = ttk.Combobox(frame, width=28)
        self.target_box.grid(row=4, column=1, sticky="w", pady=(4, 0))

        self.translate_btn = ttk.Button(
            frame, text="Traducir", command=self.start_translation, state="disabled"
        )
        self.translate_btn.grid(row=5, column=0, sticky="w", pady=12)
        self.cancel_btn = ttk.Button(
            frame, text="Cancelar", command=self.cancel, state="disabled"
        )
        self.cancel_btn.grid(row=5, column=1, sticky="w", pady=12)
        self.open_btn = ttk.Button(
            frame, text="Abrir HTML", command=self.open_html, state="disabled"
        )
        self.open_btn.grid(row=5, column=2, sticky="e", pady=12)

        self.bar = ttk.Progressbar(frame, mode="determinate")
        self.bar.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.progress_label = ttk.Label(frame, text="")
        self.progress_label.grid(row=7, column=0, columnspan=3, sticky="w")

        self.status_label = ttk.Label(frame, text="Elige un fichero para empezar.")
        self.status_label.grid(row=8, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self._fill_language_boxes()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(200, self._poll)

    # ---------- utilidades de interfaz ----------

    def _fill_language_boxes(self) -> None:
        from bilingue.langs import available_language_catalog

        catalog = available_language_catalog()
        values = [f"{code} — {name}" for code, name in sorted(catalog.items())]
        self.source_box["values"] = values
        self.target_box["values"] = values

    @staticmethod
    def _box_code(box: ttk.Combobox) -> str | None:
        from bilingue.langs import parse_language

        raw = box.get().split("—")[0]
        return parse_language(raw)

    def _set_status(self, text: str) -> None:
        self.status_label.config(text=text)

    # ---------- acciones ----------

    def pick_file(self) -> None:
        chosen = filedialog.askopenfilename(filetypes=_FILETYPES)
        if not chosen:
            return
        self.path = Path(chosen)
        self.file_label.config(text=self.path.name)
        self.info_label.config(text="Leyendo el fichero…")
        self.warn_label.config(text="")
        self.open_btn.config(state="disabled")
        self.translate_btn.config(state="disabled")
        threading.Thread(target=self._extract_worker, args=(self.path,), daemon=True).start()

    def _extract_worker(self, path: Path) -> None:
        try:
            from bilingue.extract import extract
            from bilingue.langs import detect_source_language

            doc = extract(path)
            detected = detect_source_language(doc.sample_text())
        except BilingueError as exc:
            self.root.after(0, lambda: self._extract_failed(str(exc)))
            return
        except Exception as exc:  # noqa: BLE001 — cualquier fallo debe verse en la GUI
            self.root.after(0, lambda: self._extract_failed(f"error inesperado: {exc}"))
            return
        self.root.after(0, lambda: self._extract_done(doc, detected))

    def _extract_failed(self, message: str) -> None:
        self.info_label.config(text="")
        messagebox.showerror("bilingue", message)
        self._set_status("Elige otro fichero.")

    def _extract_done(self, doc: Document, detected: str | None) -> None:
        self.doc = doc
        chapters = len(doc.chapters)
        self.info_label.config(
            text=(
                f"{doc.format} · {doc.word_count:,} palabras · "
                f"{doc.paragraph_count:,} párrafos · {chapters} capítulo"
                f"{'s' if chapters != 1 else ''}"
            ).replace(",", ".")
        )
        self.warn_label.config(text="\n".join(doc.warnings))
        if detected:
            self.source_box.set(detected)
        self.translate_btn.config(state="normal")
        self._set_status("Comprueba los idiomas y pulsa «Traducir».")

    def start_translation(self) -> None:
        if self.doc is None or self.path is None:
            return
        source = self._box_code(self.source_box)
        target = self._box_code(self.target_box)
        if not source:
            messagebox.showwarning("bilingue", "Indica el idioma de origen (código o nombre).")
            return
        if not target:
            messagebox.showwarning("bilingue", "Indica el idioma de destino (código o nombre).")
            return

        self.stop_event.clear()
        self.progress.update(
            done=0, total=self.doc.translatable_count, start=time.monotonic(),
            status="", error="", finished=False,
        )
        self.bar.config(maximum=max(self.doc.translatable_count, 1), value=0)
        self.translate_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.open_btn.config(state="disabled")
        self.worker = threading.Thread(
            target=self._translate_worker, args=(self.doc, self.path, source, target), daemon=True
        )
        self.worker.start()

    def _translate_worker(self, doc: Document, path: Path, source: str, target: str) -> None:
        state = self.progress

        def log(message: str) -> None:
            state["status"] = message

        try:
            from bilingue.checkpoint import Checkpoint, file_sha256
            from bilingue.html_out import write_html
            from bilingue.langs import ensure_installed, get_translation, resolve_pair
            from bilingue.translate import TranslationCancelled, run_translation

            log("Validando el par de idiomas…")
            plan = resolve_pair(source, target)
            if plan.pivot:
                log(
                    f"Sin paquete directo {source}→{target}: se traduce por pivote "
                    f"({source}→en→{target}); duplica el tiempo de cómputo."
                )
            ensure_installed(plan, log=log)
            log("Cargando el motor de traducción…")
            translation = get_translation(plan, log=log)

            checkpoint = Checkpoint(path, file_sha256(path), source, target)
            resumed = min(checkpoint.load(), doc.translatable_count)
            state["done"] = resumed
            if resumed:
                log(f"Reanudando desde el checkpoint: {resumed} bloques ya traducidos.")
            state["start"] = time.monotonic()
            state["resumed"] = resumed

            def on_progress() -> None:
                state["done"] += 1

            try:
                run_translation(
                    doc,
                    translation,
                    checkpoint,
                    on_progress=on_progress,
                    should_stop=self.stop_event.is_set,
                )
            except TranslationCancelled:
                checkpoint.close()
                log("Interrumpido: el progreso queda guardado; vuelve a pulsar «Traducir» para reanudar.")
                state["finished"] = True
                return
            finally:
                checkpoint.close()

            out_path = path.with_suffix(".bilingue.html")
            write_html(doc, out_path, source, target, title=path.stem, pivot=plan.pivot)
            checkpoint.discard()
            self.out_path = out_path
            log(f"Completado: {out_path.name}")
            state["finished"] = True
        except BilingueError as exc:
            state["error"] = str(exc)
            state["finished"] = True
        except Exception as exc:  # noqa: BLE001
            state["error"] = f"Error inesperado: {exc}"
            state["finished"] = True

    def _poll(self) -> None:
        state = self.progress
        done, total = state["done"], state["total"]
        if total:
            self.bar.config(value=done)
            fresh = done - state.get("resumed", 0)
            elapsed = time.monotonic() - state["start"]
            if fresh > 0 and elapsed > 0:
                rate = fresh / elapsed
                remaining = (total - done) / rate if rate > 0 else 0
                self.progress_label.config(
                    text=f"{done}/{total} párrafos · {rate:.1f} párr./s · quedan ~{int(remaining // 60)} min {int(remaining % 60)} s"
                )
            else:
                self.progress_label.config(text=f"{done}/{total} párrafos")
        if state["status"]:
            self._set_status(state["status"])
        if state["finished"]:
            state["finished"] = False
            self.cancel_btn.config(state="disabled")
            self.translate_btn.config(state="normal" if self.doc else "disabled")
            if state["error"]:
                messagebox.showerror("bilingue", state["error"])
                state["error"] = ""
            elif self.out_path is not None and self.out_path.exists():
                self.open_btn.config(state="normal")
        self.root.after(200, self._poll)

    def cancel(self) -> None:
        self.stop_event.set()
        self._set_status("Cancelando tras el párrafo en curso…")

    def open_html(self) -> None:
        if self.out_path is not None and self.out_path.exists():
            webbrowser.open(self.out_path.resolve().as_uri())

    def on_close(self) -> None:
        # El checkpoint se persiste párrafo a párrafo: cerrar nunca pierde nada.
        self.stop_event.set()
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
