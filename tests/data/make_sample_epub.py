"""Genera `sample-en.epub`: EPUB sintético mínimo para las pruebas.

Tres capítulos con encabezado, una imagen (PNG de 1×1), una tabla y una nota
al pie con su referencia, para verificar filas a ancho completo y marcas de
omisión. El zip se escribe con fecha fija para que el fichero sea reproducible.

Verdad de referencia (usada por los tests):
  - 7 párrafos, 3 encabezados
  - 1 [imagen omitida], 1 [tabla omitida], 1 [nota omitida]
"""

from __future__ import annotations

import base64
import zipfile
from pathlib import Path

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">urn:uuid:6c1f30e2-5a55-4f47-9d6a-sample-voyage</dc:identifier>
    <dc:title>The Sample Voyage</dc:title>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">2026-08-15T00:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="c1" href="chap1.xhtml" media-type="application/xhtml+xml"/>
    <item id="c2" href="chap2.xhtml" media-type="application/xhtml+xml"/>
    <item id="c3" href="chap3.xhtml" media-type="application/xhtml+xml"/>
    <item id="px" href="pixel.png" media-type="image/png"/>
  </manifest>
  <spine>
    <itemref idref="nav" linear="no"/>
    <itemref idref="c1"/>
    <itemref idref="c2"/>
    <itemref idref="c3"/>
  </spine>
</package>
"""

NAV = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Contents</title></head>
<body>
  <nav epub:type="toc">
    <ol>
      <li><a href="chap1.xhtml">Chapter One</a></li>
      <li><a href="chap2.xhtml">Chapter Two</a></li>
      <li><a href="chap3.xhtml">Chapter Three</a></li>
    </ol>
  </nav>
</body>
</html>
"""

CHAP1 = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter One</title></head>
<body>
  <h1>Chapter One: The Departure</h1>
  <p>The morning was cold, and the harbour lay under a thin veil of fog.</p>
  <p>Anne walked slowly along the pier, thinking of the <i>long</i> voyage ahead.</p>
  <p>Nobody knew, not even her <b>brother</b>, why she had chosen this ship.</p>
</body>
</html>
"""

CHAP2 = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter Two</title></head>
<body>
  <h1>Chapter Two: The Storm</h1>
  <p>On the third night the wind rose, and the sea turned against them.</p>
  <img src="pixel.png" alt="The ship in the storm"/>
  <p>By dawn the storm had passed, leaving the deck covered in salt.</p>
</body>
</html>
"""

CHAP3 = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Chapter Three</title></head>
<body>
  <h1>Chapter Three: The Arrival</h1>
  <p>The captain kept his word, as captains sometimes do.<sup><a href="#fn1">1</a></sup></p>
  <table>
    <tr><th>Day</th><th>Distance</th></tr>
    <tr><td>First</td><td>120 miles</td></tr>
    <tr><td>Second</td><td>95 miles</td></tr>
  </table>
  <p>They reached the port on a quiet Sunday morning.</p>
  <aside epub:type="footnote" id="fn1">
    <p>1. He had promised to arrive before winter.</p>
  </aside>
</body>
</html>
"""

FILES: list[tuple[str, bytes]] = [
    ("META-INF/container.xml", CONTAINER.encode("utf-8")),
    ("OEBPS/content.opf", OPF.encode("utf-8")),
    ("OEBPS/nav.xhtml", NAV.encode("utf-8")),
    ("OEBPS/chap1.xhtml", CHAP1.encode("utf-8")),
    ("OEBPS/chap2.xhtml", CHAP2.encode("utf-8")),
    ("OEBPS/chap3.xhtml", CHAP3.encode("utf-8")),
    ("OEBPS/pixel.png", PNG_1X1),
]

STAMP = (2026, 8, 15, 0, 0, 0)


def build(target: Path) -> None:
    with zipfile.ZipFile(target, "w") as zf:
        info = zipfile.ZipInfo("mimetype", date_time=STAMP)
        zf.writestr(info, b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in FILES:
            info = zipfile.ZipInfo(name, date_time=STAMP)
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)


if __name__ == "__main__":
    out = Path(__file__).parent / "sample-en.epub"
    build(out)
    print(f"Escrito {out} ({out.stat().st_size} bytes)")
