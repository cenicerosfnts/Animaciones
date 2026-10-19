# Animaciones 🎬

Motion graphics generados a partir de un **guion en texto**. Tú describes lo que quieres,
se escribe un `.yaml` y el programa renderiza el video. Dos estilos:

- **Explicativo / documental** — fondo liso, texto que aparece palabra por palabra al ritmo de
  la voz, ilustraciones de línea con acento rojo, fotos recortadas, cámara que hace zoom y se
  desplaza, transiciones de color en "V".
  ▶️ [`ejemplos/explicativo.mp4`](ejemplos/explicativo.mp4) (guion: [`ejemplos/explicativo.yaml`](ejemplos/explicativo.yaml))
- **Creador / reels** — títulos que "explotan", subtítulos dinámicos, flechas, círculos, pines,
  contadores, zoom de golpe y sacudidas.
  ▶️ [`ejemplos/demo.mp4`](ejemplos/demo.mp4) (guion: [`ejemplos/demo.yaml`](ejemplos/demo.yaml))

## Editor visual (recomendado)

`editor/index.html` es un editor de video completo en el navegador, sin instalar nada:

- **Línea de tiempo** con capas, cortar (S), recortar bordes, mover entre capas, imán, deshacer.
- **Tus medios**: importa videos, fotos, música y tu narración (se quedan en tu navegador).
- **Plantillas** estilo documental: presentación de personaje, pregunta narrada, golpe de color en V,
  escala vertical, línea del tiempo, lupa, cita, lugar en el mapa, comparación, capítulo, nota a mano…
- **Ilustraciones** con buscador que toman los colores de tu estilo y se pueden "dibujar solas";
  importa tus propios SVG.
- **Mi estilo**: paletas (Documental rojo, Museo, Noche, México…) y tipografías para todo el video.
- **Cámara virtual** con puntos de zoom/paneo, **lupa** que amplía lo que hay debajo, sonidos (pop, whoosh, ding…).
- **Claude**: describe una escena o pega tu narración y arma las animaciones (al abrirlo dentro de Claude).
- **Exportar MP4** H.264 + AAC en 720p, 1080p, 2K o 4K a 24/30/60 fps (Chrome, Edge o Safari).

### Vista app (tipo CapCut)

En el celular (o con el botón **Vista app**) el editor cambia a una app: vista previa arriba, cabezal fijo al
centro (deslizas la línea de tiempo para moverte, pellizcas para acercar), miniaturas del video y ondas de audio
en los clips, barra de herramientas abajo (Agregar, Texto, Stickers, Plantillas, Efectos, Voz, Subtítulos, IA…)
y, con un clip seleccionado: Dividir, Velocidad, Volumen, Animación, Filtros, Reemplazar, Duplicar y Borrar.
Lo que importas entra directo al video en el cabezal. En la computadora: Ctrl/⌘ + rueda para hacer zoom.

### Estructura recomendada para Reels y TikTok

1. **Avance** (1–2 s): la escena más fuerte, sin logo → plantilla *Avance al inicio*.
2. **Gancho a cámara** (2–3 s): la pregunta o el dato.
3. **Firma relámpago** (0.7 s): tu logo como golpe de transición.
4. **Historia**: un cambio visual cada 2–3 s.
5. **Remate + pregunta** para comentarios, y **cierre** corto.

En YouTube: avance de 15–30 s y firma completa de 1.8 s.

### Dónde abrirlo

| | Dentro de Claude | Tu página (GitHub Pages) o `--editor` |
|---|---|---|
| IA (asistente, nuevo video, revisión) | Automática con tu cuenta | Con tu clave de API de Anthropic (botón **IA**) |
| Grabar narración con micrófono + teleprompter | Bloqueado por Claude: usa “Grabar o elegir una nota de voz” | Sí |
| Nube (proyectos + archivos de hasta 20 MB) | Sí, en tu cuenta | No (se guarda en el navegador y con “Guardar proyecto”) |
| Exportar MP4 hasta 4K | Sí | Sí |

