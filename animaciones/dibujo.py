"""Utilidades de dibujo: colores, fuentes, sprites de texto y composición."""
import math
import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CARPETA_FUENTES = os.path.join(os.path.dirname(__file__), "fuentes")

COLORES = {
    "blanco": "#FFFFFF",
    "negro": "#000000",
    "amarillo": "#FFD60A",
    "rojo": "#FF3B30",
    "azul": "#0A84FF",
    "celeste": "#64D2FF",
    "verde": "#30D158",
    "rosa": "#FF2D95",
    "naranja": "#FF9F0A",
    "morado": "#BF5AF2",
    "gris": "#8E8E93",
}

# nombre -> (archivo, variación de peso o None)
FUENTES = {
    "anton": ("Anton-Regular.ttf", None),
    "bangers": ("Bangers-Regular.ttf", None),
    "montserrat": ("Montserrat.ttf", "Black"),
    "montserrat-bold": ("Montserrat.ttf", "Bold"),
    "montserrat-medium": ("Montserrat.ttf", "Medium"),
}


def color(valor, alfa=255):
    """Convierte 'amarillo', '#FFD60A' o [r, g, b(, a)] a una tupla RGBA."""
    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        v = tuple(int(c) for c in valor)
        return v if len(v) == 4 else v + (alfa,)
    valor = COLORES.get(str(valor).lower(), str(valor))
    h = valor.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4, 6))
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (alfa,)


@lru_cache(maxsize=64)
def fuente(nombre, tam):
    nombre = (nombre or "anton").lower()
    tam = max(1, int(round(tam)))
    if nombre in FUENTES:
        archivo, peso = FUENTES[nombre]
        f = ImageFont.truetype(os.path.join(CARPETA_FUENTES, archivo), tam)
        if peso:
            f.set_variation_by_name(peso)
        return f
    return ImageFont.truetype(nombre, tam)  # ruta a un .ttf/.otf propio


