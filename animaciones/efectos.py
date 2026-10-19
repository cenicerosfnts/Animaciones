"""Catálogo de animaciones. Cada clase es un `tipo:` que se puede usar en el guion YAML."""
import math
import os
import re

from PIL import Image, ImageDraw, ImageFilter

from . import dibujo as dj
from . import easing as ez

POSICIONES = {
    "centro": (0.5, 0.5),
    "arriba": (0.5, 0.2),
    "abajo": (0.5, 0.78),
    "izquierda": (0.25, 0.5),
    "derecha": (0.75, 0.5),
    "arriba-izq": (0.25, 0.2),
    "arriba-der": (0.75, 0.2),
    "abajo-izq": (0.25, 0.8),
    "abajo-der": (0.75, 0.8),
}


class Elemento:
    """Base de todos los elementos que se dibujan encima del video."""

    capa = "mundo"  # mundo (se mueve con la cámara) | fija (encima, sin cámara) | fondo

    duracion_defecto = 3.0
    entrada_defecto = 0.4
    salida_defecto = 0.3
    sonido_defecto = None  # nombre de efecto de sonido que suena al entrar

    def __init__(self, cfg, escena):
        self.cfg = cfg
        self.W, self.H = escena.W, escena.H
        self.Wo, self.Ho = escena.Wo, escena.Ho
        self.u = min(self.W, self.H) / 1080  # unidad: 1 px de un video de 1080 de ancho
        self.inicio = float(cfg.get("inicio", 0))
        if "fin" in cfg:
            self.duracion = float(cfg["fin"]) - self.inicio
        else:
            self.duracion = float(cfg.get("duracion", self.duracion_defecto))
        self.entrada = float(cfg.get("entrada", self.entrada_defecto))
        self.salida = float(cfg.get("salida", self.salida_defecto))
        snd = cfg.get("sonido", self.sonido_defecto)
        self.sonido = None if snd in (False, None, "no", "ninguno") else snd
        self.capa = cfg.get("capa", "fija" if cfg.get("fijo") else self.capa)

    @property
    def fin(self):
        return self.inicio + self.duracion

    def activo(self, t):
        return self.inicio <= t < self.fin

    def p_entrada(self, t):
        return ez.limitar(t / self.entrada) if self.entrada > 0 else 1.0

    def p_salida(self, t):
        """0 mientras está en pantalla, sube a 1 durante la salida."""
        if self.salida <= 0:
            return 0.0
        return ez.limitar((t - (self.duracion - self.salida)) / self.salida)

    def punto(self, valor):
        """[x, y] en fracción de pantalla (0-1), en píxeles, o un nombre como 'arriba'."""
        if isinstance(valor, str):
            valor = POSICIONES.get(valor, POSICIONES["centro"])
        x, y = valor
        x = x * self.W if abs(x) <= 5 else x * self.W / self.Wo  # fracción de pantalla o píxeles
        y = y * self.H if abs(y) <= 5 else y * self.H / self.Ho
        return (x, y)

    def tam(self, clave, defecto):
        return float(self.cfg.get(clave, defecto)) * self.u

    def dibujar(self, lienzo, t):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def _limpiar(p):
    return re.sub(r"[^\wáéíóúüñ]", "", str(p).lower())