- **En tu computadora:** `python -m animaciones --editor`
- **Tu propia página web:** en GitHub ve a *Settings → Pages → Source: GitHub Actions*. Cada cambio en `main`
  publica el editor en `https://<usuario>.github.io/<repositorio>/` (workflow `.github/workflows/editor-pages.yml`).
  En repos privados GitHub Pages requiere un plan de pago.

### Videos de iPhone (HEVC / HDR)

Si el navegador no abre un video, conviértelo sin pérdida visible (H.264, CRF 14, misma resolución y fps; el HDR
se ajusta a SDR para que no se vea deslavado):

```bash
python -m animaciones convertir carpeta_de_clips/ -o compatibles/
```

Al importar un archivo que el proyecto ya usaba (mismo nombre y tamaño), se reconecta solo.

## Motor por línea de comandos

## Instalación

Necesitas **Python 3.9+** y **ffmpeg**.

```bash
pip install -r requirements.txt
# ffmpeg:  macOS -> brew install ffmpeg   |   Windows -> winget install ffmpeg
```

## Uso rápido

```bash
python -m animaciones ejemplos/demo.yaml               # video + animaciones -> demo.mp4
python -m animaciones ejemplos/intro_transparente.yaml # sin video -> .mov TRANSPARENTE
python -m animaciones mi_guion.yaml --cuadro 2.5       # vista previa PNG del segundo 2.5
python -m animaciones --lista                          # catálogo de animaciones
```

### Dos formas de trabajar

1. **Overlay transparente** (recomendado): el guion no lleva `video:`. Sale un `.mov`
   (ProRes 4444 con transparencia) que arrastras encima de tu clip en Premiere, Final Cut,
   DaVinci o CapCut de escritorio. Los sonidos salen aparte en `*_sonidos.wav`.
   - ¿Editas en el celular? Usa `-o intro.mp4` y sale con **fondo verde** para quitarlo con croma.
   - `-o intro.webm` también trae transparencia (útil para web).
2. **Todo en uno**: pon `video: mi_clip.mp4` en el guion y sale el `.mp4` final con las
   animaciones, el zoom/sacudidas aplicados al video y los efectos de sonido mezclados con tu audio.

## El guion

```yaml
formato: vertical        # vertical (1080x1920) | horizontal (1920x1080) | cuadrado | [ancho, alto]
fps: 30
video: mi_clip.mp4       # opcional
sonidos: true            # pop / whoosh / ding / golpe automáticos (false para quitarlos)

elementos:
  - tipo: titulo
    texto: "Esto NO lo puedo creer"
    resaltar: [creer]
    inicio: 0.2           # segundo en el que aparece
    duracion: 2.5
```

**Posiciones**: `[x, y]` en fracción de la pantalla (`[0.5, 0.5]` = centro), en píxeles, o un nombre:
`centro, arriba, abajo, izquierda, derecha, arriba-izq, arriba-der, abajo-izq, abajo-der`.
**Colores**: `blanco, negro, amarillo, rojo, azul, celeste, verde, rosa, naranja, morado, gris` o `#RRGGBB`.
**Tamaños** están pensados para un video de 1080 px de ancho y se escalan solos.
Cualquier elemento acepta `inicio`, `duracion` (o `fin`), `entrada`, `salida` y `sonido`
(`pop`, `whoosh`, `ding`, `golpe`, un `.wav` propio o `no`).

### Estilo explicativo

```yaml
formato: horizontal
fondo: blanco                  # color base de toda la escena
camara:                        # opcional: zoom y paneo con keyframes
  - {t: 2, zoom: 1.0, centro: [0.5, 0.5]}
  - {t: 4, zoom: 1.8, centro: [0.65, 0.7]}   # se acerca a ese punto entre el segundo 2 y el 4
elementos:
  - {tipo: ilustracion, recurso: hombre, ancho: 560, posicion: [0.44, 0.88], ancla: [0.5, 1.0], inicio: 0.5, fin: 6}
  - {tipo: texto, texto: "¿QUÉ CHILES ERAN LOS MÁS PICANTES?", color: gris-claro, fijo: true, posicion: [0.5, 0.15], inicio: 1, fin: 5}
  - {tipo: fondo, color: rojo-doc, entrada_estilo: v, inicio: 6}
```

