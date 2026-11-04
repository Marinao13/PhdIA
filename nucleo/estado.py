"""
Estado del sistema. La unica fuente de verdad sobre la fase es el git log.
No hay ficheros de estado que se puedan editar a mano.

    inicio sesion X      -> fase 1  (motor OFF)
    sellado :: fase 1    -> fase 2  (motor ON)
    ataque               -> fase 3  (motor OFF)
    sellado :: fase 3    -> fase 4  (motor ON)
    cierre               -> libre
    pausa :: fase N      -> la misma fase, con el reloj parado
    reanudacion :: fase N-> la misma fase, reloj en marcha

Se mira el ultimo ciclo (desde su 'inicio'), no "los commits de hoy": una sesion que
empieza a las 22:00 sigue siendo la misma sesion a las 00:30, con el motor apagado si
toca. Un ciclo sin cerrar caduca cuando pasan VENTANA_HORAS sin ninguna marca suya,
salvo que este en pausa: una sesion pausada espera lo que haga falta, y `estado`
avisa cuando lleva mas de PAUSA_AVISO_HORAS. Los minutos de fase 1 y fase 3 descuentan
las pausas. Sin ciclo abierto -> 'libre' (motor ON: lagunas, laboratorio, etc.).
"""
import os, glob, subprocess, datetime
from . import config as C

VENTANA_HORAS = 20        # mas que la sesion mas larga posible, menos que un dia
PAUSA_AVISO_HORAS = 72    # una pausa mas larga pide reanudar o cerrar

MARCAS_CICLO = ("inicio sesion", "inicio diagnostico", "sellado ::", "ataque", "cierre",
                "pausa", "reanudacion")


_ENV_GIT = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")