class Titulo(Elemento):
    """Texto grande que aparece palabra por palabra (pop, golpe, deslizar o maquina)."""

    sonido_defecto = "pop"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        txt = str(cfg.get("texto", "TEXTO"))
        if cfg.get("mayusculas", True):
            txt = txt.upper()
        self.estilo = cfg.get("estilo", "pop")
        self.retraso = float(cfg.get("retraso_palabra", 0.07))
        self.rot_grupo = float(cfg.get("rotacion", 0))
        tam = self.tam("tamano", 130)
        nombre_f = cfg.get("fuente", "anton")
        resaltar = {_limpiar(w) for w in cfg.get("resaltar", [])}
        col = cfg.get("color", "blanco")
        col_r = cfg.get("color_resalte", "amarillo")
        borde = cfg.get("borde", "negro")
        caja_resalte = cfg.get("caja_resalte", False)
        ancho_max = float(cfg.get("ancho_max", 0.86)) * self.W

        f = dj.fuente(nombre_f, tam)
        espacio = f.getlength(" ")
        palabras = []
        for w in txt.split():
            es_r = _limpiar(w) in resaltar
            if es_r and caja_resalte:
                spr = dj.texto(w, nombre_f, tam, relleno=cfg.get("color_texto_caja", "negro"),
                               borde=None, sombra_on=False)
                fondo = dj.caja_redondeada(spr.width + tam * 0.3, spr.height,
                                           tam * 0.12, col_r)
                fondo.alpha_composite(spr, (int(tam * 0.15), 0))
                spr = dj.sombra(fondo, (0, int(tam / 18)), int(tam / 12))
                ancho = f.getlength(w) + tam * 0.4
            else:
                spr = dj.texto(w, nombre_f, tam, relleno=col_r if es_r else col, borde=borde)
                ancho = f.getlength(w) + tam / 7
            palabras.append([w, spr, ancho])

        # Acomodo en líneas
        lineas, actual, ancho_act = [], [], 0
        for p in palabras:
            extra = p[2] + (espacio if actual else 0)
            if actual and ancho_act + extra > ancho_max:
                lineas.append((actual, ancho_act))
                actual, ancho_act = [], 0
                extra = p[2]
            actual.append(p)
            ancho_act += extra
        if actual:
            lineas.append((actual, ancho_act))

        alto_linea = tam * float(cfg.get("interlineado", 1.08))
        cx, cy = self.punto(cfg.get("posicion", "centro"))
        y0 = cy - alto_linea * (len(lineas) - 1) / 2
        self.items = []  # (sprite, x, y)
        for i, (ws, ancho_l) in enumerate(lineas):
            x = cx - ancho_l / 2
            for p in ws:
                self.items.append((p[1], x + p[2] / 2, y0 + i * alto_linea))
                x += p[2] + espacio
        self.centro = (cx, cy)
        self.tam_px = tam

    def dibujar(self, lienzo, t):
        q = self.p_salida(t)
        ang = math.radians(-self.rot_grupo)
        respira = 1 + 0.012 * math.sin(t * 5) if self.cfg.get("respirar", True) else 1
        for i, (spr, x, y) in enumerate(self.items):
            ti = t - i * self.retraso
            if ti < 0:
                continue
            p = ez.limitar(ti / self.entrada)
            esc, op, dy, rot = 1.0, 1.0, 0.0, 0.0
            if self.estilo == "pop":
                esc = ez.salida_rebote(p, 2.6)
                op = ez.limitar(p * 3)
                rot = (1 - p) * -14
            elif self.estilo == "golpe":
                esc = 1 + 2.2 * (1 - ez.salida_cubica(p))
                op = ez.limitar(p * 2.5)
            elif self.estilo == "deslizar":
                dy = (1 - ez.salida_cubica(p)) * self.tam_px * 0.9
                op = ez.salida_cubica(p)
            elif self.estilo == "maquina":
                op = 1.0 if p > 0 else 0.0
            esc *= respira
            if q > 0:
                if self.estilo in ("pop", "golpe"):
                    esc *= 1 - ez.entrada_rebote(q, 2.0)
                else:
                    op *= 1 - q
                    dy -= q * self.tam_px * 0.5
            # rotar la posición del grupo alrededor de su centro
            rx, ry = x - self.centro[0], y + dy - self.centro[1]
            px = self.centro[0] + rx * math.cos(ang) - ry * math.sin(ang)
            py = self.centro[1] + rx * math.sin(ang) + ry * math.cos(ang)
            dj.pegar(lienzo, spr, (px, py), esc, self.rot_grupo + rot, op)


def leer_srt(ruta):
    """Lee un .srt y devuelve [(inicio, fin, texto)]."""
    def seg(ts):
        h, m, s = ts.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    bloques = re.split(r"\n\s*\n", open(ruta, encoding="utf-8-sig").read().strip())
    frases = []
    for b in bloques:
        lineas = [l for l in b.strip().splitlines() if l.strip()]
        for i, l in enumerate(lineas):
            if "-->" in l:
                a, z = [x.strip() for x in l.split("-->")]
                frases.append((seg(a), seg(z.split()[0]), " ".join(lineas[i + 1:])))
                break
    return frases


