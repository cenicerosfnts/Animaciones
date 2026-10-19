"""Estilo explicativo / documental: fondos lisos, texto palabra por palabra, ilustraciones
de línea, fotos recortadas, líneas que crecen y cámara virtual (ver motor.Camara)."""
import io
import math
import os

from PIL import Image, ImageDraw, ImageOps

from . import dibujo as dj
from . import easing as ez
from .efectos import Elemento

CARPETA_RECURSOS = os.path.join(os.path.dirname(__file__), "recursos")


def cargar_imagen(ruta, ancho=None, alto=None):
    """Abre PNG/JPG/SVG y lo escala. Los SVG se rasterizan al tamaño exacto (nítidos con zoom)."""
    if ruta.lower().endswith(".svg"):
        import cairosvg  # solo hace falta para SVG
        kw = {"output_width": int(ancho)} if ancho else {"output_height": int(alto)} if alto else {}
        img = Image.open(io.BytesIO(cairosvg.svg2png(url=ruta, **kw))).convert("RGBA")
    else:
        img = Image.open(ruta).convert("RGBA")
    if ancho and img.width != int(ancho):
        img = img.resize((int(ancho), max(1, int(img.height * ancho / img.width))), Image.LANCZOS)
    elif alto and not ancho and img.height != int(alto):
        img = img.resize((max(1, int(img.width * alto / img.height)), int(alto)), Image.LANCZOS)
    return img


def ruta_recurso(cfg, escena):
    """`recurso: chile` busca en la biblioteca incluida; `archivo:` es relativo al guion."""
    if cfg.get("recurso"):
        nombre = cfg["recurso"]
        return os.path.join(CARPETA_RECURSOS, nombre if "." in nombre else nombre + ".svg")
    return os.path.join(escena.carpeta, cfg["archivo"])


class Texto(Elemento):
    """Texto plano que aparece palabra por palabra (o letra por letra) al ritmo de la voz."""

    entrada_defecto = 0.18
    salida_defecto = 0.25

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        self.anim = cfg.get("animacion", "palabras")
        txt = str(cfg.get("texto", ""))
        if cfg.get("mayusculas", False):
            txt = txt.upper()
        self.tam_px = self.tam("tamano", 80)
        self.nombre_f = cfg.get("fuente", "mano" if self.anim == "letras" else "barlow")
        self.col = cfg.get("color", "negro")
        f = dj.fuente(self.nombre_f, self.tam_px)
        esp = f.getlength(" ")
        ancho_max = float(cfg.get("ancho_max", 0.8)) * self.W
        alinear = cfg.get("alinear", "centro")

        # Acomodo en líneas respetando saltos manuales (\n)
        lineas = []
        for parrafo in txt.split("\n"):
            act = []
            for w in parrafo.split():
                if act and f.getlength(" ".join(act + [w])) > ancho_max:
                    lineas.append(act)
                    act = []
                act.append(w)
            lineas.append(act)

        alto_l = self.tam_px * float(cfg.get("interlineado", 1.0))
        x0, y0 = self.punto(cfg.get("posicion", "centro"))
        y0 -= alto_l * (len(lineas) - 1) / 2
        self.palabras = []  # (sprite, x_izq, y_centro, indice_global_de_letra)
        self.lineas = []    # (texto, x_izq, y_centro, primer_indice_de_letra)
        n_letra = 0
        for i, ws in enumerate(lineas):
            linea = " ".join(ws)
            ancho = f.getlength(linea)
            x = {"izquierda": x0, "derecha": x0 - ancho}.get(alinear, x0 - ancho / 2)
            y = y0 + i * alto_l
            self.lineas.append((linea, x, y, n_letra))
            for w in ws:
                spr = dj.texto(w, self.nombre_f, self.tam_px, relleno=self.col, borde=None, sombra_on=False)
                self.palabras.append((spr, x, y, n_letra))
                x += f.getlength(w) + esp
                n_letra += len(w) + 1
        self.n_letras = n_letra

        # Tiempos de aparición de cada palabra: lista explícita o ritmo constante
        ritmo = float(cfg.get("ritmo", 0.22 if self.anim == "palabras" else 0.045))
        if "tiempos" in cfg:
            self.tiempos = [float(t) for t in cfg["tiempos"]]
        else:
            self.tiempos = [i * ritmo for i in range(len(self.palabras))]
        self.ritmo = ritmo
        self.cache = {}

    def _linea_parcial(self, linea, n):
        clave = (linea, n)
        if clave not in self.cache:
            self.cache[clave] = dj.texto(linea[:n] or " ", self.nombre_f, self.tam_px,
                                         relleno=self.col, borde=None, sombra_on=False)
        return self.cache[clave]

    def dibujar(self, lienzo, t):
        op_sal = 1 - ez.salida_cubica(self.p_salida(t))
        if self.anim == "letras":
            visibles = int(t / self.ritmo) + 1
            for linea, x, y, i0 in self.lineas:
                n = max(0, min(len(linea), visibles - i0))
                if n:
                    dj.pegar(lienzo, self._linea_parcial(linea, n), (x, y), 1, 0, op_sal, ancla=(0, 0.5))
            return
        for k, (spr, x, y, _) in enumerate(self.palabras):
            ti = t - (self.tiempos[k] if k < len(self.tiempos) else self.tiempos[-1])
            if ti < 0:
                continue
            p = ez.limitar(ti / self.entrada) if self.entrada > 0 else 1
            esc, dy, op = 1.0, 0.0, ez.salida_cubica(p)
            if self.anim == "palabras":
                dy = (1 - ez.salida_cubica(p)) * self.tam_px * 0.18
            elif self.anim == "pop":
                esc = ez.salida_rebote(p, 1.8)
            elif self.anim == "zoom":
                esc = 1 + 0.25 * (1 - ez.salida_cubica(p))
            elif self.anim == "corte":
                op = 1.0
            dj.pegar(lienzo, spr, (x, y + dy), esc, 0, op * op_sal, ancla=(0, 0.5))


