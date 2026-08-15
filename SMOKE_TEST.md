# Guion de humo (manual, máquinas reales)

Para verificar la app en tus máquinas: Windows 10/11 x64 y macOS Intel. El
runner de CI usa macOS 15; si tu Mac es anterior, este guion es la única
verificación real en esa versión. Tiempo estimado: 15–20 min (más la descarga
de ~150 MB la primera vez).

En cada paso está el resultado esperado; si algo no cuadra, apunta el paso,
el mensaje completo y la versión del sistema.

## 0. Requisitos previos

- Python 3.10, 3.11 o 3.12 (`python --version` / `python3 --version`).
  **3.13 o 3.14 no valen** (la instalación fallará al resolver torch).
  - Windows: instalador de python.org (marca «Add python.exe to PATH»).
  - macOS Intel: instalador de python.org o `brew install python@3.12`.
- Conexión a internet para los pasos 1 y 2.

## 1. Instalación limpia

```bash
git clone https://github.com/malenasahara/a-tr2c.git
cd a-tr2c
python -m venv .venv          # en macOS: python3.12 -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS
pip install .
```

**Esperado:** termina sin errores. En macOS Intel, pip debe resolver
`torch 2.2.2` (se ve en el log de pip); si intenta una torch más moderna y
falla, la versión de Python no es la correcta.

## 2. Primera traducción (con red): TXT de prueba en→es

```bash
bilingue tests/data/sample-en.txt
```

- A «Idioma de origen [en]:» pulsa **Enter** (acepta el defecto detectado).
- A «Idioma de destino:» escribe **es** (o «español»).

**Esperado:**
- Muestra `Volumen: 238 palabras · 8 párrafos · 1 capítulo`.
- Primera vez: mensaje de descarga del paquete English → Spanish (~150 MB)
  y «Preparando el segmentador de frases… (descarga única)».
- Barra de progreso hasta 11/11 y resumen final con
  `Párrafos: 8`, la ruta del HTML y `Avisos: ninguno`.
- Queda `tests/data/sample-en.bilingue.html` y **no** queda
  `tests/data/.bilingue-cache/`.

## 3. Comprobación del HTML

Abre `tests/data/sample-en.bilingue.html` en el navegador.

**Esperado:**
- Tabla de dos columnas: inglés a la izquierda, español a la derecha,
  alineados párrafo a párrafo (8 filas de texto).
- 3 encabezados a ancho completo, cada uno con su traducción debajo.
- Vista previa de impresión (Ctrl+P): la tabla se pagina sin partir filas.

## 4. Prueba sin conexión

1. Borra el HTML anterior (`tests/data/sample-en.bilingue.html`).
2. **Desactiva la Wi-Fi** (o el adaptador de red; el modo avión también vale).
3. Repite el paso 2 (mismo comando, mismas respuestas).
4. Reactiva la red.

**Esperado:** la traducción completa exactamente igual, sin ningún error ni
intento de conexión. Si algo intentara tocar la red, fallaría al instante con
la red apagada.

## 5. Interrupción con Ctrl+C y reanudación

Para que dé tiempo a interrumpir se usa un fichero más largo:

```bash
python - <<'EOF'
lines = ["# A Long Voyage", ""]
for i in range(1, 61):
    lines += [f"Paragraph number {i}. The captain looked at the horizon and "
              "wrote the log with a steady hand, while the crew argued about "
              "the weather and the cook burned the bread again.", ""]
open("humo-largo.txt", "w", encoding="utf-8").write("\n".join(lines))
EOF
bilingue humo-largo.txt        # en, es — y a mitad de la barra pulsa Ctrl+C
```

(En Windows, si no tienes heredoc: crea `humo-largo.txt` copiando 60 veces un
párrafo separado por líneas en blanco.)

**Esperado al interrumpir:** mensaje
`Interrumpido. El progreso queda guardado en .bilingue-cache/…` y existe
`.bilingue-cache/` junto al fichero.

```bash
bilingue humo-largo.txt        # otra vez: en, es
```

**Esperado al relanzar:** línea `Reanudando desde el checkpoint: N/61 bloques
ya traducidos`, la barra arranca de N, completa, deja el HTML con 60 filas de
párrafo y `.bilingue-cache/` desaparece.

## 6. (Opcional) GUI

```bash
bilingue-gui
```

**Esperado:** ventana con selector de fichero; al elegir el TXT muestra
formato y volumen y preselecciona `en` como origen; con destino `es`, el
botón «Traducir» completa con barra de progreso y «Abrir HTML» muestra el
resultado en el navegador.