class Subtitulos(Elemento):
    """Subtítulos dinámicos: grupos cortos de palabras con la palabra actual resaltada."""

    capa = "fija"

    entrada_defecto = 0.12

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        if "srt" in cfg:
            frases = leer_srt(os.path.join(escena.carpeta, cfg["srt"]))
        else:
            frases = [(float(f["inicio"]), float(f["fin"]), str(f["texto"])) for f in cfg.get("frases", [])]
        self.mayus = cfg.get("mayusculas", True)
        self.fuente_n = cfg.get("fuente", "montserrat")
        self.tam_px = self.tam("tamano", 92)
        self.col = cfg.get("color", "blanco")
        self.col_act = cfg.get("color_activo", "amarillo")
        self.pos = self.punto(cfg.get("posicion", (0.5, 0.72)))
        self.cache = {}
        f = dj.fuente(self.fuente_n, self.tam_px)
        self.esp = f.getlength(" ")
        ancho_max = float(cfg.get("ancho_max", 0.86)) * self.W
        n = int(cfg.get("palabras_por_grupo", 3))

        # Cada palabra: [inicio, fin, texto, ancho]. El tiempo de la frase se reparte según el largo.
        # Los grupos nunca cruzan de una frase a otra ni pasan del ancho máximo.
        self.grupos = []
        ultimo_fin = 0.0
        for a, z, txt in frases:
            ws = [w.upper() if self.mayus else w for w in txt.split()]
            if not ws:
                continue
            total = sum(len(w) + 2 for w in ws)
            t, g, ancho_g = a, [], 0.0
            for w in ws:
                d = (z - a) * (len(w) + 2) / total
                ancho = f.getlength(w) + self.tam_px / 5
                if g and (len(g) >= n or ancho_g + self.esp + ancho > ancho_max):
                    self.grupos.append(g)
                    g, ancho_g = [], 0.0
                g.append([t, t + d, w, ancho])
                ancho_g += ancho + (self.esp if len(g) > 1 else 0)
                t += d
                if re.search(r"[.,!?;:]$", w):
                    self.grupos.append(g)
                    g, ancho_g = [], 0.0
            if g:
                self.grupos.append(g)
            ultimo_fin = max(ultimo_fin, z)
        self.ancho_max = ancho_max
        if self.grupos:
            self.duracion = ultimo_fin + 0.3

    def _spr(self, w, activo):
        clave = (w, activo)
        if clave not in self.cache:
            self.cache[clave] = dj.texto(w, self.fuente_n, self.tam_px,
                                         relleno=self.col_act if activo else self.col,
                                         ancho_borde=self.tam_px / 9)
        return self.cache[clave]

    def dibujar(self, lienzo, t):
        g = next((gr for gr in self.grupos if gr[0][0] <= t < gr[-1][1] + 0.05), None)
        if g is None:
            return
        extra = 0.1  # la palabra activa crece un 10 %; dejamos espacio para que no se encime
        total = sum(w[3] for w in g) * (1 + extra / len(g)) + self.esp * (len(g) - 1)
        ajuste = min(1.0, self.ancho_max / total)  # una palabra larguísima se encoge para caber
        p = ez.limitar((t - g[0][0]) / self.entrada)
        esc_g = ajuste * (0.75 + 0.25 * ez.salida_rebote(p, 2.2))
        x = self.pos[0] - total / 2 * esc_g
        for w in g:
            activo = w[0] <= t < w[1]
            if self.cfg.get("acumular", False) and t < w[0]:
                break
            if activo:
                pa = ez.limitar((t - w[0]) / 0.1)
                esc = esc_g * (1 + extra * ez.salida_rebote(pa))
                ancho = w[3] * (1 + extra)
            else:
                esc, ancho = esc_g, w[3]
            dj.pegar(lienzo, self._spr(w[2], activo), (x + ancho * esc_g / 2, self.pos[1]), esc)
            x += (ancho + self.esp) * esc_g


