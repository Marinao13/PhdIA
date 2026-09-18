"""
Raices multiples de P(z, y) = 0: poligono de Newton, ramificacion y Puiseux (BRIEF 4.4, 4g).

P(z, y) = sum_i p_i(z) y^i con p_i Series exactas (Fraction). Algoritmo clasico:

  1. Puntos (i, ord_z p_i) para cada p_i no nulo. Poligono de Newton = envolvente
     convexa inferior. Cada arista de pendiente -mu (mu = a/r en terminos reducidos,
     mu >= 0) corresponde a ramas y ~ c z^mu.
  2. En la arista, los terminos dominantes dan la ecuacion caracteristica
        sum_{(i, ord) en la arista} lc(p_i) c^i = 0
     cuyas raices c != 0 (racionales aqui; para otras, pasa c a mano) son los
     coeficientes iniciales.
  3. Ramificar: z = t^r, y = t^a (c + y_1). Si c es raiz simple de la caracteristica,
     y_1 es una raiz simple de la ecuacion transformada con y_1(0) = 0 y se termina con
     Hensel (algebraic.py). Si es multiple, se repite el poligono sobre la transformada
     (profundidad acotada).
  Cada rama es una Serie en t, con z = t^r; la traza registra aristas, mu, r, c.

Test 4 del BRIEF: y^2 = z (1 + z f(z)). Puntos (2, 0) y (0, 1): una arista de pendiente
-1/2, mu = 1/2, r = 2; caracteristica c^2 - 1 = 0, c = +-1, simples; z = t^2,
y = t (+-1 + y_1), y_1 por Hensel. Dos ramas de Puiseux y = +-z^{1/2} (1 + ...).

Con Sage (WSL) esto lo hace `puiseux`; aqui basta Fraction, como decidio Mariano.
"""
from fractions import Fraction
from math import gcd

try:
    from .series import Serie
    from . import algebraic as A
except ImportError:            # ejecutado como script desde lab/
    from series import Serie
    import algebraic as A


def _orden(p):
    """ord_z de una Serie (indice del primer coeficiente no nulo), o None si es nula."""
    for n, c in enumerate(p.c):
        if c != 0:
            return n
    return None


def poligono(P):
    """
    Aristas del poligono de Newton de P = [p_0, ..., p_d]: lista de dicts con
    puntos (i, ord), pendiente y mu = -pendiente (>= 0 para ramas y -> 0).
    """
    puntos = [(i, _orden(p)) for i, p in enumerate(P)]
    puntos = [(i, o) for i, o in puntos if o is not None]
    if len(puntos) < 2:
        raise ValueError("P necesita al menos dos coeficientes no nulos")
    # envolvente convexa inferior (monotona en i), Andrew
    inf = []
    for pt in puntos:
        while len(inf) >= 2:
            (x1, y1), (x2, y2) = inf[-2], inf[-1]
            x3, y3 = pt
            if (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1) <= 0:   # giro no a la izquierda
                inf.pop()
            else:
                break
        inf.append(pt)
    aristas = []
    for (x1, y1), (x2, y2) in zip(inf, inf[1:]):
        pend = Fraction(y2 - y1, x2 - x1)
        mu = -pend
        en_arista = [(i, o) for i, o in puntos if Fraction(o - y1) == pend * (i - x1)]
        aristas.append(dict(puntos=en_arista, pendiente=pend, mu=mu))
    return aristas


def caracteristica(P, arista):
    """Coeficientes (Fraction, grado creciente en c) de sum lc(p_i) c^i sobre la arista."""
    grado = max(i for i, _ in arista["puntos"])
    coefs = [Fraction(0)] * (grado + 1)
    for i, o in arista["puntos"]:
        coefs[i] = Fraction(P[i].c[o])
    return coefs


def raices_racionales(coefs):
    """Raices racionales no nulas de un polinomio con coeficientes Fraction, con multiplicidad."""
    from sympy import Poly, symbols, Rational
    x = symbols("x")
    pol = Poly(sum(Rational(c.numerator, c.denominator) * x ** i for i, c in enumerate(coefs)), x)
    out = []
    for r_, mult in pol.ground_roots().items():
        if r_.is_rational and r_ != 0:
            out.append((Fraction(int(r_.p), int(r_.q)), int(mult)))
    return sorted(out)


