"""
Borel, Pade y Laplace numerica (BRIEF 4.4, borel.py).

Normalizacion (Balser, [balser-2000:p97]): la transformada de Borel formal de orden k es
    (B_k f)(zeta) = sum_n f_n zeta^n / Gamma(1 + n/k).
Con k = 1 y la serie de Euler f_n = (-1)^n n!,  B_1 f = sum (-1)^n zeta^n = 1/(1 + zeta):
polo simple en zeta = -1, direccion singular arg z = pi.

Que hace cada pieza:
  borel(coefs, k)             coeficientes b_n = f_n / Gamma(1 + n/k) (mpf).
  singularidades_pade(b, L, M) polos del aproximante de Pade [L/M] de sum b_n zeta^n,
                              con mpmath.pade. Polos espurios: se filtran los que casi
                              cancelan con un cero (dobletes de Froissart) y se exige
                              estabilidad al variar (L, M).
  direcciones_singulares(polos)  argumentos de los polos, agrupados; y el radio de
                              convergencia estimado (modulo del polo mas cercano).
  laplace(b, k, d, z)         suma de Borel en direccion d: k z^{-k} int_0^{oo e^{id}}
                              B(u) exp(-(u/z)^k) u^{k-1} du, con B evaluada por Pade fuera
                              del disco de convergencia. Numerica (mpmath.quad).
  euler_funcion(z)            int_0^oo exp(-t/z)/(1+t) dt: la suma de Borel de Euler en
                              direccion 0, para comparar.

Aviso, como en pesos.py: esto REFUTA. Un polo que Pade ve en -1.0003 no demuestra nada
sobre la singularidad; un polo que Pade NO ve tampoco demuestra que no exista.
"""
from mpmath import mp, mpf, mpc, gamma, pade, polyroots, polyval, quad, exp, inf, pi, arg, fabs, log

mp.dps = 40


def borel(coefs, k=1):
    """b_n = f_n / Gamma(1 + n/k). coefs: lista de mpf/Fraction/int."""
    out = []
    for n, f in enumerate(coefs):
        f = mpf(f.numerator) / mpf(f.denominator) if hasattr(f, "numerator") else mpf(f)
        out.append(f / gamma(1 + mpf(n) / k))
    return out


def _pade(b, L, M):
    """Numerador p y denominador q (listas de coeficientes ascendentes) del Pade [L/M].
    None si el sistema es singular (pasa cuando la serie es racional de grado menor: la
    Borel de Euler es exactamente 1/(1+zeta) y un [20/20] no tiene sentido)."""
    try:
        p, q = pade(b[:L + M + 1], L, M)
    except ZeroDivisionError:
        return None
    return list(p), list(q)


def _serie_de_racional(p, q, N):
    """Primeros N+1 coeficientes de p(x)/q(x), p y q ascendentes, q[0] != 0."""
    inv = [1 / q[0]]
    for n in range(1, N + 1):
        s = mpc(0)
        for i in range(1, min(n, len(q) - 1) + 1):
            s += q[i] * inv[n - i]
        inv.append(-s / q[0])
    out = []
    for n in range(N + 1):
        s = mpc(0)
        for i in range(0, min(n, len(p) - 1) + 1):
            s += p[i] * inv[n - i]
        out.append(s)
    return out