class Cartel(Elemento):
    """Lower third: nombre / lugar con barra de acento que entra deslizándose."""

    duracion_defecto = 4.0
    entrada_defecto = 0.55
    sonido_defecto = "whoosh"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        u = self.u
        acento = cfg.get("color", "amarillo")
        t1 = dj.texto(str(cfg.get("titulo", "TÍTULO")).upper(), "montserrat", 64 * u,
                      relleno=cfg.get("color_texto", "negro"), borde=None, sombra_on=False)
        caja = dj.caja_redondeada(t1.width + 70 * u, t1.height + 36 * u, 14 * u, cfg.get("fondo", "blanco"))
        barra = dj.caja_redondeada(14 * u, caja.height, 7 * u, acento)
        caja.alpha_composite(barra, (0, 0))
        caja.alpha_composite(t1, (int(42 * u), int(18 * u)))
        self.caja = dj.sombra(caja, (0, int(8 * u)), int(14 * u))
        self.sub = None
        if cfg.get("subtitulo"):
            t2 = dj.texto(str(cfg["subtitulo"]), "montserrat-bold", 40 * u, relleno="blanco",
                          borde=None, sombra_on=False)
            s = dj.caja_redondeada(t2.width + 44 * u, t2.height + 22 * u, 10 * u, acento if cfg.get("subtitulo_acento", False) else "#111111")
            s.alpha_composite(t2, (int(22 * u), int(11 * u)))
            self.sub = dj.sombra(s, (0, int(6 * u)), int(10 * u))
        self.pos = self.punto(cfg.get("posicion", (0.07, 0.6) if self.H > self.W else (0.05, 0.8)))

    def dibujar(self, lienzo, t):
        q = self.p_salida(t)
        for i, spr in enumerate([self.caja, self.sub]):
            if spr is None:
                continue
            p = ez.limitar((t - i * 0.12) / self.entrada)
            if p <= 0:
                continue
            avance = ez.salida_rebote(p, 1.4) - ez.entrada_cubica(q) * 1.2
            x = self.pos[0] - (1 - avance) * (spr.width + self.pos[0])
            y = self.pos[1] + (i * (self.caja.height * 0.78))
            dj.pegar(lienzo, spr, (x, y), 1.0, 0, min(1, p * 3) * (1 - q), ancla=(0, 0.5))


class Dato(Elemento):
    """Tarjeta tipo '¿SABÍAS QUÉ?' con encabezado y texto."""

    duracion_defecto = 4.0
    entrada_defecto = 0.6
    sonido_defecto = "pop"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        u = self.u
        acento = cfg.get("color", "amarillo")
        ancho = float(cfg.get("ancho", 0.8)) * self.W
        f = dj.fuente("montserrat-bold", 50 * u)
        # Ajuste de texto en líneas
        lineas, act = [], ""
        for w in str(cfg.get("texto", "")).split():
            prueba = (act + " " + w).strip()
            if f.getlength(prueba) > ancho - 90 * u and act:
                lineas.append(act)
                act = w
            else:
                act = prueba
        lineas.append(act)
        alto_l = 64 * u
        cuerpo = dj.caja_redondeada(ancho, alto_l * len(lineas) + 110 * u, 30 * u, cfg.get("fondo", "blanco"))
        d = ImageDraw.Draw(cuerpo)
        for i, l in enumerate(lineas):
            d.text((ancho / 2, 75 * u + i * alto_l), l, font=f, fill=dj.color(cfg.get("color_texto", "#111111")), anchor="mm")
        enc_t = dj.texto(str(cfg.get("titulo", "¿SABÍAS QUÉ?")).upper(), "anton", 70 * u, relleno="negro", borde=None, sombra_on=False)
        enc = dj.caja_redondeada(enc_t.width + 60 * u, enc_t.height + 20 * u, 22 * u, acento)
        enc.alpha_composite(enc_t, (int(30 * u), int(10 * u)))
        self.enc, self.cuerpo = dj.sombra(enc, (0, 6), 10), dj.sombra(cuerpo, (0, int(12 * u)), int(22 * u))
        self.pos = self.punto(cfg.get("posicion", "centro"))

    def dibujar(self, lienzo, t):
        q = self.p_salida(t)
        p = self.p_entrada(t)
        esc = ez.resorte(p, 5, 1.6) * (1 - ez.entrada_rebote(q))
        cx, cy = self.pos
        h = self.cuerpo.height
        dj.pegar(lienzo, self.cuerpo, (cx, cy), esc, 0, min(1, p * 4))
        p2 = ez.limitar((t - 0.18) / self.entrada)
        esc2 = ez.salida_rebote(p2, 2.5) * (1 - ez.entrada_rebote(q))
        dj.pegar(lienzo, self.enc, (cx, cy - h / 2 * esc + 10 * self.u), esc2, -4 * (1 - p2) - 2)


