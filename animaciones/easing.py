"""Curvas de animación (easing). Todas reciben t en [0, 1] y devuelven el avance."""
import math


def limitar(t, a=0.0, b=1.0):
    return max(a, min(b, t))


def lineal(t):
    return limitar(t)


def entrada_cubica(t):
    t = limitar(t)
    return t * t * t


def salida_cubica(t):
    t = limitar(t)
    return 1 - (1 - t) ** 3


def suave(t):
    """Ease in-out cúbico."""
    t = limitar(t)
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def salida_rebote(t, fuerza=1.70158):
    """Se pasa un poco del objetivo y regresa (efecto 'pop')."""
    t = limitar(t)
    c3 = fuerza + 1
    return 1 + c3 * (t - 1) ** 3 + fuerza * (t - 1) ** 2


def entrada_rebote(t, fuerza=1.70158):
    t = limitar(t)
    c3 = fuerza + 1
    return c3 * t * t * t - fuerza * t * t


def elastico(t):
    t = limitar(t)
    if t in (0.0, 1.0):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


def resorte(t, amortiguacion=6.0, frecuencia=3.2):
    """Resorte amortiguado: arranca rápido y oscila hasta asentarse en 1."""
    t = limitar(t)
    return 1 - math.exp(-amortiguacion * t) * math.cos(frecuencia * 2 * math.pi * t)


def caida_rebote(t):
    """Como una pelota que cae y rebota (para pines y stickers)."""
    t = limitar(t)
    n1, d1 = 7.5625, 2.75
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


CURVAS = {
    "lineal": lineal,
    "suave": suave,
    "salida": salida_cubica,
    "entrada": entrada_cubica,
    "pop": salida_rebote,
    "elastico": elastico,
    "resorte": resorte,
    "rebote": caida_rebote,
}


def curva(nombre):
    return CURVAS.get(nombre, salida_rebote)