def _sustituir(P, r, a, c, N):
    """
    Q(t, y_1) = t^(-s) P(t^r, t^a (c + y_1)), truncada a orden N en t, como lista de Series
    en t. s = min exponente en t, para que Q tenga termino no nulo en t^0.
    """
    d = len(P) - 1
    # p_i(t^r): reindexar coeficientes
    Pt = []
    for p in P:
        cs = [Fraction(0)] * (N + 1)
        for n, coef in enumerate(p.c):
            if n * r <= N:
                cs[n * r] = Fraction(coef)
        Pt.append(Serie(cs))
    # (c + y_1)^i = sum_j C(i, j) c^(i-j) y_1^j ; y^i = t^(a i) (c + y_1)^i
    from math import comb
    Q = [Serie([Fraction(0)] * (N + 1)) for _ in range(d + 1)]      # coeficiente de y_1^j
    for i in range(d + 1):
        pi = Pt[i]
        if all(x == 0 for x in pi.c):
            continue
        desplazado = Serie([Fraction(0)] * (a * i) + pi.c[:max(0, N + 1 - a * i)]) if a * i <= N \
            else Serie([Fraction(0)] * (N + 1))
        for j in range(i + 1):
            Q[j] = Q[j] + desplazado * (Fraction(comb(i, j)) * c ** (i - j))
    s = min(_orden(q) for q in Q if _orden(q) is not None)
    Q = [Serie(q.c[s:] + [Fraction(0)] * s) for q in Q]
    return Q


def ramas(P, N=None, profundidad=3, traza=None):
    """
    Ramas de Puiseux de P(z, y) = 0 con y -> 0: lista de dicts
        dict(r, a, c, mu, y_t=Serie en t)   con z = t^r,  y = t^a (c + y_1(t)).
    Solo raices caracteristicas racionales no nulas (las demas: pasa c a mano).
    traza (lista) recibe lineas legibles del poligono y de cada paso.
    """
    N = N if N is not None else min(p.N for p in P)
    out = []
    for arista in poligono(P):
        mu = arista["mu"]
        if mu < 0:
            continue                                  # ramas con y -> infinito: no aqui
        a, r = mu.numerator, mu.denominator
        car = caracteristica(P, arista)
        if traza is not None:
            traza.append(f"arista {arista['puntos']}  pendiente {arista['pendiente']}  mu = {mu} = {a}/{r}"
                         f"  caracteristica {car}")
        for c, mult in raices_racionales(car):
            Q = _sustituir(P, r, a, c, N)
            if mult == 1:
                y1 = A.hensel(Q, Fraction(0), N)
                # y = t^a (c + y_1): desplazar y sumar c en t^a
                y_t = Serie([Fraction(0)] * (N + 1))
                for n, coef in enumerate(y1.c):
                    if n + a <= N:
                        y_t.c[n + a] += coef
                if a <= N:
                    y_t.c[a] += c
                out.append(dict(r=r, a=a, c=c, mu=mu, y_t=y_t, multiplicidad=1))
                if traza is not None:
                    traza.append(f"  c = {c} simple: z = t^{r}, y = t^{a} ({c} + y_1), Hensel en t")
            else:
                if traza is not None:
                    traza.append(f"  c = {c} multiple (x{mult}): poligono de la transformada (profundidad {profundidad})")
                if profundidad <= 0:
                    out.append(dict(r=r, a=a, c=c, mu=mu, y_t=None, multiplicidad=mult))
                    continue
                sub = ramas(Q, N, profundidad - 1, traza)
                for s_ in sub:
                    # y = t^a (c + y_1),  y_1 en t' con t = t'^{r'}: componer ramificaciones
                    rr = r * s_["r"]
                    y_t = Serie([Fraction(0)] * (N + 1))
                    for n, coef in enumerate(s_["y_t"].c if s_["y_t"] else []):
                        if n + a * s_["r"] <= N:
                            y_t.c[n + a * s_["r"]] += coef
                    if a * s_["r"] <= N:
                        y_t.c[a * s_["r"]] += c
                    out.append(dict(r=rr, a=a * s_["r"], c=c, mu=mu, y_t=y_t, multiplicidad=mult))
    return out


def comprobar(P, rama, N=None):
    """Residuo P(t^r, y(t)) truncado: todo cero si la rama es correcta."""
    r, y_t = rama["r"], rama["y_t"]
    N = N if N is not None else y_t.N
    Pt = []
    for p in P:
        cs = [Fraction(0)] * (N + 1)
        for n, coef in enumerate(p.c):
            if n * r <= N:
                cs[n * r] = Fraction(coef)
        Pt.append(Serie(cs))
    return A.evaluar(Pt, y_t.truncar(N))
