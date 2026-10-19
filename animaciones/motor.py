"""Motor de render: lee un guion, dibuja cuadro por cuadro y lo codifica con ffmpeg."""
import json
import math
import os
import subprocess
import sys
import tempfile

import yaml
from PIL import Image

from . import dibujo as dj
from . import easing as ez
from . import sonidos
from .efectos import POSICIONES, TIPOS, TIPOS_VIDEO
from .explicativo import TIPOS_EXPLICATIVO

TIPOS = {**TIPOS, **TIPOS_EXPLICATIVO}

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


class Camara:
    """Cámara virtual: keyframes [{t, zoom, centro}] interpolados suavemente.

    `centro` es el punto de la pantalla (en fracción, píxeles o nombre) que queda al centro.
    """

    def __init__(self, claves, Wo, Ho):
        self.claves = []
        for c in claves or []:
            centro = c.get("centro", "centro")
            centro = POSICIONES.get(centro, (0.5, 0.5)) if isinstance(centro, str) else centro
            cx = centro[0] / Wo if abs(centro[0]) > 5 else centro[0]
            cy = centro[1] / Ho if abs(centro[1]) > 5 else centro[1]
            self.claves.append((float(c.get("t", 0)), float(c.get("zoom", 1)), cx, cy, c.get("curva", "suave")))
        self.claves.sort(key=lambda c: c[0])

    def __bool__(self):
        return bool(self.claves)

    def zoom_max(self):
        return max([c[1] for c in self.claves] or [1])

    def en(self, t):
        """(zoom, cx, cy) con cx, cy en fracción de pantalla."""
        if not self.claves:
            return 1.0, 0.5, 0.5
        if t <= self.claves[0][0]:
            return self.claves[0][1:4]
        for a, b in zip(self.claves, self.claves[1:]):
            if t < b[0]:
                k = ez.curva(b[4])((t - a[0]) / (b[0] - a[0]))
                # el zoom se interpola en escala logarítmica para que se sienta constante
                z = math.exp(math.log(a[1]) + (math.log(b[1]) - math.log(a[1])) * k)
                return z, a[2] + (b[2] - a[2]) * k, a[3] + (b[3] - a[3]) * k
        return self.claves[-1][1:4]


class Escena:
    def __init__(self, guion, carpeta="."):
        self.carpeta = carpeta
        fmt = guion.get("formato", "vertical")
        self.Wo, self.Ho = FORMATOS[fmt] if isinstance(fmt, str) else (int(fmt[0]), int(fmt[1]))
        self.camara = Camara(guion.get("camara"), self.Wo, self.Ho)
        # Con cámara dibujamos el "mundo" a más resolución para que el zoom quede nítido.
        self.k = float(guion.get("nitidez_camara", min(2.0, max(1.0, self.camara.zoom_max()))))
        self.W, self.H = int(round(self.Wo * self.k)), int(round(self.Ho * self.k))
        self.fondo = guion.get("fondo")
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
        fines = [e.fin for e in self.elementos + self.efectos_video if e.fin < 9000] or [3]
        self.duracion = float(guion.get("duracion") or dur_video or max(fines) + 0.2)

    @classmethod
    def desde_archivo(cls, ruta):
        with open(ruta, encoding="utf-8") as f:
            return cls(yaml.safe_load(f) or {}, os.path.dirname(os.path.abspath(ruta)))

    # --- dibujo -----------------------------------------------------------

    def _dibujar_capa(self, nombre, t, origen=(0.0, 0.0)):
        activos = [e for e in self.elementos if e.capa == nombre and e.activo(t)]
        if not activos:
            return None
        lienzo = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        dj.ORIGEN[:] = origen
        try:
            for e in activos:
                e.dibujar(lienzo, t - e.inicio)
        finally:
            dj.ORIGEN[:] = (0.0, 0.0)
        return lienzo

    def capa(self, t, img=None):
        """Dibuja fondos, mundo (a través de la cámara) y capa fija sobre `img` (tamaño de salida)."""
        Wo, Ho = self.Wo, self.Ho
        if img is None:
            img = Image.new("RGBA", (Wo, Ho), (0, 0, 0, 0))
        for e in self.elementos:  # los fondos se pintan directo a la resolución de salida
            if e.capa == "fondo" and e.activo(t):
                e.dibujar(img, t - e.inicio)
        z, cx, cy = self.camara.en(t)
        w, h = self.W / z, self.H / z
        x0, y0 = cx * self.W - w / 2, cy * self.H - h / 2
        # El lienzo del mundo se centra en lo que ve la cámara (puede estar fuera de 0..W, 0..H).
        origen = (x0 - (self.W - w) / 2, y0 - (self.H - h) / 2)
        mundo = self._dibujar_capa("mundo", t, origen)
        if mundo is not None:
            if abs(z - 1) < 1e-4 and abs(x0) < 0.5 and abs(y0) < 0.5 and self.k == 1:
                img.alpha_composite(mundo)
            else:
                lx, ly = x0 - origen[0], y0 - origen[1]
                img.alpha_composite(mundo.resize((Wo, Ho), Image.BICUBIC, box=(lx, ly, lx + w, ly + h)))
        fija = self._dibujar_capa("fija", t)
        if fija is not None:
            img.alpha_composite(fija if self.k == 1 else fija.resize((Wo, Ho), Image.LANCZOS))
        return img

    def transformar_video(self, img, t):
        esc, centro, dx, dy = 1.0, (self.Wo / 2, self.Ho / 2), 0.0, 0.0
        for ef in self.efectos_video:
            if ef.activo(t):
                e, c, (ox, oy) = ef.transformar(t - ef.inicio)
                esc *= e
                if e != 1 and ef.__class__.__name__ == "Zoom":
                    centro = c
                dx, dy = dx + ox, dy + oy
        if esc <= 1.0001 and not dx and not dy:
            return img
        w, h = self.Wo / esc, self.Ho / esc
        x0 = min(max(centro[0] - w / 2 + dx / esc, 0), self.Wo - w)
        y0 = min(max(centro[1] - h / 2 + dy / esc, 0), self.Ho - h)
        return img.resize((self.Wo, self.Ho), Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))

    def cuadro(self, t, base=None, fondo=None):
        fondo = fondo or self.fondo
        if base is not None:
            img = self.transformar_video(base, t).convert("RGBA")
        elif fondo:
            img = Image.new("RGBA", (self.Wo, self.Ho), dj.color(fondo))
        else:
            img = Image.new("RGBA", (self.Wo, self.Ho), (0, 0, 0, 0))
        return self.capa(t, img)

    def eventos_sonido(self):
        return sorted((e.inicio, e.sonido) for e in self.elementos + self.efectos_video if e.sonido)

    # --- render -----------------------------------------------------------

    def render(self, salida, fondo=None, sin_sonido=False, desde=0.0, hasta=None):
        ext = os.path.splitext(salida)[1].lower()
        fondo = fondo or self.fondo
        alfa = ext in (".mov", ".webm") and not self.video and not fondo
        if ext == ".mp4" and not self.video and not fondo:
            fondo = "#00FF00"  # verde para croma en apps que no leen transparencia
        hasta = min(hasta or self.duracion, self.duracion)
        n = int(round((hasta - desde) * self.fps))
        W, H = self.Wo, self.Ho

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
