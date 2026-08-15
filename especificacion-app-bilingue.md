# App CLI: edición bilingüe en dos columnas

Aplicación de línea de comandos, local y determinista, que a partir de un fichero
genera una edición bilingüe en HTML: tabla de dos columnas con el texto original
a la izquierda y su traducción en paralelo a la derecha, alineadas por párrafo.
Traducción con Argos Translate, íntegramente en la máquina del usuario, sin
servicios externos (salvo la descarga inicial de los paquetes de idioma).

Este documento adapta la especificación de la skill homónima (entrevista cerrada
el 15-08-2026) al caso de una app local. Cambios respecto a aquella: la
decisión 8 (invocación) la cambió el usuario — la app pregunta origen y destino
al inicio en vez de autodetectar en silencio —, y las decisiones 2, 7 y 9 se
adaptan al entorno local (sin contenedor, sin skills del chat, sin límite de
sesión). El resto se transfiere sin cambios.

## Decisiones

1. **Motor de traducción** — Argos Translate (librería Python `argostranslate`)
   como único motor, ejecutado localmente.
   - Por qué: una sola librería, paquetes autocontenidos con segmentación de
     frases incluida, ~100 pares de idiomas. Salida determinista: mismo fichero
     + misma versión del paquete → misma traducción.
   - Rendimiento de referencia: ~70 palabras/s medidas con 1 CPU; en una máquina
     multinúcleo escala con los hilos (CTranslate2 por debajo). Un libro de
     ~108k palabras: minutos, no horas.
   - Los paquetes (~150 MB por par) se descargan la primera vez desde el índice
     oficial (`argos-net.com`) a la caché local del usuario y **persisten**
     entre ejecuciones.
   - Decidido por: usuario.

2. **Formatos de entrada** — EPUB, TXT, MD, DOCX y PDF.
   - EPUB: documentos HTML del zip en orden de spine; parseo con lxml /
     BeautifulSoup.
   - TXT/MD: párrafos separados por línea en blanco; encabezados `#` de MD como
     encabezados.
   - DOCX: párrafos y estilos de encabezado vía `python-docx`.
   - PDF: **adaptación respecto a la skill** — fuera del chat no existe la skill
     `pdf-texto-to-markdown`, así que la app implementa su propia conversión:
     extracción de la capa de texto (PyMuPDF), párrafos por heurística de
     layout. Páginas sin capa de texto (escaneadas) se omiten con aviso; OCR
     fuera del alcance de la v1. La app avisa siempre de la menor fidelidad en
     PDF (tablas e imágenes se pierden, división en párrafos heurística).
   - Decidido por: usuario (formatos); adaptación PDF: por defecto.

3. **Unidad de alineación** — párrafo. Cada fila de la tabla es un párrafo
   original frente a su traducción; correspondencia 1:1 por construcción.
   - Por qué: la alineación por frase se desincroniza cuando la traducción funde
     o parte frases; el capítulo es demasiado grueso. Es la unidad de las
     ediciones bilingües impresas.
   - Decidido por: usuario.

4. **Formato de salida** — un único fichero HTML, junto al fichero de entrada,
   con nombre `<original>.bilingue.html`. Tabla de dos columnas con CSS embebido
   para pantalla e impresión (el navegador lo pasa a PDF). Conserva cursivas y
   negritas del original (etiquetas inline `<i>/<b>/<em>/<strong>`); en la
   columna traducida no se garantiza el formato inline (Argos traduce texto
   plano).
   - Por qué: miles de filas son triviales en HTML; generar PDF/DOCX es lento y
     frágil.
   - Decidido por: usuario.

5. **Pares de idiomas** — cualquier par que Argos resuelva: directo si existe en
   el índice, o pivote automático por inglés (X→en→Y) si no. El par pedido se
   valida antes de arrancar — **primero contra los paquetes ya instalados
   localmente; el índice online solo se consulta si falta alguno** (requisito
   sin conexión, ver abajo); si requiere pivote, la app lo
   avisa en ese momento (duplica tiempo de cómputo y acumula errores de dos
   traducciones); si el par es irresoluble, error claro con la lista de idiomas
   disponibles.
   - Decidido por: usuario.

