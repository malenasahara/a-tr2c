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

## 7. Paquete autocontenido (sin Python)

Verificación de los zips de la Release en máquinas sin Python ni venv.
Independiente de los pasos anteriores (usa su propia copia del TXT de
muestra; descárgalo de
`https://raw.githubusercontent.com/malenasahara/a-tr2c/main/tests/data/sample-en.txt`
o copia cualquier TXT corto en inglés).

### 7a. Windows 11

1. Descarga `bilingue-<versión>-windows-x64.zip` de la Release y
   descomprímelo (~215 MB). No actives ningún venv.
2. Si SmartScreen avisa al ejecutar: «Más información» → «Ejecutar de todas
   formas» (binario sin firmar; esperado).
3. En una terminal, dentro de la carpeta descomprimida:
   `.\bilingue.exe C:\ruta\al\sample-en.txt` — responde `en` y `es`.
   **Esperado:** igual que el paso 2 (8 párrafos, HTML junto al TXT,
   `Avisos: ninguno`); primera vez con descarga de ~150 MB si este equipo
   nunca tuvo el par en→es.
4. **Sin conexión**: borra el HTML, desactiva la Wi-Fi, repite el comando.
   **Esperado:** completa igual, sin errores. Reactiva la red.
5. **Interrupción**: con el fichero largo del paso 5, `.\bilingue.exe
   humo-largo.txt`, Ctrl+C a mitad y relanza. **Esperado:** «Reanudando
   desde el checkpoint» y HTML completo al final.
6. **GUI**: doble clic en `bilingue-gui.exe`. **Esperado:** se abre la
   ventana SIN ninguna consola detrás; traduce el TXT igual que en el
   paso 6 y «Abrir HTML» funciona.

### 7b. Mac Intel

1. Comprueba la versión del sistema: `sw_vers -productVersion` debe ser
   **13 o superior** (Ventura). Con macOS 12 o anterior el paquete no puede
   funcionar (ruedas Intel de onnxruntime); anótalo y para aquí.
2. Descarga `bilingue-<versión>-macos-x86_64.zip`, descomprímelo y libera la
   cuarentena de Gatekeeper (una sola vez):
   `xattr -dr com.apple.quarantine bilingue/`.
3. Desde Terminal: `./bilingue/bilingue /ruta/al/sample-en.txt` — responde
   `en` y `es`. **Esperado:** igual que en Windows (8 párrafos, HTML junto
   al TXT).
4. Repite los pasos 4–6 de 7a (sin conexión, interrupción, GUI; la GUI se
   lanza con `./bilingue/bilingue-gui`).
5. **Si una traducción fallara o se colgara en este Mac**: reintenta con
   `OMP_NUM_THREADS=1 ./bilingue/bilingue …` y anota la diferencia (en el
   paquete sin torch no debería hacer falta).
