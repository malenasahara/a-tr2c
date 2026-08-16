# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller (onedir): una carpeta `dist/bilingue/` con dos
ejecutables — `bilingue` (CLI con consola) y `bilingue-gui` (sin consola en
Windows) — y un COLLECT compartido.

La pila stanza/torch/spacy queda excluida: el segmentador de la app es
MiniSBD y el import incondicional de stanza en argostranslate.sbd lo cubre
el runtime hook rthook_stanza_stub.py.

Build:  pyinstaller --noconfirm --clean packaging/bilingue.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

SPEC_DIR = Path(SPECPATH)          # .../packaging
ROOT = SPEC_DIR.parent             # raíz del repo (paquete bilingue/ como fuente)

datas = [
    # perfiles de idioma y messages.properties, cargados relativos a __file__
    *collect_data_files("langdetect"),
    # data/ de sacremoses (nonbreaking_prefixes…), cargado vía pkgutil
    *collect_data_files("sacremoses"),
]

binaries = [
    # ctranslate2 carga con ctypes TODOS los DLL de su directorio; no hay hook oficial
    *collect_dynamic_libs("ctranslate2"),
    # onnxruntime (lo usa minisbd); el hook oficial existe — cinturón y tirantes
    *collect_dynamic_libs("onnxruntime"),
]

hiddenimports = ["onnxruntime.capi._pybind_state"]

excludes = [
    # pila del segmentador stanza y satélites: nunca usados en modo MiniSBD
    "stanza",
    "torch",
    "sympy",
    "mpmath",
    "networkx",
    "spacy",
    "spacy_legacy",
    "spacy_loggers",
    "thinc",
    "blis",
    "preshed",
    "cymem",
    "murmurhash",
    "srsly",
    "catalogue",
    "confection",
    "wasabi",
    "weasel",
    "cloudpathlib",
    "smart_open",
    "emoji",
    "pydantic",
    "pydantic_core",
    "typer",
    "shellingham",
    "rich",
    "pygments",
    "jinja2",
    "markupsafe",
    "fsspec",
    # nunca presentes; por si el venv de build los arrastrara
    "IPython",
    "matplotlib",
    "scipy",
    "PIL",
]

common = dict(
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    hookspath=[],
    runtime_hooks=[str(SPEC_DIR / "rthook_stanza_stub.py")],
    noarchive=False,
)

a_cli = Analysis([str(SPEC_DIR / "entry_cli.py")], **common)
a_gui = Analysis([str(SPEC_DIR / "entry_gui.py")], **common)

pyz_cli = PYZ(a_cli.pure)
pyz_gui = PYZ(a_gui.pure)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name="bilingue",
    console=True,
    upx=False,
    strip=False,
)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="bilingue-gui",
    console=False,
    upx=False,
    strip=False,
)

coll = COLLECT(
    exe_cli,
    exe_gui,
    a_cli.binaries,
    a_cli.datas,
    a_gui.binaries,
    a_gui.datas,
    name="bilingue",
    upx=False,
    strip=False,
)
