"""Convierte videos (por ejemplo HEVC/HDR de iPhone) a H.264 de muy alta calidad que abre cualquier navegador
y editor: misma resolución y cuadros por segundo, CRF 14 (visualmente sin pérdida) y audio AAC 320 kbps."""
import json
import os
import subprocess

HDR = {"arib-std-b67", "smpte2084"}  # HLG (iPhone) y PQ


def info(ruta):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=codec_name,color_transfer,width,height,r_frame_rate", "-of", "json", ruta],
                       capture_output=True, text=True, check=True)
    flujos = json.loads(r.stdout).get("streams", [])
    return flujos[0] if flujos else None


def convertir(ruta, carpeta_salida=None, forzar=False):
    v = info(ruta)
    if not v:
        print(f"  {ruta}: no tiene video, se omite")
        return None
    if v.get("codec_name") == "h264" and v.get("color_transfer") not in HDR and not forzar:
        print(f"  {os.path.basename(ruta)}: ya es compatible (H.264), no hace falta convertir")
        return ruta
    base = os.path.splitext(os.path.basename(ruta))[0]
    salida = os.path.join(carpeta_salida or os.path.dirname(os.path.abspath(ruta)), base + "_compatible.mp4")
    filtros = []
    if v.get("color_transfer") in HDR:
        # HDR -> SDR para que no se vea deslavado en navegadores y redes
        filtros = ["zscale=t=linear:npl=203", "format=gbrpf32le", "zscale=p=bt709",
                   "tonemap=tonemap=hable:desat=0", "zscale=t=bt709:m=bt709:r=tv", "format=yuv420p"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats", "-i", ruta, "-map", "0:v:0", "-map", "0:a?",
           "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart", "-map_metadata", "0"]
    if filtros:
        cmd += ["-vf", ",".join(filtros)]
    cmd.append(salida)
    print(f"  {os.path.basename(ruta)} ({v.get('codec_name')}, {v.get('width')}x{v.get('height')}"
          f"{', HDR' if filtros else ''}) -> {os.path.basename(salida)}")
    subprocess.run(cmd, check=True)
    return salida


def main(rutas, carpeta_salida=None, forzar=False):
    archivos = []
    for r in rutas:
        if os.path.isdir(r):
            archivos += [os.path.join(r, f) for f in sorted(os.listdir(r))
                         if f.lower().endswith((".mov", ".mp4", ".m4v", ".hevc", ".mkv")) and "_compatible" not in f]
        else:
            archivos.append(r)
    if not archivos:
        print("No encontré videos para convertir.")
        return 1
    if carpeta_salida:
        os.makedirs(carpeta_salida, exist_ok=True)
    print(f"Convirtiendo {len(archivos)} videos…")
    for a in archivos:
        convertir(a, carpeta_salida, forzar)
    print("Listo. Importa los archivos *_compatible.mp4 en el editor.")
    return 0
