# Instrucciones para Claude

Este repo es un generador de motion graphics. El usuario pide animaciones en lenguaje natural
("pon un título que diga X en el segundo 3 con la palabra Y en amarillo", "una flecha señalando
la torre", "subtítulos con este .srt"); tu trabajo es traducir eso a un guion YAML y renderizarlo.

Estilo preferido del usuario: **explicativo/documental** (ver `ejemplos/explicativo.yaml`):
fondo blanco o `rojo-doc`, tipografía `barlow` en mayúsculas, texto gris (`gris-claro`) palabra
por palabra para la narración, ilustraciones de línea negra con acento rojo, cámara con zoom/paneo
y transición `fondo` con `entrada_estilo: v`. Ilustraciones nuevas: SVG en `animaciones/recursos/`
con trazo #111 de 6-7 px, puntas redondas, relleno blanco y acentos #D0161B.

El editor visual vive en `editor/index.html` (un solo archivo, JS sin dependencias salvo mp4-muxer;
sin `<html>/<head>` porque se publica como Artifact en https://claude.ai/artifact/47vks5cDGMpc4SqoDTx5hV;
`python -m animaciones --editor` lo sirve localmente). Plantillas en `PLANTILLAS`, ilustraciones en `ILUS`.

Flujo con el motor YAML:
1. Escribe/edita el guion en `guiones/<nombre>.yaml` (ver `README.md` para el catálogo y
   `ejemplos/demo.yaml` como referencia de todas las opciones).
2. Revisa con vistas previas antes del render completo:
   `python -m animaciones guiones/x.yaml --cuadro <segundo> -o /tmp/prev.png` y mira el PNG.
   Si no hay video, añade `--fondo "#333333"` para ver el texto blanco.
3. Renderiza: sin `video:` → `.mov` transparente; con `video:` → `.mp4` final.
   Si el usuario edita en celular, ofrécele `-o x.mp4` (fondo verde para croma).

Convenciones del código: todo en español (nombres, comentarios, opciones del YAML).
Los efectos viven en `animaciones/efectos.py`; uno nuevo es una clase con `dibujar(lienzo, t)`
(t = segundos desde su `inicio`) registrada en `TIPOS` (o `TIPOS_VIDEO` con `transformar(t)`).
Tamaños en "px de un video de 1080" multiplicados por `self.u`.
