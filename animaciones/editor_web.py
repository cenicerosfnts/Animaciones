"""Arma la página completa del editor (editor/index.html no trae <html>/<head> porque también se publica en Claude)."""
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITOR = os.path.join(RAIZ, "editor", "index.html")


def pagina():
    with open(EDITOR, encoding="utf-8") as f:
        cuerpo = f.read()
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>'
            + cuerpo + "</body></html>")


def construir(carpeta):
    """Escribe <carpeta>/index.html listo para publicar (por ejemplo en GitHub Pages)."""
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina())