6. **Elementos no textuales** — los encabezados (capítulos, secciones) se
   traducen y se emiten como filas que abarcan las dos columnas; imágenes,
   tablas y notas al pie se omiten dejando marca visible (`[imagen omitida]`,
   `[tabla omitida]`, `[nota omitida]`).
   - Por qué: son imprescindibles para navegar y traducirlos es gratis; imágenes
     y tablas rompen la maqueta de dos columnas; las notas exigirían doble
     sistema de anclas. Riesgo asumido: pérdida de información en ensayo técnico
     con tablas esenciales.
   - Decidido por: usuario.

7. **Progreso e interrupción** — *(adaptada al entorno local)* barra de progreso
   en consola (párrafos traducidos / totales, velocidad, tiempo restante) y
   checkpoint simple en disco: los capítulos ya traducidos se guardan en un
   directorio de caché junto al fichero (`.bilingue-cache/`, JSONL por capítulo,
   ligado al hash del fichero y al par de idiomas). Si la ejecución se
   interrumpe (Ctrl+C, cierre), relanzar el mismo comando reanuda donde quedó;
   al completar, la caché se borra. Sin flags: la reanudación es automática.
   - Por qué: sustituye al esquema de checkpoint + zip re-adjuntable de la
     skill, que solo existía porque el contenedor del chat muere entre
     sesiones. En local el proceso vive lo que haga falta; el checkpoint queda
     como seguro barato contra interrupciones.
   - Decidido por: por defecto (adaptación de una decisión del usuario).

8. **Invocación** — `bilingue <fichero>`. El fichero es el único argumento. Al
   arrancar, la app muestra formato detectado y volumen (palabras, capítulos) y
   **pregunta interactivamente**: primero el idioma de origen, después el de
   destino. La pregunta de origen lleva como valor por defecto el idioma
   detectado del texto (pulsar Enter lo acepta); la de destino no lleva
   defecto. Ambas respuestas se validan contra el índice de Argos (códigos ISO
   639-1 o nombre del idioma). Sin más parámetros ni flags en v1.
   - Por qué: decisión explícita del usuario — la app debe preguntar origen y
     destino al inicio (sustituye a la autodetección silenciosa de la skill).
     El defecto detectado en origen conserva la comodidad sin quitar el
     control.
   - Decidido por: usuario (preguntar ambos); defecto detectado en origen: por
     defecto.

9. **Entregables** — al completar: el HTML bilingüe junto al fichero de entrada
   y un resumen final en consola (párrafos, palabras, tiempo, ruta del HTML,
   avisos acumulados: pivote, PDF, elementos omitidos). Sin parciales: en local
   el checkpoint de la decisión 7 ya cubre la interrupción.
   - Decidido por: por defecto (adaptación de una decisión del usuario).

## Funcionamiento sin conexión (requisito)

Tras el aprovisionamiento inicial con internet (dependencias pip + paquetes
Argos del par + recursos del segmentador, que se descargan en la primera
traducción), la app debe funcionar 100 % offline. Dos implicaciones verificadas
empíricamente el 15-08-2026 (traducción probada en un namespace de red vacío):

- El segmentador de frases stanza, que `argostranslate` usa por debajo, intenta
  descargar `resources.json` de raw.githubusercontent.com en **cada arranque de
  proceso** y rompe sin red aunque todo esté cacheado. La app debe inicializarlo
  sin descargas, parcheando antes de importar el traductor:

  ```python
  import stanza, functools
  import argostranslate.sbd as sbd
  sbd.stanza.Pipeline = functools.partial(stanza.Pipeline, download_method=None)
  ```

  Verificado: con este parche la traducción en→de funciona sin ninguna conexión.