def pade_minimo(b, tol=mpf("1e-18"), maximo=12):
    """
    (p, q, m) del menor Pade [m/m] que reproduce TODOS los coeficientes de b, o None.
    Si existe, la serie es (numericamente) racional de grado <= m: sus polos son las
    singularidades y ordenes mayores son degenerados y solo anaden basura.
    """
    N = len(b) - 1
    for m in range(1, min(maximo, N // 2) + 1):
        pq = _pade(b, m, m)
        if pq is None:
            continue
        p, q = pq
        c = _serie_de_racional(p, q, N)
        # comparacion RELATIVA coeficiente a coeficiente: una Borel entera tiene coeficientes
        # de 1e-30 que "coinciden" con cualquier racional si la tolerancia es absoluta
        escala = max(fabs(x) for x in b) or mpf(1)
        if all(fabs(c[n] - b[n]) <= tol * fabs(b[n]) for n in range(N + 1)
               if fabs(b[n]) > mpf("1e-35") * escala):
            return p, q, m
    return None


def ordenes_por_defecto(N):
    """(L, M) moderados y crecientes; los degenerados se saltan solos."""
    return [(m, m) for m in (2, 3, 4, 5, 6, 8, 10, 12) if 2 * m + 1 <= N + 1]


def singularidades_pade(b, L=None, M=None, tolerancia_doblete=mpf("1e-6")):
    """
    Polos del aproximante de Pade [L/M] de sum b_n zeta^n, sin dobletes de Froissart.
    Por defecto L = M = (len(b) - 1) // 2. Devuelve lista de mpc ordenada por modulo.
    """
    N = len(b) - 1
    L = L if L is not None else min(8, N // 2)
    M = M if M is not None else L
    pq = _pade(b, L, M)
    if pq is None:
        return []
    p, q = pq

    def raices(coefs_asc):
        # quitar coeficientes nulos de grado superior: polyroots no admite lider cero
        c = list(coefs_asc)
        while len(c) > 1 and fabs(c[-1]) < mpf("1e-30") * max(1, max(fabs(x) for x in c)):
            c.pop()
        return polyroots(list(reversed(c)), maxsteps=200, extraprec=60) if len(c) > 1 else []

    try:
        polos = raices(q)
        ceros = raices(p)
    except (ZeroDivisionError, ValueError):
        return []
    limpios = []
    for z in polos:
        if any(fabs(z - c) < tolerancia_doblete * max(1, fabs(z)) for c in ceros):
            continue                                  # polo que cancela con un cero: espurio
        limpios.append(mpc(z))
    return sorted(limpios, key=lambda z: fabs(z))


def singularidades_estables(b, ordenes=None, tolerancia=mpf("1e-3")):
    """
    Polos que aparecen en varios aproximantes de Pade con (L, M) distintos, cerca unos
    de otros. Es la unica forma razonable de distinguir singularidad de artefacto.
    Devuelve [(polo_medio, veces)] ordenado por modulo.
    """
    N = len(b) - 1
    ordenes = ordenes or ordenes_por_defecto(N)
    exacto = pade_minimo(b)
    if exacto is not None:                     # racional exacta: sus polos, sin votacion
        p, q, m = exacto
        polos = singularidades_pade(b, m, m)
        return [(z, len(ordenes)) for z in polos]
    conjuntos = [c for c in (singularidades_pade(b, L, M) for L, M in ordenes) if c]
    if not conjuntos:
        return []
    candidatos = [z for c in conjuntos for z in c]
    estables, usados = [], []
    for z in candidatos:
        if any(fabs(z - w) < tolerancia * max(1, fabs(w)) for w in usados):
            continue
        cerca = [w for c in conjuntos for w in c if fabs(w - z) < tolerancia * max(1, fabs(z))]
        veces = sum(1 for c in conjuntos if any(fabs(w - z) < tolerancia * max(1, fabs(z)) for w in c))
        if veces >= min(3, len(conjuntos)):
            media = sum(cerca) / len(cerca)
            estables.append((media, veces))
            usados.append(media)
    return sorted(estables, key=lambda t: fabs(t[0]))


def direcciones_singulares(polos, agrupar=mpf("0.05")):
    """
    [(direccion en radianes, modulo minimo)] a partir de los polos: direcciones singulares
    del plano de Borel y radio de convergencia estimado (el modulo del polo mas cercano).
    """
    dirs = []
    for z in polos:
        z = z[0] if isinstance(z, tuple) else z
        a, r = arg(z), fabs(z)
        for i, (d, rr) in enumerate(dirs):
            if fabs(d - a) < agrupar:
                dirs[i] = (d, min(rr, r))
                break
        else:
            dirs.append((a, r))
    return sorted(dirs, key=lambda t: t[1])


def radio_convergencia(polos):
    polos = [z[0] if isinstance(z, tuple) else z for z in polos]
    return min(fabs(z) for z in polos) if polos else inf


def laplace(b, k, d, z, L=None, M=None):
    """
    Suma de Borel de orden k en direccion d, evaluada en z:
        f(z) = k z^{-k} int_0^{oo e^{i d}} B(u) exp(-(u/z)^k) u^{k-1} du,
    con B = aproximante de Pade [L/M] de sum b_n u^n (prolonga fuera del disco).
    Normalizacion: la transformada de Laplace de u^lambda es Gamma(1 + lambda/k) z^lambda,
    inversa de la Borel de arriba [balser-2000:p95].
    """
    N = len(b) - 1
    exacto = pade_minimo(b) if L is None and M is None else None
    if exacto is not None:
        p, q, _ = exacto
    else:
        L = L if L is not None else min(8, N // 2)
        M = M if M is not None else L
        pq = _pade(b, L, M)
        while pq is None and L > 1:              # orden degenerado: bajar hasta que cuadre
            L -= 1
            M = L
            pq = _pade(b, L, M)
        if pq is None:
            raise ValueError("no hay aproximante de Pade no singular para esta serie")
        p, q = pq
    P = list(reversed(p))
    Q = list(reversed(q))
    z = mpc(z)
    e_id = exp(mpc(0, 1) * d)

    def integrando(t):
        u = t * e_id
        B = polyval(P, u) / polyval(Q, u)
        return B * exp(-(u / z) ** k) * u ** (k - 1) * e_id

    return k * z ** (-k) * quad(integrando, [0, 1, 10, inf])


def euler_funcion(z):
    """Suma de Borel de sum (-1)^n n! z^n en direccion 0, Re z > 0:
        E(z) = int_0^oo exp(-s) / (1 + z s) ds  =  (1/z) int_0^oo exp(-u/z) / (1 + u) du.
    (sum (-1)^n n! z^n = sum (-1)^n z^n int_0^oo s^n e^{-s} ds, intercambiando formalmente.)"""
    z = mpc(z)
    return quad(lambda s: exp(-s) / (1 + z * s), [0, 1, 10, inf])


def informe(coefs, k=1, nombre="f"):
    """Texto: singularidades estables, direcciones, radio. Sin veredicto."""
    b = borel(coefs, k)
    est = singularidades_estables(b)
    lineas = [f"Borel de orden {k} de {nombre}: {len(b)} coeficientes  (normalizacion [balser-2000:p97])"]
    if not est:
        lineas.append("  Pade no encuentra singularidades estables (serie convergente en el plano de Borel, o N corto)")
        return "\n".join(lineas)
    for z, veces in est[:6]:
        lineas.append(f"  polo en {mp.nstr(z, 8)}   |z| = {mp.nstr(fabs(z), 6)}   arg = {mp.nstr(arg(z), 6)}   ({veces} aproximantes)")
    for d, r in direcciones_singulares(est):
        lineas.append(f"  direccion singular arg = {mp.nstr(d, 6)} rad  (radio {mp.nstr(r, 6)})")
    lineas.append(f"  radio de convergencia estimado de la Borel: {mp.nstr(radio_convergencia(est), 6)}")
    return "\n".join(lineas)