class Contador(Elemento):
    """Número que cuenta de `desde` a `hasta` (dinero, seguidores, km...)."""

    entrada_defecto = 0.3
    sonido_defecto = "ding"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        self.desde = float(cfg.get("desde", 0))
        self.hasta = float(cfg.get("hasta", 100))
        self.t_conteo = float(cfg.get("duracion_conteo", min(1.6, self.duracion * 0.6)))
        self.dec = int(cfg.get("decimales", 0))
        self.pos = self.punto(cfg.get("posicion", "centro"))
        self.tam_px = self.tam("tamano", 170)
        self.cache = {}

    def _fmt(self, v):
        s = f"{v:,.{self.dec}f}"
        return f"{self.cfg.get('prefijo', '')}{s}{self.cfg.get('sufijo', '')}"

    def dibujar(self, lienzo, t):
        pc = ez.salida_cubica(t / self.t_conteo) if self.t_conteo > 0 else 1
        txt = self._fmt(self.desde + (self.hasta - self.desde) * pc)
        listo = t >= self.t_conteo
        if (txt, listo) not in self.cache:
            col = self.cfg.get("color_final", "amarillo") if listo else self.cfg.get("color", "blanco")
            self.cache[(txt, listo)] = dj.texto(txt, self.cfg.get("fuente", "anton"), self.tam_px, relleno=col)
        esc = ez.salida_rebote(self.p_entrada(t), 2)
        if listo:  # golpecito al terminar
            k = ez.limitar((t - self.t_conteo) / 0.35)
            esc *= 1 + 0.18 * math.sin(k * math.pi)
        q = self.p_salida(t)
        esc *= 1 - ez.entrada_rebote(q)
        dj.pegar(lienzo, self.cache[(txt, listo)], self.pos, esc)


# ---------------------------------------------------------------------------
# Trazos: flechas y círculos
# ---------------------------------------------------------------------------

def _bezier(a, c, b, n):
    pts = []
    for i in range(n + 1):
        s = i / n
        x = (1 - s) ** 2 * a[0] + 2 * (1 - s) * s * c[0] + s * s * b[0]
        y = (1 - s) ** 2 * a[1] + 2 * (1 - s) * s * c[1] + s * s * b[1]
        pts.append((x, y))
    return pts


def _caja(pts, margen):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs) - margen, min(ys) - margen, max(xs) + margen, max(ys) + margen)


class Flecha(Elemento):
    """Flecha que se dibuja sola desde un punto hacia otro (opcional: texto al inicio)."""

    entrada_defecto = 0.5
    sonido_defecto = "whoosh"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        self.a = self.punto(cfg.get("desde", (0.3, 0.3)))
        self.b = self.punto(cfg.get("hasta", (0.6, 0.6)))
        dx, dy = self.b[0] - self.a[0], self.b[1] - self.a[1]
        k = float(cfg.get("curva", 0.25))
        self.c = ((self.a[0] + self.b[0]) / 2 - dy * k, (self.a[1] + self.b[1]) / 2 + dx * k)
        self.grosor = self.tam("grosor", 16)
        self.col = cfg.get("color", "amarillo")
        self.borde = cfg.get("borde", "negro")
        self.etiqueta = None
        if cfg.get("texto"):
            self.etiqueta = dj.texto(str(cfg["texto"]).upper(), cfg.get("fuente", "anton"),
                                     self.tam("tamano", 90), relleno=cfg.get("color_texto", self.col))

    def dibujar(self, lienzo, t):
        p = ez.salida_cubica(self.p_entrada(t))
        op = 1 - self.p_salida(t)
        if self.etiqueta is not None:
            pe = ez.limitar(t / 0.3)
            off = (self.a[0] - self.c[0], self.a[1] - self.c[1])
            n = math.hypot(*off) or 1
            pos = (self.a[0] + off[0] / n * self.etiqueta.height * 0.6,
                   self.a[1] + off[1] / n * self.etiqueta.height * 0.6)
            dj.pegar(lienzo, self.etiqueta, pos, ez.salida_rebote(pe, 2.5), 0, op)
        # meneo sutil de la punta mientras está en pantalla
        mov = math.sin(t * 7) * 6 * self.u * (p >= 1)
        dirx, diry = self.b[0] - self.c[0], self.b[1] - self.c[1]
        n = math.hypot(dirx, diry) or 1
        b = (self.b[0] + dirx / n * mov, self.b[1] + diry / n * mov)
        pts = _bezier(self.a, self.c, b, 60)
        corte = max(2, int(len(pts) * p))
        pts = pts[:corte]
        g, gb = self.grosor, self.grosor + self.tam("ancho_borde", 7) * 2
        pin = dj.Pincel(lienzo, _caja(_bezier(self.a, self.c, b, 60), gb * 4))
        # cabeza de flecha
        cabeza = None
        if p > 0.7:
            (x1, y1), (x2, y2) = pts[-4], pts[-1]
            ang = math.atan2(y2 - y1, x2 - x1)
            L = g * 3.4 * ez.salida_rebote(ez.limitar((p - 0.7) / 0.3), 2.2)
            ab = 0.5
            cabeza = [(x2 + math.cos(ang) * L * 0.35, y2 + math.sin(ang) * L * 0.35),
                      (x2 - math.cos(ang - ab) * L, y2 - math.sin(ang - ab) * L),
                      (x2 - math.cos(ang + ab) * L, y2 - math.sin(ang + ab) * L)]
        if self.borde:
            pin.linea(pts, self.borde, gb)
            if cabeza:
                pin.poligono(cabeza, self.borde, self.borde, gb - g)
        pin.linea(pts, self.col, g)
        if cabeza:
            pin.poligono(cabeza, self.col)
        pin.terminar(op, con_sombra=True)


