import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

img = Image.open('ref.png').convert('L')
a = np.array(img) < 140
lab, n = ndimage.label(a, structure=np.ones((3, 3)))
objs = ndimage.find_objects(lab)
comps = []
for i, sl in enumerate(objs):
    ys, xs = sl
    area = int((lab[sl] == i + 1).sum())
    if area < 30:
        continue
    comps.append(dict(id=i + 1, x0=xs.start, x1=xs.stop, y0=ys.start, y1=ys.stop, cy=(ys.start + ys.stop) / 2, area=area))
centros = [390, 684, 1005, 1320, 1875, 2205, 2535, 2865]
filas = [[] for _ in centros]
asig = {}
for c in comps:
    asig[c['id']] = int(np.argmin([abs(c['cy'] - y) for y in centros]))
# Condensada: los acentos quedan entre filas; van a la fila de abajo
tops, bases = {}, {}
for r in range(4, 8):
    grandes = [c for c in comps if asig[c['id']] == r and c['y1'] - c['y0'] > 200]
    tops[r] = float(np.median([c['y0'] for c in grandes])); bases[r] = float(np.median([c['y1'] for c in grandes]))
for c in comps:
    for r in range(5, 8):
        if c['y1'] - c['y0'] < 100 and c['y0'] >= bases[r - 1] + 8 and c['y1'] <= tops[r] + 8:
            asig[c['id']] = r
for c in comps:
    filas[asig[c['id']]].append(c)
FUSIONES = {0: [(0, 7)], 2: [(2, 21)], 6: [(6, 5)]}
glifos = []
for k, fila in enumerate(filas):
    fila.sort(key=lambda c: c['x0'])
    grupos = []
    for c in fila:
        if grupos and c['x0'] < grupos[-1]['x1'] - 4:
            g = grupos[-1]; g['comps'].append(c['id'])
            g['x0'] = min(g['x0'], c['x0']); g['x1'] = max(g['x1'], c['x1']); g['y0'] = min(g['y0'], c['y0']); g['y1'] = max(g['y1'], c['y1'])
        else:
            grupos.append(dict(comps=[c['id']], x0=c['x0'], x1=c['x1'], y0=c['y0'], y1=c['y1'], fila=k))
    # fusiones manuales: punto de la i (fila 0) y comillas dobles
    for (fk, idx) in FUSIONES.get(k, []):
        g, h = grupos[idx], grupos[idx + 1]
        g['comps'] += h['comps']; g['x0'] = min(g['x0'], h['x0']); g['x1'] = max(g['x1'], h['x1']); g['y0'] = min(g['y0'], h['y0']); g['y1'] = max(g['y1'], h['y1'])
        del grupos[idx + 1]
    glifos.append(grupos)
print([len(f) for f in glifos])
json.dump(glifos, open('glifos.json', 'w'))
np.save('lab.npy', lab)
# hoja de control
ctl = Image.open('ref.png').convert('RGB').resize((2000, 1125))
d = ImageDraw.Draw(ctl)
for fila in glifos:
    for i, g in enumerate(fila):
        d.rectangle([g['x0'] / 3, g['y0'] / 3, g['x1'] / 3, g['y1'] / 3], outline='red')
        d.text((g['x0'] / 3, g['y1'] / 3 + 1), str(i), fill='blue')
ctl.save('control.png')
