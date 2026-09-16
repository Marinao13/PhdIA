"""
Estimador de clase de crecimiento (BRIEF 4.4, growth.py).

Para una serie con coeficientes a_n, tres miradas independientes sobre la cola:

  ajuste_cola    minimos cuadrados de  log|a_n| ~ alpha * n log n + n log A + c
                 en n >= N/2. Devuelve alpha, log A, c y un intervalo tosco: la
                 dispersion de alpha al ajustar en dos mitades de la cola.
  cocientes      log|a_{n+1}/a_n| ~ alpha log n + log A. Menos sensible a c, mas
                 ruidoso con eps_n.
  roumieu_beurling(a, M)  c_n = (|a_n| / M_n)^(1/n) frente a una sucesion M dada.
                 Roumieu: c_n acotada (existe A). Beurling: c_n -> 0 (para todo A).
                 Lo segundo se ve MAL numericamente: una cota grande y un limite
                 cero se distinguen solo por la pendiente de log c_n, y con N
                 finito la pendiente es una estimacion, no una prueba.

Todo en escala logaritmica con mpmath: (n!)^2 con n = 200 no cabe en un float.
Es un motor de refutacion, como pesos.py: un alpha ~ 1 dice "compatible con
Gevrey-1", no "es Gevrey-1".
"""
from mpmath import mp, mpf, log, loggamma, inf
import numpy as np

mp.dps = 40


def _logabs(coefs):
    """[(n, log|a_n|)] para a_n != 0."""
    out = []
    for n, a in enumerate(coefs):
        a = mpf(a) if not hasattr(a, "real") or isinstance(a, (int, float)) else a
        m = abs(a)
        if m > 0:
            out.append((n, float(log(m))))
    return out


def _cola(pares, desde=None):
    N = pares[-1][0]
    desde = desde if desde is not None else max(4, N // 2)
    return [(n, v) for n, v in pares if n >= desde]


def ajuste_cola(coefs, desde=None):
    """
    Ajuste log|a_n| = alpha n log n + n log A + c en la cola.
    Devuelve dict(alpha, logA, c, residuo, intervalo=(alpha_1a_mitad, alpha_2a_mitad), n_puntos).
    """
    pares = _cola(_logabs(coefs), desde)
    if len(pares) < 6:
        raise ValueError("cola demasiado corta para ajustar (hace falta N mayor)")

    def ajustar(ps):
        n = np.array([p[0] for p in ps], dtype=float)
        y = np.array([p[1] for p in ps], dtype=float)
        X = np.column_stack([n * np.log(n), n, np.ones_like(n)])
        sol, res, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = float(np.sqrt(np.mean((X @ sol - y) ** 2)))
        return sol, r

    sol, res = ajustar(pares)
    mitad = len(pares) // 2
    a1, _ = ajustar(pares[:mitad]) if mitad >= 4 else (sol, 0)
    a2, _ = ajustar(pares[mitad:]) if len(pares) - mitad >= 4 else (sol, 0)
    return dict(alpha=float(sol[0]), logA=float(sol[1]), c=float(sol[2]), residuo=res,
                intervalo=(min(a1[0], a2[0]), max(a1[0], a2[0])), n_puntos=len(pares))


def cocientes(coefs, desde=None):
    """
    Ajuste de log|a_{n+1}/a_n| = alpha log n + log A en la cola.
    Devuelve dict(alpha, logA, intervalo, n_puntos). Con signos alternos usa |.|.
    """
    la = dict(_logabs(coefs))
    N = max(la)
    desde = desde if desde is not None else max(4, N // 2)
    ps = [(n, la[n + 1] - la[n]) for n in range(desde, N) if n in la and n + 1 in la]
    if len(ps) < 6:
        raise ValueError("cola demasiado corta")

    def ajustar(qs):
        x = np.log(np.array([q[0] for q in qs], dtype=float))
        y = np.array([q[1] for q in qs], dtype=float)
        X = np.column_stack([x, np.ones_like(x)])
        sol, *_ = np.linalg.lstsq(X, y, rcond=None)
        return sol

    sol = ajustar(ps)
    m = len(ps) // 2
    a1, a2 = ajustar(ps[:m]), ajustar(ps[m:])
    return dict(alpha=float(sol[0]), logA=float(sol[1]),
                intervalo=(min(a1[0], a2[0]), max(a1[0], a2[0])), n_puntos=len(ps))


def roumieu_beurling(coefs, logM, desde=None, puntos=5):
    """
    c_n = (|a_n| / M_n)^(1/n) con logM[n] = log M_n (como en lab/pesos.py).
    Devuelve dict(valores=[(n, c_n)], sup_cola, pendiente_log) donde pendiente_log
    es la pendiente de log c_n frente a log n en la cola: ~0 o positiva sugiere
    Roumieu (acotada); claramente negativa sugiere Beurling (tiende a 0).
    """
    la = dict(_logabs(coefs))
    N = min(max(la), len(logM) - 1)
    desde = desde if desde is not None else max(4, N // 2)
    ns = [n for n in range(desde, N + 1) if n in la]
    lc = {n: (la[n] - float(logM[n])) / n for n in ns}
    if len(ns) < 6:
        raise ValueError("cola demasiado corta")
    x = np.log(np.array(ns, dtype=float))
    y = np.array([lc[n] for n in ns])
    pend = float(np.polyfit(x, y, 1)[0])
    paso = max(1, len(ns) // puntos)
    valores = [(n, float(np.exp(lc[n]))) for n in ns[::paso]]
    return dict(valores=valores, sup_cola=float(np.exp(max(y))), pendiente_log=pend)


def informe(serie, logM=None, nombre_M="M"):
    """Texto con las tres miradas. Sin veredicto: los numeros y sus intervalos."""
    coefs = serie.coeficientes_mp() if hasattr(serie, "coeficientes_mp") else list(serie)
    lineas = [f"serie {getattr(serie, 'nombre', '')}  N={len(coefs) - 1}"]
    try:
        a = ajuste_cola(coefs)
        lineas.append(f"  ajuste de cola   alpha = {a['alpha']:.3f}  [{a['intervalo'][0]:.3f}, {a['intervalo'][1]:.3f}]"
                      f"   log A = {a['logA']:.3f}   residuo {a['residuo']:.3f}   ({a['n_puntos']} puntos)")
    except ValueError as ex:
        lineas.append(f"  ajuste de cola   {ex}")
    try:
        q = cocientes(coefs)
        lineas.append(f"  cocientes        alpha = {q['alpha']:.3f}  [{q['intervalo'][0]:.3f}, {q['intervalo'][1]:.3f}]"
                      f"   log A = {q['logA']:.3f}")
    except ValueError as ex:
        lineas.append(f"  cocientes        {ex}")
    if logM is not None:
        r = roumieu_beurling(coefs, logM)
        vals = "  ".join(f"c_{n}={v:.3g}" for n, v in r["valores"])
        lineas.append(f"  frente a {nombre_M}:  {vals}")
        lineas.append(f"  sup en la cola {r['sup_cola']:.3g};  pendiente de log c_n: {r['pendiente_log']:+.3f}"
                      "  (~0 o >0: compatible con Roumieu; claramente <0: compatible con Beurling)")
    return "\n".join(lineas)
