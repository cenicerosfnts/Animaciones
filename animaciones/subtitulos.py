"""Transcribe tu voz con Whisper (en tu computadora, sin internet después de la primera vez) y crea
subtítulos: <clip>.srt y <clip>.palabras.json (tiempos por palabra para el editor).

    pip install faster-whisper
    python -m animaciones subtitular clip.mov [otro.mov ...]
"""
import json
import os


def _ts(t):
    h, r = divmod(max(0.0, t), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def escribir(palabras, base):
    """palabras = [{"texto", "inicio", "fin"}] -> base.srt (frases cortas) y base.palabras.json."""
    with open(base + ".palabras.json", "w", encoding="utf-8") as f:
        json.dump({"palabras": palabras}, f, ensure_ascii=False, indent=1)
    bloques, actual = [], []
    for i, p in enumerate(palabras):
        actual.append(p)
        sig = palabras[i + 1] if i + 1 < len(palabras) else None
        largo = len(" ".join(x["texto"] for x in actual))
        if len(actual) >= 6 or largo >= 32 or p["texto"][-1:] in ".?!…" or not sig or sig["inicio"] - p["fin"] > 0.6:
            bloques.append(actual)
            actual = []
    with open(base + ".srt", "w", encoding="utf-8") as f:
        for n, b in enumerate(bloques, 1):
            f.write(f"{n}\n{_ts(b[0]['inicio'])} --> {_ts(b[-1]['fin'])}\n{' '.join(x['texto'] for x in b)}\n\n")
    return base + ".srt", base + ".palabras.json"


def transcribir(ruta, modelo="small", idioma="es"):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("Falta instalar Whisper: pip install faster-whisper")
    m = WhisperModel(modelo, device="auto", compute_type="auto")
    segmentos, _ = m.transcribe(ruta, language=idioma, word_timestamps=True, vad_filter=True)
    palabras = []
    for seg in segmentos:
        for w in seg.words or []:
            t = w.word.strip()
            if t:
                palabras.append({"texto": t, "inicio": round(w.start, 3), "fin": round(w.end, 3)})
    return palabras


def main(rutas, modelo="small"):
    if not rutas:
        print("Uso: python -m animaciones subtitular clip.mov [otro.mov ...]")
        return 1
    for r in rutas:
        print(f"Transcribiendo {os.path.basename(r)} (modelo {modelo})…")
        srt, js = escribir(transcribir(r, modelo), os.path.splitext(r)[0])
        print(f"  -> {os.path.basename(srt)} y {os.path.basename(js)}")
    print("En el editor: selecciona el clip, pestaña Narración → Subtítulos → Importar transcripción.")
    return 0