| tipo | qué hace | opciones principales |
|---|---|---|
| `texto` | Texto plano palabra por palabra (o letra por letra a mano) | `texto, animacion (palabras/letras/pop/zoom/corte), ritmo (s por palabra) o tiempos: [...], fuente, tamano, color, alinear, ancho_max` |
| `ilustracion` / `imagen` | SVG de la biblioteca o tu PNG/JPG/SVG | `recurso: chile` o `archivo: foto.png`, `ancho/alto, ancla, animacion (aparecer/pop/subir/zoom/caer/corte), flotar, gris, espejo, sombra` |
| `linea` | Línea que crece, con flecha opcional | `desde, hasta, color, grosor, flecha` |
| `fondo` | Color a pantalla completa | `color, entrada_estilo (v/barrido/circulo/desvanecer/corte)`; dura hasta su `fin` |

- **Cámara**: lo que no lleva `fijo: true` se mueve con ella. Las posiciones pueden salir de la
  pantalla (`[0.5, -1.0]` está una pantalla arriba), así se arman escalas y líneas de tiempo largas.
- **Biblioteca incluida** (`animaciones/recursos/`): `hombre, chile, campana, vaso_rojo, vaso_claro,
  morron, jalapeno, habanero, fuego`. Agrega tus propios SVG ahí y úsalos con `recurso: nombre`.
- **Fuentes**: `barlow` (condensada gruesa), `barlow-bold`, `barlow-medium`, `barlow-light`, `mano`
  (escrita a mano), además de `anton`, `bangers` y `montserrat`.
- **Colores extra**: `rojo-doc`, `gris-claro`, `crema`.

### Catálogo estilo creador

| tipo | qué hace | opciones principales |
|---|---|---|
| `titulo` | Texto grande palabra por palabra | `texto, estilo (pop/golpe/deslizar/maquina), resaltar, color_resalte, caja_resalte, tamano, fuente, rotacion, posicion` |
| `subtitulos` | Subtítulos dinámicos con palabra activa resaltada | `srt: archivo.srt` o `frases: [{inicio, fin, texto}]`, `palabras_por_grupo, color_activo, tamano, posicion, acumular` |
| `cartel` | Lower third (nombre/lugar) | `titulo, subtitulo, color, fondo, posicion` |
| `dato` | Tarjeta "¿SABÍAS QUÉ?" | `titulo, texto, color, ancho, posicion` |
| `contador` | Número que sube (dinero, km, seguidores) | `desde, hasta, prefijo, sufijo, decimales, duracion_conteo, color_final` |
| `flecha` | Flecha que se dibuja sola | `desde, hasta, curva, texto, color, grosor` |
| `circulo` | Círculo a mano que encierra algo | `posicion, radio (o [rx, ry]), color, grosor, vueltas` |
| `emoji` / `sticker` | Emoji o PNG que rebota | `emoji: "🔥"` o `archivo: logo.png`, `tamano, rotacion, animacion (pop/caer)` |
| `ubicacion` | Pin que cae + nombre del lugar | `lugar, posicion (punta del pin), color` |
| `transicion` | Barrido de colores a pantalla completa | `colores: [amarillo, negro], estilo (barrido/circulo)` → **corta tu clip a la mitad** |
| `flash` | Destello | `color, intensidad` |
| `zoom` | Acercamiento al video | `factor, estilo (golpe/suave), posicion` |
| `sacudida` | Temblor de cámara | `intensidad` |

Las fuentes incluidas (Anton, Bangers, Montserrat, Barlow Condensed, Gochi Hand y Noto Color Emoji) tienen licencia OFL.
Puedes usar cualquier `.ttf` propio poniendo su ruta en `fuente:`.
