import json
import numpy as np
import potrace
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen

lab = np.load('lab.npy')
PAD = 3
glifos = json.load(open('glifos.json'))
FILAS = [
    "qwertyuiopasdfghjklñzxcvbnmQWERTY",
    "UIOPASDFGHJKLÑZXCVBNMÁÉÓÍÚáéí",
    "óú1234567890-/:;()$&@\".,?!'[]",
    "{}#%^*+=_\\|~<>€£¥•.,?!'",
    "QWERTYUIOPASDFGHJKLÑZXCVBNM",
    "ÁÉÓÍÚáéíóú1234567890-/:;",
    "()$&@”.,?!’[]{}#%^*+=_\\|~<>€£",
    "¥•.,?!’",
]
for f, g in zip(FILAS, glifos):
    assert len(f) == len(g), (f, len(g))


def mascara(g):
    x0, y0, x1, y1 = g['x0'], g['y0'], g['x1'], g['y1']
    sub = np.isin(lab[y0:y1, x0:x1], g['comps'])
    return sub


def trazar(m):
    bm = potrace.Bitmap(~np.pad(m, PAD))  # potracer rellena lo False: invertimos
    return bm.trace(turdsize=6, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY, alphamax=1.0, opticurve=True, opttolerance=0.25)


def P(p):
    return (p.x, p.y) if hasattr(p, 'x') else tuple(p)


def dibujar(pen, path):
    for curva in path:
        pen.moveTo(P(curva.start_point))
        for seg in curva.segments:
            if seg.is_corner:
                pen.lineTo(P(seg.c)); pen.lineTo(P(seg.end_point))
            else:
                pen.curveTo(P(seg.c1), P(seg.c2), P(seg.end_point))
        pen.closePath()


def construir(nombre, archivo, filas, base_de_fila, escala, lado, espacio, mapa_extra, descend=-260, ascend=900):
    glyphs = {}  # nombre_glifo -> (path, ancho, dx, base, girado)
    cmap = {}
    for k in filas:
        for ch, g in zip(FILAS[k], glifos[k]):
            if ord(ch) in cmap:
                continue
            gn = 'uni%04X' % ord(ch)
            glyphs[gn] = dict(g=g, base=base_de_fila[k], girar=False)
            cmap[ord(ch)] = gn
    # ¿ y ¡ a partir de ? y !
    for src, dst in (('?', '¿'), ('!', '¡')):
        if ord(src) in cmap and ord(dst) not in cmap:
            info = glyphs[cmap[ord(src)]]
            gn = 'uni%04X' % ord(dst)
            glyphs[gn] = dict(g=info['g'], base=info['base'], girar=True)
            cmap[ord(dst)] = gn
    order = ['.notdef', 'space'] + sorted(glyphs)
    charstrings, metrics = {}, {}
    pen = T2CharStringPen(500, None); pen.moveTo((50, 0)); pen.lineTo((450, 0)); pen.lineTo((450, 700)); pen.lineTo((50, 700)); pen.closePath()
    charstrings['.notdef'] = pen.getCharString(); metrics['.notdef'] = (500, 50)
    pen = T2CharStringPen(espacio, None); charstrings['space'] = pen.getCharString(); metrics['space'] = (espacio, 0)
    for gn, info in glyphs.items():
        g = info['g']; m = mascara(g)
        if info['girar']:
            m = m[::-1, ::-1]
        path = trazar(m)
        w_px = g['x1'] - g['x0']
        ancho = int(round(w_px * escala + 2 * lado))
        if info['girar']:
            # el signo invertido cuelga desde la altura x hacia abajo
            alto_px = g['y1'] - g['y0']; top_u = 520
            t = (escala, 0, 0, -escala, lado - PAD * escala, top_u + PAD * escala)
        else:
            t = (escala, 0, 0, -escala, lado - PAD * escala, (info['base'] - g['y0'] + PAD) * escala)
        pen = T2CharStringPen(ancho, None)
        dibujar(TransformPen(pen, t), path)
        charstrings[gn] = pen.getCharString()
        metrics[gn] = (ancho, lado)
    cmap[32] = 'space'; cmap[0xA0] = 'space'
    for dst, src in mapa_extra.items():
        if ord(src) in cmap and ord(dst) not in cmap:
            cmap[ord(dst)] = cmap[ord(src)]
    fb = FontBuilder(1000, isTTF=False)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    ps = nombre.replace(' ', '')
    fb.setupCFF(ps, {'FullName': nombre}, charstrings, {})
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ascend, descent=descend)
    fb.setupNameTable({'familyName': nombre, 'styleName': 'Regular'})
    fb.setupOS2(sTypoAscender=ascend, sTypoDescender=descend, usWinAscent=ascend, usWinDescent=-descend, sCapHeight=700, sxHeight=480)
    fb.setupPost()
    fb.save(archivo)
    print(archivo, len(glyphs), 'glifos')


def mediana_y1(k, chars):
    return float(np.median([g['y1'] for ch, g in zip(FILAS[k], glifos[k]) if ch in chars]))


# --- Letra a mano ---
bases_m = {0: mediana_y1(0, 'acemnorsuvwxzQWERT'), 1: mediana_y1(1, 'UIOPASDFHKLMNZXCVB'), 2: mediana_y1(2, '1234567890'), 3: mediana_y1(3, '#€£¥!?')}
alto_cap = float(np.median([g['y1'] - g['y0'] for ch, g in zip(FILAS[1], glifos[1]) if ch in 'UIOPASDFHKLMNZXCVB']))
esc_m = 680 / alto_cap
comillas = {'“': '"', '”': '"', '‘': "'", '’': "'", '–': '-', '—': '-', '·': '•'}
mayus_a_minus = {}
construir('Angel Mano', 'AngelMano.otf', [0, 1, 2, 3], bases_m, esc_m, 34, 300, comillas)

# --- Condensada (solo mayúsculas: las minúsculas usan las mayúsculas) ---
bases_c = {4: mediana_y1(4, 'WERTYUIOPASDFGHKLZXCVBNM'), 5: mediana_y1(5, '1234567890'), 6: mediana_y1(6, '?!#%€£'), 7: mediana_y1(7, '¥?!')}
alto_c = float(np.median([g['y1'] - g['y0'] for ch, g in zip(FILAS[4], glifos[4]) if ch in 'WERTYUIOPASDFHKLZXCVBNM']))
esc_c = 700 / alto_c
extra = {'"': '”', '“': '”', "'": '’', '‘': '’', '–': '-', '—': '-', '·': '•'}
for ch in 'qwertyuiopasdfghjklñzxcvbnm':
    extra[ch] = ch.upper()
construir('Angel Condensada', 'AngelCondensada.otf', [4, 5, 6, 7], bases_c, esc_c, 42, 230, extra)