class Circulo(Elemento):
    """Círculo hecho 'a mano' que encierra algo en pantalla."""

    entrada_defecto = 0.55
    sonido_defecto = "whoosh"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        self.c = self.punto(cfg.get("posicion", "centro"))
        r = cfg.get("radio", 180)
        rx, ry = (r, r) if not isinstance(r, (list, tuple)) else r
        self.rx, self.ry = rx * self.u, ry * self.u
        self.grosor = self.tam("grosor", 13)
        self.col = cfg.get("color", "rojo")
        self.vueltas = float(cfg.get("vueltas", 1.15))

    def dibujar(self, lienzo, t):
        p = ez.suave(self.p_entrada(t))
        op = 1 - self.p_salida(t)
        n = 90
        a0 = math.radians(-110)
        pts = []
        for i in range(int(n * p) + 1):
            s = i / n
            th = a0 + s * 2 * math.pi * self.vueltas
            k = 1 + 0.035 * math.sin(3 * th + 1) + 0.07 * s  # imperfección + espiral
            pts.append((self.c[0] + math.cos(th) * self.rx * k, self.c[1] + math.sin(th) * self.ry * k * 0.97))
        m = self.grosor * 3
        pin = dj.Pincel(lienzo, (self.c[0] - self.rx * 1.2 - m, self.c[1] - self.ry * 1.2 - m,
                                 self.c[0] + self.rx * 1.2 + m, self.c[1] + self.ry * 1.2 + m))
        if self.cfg.get("borde"):
            pin.linea(pts, self.cfg["borde"], self.grosor + 10 * self.u)
        pin.linea(pts, self.col, self.grosor)
        pin.terminar(op, con_sombra=True)


# ---------------------------------------------------------------------------
# Íconos, stickers, ubicación
# ---------------------------------------------------------------------------

class Sticker(Elemento):
    """Emoji o imagen PNG que aparece con rebote y se mece."""

    entrada_defecto = 0.45
    sonido_defecto = "pop"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        tam = self.tam("tamano", 220)
        if cfg.get("archivo"):
            img = Image.open(os.path.join(escena.carpeta, cfg["archivo"])).convert("RGBA")
            k = tam / max(img.width, img.height)
            img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.LANCZOS)
            if cfg.get("borde_blanco", True):  # contorno blanco tipo sticker
                m = int(tam * 0.06)
                base = Image.new("RGBA", (img.width + 2 * m, img.height + 2 * m), (0, 0, 0, 0))
                base.paste(img, (m, m), img)
                a = base.getchannel("A").filter(ImageFilter.MaxFilter(m * 2 - 1 if m > 1 else 3))
                blanco = Image.new("RGBA", base.size, (255, 255, 255, 255))
                blanco.putalpha(a)
                blanco.alpha_composite(base)
                img = blanco
            self.spr = dj.sombra(img, (0, int(tam / 25)), int(tam / 18))
        else:
            self.spr = dj.emoji(str(cfg.get("emoji", "🔥")), int(tam))
        self.pos = self.punto(cfg.get("posicion", "centro"))
        self.rot = float(cfg.get("rotacion", 0))
        self.anim = cfg.get("animacion", "pop")

    def dibujar(self, lienzo, t):
        p = self.p_entrada(t)
        q = self.p_salida(t)
        x, y = self.pos
        rot = self.rot + math.sin(t * 4) * 5
        if self.anim == "caer":
            y -= (1 - ez.caida_rebote(p)) * self.H * 0.4
            esc = 1
        else:
            esc = ez.salida_rebote(p, 3)
            rot += (1 - p) * 40
        esc *= 1 - ez.entrada_rebote(q, 2)
        dj.pegar(lienzo, self.spr, (x, y), esc, rot, min(1, p * 4))


