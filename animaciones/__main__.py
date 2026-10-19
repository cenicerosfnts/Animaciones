"""Uso:
    python -m animaciones guion.yaml                  -> guion.mov (transparente) o guion.mp4 (si trae video)
    python -m animaciones guion.yaml -o intro.webm    -> overlay transparente en WebM
    python -m animaciones guion.yaml -o intro.mp4     -> fondo verde para croma (o el video si lo trae)
    python -m animaciones guion.yaml --cuadro 1.2     -> vista previa PNG del segundo 1.2
    python -m animaciones --lista                     -> catálogo de animaciones
"""
import argparse
import os
import sys

from .efectos import TIPOS_VIDEO
from .motor import TIPOS, Escena


def main(argv=None):
    ap = argparse.ArgumentParser(prog="animaciones", description="Motion graphics a partir de un guion YAML.")
    ap.add_argument("guion", nargs="?", help="archivo .yaml con las animaciones")
    ap.add_argument("-o", "--salida", help="archivo de salida (.mov, .webm, .mp4 o .png)")
    ap.add_argument("--fondo", help="color de fondo (ej. verde, negro, #00FF00). Sin esto: transparente")
    ap.add_argument("--cuadro", type=float, help="renderiza solo el cuadro de ese segundo como PNG")
    ap.add_argument("--desde", type=float, default=0.0, help="renderiza a partir de este segundo")
    ap.add_argument("--hasta", type=float, help="renderiza hasta este segundo")
    ap.add_argument("--sin-sonido", action="store_true", help="no agrega efectos de sonido")
    ap.add_argument("--lista", action="store_true", help="muestra las animaciones disponibles")
    ap.add_argument("--editor", action="store_true", help="abre el editor visual en tu navegador")
    a = ap.parse_args(argv)

    if a.editor:
        return abrir_editor()

    if a.lista or not a.guion:
        print("Animaciones disponibles (tipo: descripción):")
        for nombre, cls in {**TIPOS, **TIPOS_VIDEO}.items():
            print(f"  {nombre:<11} {(cls.__doc__ or '').strip().splitlines()[0]}")
        return 0

    escena = Escena.desde_archivo(a.guion)
    base = os.path.splitext(a.guion)[0]
    if a.cuadro is not None:
        salida = a.salida or f"{base}_{a.cuadro:.2f}s.png"
        base_img = None
        if escena.video:
            import subprocess
            from PIL import Image
            vf = f"scale={escena.Wo}:{escena.Ho}:force_original_aspect_ratio=increase,crop={escena.Wo}:{escena.Ho}"
            datos = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(escena.video_inicio + a.cuadro),
                                    "-i", escena.video, "-frames:v", "1", "-vf", vf, "-f", "rawvideo",
                                    "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
            base_img = Image.frombytes("RGB", (escena.Wo, escena.Ho), datos)
        escena.cuadro(a.cuadro, base_img, a.fondo).save(salida)
    else:
        salida = a.salida or base + (".mp4" if escena.video else ".mov")
        print(f"Renderizando {escena.Wo}x{escena.Ho} @ {escena.fps:g} fps, {escena.duracion:.2f} s -> {salida}")
        escena.render(salida, a.fondo, a.sin_sonido, a.desde, a.hasta)
    print(f"Listo: {salida}")
    return 0


def abrir_editor(puerto=8765):
    """Sirve editor/index.html (que no trae <html>/<head> propios) envuelto en un documento completo."""
    import http.server
    import webbrowser

    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "editor", "index.html")

    class Manejador(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            with open(ruta, encoding="utf-8") as f:
                cuerpo = f.read()
            html = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
                    '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>'
                    + cuerpo + "</body></html>").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, *args):
            pass

    url = f"http://localhost:{puerto}/"
    print(f"Editor abierto en {url}  (Ctrl+C para cerrar)")
    webbrowser.open(url)
    http.server.ThreadingHTTPServer(("localhost", puerto), Manejador).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