def git(*args, check=False, timeout=None):
    """git en la raiz del repo. Con timeout, mata a git y a sus ayudantes (git-remote-http) si
    se pasa: en Windows, matar solo al padre deja la tuberia abierta y communicate() espera."""
    cmd = ["git", *args]
    if timeout is None:
        r = subprocess.run(cmd, cwd=C.RAIZ, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, env=_ENV_GIT)
    else:
        p = subprocess.Popen(cmd, cwd=C.RAIZ, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", env=_ENV_GIT)
        try:
            out, err = p.communicate(timeout=timeout)
            r = subprocess.CompletedProcess(cmd, p.returncode, out, err)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            else:
                p.kill()
            try:
                p.communicate(timeout=5)
            except Exception:
                pass
            r = subprocess.CompletedProcess(cmd, 124, "", "tiempo agotado")
    if check and r.returncode != 0:
        raise RuntimeError((r.stdout + r.stderr).strip())
    return r


# --- dos maquinas: el log de git es la fase, asi que viaja con pull y push ---------------
SIN_RED = os.environ.get("DOC_SIN_RED", "") not in ("", "0", "false")
_SINCRONIZADO = None      # aviso de la primera sincronizacion del proceso; las siguientes no repiten el fetch


def _remoto():
    """Rama remota de seguimiento ('origin/master'), o None si no hay."""
    r = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def sincronizar_antes():
    """
    Antes de leer la fase o sellar: trae el remoto y avanza en linea recta si otra maquina
    sello algo. Una vez por proceso. Devuelve un aviso (vacio si todo fue bien o no hay
    remoto). Nunca bloquea mas de unos segundos.
    """
    global _SINCRONIZADO
    if _SINCRONIZADO is not None:
        return _SINCRONIZADO
    if SIN_RED or not _remoto():
        _SINCRONIZADO = ""
        return ""
    r = git("fetch", "-q", timeout=15)
    if r.returncode != 0:
        _SINCRONIZADO = "sin red: no se pudo traer el remoto. Haz git pull antes de cambiar de maquina."
        return _SINCRONIZADO
    r = git("merge", "--ff-only", "-q", "@{u}")
    if r.returncode == 0:
        _SINCRONIZADO = ""
    elif git("merge-base", "--is-ancestor", "HEAD", "@{u}").returncode == 0:
        # el remoto va por delante en linea recta, pero toca ficheros que aqui estan sin sellar
        ficheros = [l.strip() for l in (r.stdout + r.stderr).splitlines() if l.startswith("\t")]
        _SINCRONIZADO = ("el remoto tiene sellados nuevos que cambian ficheros que aqui tienes sin sellar"
                         + (": " + ", ".join(ficheros[:4]) if ficheros else "")
                         + ". Este sellado creara divergencia: sella y luego git pull (o git stash, git pull, git stash pop).")
    else:
        _SINCRONIZADO = ("el remoto y esta maquina divergen (sellados en las dos sin sincronizar): "
                         "resuelve con git pull antes de seguir; este sellado se hace igualmente.")
    return _SINCRONIZADO


def empujar_despues():
    """Tras sellar: push al remoto. Devuelve un aviso (vacio si fue bien o no hay remoto)."""
    if SIN_RED or not _remoto():
        return ""
    r = git("push", "-q", timeout=20)
    if r.returncode != 0:
        return "sin push: la otra maquina no vera este sellado hasta que hagas git push."
    return ""


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


def ahora():
    return datetime.datetime.now().astimezone()


def sellar(etiqueta, vacio_ok=False):
    """
    Sincroniza, git add -A, commit fechado y push. Devuelve (ok, mensaje); el mensaje lleva
    los AVISOS de red (sin red, sin push, divergencia) para que todo comando los imprima.
    vacio_ok: deja la marca aunque no haya cambios (commit vacio): ataque, pausa, reanudacion.
    """
    if not hay_repo():
        return False, "no hay repositorio git. Ejecuta: python instalar.py"
    avisos = [sincronizar_antes()]
    git("add", "-A")
    marca = ahora().strftime("%Y-%m-%d %H:%M")
    r = git("commit", "-q", "-m", f"{etiqueta} {marca}")
    if r.returncode != 0 and "nothing to commit" in (r.stdout + r.stderr):
        if not vacio_ok:
            return False, "nada que sellar: no has escrito nada desde el ultimo commit" \
                + "".join("\n  AVISO: " + a for a in avisos if a)
        r = git("commit", "-q", "--allow-empty", "-m", f"{etiqueta} {marca}")
    if r.returncode != 0:
        return False, (r.stdout + r.stderr).strip() or "git commit fallo sin mensaje"
    avisos.append(empujar_despues())
    return True, f"{etiqueta} {marca}" + "".join("\n  AVISO: " + a for a in avisos if a)


def marcar(etiqueta):
    """Como sellar, pero deja la marca aunque no haya cambios (commit vacio). (ok, mensaje)."""
    return sellar(etiqueta, vacio_ok=True)


def _marcas_vacias():
    return dict(inicio=None, sello1=None, ataque=None, sello3=None,
                pausas=[], pausada=False, ultimo=None, caducado=False)


def _ciclo(commits=None, en=None):
    """
    (marcas, cerrado) del ultimo ciclo del historial. Cada 'inicio' arranca un ciclo
    nuevo; 'cierre' lo termina; sin cierre, caduca pasadas VENTANA_HORAS desde su
    ultima marca, salvo en pausa. marcas = {'inicio','sello1','ataque','sello3'} ->
    datetime o None; 'pausas' -> [[t_pausa, t_reanudacion o None], ...]; 'pausada';
    'ultimo' (ultima marca del ciclo); 'caducado'.
    """
    en = en or ahora()
    marcas = _marcas_vacias()
    cerrado = False
    for ts, msg in (commits_todos() if commits is None else commits):
        if msg.startswith("inicio sesion") or msg.startswith("inicio diagnostico"):
            marcas = _marcas_vacias()
            marcas["inicio"] = ts
            cerrado = False
        elif marcas["inicio"] is None:
            continue                                   # antes de cualquier ciclo
        elif msg.startswith("sellado :: fase 1") or msg.startswith("sellado :: diagnostico"):
            marcas["sello1"] = marcas["sello1"] or ts
        elif msg.startswith("ataque"):
            marcas["ataque"] = marcas["ataque"] or ts
        elif msg.startswith("sellado :: fase 3"):
            marcas["sello3"] = marcas["sello3"] or ts
        elif msg.startswith("cierre"):
            cerrado = True
        elif msg.startswith("pausa"):
            if not marcas["pausada"]:
                marcas["pausas"].append([ts, None])
                marcas["pausada"] = True
        elif msg.startswith("reanud"):
            if marcas["pausada"]:
                marcas["pausas"][-1][1] = ts
                marcas["pausada"] = False
        else:
            continue                                   # commit ajeno: no toca el ciclo
        marcas["ultimo"] = ts
    if marcas["inicio"] and not cerrado and not marcas["pausada"] \
            and en - marcas["ultimo"] > datetime.timedelta(hours=VENTANA_HORAS):
        marcas["caducado"] = True
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
    Devuelve (fase, marcas) con fase en {'libre','f1','f2','f3','f4'} y marcas como
    en _ciclo (con 'pausas' y 'pausada'). Una pausa no cambia la fase.
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


def minutos_netos(a, b, pausas=(), en=None):
    """Minutos entre a y b descontando las pausas que caen dentro (una pausa sin
    reanudar cuenta hasta `en`, por defecto ahora)."""
    if a is None or b is None:
        return None
    en = en or ahora()
    total = (b - a).total_seconds()
    for p, r in pausas:
        r = r or en
        solape = (min(r, b) - max(p, a)).total_seconds()
        if solape > 0:
            total -= solape
    return round(total / 60, 1)


def horas_pausada(marcas, en=None):
    """Horas que lleva pausado el ciclo, o None si no esta en pausa."""
    if not marcas.get("pausada") or not marcas.get("pausas"):
        return None
    en = en or ahora()
    return round((en - marcas["pausas"][-1][0]).total_seconds() / 3600, 1)
