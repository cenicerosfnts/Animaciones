"""Motor de render: lee un guion, dibuja cuadro por cuadro y lo codifica con ffmpeg."""
import json
import os
import subprocess
import sys
import tempfile

import yaml
from PIL import Image

from . import dibujo as dj
from . import sonidos
from .efectos import TIPOS, TIPOS_VIDEO

FORMATOS = {
    "vertical": (1080, 1920),     # Reels / TikTok / Shorts
    "horizontal": (1920, 1080),   # YouTube
    "cuadrado": (1080, 1080),
    "4k": (3840, 2160),
}


def sondear(ruta):
    """Duración y si tiene audio, usando ffprobe."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                        "-of", "json", ruta], capture_output=True, text=True, check=True)
    info = json.loads(r.stdout)
    dur = float(info["format"]["duration"])
    audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    return dur, audio


class Escena:
    def __init__(self, guion, carpeta="."):
        self.carpeta = carpeta
        fmt = guion.get("formato", "vertical")
        self.W, self.H = FORMATOS[fmt] if isinstance(fmt, str) else (int(fmt[0]), int(fmt[1]))
        self.fps = float(guion.get("fps", 30))
        self.video = os.path.join(carpeta, guion["video"]) if guion.get("video") else None
        self.video_inicio = float(guion.get("video_inicio", 0))
        self.con_sonidos = guion.get("sonidos", True)
        self.volumen_sonidos = float(guion.get("volumen_sonidos", 0.8))
        self.elementos, self.efectos_video = [], []
        for i, cfg in enumerate(guion.get("elementos", [])):
            tipo = cfg.get("tipo")
            if tipo in TIPOS:
                self.elementos.append(TIPOS[tipo](cfg, self))
            elif tipo in TIPOS_VIDEO:
                self.efectos_video.append(TIPOS_VIDEO[tipo](cfg, self))
            else:
                raise ValueError(f"Elemento #{i + 1}: tipo desconocido '{tipo}'. "
                                 f"Opciones: {', '.join(list(TIPOS) + list(TIPOS_VIDEO))}")
        self.video_audio = False
        dur_video = None
        if self.video:
            dur_video, self.video_audio = sondear(self.video)
            dur_video -= self.video_inicio
        fines = [e.fin for e in self.elementos + self.efectos_video] or [3]
        self.duracion = float(guion.get("duracion") or dur_video or max(fines) + 0.2)

    @classmethod
    def desde_archivo(cls, ruta):
        with open(ruta, encoding="utf-8") as f:
            return cls(yaml.safe_load(f) or {}, os.path.dirname(os.path.abspath(ruta)))

    # --- dibujo -----------------------------------------------------------

    def capa(self, t):
        """Capa RGBA transparente con todos los elementos activos en el segundo t."""
        lienzo = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        for e in self.elementos:
            if e.activo(t):
                e.dibujar(lienzo, t - e.inicio)
        return lienzo

    def transformar_video(self, img, t):
        esc, centro, dx, dy = 1.0, (self.W / 2, self.H / 2), 0.0, 0.0
        for ef in self.efectos_video:
            if ef.activo(t):
                e, c, (ox, oy) = ef.transformar(t - ef.inicio)
                esc *= e
                if e != 1 and ef.__class__.__name__ == "Zoom":
                    centro = c
                dx, dy = dx + ox, dy + oy
        if esc <= 1.0001 and not dx and not dy:
            return img
        w, h = self.W / esc, self.H / esc
        x0 = min(max(centro[0] - w / 2 + dx / esc, 0), self.W - w)
        y0 = min(max(centro[1] - h / 2 + dy / esc, 0), self.H - h)
        return img.resize((self.W, self.H), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))

    def cuadro(self, t, base=None, fondo=None):
        if base is not None:
            img = self.transformar_video(base, t).convert("RGBA")
        elif fondo:
            img = Image.new("RGBA", (self.W, self.H), dj.color(fondo))
        else:
            img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        img.alpha_composite(self.capa(t))
        return img

    def eventos_sonido(self):
        return sorted((e.inicio, e.sonido) for e in self.elementos + self.efectos_video if e.sonido)

    # --- render -----------------------------------------------------------

    def render(self, salida, fondo=None, sin_sonido=False, desde=0.0, hasta=None):
        ext = os.path.splitext(salida)[1].lower()
        alfa = ext in (".mov", ".webm") and not self.video and not fondo
        if ext == ".mp4" and not self.video and not fondo:
            fondo = "#00FF00"  # verde para croma en apps que no leen transparencia
        hasta = min(hasta or self.duracion, self.duracion)
        n = int(round((hasta - desde) * self.fps))
        W, H = self.W, self.H

        tmp = tempfile.mkdtemp(prefix="anim_")
        audio = None
        eventos = [] if sin_sonido or not self.con_sonidos else [(t - desde, s) for t, s in self.eventos_sonido() if desde <= t < hasta]
        if eventos:
            audio = os.path.join(tmp, "sfx.wav")
            sonidos.guardar_wav(audio, sonidos.pista(eventos, hasta - desde, self.carpeta, self.volumen_sonidos))

        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba" if alfa else "rgb24",
               "-s", f"{W}x{H}", "-r", str(self.fps), "-i", "-"]
        mapas_audio = []
        idx = 1
        if self.video and self.video_audio:
            cmd += ["-ss", str(self.video_inicio + desde), "-t", str(hasta - desde), "-i", self.video]
            mapas_audio.append(idx)
            idx += 1
        if audio:
            cmd += ["-i", audio]
            mapas_audio.append(idx)
        cmd += ["-map", "0:v"]
        if len(mapas_audio) == 2:
            cmd += ["-filter_complex", f"[{mapas_audio[0]}:a][{mapas_audio[1]}:a]amix=inputs=2:normalize=0[a]", "-map", "[a]"]
        elif mapas_audio:
            cmd += ["-map", f"{mapas_audio[0]}:a"]
        if ext == ".mov":
            cmd += ["-c:v", "prores_ks", "-profile:v", "4444" if alfa else "3",
                    "-pix_fmt", "yuva444p10le" if alfa else "yuv422p10le", "-c:a", "pcm_s16le"]
        elif ext == ".webm":
            cmd += ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p" if alfa else "yuv420p", "-b:v", "6M",
                    "-auto-alt-ref", "0", "-c:a", "libopus"]
        else:
            cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                    "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-shortest", salida] if mapas_audio else [salida]
        enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        dec = None
        if self.video:
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={self.fps}"
            dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", str(self.video_inicio + desde), "-i", self.video,
                                    "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        ultimo = None
        try:
            for i in range(n):
                t = desde + i / self.fps
                base = None
                if dec:
                    datos = dec.stdout.read(W * H * 3)
                    if len(datos) == W * H * 3:
                        ultimo = Image.frombytes("RGB", (W, H), datos)
                    base = ultimo if ultimo is not None else Image.new("RGB", (W, H))
                img = self.cuadro(t, base, fondo)
                enc.stdin.write(img.tobytes() if alfa else img.convert("RGB").tobytes())
                if i % 15 == 0 or i == n - 1:
                    sys.stderr.write(f"\r  render {i + 1}/{n} cuadros ({100 * (i + 1) // n}%)")
                    sys.stderr.flush()
        finally:
            enc.stdin.close()
            enc.wait()
            if dec:
                dec.stdout.close()
                dec.kill()
            sys.stderr.write("\n")
        if enc.returncode != 0:
            raise RuntimeError("ffmpeg falló al codificar el video")
        if audio and alfa:  # en overlays también dejamos los sonidos aparte
            import shutil
            shutil.copy(audio, os.path.splitext(salida)[0] + "_sonidos.wav")
        return salida