class Imagen(Elemento):
    """Ilustración (SVG de la biblioteca o propio) o foto recortada PNG/JPG."""

    entrada_defecto = 0.35
    salida_defecto = 0.25

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        ancho = self.tam("ancho", 0) or None
        alto = self.tam("alto", 0) or None
        if not ancho and not alto:
            ancho = 300 * self.u
        img = cargar_imagen(ruta_recurso(cfg, escena), ancho, alto)
        if cfg.get("gris"):
            a = img.getchannel("A")
            img = ImageOps.grayscale(img.convert("RGB")).convert("RGBA")
            img.putalpha(a)
        if cfg.get("espejo"):
            img = ImageOps.mirror(img)
        if cfg.get("sombra"):
            img = dj.sombra(img, (0, int(10 * self.u)), int(16 * self.u), (0, 0, 0, 90))
        self.img = img
        self.pos = self.punto(cfg.get("posicion", "centro"))
        self.anim = cfg.get("animacion", "aparecer")
        self.rot = float(cfg.get("rotacion", 0))
        self.flotar = float(cfg.get("flotar", 0)) * self.u
        self.ancla = tuple(cfg.get("ancla", (0.5, 0.5)))

    def dibujar(self, lienzo, t):
        p = self.p_entrada(t)
        q = self.p_salida(t)
        x, y = self.pos
        esc, op, rot = 1.0, ez.salida_cubica(p), self.rot
        if self.anim == "pop":
            esc = ez.salida_rebote(p, 2.0)
            op = ez.limitar(p * 3)
        elif self.anim == "subir":
            y += (1 - ez.salida_cubica(p)) * 60 * self.u
        elif self.anim == "zoom":
            esc = 1 + 0.12 * (1 - ez.salida_cubica(p))
        elif self.anim == "caer":
            y -= (1 - ez.caida_rebote(p)) * self.H * 0.3
            op = ez.limitar(p * 5)
        elif self.anim == "corte":
            op = 1.0
        if self.flotar:
            y += math.sin(t * 2.2) * self.flotar
            rot += math.sin(t * 1.7) * 1.5
        sal = self.cfg.get("salida_estilo", "desvanecer")
        if sal == "encoger":
            esc *= 1 - ez.entrada_rebote(q, 1.5)
        else:
            op *= 1 - q
        dj.pegar(lienzo, self.img, (x, y), esc, rot, op, ancla=self.ancla)