class Ubicacion(Elemento):
    """Pin de ubicación que cae rebotando y despliega el nombre del lugar."""

    duracion_defecto = 3.5
    entrada_defecto = 0.7
    sonido_defecto = "pop"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        u = self.u
        R = 46 * u
        ss = 4
        pin = Image.new("RGBA", (int(R * 2 * ss + 8), int(R * 3.1 * ss)), (0, 0, 0, 0))
        d = ImageDraw.Draw(pin)
        col = dj.color(cfg.get("color", "rojo"))
        cx = pin.width / 2
        d.polygon([(cx - R * ss * 0.86, R * ss * 1.5), (cx + R * ss * 0.86, R * ss * 1.5), (cx, R * 3.05 * ss)], fill=col)
        d.ellipse([cx - R * ss, 4, cx + R * ss, 4 + 2 * R * ss], fill=col)
        r2 = R * ss * 0.42
        d.ellipse([cx - r2, 4 + R * ss - r2, cx + r2, 4 + R * ss + r2], fill=(255, 255, 255, 255))
        pin = pin.resize((pin.width // ss, pin.height // ss), Image.LANCZOS)
        self.pin = dj.sombra(pin, (0, int(6 * u)), int(8 * u))
        txt = dj.texto(str(cfg.get("lugar", "Lugar")), "montserrat", 58 * u, relleno="negro", borde=None, sombra_on=False)
        et = dj.caja_redondeada(txt.width + 60 * u, txt.height + 34 * u, (txt.height + 34 * u) / 2, cfg.get("fondo", "blanco"))
        et.alpha_composite(txt, (int(30 * u), int(17 * u)))
        self.etiqueta = dj.sombra(et, (0, int(8 * u)), int(12 * u))
        self.pos = self.punto(cfg.get("posicion", (0.3, 0.3)))

    def dibujar(self, lienzo, t):
        q = self.p_salida(t)
        op = 1 - q
        p = self.p_entrada(t)
        x, y = self.pos  # punta del pin
        y_pin = y - (1 - ez.caida_rebote(p)) * self.H * 0.35
        dj.pegar(lienzo, self.pin, (x, y_pin), 1, 0, min(1, p * 5) * op, ancla=(0.5, 0.86))
        pe = ez.limitar((t - self.entrada * 0.8) / 0.4)
        if pe > 0:
            sx = ez.salida_rebote(pe, 1.6)
            dj.pegar(lienzo, self.etiqueta, (x + 40 * self.u, y - self.pin.height * 0.55),
                     (max(0.02, sx), 1.0), 0, op, ancla=(0, 0.5))


# ---------------------------------------------------------------------------
# Pantalla completa: transiciones y flash
# ---------------------------------------------------------------------------

class Transicion(Elemento):
    """Barrido de colores a pantalla completa. Pon el corte de tu video a la mitad."""

    capa = "fija"

    duracion_defecto = 0.8
    entrada_defecto = 0.0
    salida_defecto = 0.0
    sonido_defecto = "whoosh"

    def __init__(self, cfg, escena):
        super().__init__(cfg, escena)
        self.colores = cfg.get("colores", ["amarillo", "negro"])
        self.estilo = cfg.get("estilo", "barrido")
        self.centro = self.punto(cfg.get("posicion", "centro"))

    def dibujar(self, lienzo, t):
        W, H = self.W, self.H
        capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        n = len(self.colores)
        retraso = 0.08 * self.duracion
        dur = self.duracion - retraso * (n - 1)
        if self.estilo == "circulo":
            R = math.hypot(max(self.centro[0], W - self.centro[0]), max(self.centro[1], H - self.centro[1]))
            for i, c in enumerate(self.colores):
                p = ez.limitar((t - i * retraso) / dur)
                ext = R * ez.suave(min(1, p * 2))
                hueco = R * ez.suave(max(0, p * 2 - 1))
                if ext <= 0:
                    continue
                cx, cy = self.centro
                d.ellipse([cx - ext, cy - ext, cx + ext, cy + ext], fill=dj.color(c))
                if hueco > 0:
                    d.ellipse([cx - hueco, cy - hueco, cx + hueco, cy + hueco], fill=(0, 0, 0, 0))
        else:
            sesgo = H * 0.35
            bw = W + sesgo + W * 0.1
            for i, c in enumerate(self.colores):
                p = ez.suave(ez.limitar((t - i * retraso) / dur))
                x = -bw + (W + sesgo + bw) * p
                d.polygon([(x + sesgo, 0), (x + bw + sesgo, 0), (x + bw, H), (x, H)], fill=dj.color(c))
        lienzo.alpha_composite(capa)


class Flash(Elemento):
    """Destello de color que se desvanece (para golpes, cortes o revelaciones)."""

    capa = "fija"

    duracion_defecto = 0.35
    entrada_defecto = 0.0
    salida_defecto = 0.0

    def dibujar(self, lienzo, t):
        a = (1 - ez.salida_cubica(t / self.duracion)) * float(self.cfg.get("intensidad", 0.9))
        lienzo.alpha_composite(Image.new("RGBA", lienzo.size, dj.color(self.cfg.get("color", "blanco"), int(255 * a))))


# ---------------------------------------------------------------------------
# Efectos sobre el video (solo funcionan si el guion trae `video:`)
# ---------------------------------------------------------------------------

class EfectoVideo:
    def __init__(self, cfg, escena):
        self.cfg = cfg
        self.W, self.H = escena.Wo, escena.Ho  # el video base va a la resolución de salida
        self.inicio = float(cfg.get("inicio", 0))
        self.duracion = float(cfg.get("duracion", 1.0)) if "fin" not in cfg else float(cfg["fin"]) - self.inicio
        snd = cfg.get("sonido", getattr(self, "sonido_defecto", None))
        self.sonido = None if snd in (False, None, "no") else snd
        self.entrada = 0
        p = cfg.get("posicion", "centro")
        p = POSICIONES.get(p, (0.5, 0.5)) if isinstance(p, str) else p
        self.centro = (p[0] * self.W, p[1] * self.H)

    @property
    def fin(self):
        return self.inicio + self.duracion

    def activo(self, t):
        return self.inicio <= t < self.fin


class Zoom(EfectoVideo):
    """Acercamiento. estilo: 'golpe' (instantáneo, como punch-in) o 'suave'."""

    sonido_defecto = None

    def transformar(self, t):
        f = float(self.cfg.get("factor", 1.3))
        if self.cfg.get("estilo", "suave") == "golpe":
            k = 1.0
            sal = ez.limitar((t - (self.duracion - 0.12)) / 0.12)
            k *= 1 - sal
        else:
            r = float(self.cfg.get("rampa", min(0.4, self.duracion / 3)))
            k = ez.suave(t / r) * (1 - ez.suave((t - (self.duracion - r)) / r))
        return 1 + (f - 1) * k, self.centro, (0, 0)


class Sacudida(EfectoVideo):
    """Sacudida de cámara (temblor) que se va calmando."""

    sonido_defecto = "golpe"

    def transformar(self, t):
        A = float(self.cfg.get("intensidad", 28)) * min(self.W, self.H) / 1080
        dec = 1 - ez.salida_cubica(t / self.duracion)
        dx = A * dec * (math.sin(t * 61) * 0.6 + math.sin(t * 37 + 1) * 0.4)
        dy = A * dec * (math.sin(t * 53 + 2) * 0.6 + math.sin(t * 29) * 0.4)
        return 1.06, (self.W / 2, self.H / 2), (dx, dy)


TIPOS = {
    "titulo": Titulo,
    "subtitulos": Subtitulos,
    "cartel": Cartel,
    "dato": Dato,
    "contador": Contador,
    "flecha": Flecha,
    "circulo": Circulo,
    "sticker": Sticker,
    "emoji": Sticker,
    "ubicacion": Ubicacion,
    "transicion": Transicion,
    "flash": Flash,
}

TIPOS_VIDEO = {
    "zoom": Zoom,
    "sacudida": Sacudida,
}