def sombra(img, desplazamiento=(0, 8), desenfoque=12, col=(0, 0, 0, 160)):
    """Devuelve img con una sombra suave detrás (agranda el lienzo)."""
    dx, dy = int(desplazamiento[0]), int(desplazamiento[1])
    desenfoque = int(desenfoque)
    m = desenfoque * 2 + max(abs(dx), abs(dy))
    w, h = img.size
    base = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    alfa = img.getchannel("A")
    capa = Image.new("RGBA", img.size, col)
    capa.putalpha(alfa.point(lambda a: a * col[3] // 255))
    base.paste(capa, (m + dx, m + dy), capa)
    if desenfoque:
        base = base.filter(ImageFilter.GaussianBlur(desenfoque))
    base.alpha_composite(img, (m, m))
    return base


def texto(contenido, nombre_fuente="anton", tam=120, relleno="blanco", borde="negro",
          ancho_borde=None, sombra_on=True, ss=2):
    """Sprite RGBA de un texto con borde y sombra. ss = supermuestreo para bordes suaves."""
    f = fuente(nombre_fuente, tam * ss)
    if ancho_borde is None:
        ancho_borde = max(2, tam // 14)
    bw = int(ancho_borde * ss) if borde else 0
    caja = f.getbbox(contenido, stroke_width=bw)
    # Alto fijo por fuente/tamaño (acentos y descendentes incluidos) para que todas
    # las palabras compartan línea base al acomodarlas una junto a otra.
    ref = f.getbbox("ÁÑHgjy", stroke_width=bw)
    caja = (caja[0], min(caja[1], ref[1]), caja[2], max(caja[3], ref[3]))
    w, h = caja[2] - caja[0] + 4 * ss, caja[3] - caja[1] + 4 * ss
    img = Image.new("RGBA", (max(1, w), max(1, h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((-caja[0] + 2 * ss, -caja[1] + 2 * ss), contenido, font=f, fill=color(relleno),
           stroke_width=bw, stroke_fill=color(borde) if borde else None)
    if ss != 1:
        img = img.resize((max(1, w // ss), max(1, h // ss)), Image.LANCZOS)
    if sombra_on:
        img = sombra(img, (0, max(2, tam // 18)), max(2, tam // 12))
    return img


def caja_redondeada(w, h, radio, relleno, borde=None, ancho_borde=0, ss=2):
    img = Image.new("RGBA", (int(w * ss), int(h * ss)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], radius=int(radio * ss),
                        fill=color(relleno), outline=color(borde) if borde else None,
                        width=int(ancho_borde * ss))
    return img.resize((max(1, int(w)), max(1, int(h))), Image.LANCZOS)


def con_opacidad(img, opacidad):
    if opacidad >= 0.999:
        return img
    img = img.copy()
    a = img.getchannel("A").point(lambda v: int(v * max(0.0, opacidad)))
    img.putalpha(a)
    return img


def pegar(lienzo, sprite, centro, escala=1.0, rotacion=0.0, opacidad=1.0, ancla=(0.5, 0.5)):
    """Pega un sprite en el lienzo con escala, rotación (grados) y opacidad.

    `ancla` indica qué punto del sprite cae sobre `centro` (0.5, 0.5 = su centro).
    """
    sx, sy = escala if isinstance(escala, (list, tuple)) else (escala, escala)
    if sx <= 0.01 or sy <= 0.01 or opacidad <= 0.003:
        return
    s = sprite
    if abs(sx - 1) > 1e-3 or abs(sy - 1) > 1e-3:
        s = s.resize((max(1, int(s.width * sx)), max(1, int(s.height * sy))), Image.BICUBIC)
    ax, ay = ancla[0] * s.width, ancla[1] * s.height
    if abs(rotacion) > 0.05:
        # Rotamos alrededor del ancla: calculamos dónde queda tras expandir el lienzo.
        cx, cy = s.width / 2, s.height / 2
        r = s.rotate(rotacion, resample=Image.BICUBIC, expand=True)
        ang = math.radians(-rotacion)
        dx, dy = ax - cx, ay - cy
        ax = r.width / 2 + dx * math.cos(ang) - dy * math.sin(ang)
        ay = r.height / 2 + dx * math.sin(ang) + dy * math.cos(ang)
        s = r
    s = con_opacidad(s, opacidad)
    x, y = int(round(centro[0] - ax)), int(round(centro[1] - ay))
    # alpha_composite no acepta destinos negativos: recortamos a mano.
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(lienzo.width, x + s.width), min(lienzo.height, y + s.height)
    if x1 <= x0 or y1 <= y0:
        return
    trozo = s.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    lienzo.alpha_composite(trozo, (x0, y0))


class Pincel:
    """Capa supermuestreada para dibujar trazos con antialias en una región del lienzo."""

    def __init__(self, lienzo, caja, ss=3):
        x0, y0, x1, y1 = [int(v) for v in caja]
        self.lienzo = lienzo
        self.x0, self.y0 = max(0, x0), max(0, y0)
        self.x1, self.y1 = min(lienzo.width, x1), min(lienzo.height, y1)
        self.ss = ss
        self.vacio = self.x1 <= self.x0 or self.y1 <= self.y0
        w, h = max(1, self.x1 - self.x0), max(1, self.y1 - self.y0)
        self.img = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def p(self, punto):
        return ((punto[0] - self.x0) * self.ss, (punto[1] - self.y0) * self.ss)

    def linea(self, puntos, col, ancho):
        if len(puntos) < 2:
            return
        pts = [self.p(q) for q in puntos]
        a = ancho * self.ss
        self.d.line(pts, fill=color(col), width=int(a), joint="curve")
        r = a / 2
        for q in (pts[0], pts[-1]):  # puntas redondas
            self.d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=color(col))

    def poligono(self, puntos, col, borde=None, ancho=0):
        self.d.polygon([self.p(q) for q in puntos], fill=color(col),
                       outline=color(borde) if borde else None, width=int(ancho * self.ss))

    def circulo(self, centro, radio, col):
        c = self.p(centro)
        r = radio * self.ss
        self.d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=color(col))

    def terminar(self, opacidad=1.0, con_sombra=False):
        if self.vacio:
            return
        img = self.img.resize((self.x1 - self.x0, self.y1 - self.y0), Image.LANCZOS)
        img = con_opacidad(img, opacidad)
        if con_sombra:
            alfa = img.getchannel("A").filter(ImageFilter.GaussianBlur(6))
            sm = Image.new("RGBA", img.size, (0, 0, 0, 0))
            sm.putalpha(alfa.point(lambda v: v * 110 // 255))
            self.lienzo.alpha_composite(sm, (self.x0, self.y0 + 4))  # Pillow recorta lo que sobresale
        self.lienzo.alpha_composite(img, (self.x0, self.y0))


@lru_cache(maxsize=32)
def emoji(caracter, tam):
    """Sprite de un emoji a color (Noto Color Emoji solo existe en 109 px; luego se escala)."""
    f = ImageFont.truetype(os.path.join(CARPETA_FUENTES, "NotoColorEmoji.ttf"), 109)
    img = Image.new("RGBA", (300 * max(1, len(caracter)), 200), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((20, 20), caracter, font=f, embedded_color=True)
    caja = img.getbbox()
    if not caja:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    img = img.crop(caja)
    k = tam / img.height
    img = img.resize((max(1, int(img.width * k)), max(1, int(tam))), Image.LANCZOS)
    return sombra(img, (0, max(2, int(tam) // 20)), max(2, int(tam) // 14))
