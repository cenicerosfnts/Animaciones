# Animaciones 🎬

Motion graphics estilo creador (títulos que "explotan", subtítulos dinámicos, flechas, círculos,
pines de ubicación, contadores, transiciones, zoom de golpe, sacudidas y efectos de sonido)
generados a partir de un **guion en texto**. Tú describes lo que quieres, se escribe un `.yaml`
y el programa renderiza el video.

▶️ Mira el resultado en [`ejemplos/demo.mp4`](ejemplos/demo.mp4) (guion: [`ejemplos/demo.yaml`](ejemplos/demo.yaml)).

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

### Catálogo

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

Las fuentes incluidas (Anton, Bangers, Montserrat y Noto Color Emoji) tienen licencia OFL.
Puedes usar cualquier `.ttf` propio poniendo su ruta en `fuente:`.
