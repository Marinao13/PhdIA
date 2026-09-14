"""
Estado del sistema. La unica fuente de verdad sobre la fase es el git log.
No hay ficheros de estado que se puedan editar a mano.

    inicio sesion X      -> fase 1  (motor OFF)
    sellado :: fase 1    -> fase 2  (motor ON)
    ataque               -> fase 3  (motor OFF)
    sellado :: fase 3    -> fase 4  (motor ON)
    cierre               -> libre

Se mira el ultimo ciclo abierto en las ultimas VENTANA_HORAS, no "los commits
de hoy": una sesion que empieza a las 22:00 sigue siendo la misma sesion a las
00:30, con el motor apagado si toca. Sin ciclo abierto -> 'libre' (motor ON:
lagunas, laboratorio, etc.).
"""
import os, glob, subprocess, datetime
from . import config as C

VENTANA_HORAS = 20   # mas que la sesion mas larga posible, menos que un dia


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


def commits_recientes():
    """[(datetime, mensaje)] de las ultimas VENTANA_HORAS, del mas antiguo al mas reciente."""
    desde = datetime.datetime.now().astimezone() - datetime.timedelta(hours=VENTANA_HORAS)
    return _parse_log(git("log", f"--since={desde.isoformat()}", "--format=%aI%x09%s", "--reverse"))


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


def _ciclo(commits=None):
    """
    (marcas, cerrado) del ultimo ciclo en la ventana. Cada 'inicio' arranca
    un ciclo nuevo; 'cierre' lo termina. marcas = {'inicio','sello1',
    'ataque','sello3'} -> datetime o None.
    """
    marcas = dict(inicio=None, sello1=None, ataque=None, sello3=None)
    cerrado = False
    for ts, msg in (commits_recientes() if commits is None else commits):
        if msg.startswith("inicio sesion") or msg.startswith("inicio diagnostico"):
            marcas = dict(inicio=ts, sello1=None, ataque=None, sello3=None)
            cerrado = False
        elif msg.startswith("sellado :: fase 1") or msg.startswith("sellado :: diagnostico"):
            marcas["sello1"] = marcas["sello1"] or ts
        elif msg.startswith("ataque"):
            marcas["ataque"] = marcas["ataque"] or ts
        elif msg.startswith("sellado :: fase 3"):
            marcas["sello3"] = marcas["sello3"] or ts
        elif msg.startswith("cierre"):
            cerrado = True
    return marcas, cerrado


def fecha_sesion():
    """La fecha con la que se nombro la sesion en curso: la del 'inicio' del
    ciclo abierto, o la de hoy si no hay ninguno."""
    marcas, cerrado = _ciclo()
    if marcas["inicio"] and not cerrado:
        return marcas["inicio"].date().isoformat()
    return datetime.date.today().isoformat()


def sesion_hoy():
    """Ruta de la sesion normal en curso, o None. El diagnostico no cuenta."""
    dia = fecha_sesion()
    cands = [p for p in glob.glob(os.path.join(C.DIR_SESIONES, f"{dia}-*.md"))
             if "diagnostico" not in os.path.basename(p)]
    return cands[0] if cands else None


def fase_actual():
    """
    Devuelve (fase, marcas) con fase en {'libre','f1','f2','f3','f4'} y
    marcas = {'inicio','sello1','ataque','sello3'} -> datetime o None.
    """
    marcas, cerrado = _ciclo()
    if cerrado:
        return "libre", marcas
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