class Linea(Elemento):
    """Línea recta que crece de `desde` a `hasta`, con punta de flecha opcional."""

    entrada_defecto = 0.6
    salida_defecto = 0.2

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        self.a = self.punto(cfg.get("desde", (0.3, 0.5)))
        self.b = self.punto(cfg.get("hasta", (0.7, 0.5)))
        self.grosor = self.tam("grosor", 6)
        self.col = cfg.get("color", "rojo-doc")
        self.punta = cfg.get("flecha", True)

    def dibujar(self, lienzo, t):
        p = ez.suave(self.p_entrada(t))
        op = 1 - self.p_salida(t)
        b = (self.a[0] + (self.b[0] - self.a[0]) * p, self.a[1] + (self.b[1] - self.a[1]) * p)
        g = self.grosor
        pin = dj.Pincel(lienzo, (min(self.a[0], self.b[0]) - g * 6, min(self.a[1], self.b[1]) - g * 6,
                                 max(self.a[0], self.b[0]) + g * 6, max(self.a[1], self.b[1]) + g * 6))
        ang = math.atan2(self.b[1] - self.a[1], self.b[0] - self.a[0])
        L = g * 4.2 if self.punta else 0
        fin = (b[0] - math.cos(ang) * L * 0.6, b[1] - math.sin(ang) * L * 0.6)
        pin.linea([self.a, fin], self.col, g)
        if self.punta:
            pin.poligono([b, (b[0] - math.cos(ang - 0.45) * L, b[1] - math.sin(ang - 0.45) * L),
                          (b[0] - math.cos(ang + 0.45) * L, b[1] - math.sin(ang + 0.45) * L)], self.col)
        pin.terminar(op)


class Fondo(Elemento):
    """Fondo de color a pantalla completa. entrada_estilo: v, barrido, circulo, desvanecer o corte."""

    entrada_defecto = 0.6
    salida_defecto = 0.0
    duracion_defecto = 9999
    capa = "fondo"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        self.col = dj.color(cfg.get("color", "rojo-doc"))
        self.estilo = cfg.get("entrada_estilo", "v")

    def dibujar(self, lienzo, t):
        W, H = lienzo.size
        p = ez.suave(self.p_entrada(t)) if self.estilo != "corte" else 1.0
        op = 1 - self.p_salida(t)
        if p >= 1:
            lienzo.alpha_composite(Image.new("RGBA", (W, H), self.col[:3] + (int(255 * op),)))
            return
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        if self.estilo == "v":
            # Triángulo que baja desde el borde superior con la punta al centro y se ensancha
            ap = p * H * 2.3
            lado = max(0.0, p - 0.3) / 0.7 * H * 1.15
            d.polygon([(0, 0), (W, 0), (W, lado), (W / 2, ap), (0, lado)], fill=self.col)
        elif self.estilo == "barrido":
            d.rectangle([0, 0, W * p, H], fill=self.col)
        elif self.estilo == "circulo":
            c = self.punto(self.cfg.get("posicion", "centro"))
            c = (c[0] * W / self.W, c[1] * H / self.H)
            r = math.hypot(W, H) * p
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=self.col)
        else:  # desvanecer
            capa = Image.new("RGBA", (W, H), self.col[:3] + (int(255 * p),))
        if op < 1:
            capa = dj.con_opacidad(capa, op)
        lienzo.alpha_composite(capa)


TIPOS_EXPLICATIVO = {
    "texto": Texto,
    "imagen": Imagen,
    "ilustracion": Imagen,
    "linea": Linea,
    "fondo": Fondo,
}
