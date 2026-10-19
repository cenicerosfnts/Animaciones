"""Efectos de sonido sintetizados (sin archivos externos): pop, whoosh, ding, golpe."""
import os
import wave

import numpy as np

SR = 48000


def _env(n, ataque, caida):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(ataque, 1e-4)) * np.exp(-t / caida)


def pop(rng):
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 28) + 180  # barrido descendente
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.04)
    return s * 0.7


def whoosh(rng):
    n = int(0.45 * SR)
    ruido = rng.standard_normal(n)
    # filtro pasa-bajos cuyo corte sube y baja (suena a aire en movimiento)
    t = np.linspace(0, 1, n)
    corte = 0.02 + 0.25 * np.sin(np.pi * t) ** 2
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        acc += corte[i] * (ruido[i] - acc)
        y[i] = acc
    env = np.sin(np.pi * t) ** 1.5
    return y / (np.abs(y).max() + 1e-9) * env * 0.55


def ding(rng):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((1568, 1), (3136, 0.35), (4704, 0.12)))
    return s * _env(n, 0.003, 0.25) * 0.35


def golpe(rng):
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 120 * np.exp(-t * 12) + 45
    bombo = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.001, 0.12)
    chas = rng.standard_normal(n) * _env(n, 0.0005, 0.02) * 0.5
    return (bombo + chas) * 0.8


SONIDOS = {"pop": pop, "whoosh": whoosh, "ding": ding, "golpe": golpe}


def cargar_wav(ruta):
    with wave.open(ruta) as w:
        datos = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            datos = datos.reshape(-1, 2).mean(axis=1)
        if w.getframerate() != SR:  # remuestreo simple
            x = np.linspace(0, len(datos), int(len(datos) * SR / w.getframerate()), endpoint=False)
            datos = np.interp(x, np.arange(len(datos)), datos)
        return datos


def pista(eventos, duracion, carpeta=".", volumen=0.8):
    """eventos = [(segundo, nombre_o_ruta_wav)] -> arreglo mono float."""
    rng = np.random.default_rng(7)
    out = np.zeros(int((duracion + 1) * SR), dtype=np.float32)
    for t, nombre in eventos:
        if nombre in SONIDOS:
            s = SONIDOS[nombre](rng)
        else:
            s = cargar_wav(os.path.join(carpeta, nombre))
        i = int(t * SR)
        if i >= len(out):
            continue
        s = s[: len(out) - i]
        out[i:i + len(s)] += s * volumen
    return np.clip(out[: int(duracion * SR)], -1, 1)


def guardar_wav(ruta, datos):
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((datos * 32767).astype(np.int16).tobytes())
