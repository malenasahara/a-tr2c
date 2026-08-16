# bilingue

Edición bilingüe en dos columnas: a partir de un libro o documento (EPUB,
TXT, MD, DOCX o PDF) genera un único fichero HTML con el texto original a la
izquierda y su traducción en paralelo a la derecha, alineados por párrafo.
La traducción se hace íntegramente en tu máquina con
[Argos Translate](https://github.com/argosopentech/argos-translate): sin
servicios externos y sin enviar el texto a ninguna parte (solo se descargan,
una única vez, los paquetes de idioma).

Hay dos formas de instalarla: el **paquete autocontenido** (sin Python, ver
[Instalación sin Python](#instalación-sin-python)) o con **pip** en un
entorno Python.

## Requisitos

- Windows 10/11 x64 o macOS Intel (x86_64) con **macOS 13 Ventura o
  posterior** (lo exigen las ruedas Intel de onnxruntime, que usa el
  segmentador de frases). En otras plataformas probablemente funcione, pero
  no se prueba.
- Solo instalación con pip: **Python 3.10 a 3.12** (3.13+ no vale: en macOS
  Intel, torch quedó congelado en 2.2.2 y sus ruedas llegan hasta
  Python 3.12).
- Conexión a internet **solo** para instalar y para la primera traducción de
  cada par de idiomas (~150 MB de paquete + el modelo del segmentador,
  ~0,2 MB por idioma). Después, todo funciona sin conexión.

## Instalación sin Python

Cada versión publica en
[Releases](https://github.com/malenasahara/a-tr2c/releases) una carpeta
autocontenida por plataforma (zip de 90–100 MB; descomprimida, ~215 MB en
Windows y ~315 MB en macOS) con dos ejecutables: `bilingue` (línea de
comandos) y `bilingue-gui` (interfaz gráfica, en Windows sin ventana de
consola).

1. Descarga el zip de tu plataforma:
   `bilingue-<versión>-windows-x64.zip` o
   `bilingue-<versión>-macos-x86_64.zip`.
2. Descomprímelo donde quieras y ejecuta `bilingue` desde una terminal (o haz
   doble clic en `bilingue-gui`).
3. Avisos de la primera ejecución, por ser binarios sin firmar:
   - **Windows (SmartScreen)**: «Más información» → «Ejecutar de todas
     formas».
   - **macOS (Gatekeeper)**: libera la cuarentena una vez, desde Terminal:
     `xattr -dr com.apple.quarantine bilingue/` (sobre la carpeta
     descomprimida).

El paquete no incluye los idiomas: la primera traducción de cada par los
descarga (~150 MB) a `~/.local/share/argos-translate` y después funciona
100 % sin conexión, igual que la instalación con pip. A diferencia de esta,
el paquete autocontenido no trae la pila stanza, así que el modo
`ARGOS_CHUNK_TYPE=STANZA` no está disponible en él.

## Instalación con pip

```bash
git clone https://github.com/malenasahara/a-tr2c.git
cd a-tr2c
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install .
```

## Uso

```text
$ bilingue mi-libro.epub
Fichero: mi-libro.epub (EPUB)
Volumen: 108.234 palabras · 2.431 párrafos · 24 capítulos
Idioma de origen [en]:        ← Enter acepta el idioma detectado
Idioma de destino: es         ← código ISO 639-1 o nombre («español», «Spanish»)
Cargando el motor de traducción…
 41%|████▏     | 1005/2455 [03:12<04:37,  5.2párr./s]
```

Al terminar deja `mi-libro.bilingue.html` junto al fichero de entrada: una
tabla de dos columnas con CSS para pantalla e impresión (desde el navegador
puedes imprimirlo o pasarlo a PDF). Las cursivas y negritas del original se
conservan en la columna izquierda.

- **Interrupción**: puedes cortar con Ctrl+C (o cerrar la consola) cuando
  quieras; el progreso queda en `.bilingue-cache/` junto al fichero. Relanzar
  el mismo comando reanuda donde quedó y, al completar, la caché se borra.
  Sin flags: todo es automático.
- **Encabezados** (capítulos, secciones) se traducen y ocupan las dos
  columnas; **imágenes, tablas y notas al pie** no se conservan: dejan una
  marca visible (`[imagen omitida]`, `[tabla omitida]`, `[nota omitida]`).
- **Pares de idiomas**: cualquiera que Argos resuelva, directo o con pivote
  automático por inglés (X→en→Y). Si hay pivote, la app lo avisa: duplica el
  tiempo de cómputo y puede acumular errores de dos traducciones.
- **Sin conexión**: con el par ya instalado, la app funciona 100 % offline.
  El segmentador de frases (MiniSBD) descarga un modelo diminuto (~0,2 MB
  por idioma) junto con el paquete del par y no vuelve a tocar la red.

### Interfaz gráfica opcional

```bash
bilingue-gui
```

Misma funcionalidad sobre el mismo núcleo: selector de fichero, idiomas con
el origen detectado preseleccionado, barra de progreso y cancelación. Cerrar
la ventana a media traducción no pierde nada (mismo checkpoint que la CLI).

## Limitaciones

- **Calidad de la traducción**: Argos Translate es traducción automática
  neuronal local; correcta para lectura de apoyo, lejos de una traducción
  editorial (y de los grandes motores en la nube). La edición bilingüe está
  pensada precisamente para leer cotejando con el original.
- **Pivote por inglés**: en pares sin paquete directo, los errores de las dos
  traducciones se acumulan.
- **PDF con menor fidelidad**: se extrae la capa de texto y la división en
  párrafos es heurística; las páginas escaneadas (sin capa de texto) se
  omiten con aviso — no hay OCR. Para libros, mejor EPUB si existe.
- **macOS Intel con pip traduce en un solo hilo** por defecto: torch y
  ctranslate2 empaquetan cada uno su runtime OpenMP y la duplicación provoca
  violaciones de segmento; con torch presente la app fija
  `OMP_NUM_THREADS=1` (más lento pero estable; se puede sobreescribir
  exportando la variable, bajo tu responsabilidad). El paquete autocontenido
  no incluye torch y traduce multihilo.
- **Obra derivada**: una edición bilingüe de una obra con copyright es obra
  derivada. Esta app es una herramienta general; el uso queda bajo la
  responsabilidad de quien la usa.

## Notas de versión

- **v0.2.0** — el segmentador de frases pasa de stanza a **MiniSBD** (ONNX,
  ~0,2 MB por idioma), lo que permite el paquete autocontenido sin la pila
  torch/stanza (~790 MB menos). Alguna traducción puede diferir de v0.1.0
  (la validación con tres corpus no encontró ninguna); sigue siendo
  determinista: misma entrada y misma versión → mismo resultado. En
  instalaciones con pip puede forzarse el modo anterior con
  `ARGOS_CHUNK_TYPE=STANZA`.
- **v0.1.0** — primera versión.

## Desarrollo

```bash
pip install .[test]
pytest            # e2e real: la primera vez descarga el par en→es
```

Para construir el paquete autocontenido de la plataforma actual:

```bash
pip install .[build]
pyinstaller --noconfirm --clean packaging/bilingue.spec   # deja dist/bilingue/
```

CI en GitHub Actions: prueba de extremo a extremo en `windows-latest` y
`macos-15-intel`, prueba sin conexión (namespace de red vacío) en
`ubuntu-latest`, y build del paquete autocontenido en ambas plataformas con
la misma suite e2e ejecutada contra el ejecutable congelado. Un push de tag
`v*` publica la GitHub Release con los dos zips. Ver también `SMOKE_TEST.md`
para la verificación manual en máquinas reales y
`especificacion-app-bilingue.md` para las decisiones de diseño.