- La validación del par (decisión 5) es local-primero. Sin red y con el par
  instalado: arranca sin tocar la red. Sin red y con el par ausente: error claro
  pidiendo conexión para la descarga inicial.

## Plataformas (requisito)

La app debe funcionar en **Windows 10/11 x64** y **macOS Intel (x86_64)**.
Restricciones verificadas contra PyPI el 15-08-2026:

- **Python 3.10–3.12** (no 3.13+): en macOS Intel, torch quedó congelado en
  2.2.2 (última versión con ruedas x86_64; lo arrastra `stanza`, dependencia de
  `argostranslate`) y sus ruedas llegan hasta cp312.
- **`ctranslate2>=4.8,<5`** fijado explícitamente: las 4.4–4.5 no publican
  ruedas macOS x86_64; la 4.8.1 sí, y también win_amd64. En Windows no hay
  restricciones añadidas.
- Código portable: rutas con `pathlib` (nunca separadores literales), sin
  llamadas específicas de un OS, salida de consola forzada a UTF-8 en Windows
  (`sys.stdout.reconfigure(encoding="utf-8")`) y sin dependencias de
  compilación (todas las binarias tienen rueda en ambas plataformas;
  `langdetect` es sdist pero Python puro).
- La prueba sin conexión no puede usar `unshare` (solo Linux): se hace
  desactivando la red del sistema o del adaptador.

## Requisitos técnicos

- Python 3.10–3.12 (techo por macOS Intel, ver «Plataformas»). Dependencias:
  `argostranslate`, `ctranslate2>=4.8,<5` (pin explícito), `lxml`,
  `beautifulsoup4`, `python-docx`, `pymupdf`, `tqdm`, y un detector de idioma
  ligero (`langdetect` o equivalente) solo para el defecto de la pregunta de
  origen.
- Estructura: paquete `bilingue/` con `pyproject.toml` y entry point de consola
  `bilingue`; README breve (instalación, uso, limitaciones).
- Prueba mínima incluida: ejecución de extremo a extremo con un fichero corto
  que verifique nº de filas = nº de párrafos, encabezados a ancho completo y
  marcas de omisión presentes.
- Proceso: desarrollo sobre repositorio Git alojado en GitHub, con CI en
  GitHub Actions que ejecute en cada push la prueba de extremo a extremo en
  `windows-latest` y `macos-15-intel` (última etiqueta estándar x86_64,
  disponible hasta agosto de 2027) y la prueba sin conexión en `ubuntu-latest`
  (`unshare`), cacheando el paquete Argos entre ejecuciones. Las preguntas
  interactivas de la decisión 8 deben poder alimentarse por stdin para ser
  automatizables en CI.

## Abierto

Nada.

## Rechazado

- **Autodetección silenciosa del origen (diseño de la skill)** — el usuario la
  sustituyó por pregunta interactiva de origen y destino al inicio.
- **Checkpoint exportable como zip re-adjuntable** — solo tenía sentido en el
  contenedor del chat, que se borra entre sesiones.
- **Entregables parciales por tandas** — mismo motivo; en local basta barra de
  progreso + checkpoint automático.
- **Reutilizar la skill `pdf-texto-to-markdown` para PDF** — no existe fuera del
  chat; la app implementa su propia extracción de capa de texto.
- **OCR de PDFs escaneados** — fuera del alcance de la v1; las páginas sin capa
  de texto se omiten con aviso.
- **GUI** — es una CLI; una interfaz gráfica multiplica el alcance sin cambiar
  el resultado.
- **Flags y parámetros opcionales** — diseño especulativo; se añaden si aparece
  la necesidad.
- **Claude/DeepL como motor, alineación por frase, salida PDF/DOCX, conservar
  imágenes/tablas/notas** — rechazados en la entrevista original por los
  motivos allí recogidos; siguen vigentes.

## Nota factual

Una edición bilingüe de una obra con copyright es obra derivada. La app es una
herramienta general; el uso queda bajo la responsabilidad del usuario.
