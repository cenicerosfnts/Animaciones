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

Ábrelo en tu computadora con:

```bash
python -m animaciones --editor
```

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
