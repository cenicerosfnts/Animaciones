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

from .efectos import TIPOS, TIPOS_VIDEO
from .motor import Escena


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
    a = ap.parse_args(argv)

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
            vf = f"scale={escena.W}:{escena.H}:force_original_aspect_ratio=increase,crop={escena.W}:{escena.H}"
            datos = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(escena.video_inicio + a.cuadro),
                                    "-i", escena.video, "-frames:v", "1", "-vf", vf, "-f", "rawvideo",
                                    "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
            base_img = Image.frombytes("RGB", (escena.W, escena.H), datos)
        escena.cuadro(a.cuadro, base_img, a.fondo).save(salida)
    else:
        salida = a.salida or base + (".mp4" if escena.video else ".mov")
        print(f"Renderizando {escena.W}x{escena.H} @ {escena.fps:g} fps, {escena.duracion:.2f} s -> {salida}")
        escena.render(salida, a.fondo, a.sin_sonido, a.desde, a.hasta)
    print(f"Listo: {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
