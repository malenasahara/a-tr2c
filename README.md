# bilingue

Edición bilingüe en dos columnas: a partir de un libro o documento (EPUB,
TXT, MD, DOCX o PDF) genera un único fichero HTML con el texto original a la
izquierda y su traducción en paralelo a la derecha, alineados por párrafo.
La traducción se hace íntegramente en tu máquina con
[Argos Translate](https://github.com/argosopentech/argos-translate): sin
servicios externos y sin enviar el texto a ninguna parte (solo se descargan,
una única vez, los paquetes de idioma).

## Requisitos

- **Python 3.10 a 3.12** (3.13+ no vale: en macOS Intel, torch quedó
  congelado en 2.2.2 y sus ruedas llegan hasta Python 3.12).
- Windows 10/11 x64 o macOS Intel (x86_64). En otras plataformas
  probablemente funcione, pero no se prueba.
- Conexión a internet **solo** para instalar dependencias y para la primera
  traducción de cada par de idiomas (~150 MB de paquete + recursos del
  segmentador de frases). Después, todo funciona sin conexión.

## Instalación

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
- **Sin conexión**: con el par ya instalado, la app funciona 100 % offline
  (el segmentador de frases se inicializa sin descargas).

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
- **Obra derivada**: una edición bilingüe de una obra con copyright es obra
  derivada. Esta app es una herramienta general; el uso queda bajo la
  responsabilidad de quien la usa.

## Desarrollo

```bash
pip install .[test]
pytest            # e2e real: la primera vez descarga el par en→es
```

CI en GitHub Actions: prueba de extremo a extremo en `windows-latest` y
`macos-15-intel`, y prueba sin conexión (namespace de red vacío) en
`ubuntu-latest`. Ver también `SMOKE_TEST.md` para la verificación manual en
máquinas reales y `especificacion-app-bilingue.md` para las decisiones de
diseño.
