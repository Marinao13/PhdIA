"""
Estado del sistema. La unica fuente de verdad sobre la fase es el git log de
hoy. No hay ficheros de estado que se puedan editar a mano.

    inicio sesion X      -> fase 1  (motor OFF)
    sellado :: fase 1    -> fase 2  (motor ON)
    ataque               -> fase 3  (motor OFF)
    sellado :: fase 3    -> fase 4  (motor ON)

Sin sesion hoy -> 'libre' (motor ON: lagunas, laboratorio, etc.)
"""
import os, glob, subprocess, datetime
from . import config as C


def git(*args, check=False):
    r = subprocess.run(["git", *args], cwd=C.RAIZ, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError((r.stdout + r.stderr).strip())
    return r


def hay_repo():
    return git("rev-parse", "--git-dir").returncode == 0


def commits_todos():
    """[(datetime, mensaje)] de todo el historial, del mas antiguo al mas reciente."""
    return _parse_log(git("log", "--format=%aI%x09%s", "--reverse"))


def commits_hoy():
    """[(datetime, mensaje)] de hoy, del mas antiguo al mas reciente."""
    hoy = datetime.date.today().isoformat()
    return _parse_log(git("log", f"--since={hoy} 00:00", "--format=%aI%x09%s", "--reverse"))


def _parse_log(r):
    out = []
    for linea in r.stdout.splitlines():
        if "\t" not in linea:
            continue
        ts, msg = linea.split("\t", 1)
        out.append((datetime.datetime.fromisoformat(ts), msg))
    return out


def sellar(etiqueta):
    """git add -A + commit fechado. Devuelve (ok, mensaje)."""
    if not hay_repo():
        return False, "no hay repositorio git. Ejecuta: python instalar.py"
    git("add", "-A")
    marca = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    r = git("commit", "-q", "-m", f"{etiqueta} {marca}")
    if r.returncode == 0:
        return True, f"{etiqueta} {marca}"
    if "nothing to commit" in (r.stdout + r.stderr):
        return False, "nada que sellar: no has escrito nada desde el ultimo commit"
    return False, (r.stdout + r.stderr).strip()


def sesion_hoy():
    """Ruta de la sesion normal de hoy, o None. El diagnostico no cuenta."""
    hoy = datetime.date.today().isoformat()
    cands = [p for p in glob.glob(os.path.join(C.DIR_SESIONES, f"{hoy}-*.md"))
             if "diagnostico" not in os.path.basename(p)]
    return cands[0] if cands else None


def fase_actual():
    """
    Devuelve (fase, marcas) con fase en {'libre','f1','f2','f3','f4'} y
    marcas = {'inicio','sello1','ataque','sello3'} -> datetime o None.
    """
    marcas = dict(inicio=None, sello1=None, ataque=None, sello3=None)
    for ts, msg in commits_hoy():
        if msg.startswith("inicio sesion") or msg.startswith("inicio diagnostico"):
            # un inicio nuevo (p. ej. sesion tras el diagnostico) reinicia el ciclo
            marcas = dict(inicio=ts, sello1=None, ataque=None, sello3=None)
        elif msg.startswith("sellado :: fase 1") or msg.startswith("sellado :: diagnostico"):
            marcas["sello1"] = marcas["sello1"] or ts
        elif msg.startswith("ataque"):
            marcas["ataque"] = marcas["ataque"] or ts
        elif msg.startswith("sellado :: fase 3"):
            marcas["sello3"] = marcas["sello3"] or ts

    if sesion_hoy() is None and marcas["inicio"] is None:
        return "libre", marcas
    if marcas["sello1"] is None:
        return "f1", marcas
    if marcas["ataque"] is not None and marcas["sello3"] is None:
        return "f3", marcas
    if marcas["sello3"] is not None:
        return "f4", marcas
    return "f2", marcas


MOTOR_PERMITIDO = {"libre", "f2", "f4"}

EXPLICACION = {
    "f1": "estas en fase 1 (intento a ciegas). Escribe tu reconstruccion y "
          "luego:  python doc.py sellar 1",
    "f3": "estas en fase 3 (ataque). Motor apagado hasta:  python doc.py sellar 3",
}


def minutos(a, b):
    if a is None or b is None:
        return None
    return round((b - a).total_seconds() / 60, 1)
