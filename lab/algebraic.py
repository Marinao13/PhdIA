"""
Solucion formal de P(z, y) = 0 con coeficientes series formales (BRIEF 4.4, algebraic.py).

Raiz simple: Hensel / Newton. Dados P(z, y) = sum_i p_i(z) y^i con p_i Series (Fraction,
exactas) y una raiz y_0 de P(0, y) con P_y(0, y_0) != 0, la iteracion
    y_{k+1} = y_k - P(z, y_k) / P_y(z, y_k)
converge cuadraticamente en el orden de truncacion: cada paso dobla los coeficientes
correctos. Todo exacto en Fraction; la traza registra el orden alcanzado en cada paso.

Raiz multiple (poligono de Newton, ramificacion z = t^r, Puiseux): fase 4g, no aqui.
"""
from fractions import Fraction
try:
    from .series import Serie
except ImportError:            # ejecutado como script desde lab/
    from series import Serie


def _cero(N):
    return Serie([Fraction(0)] * (N + 1))


def _constante(c, N):
    return Serie([Fraction(c)] + [Fraction(0)] * N)


def evaluar(P, y):
    """P(z, y) para P = [p_0, p_1, ..., p_d] (lista de Series) y y Serie. Horner truncado."""
    N = y.N
    r = _cero(N)
    for p in reversed(P):
        r = r * y + p.truncar(N)
    return r


def derivada_y(P):
    """P_y = sum_i i p_i y^(i-1) como lista de Series."""
    return [p * Fraction(i) for i, p in enumerate(P)][1:] or [_cero(P[0].N)]


def raices_iniciales(P):
    """Raices racionales de P(0, y) por prueba de divisores (suficiente para los tests;
    para una raiz no racional pasa y0 a mano)."""
    coefs = [Fraction(p.c[0]) for p in P]
    while coefs and coefs[-1] == 0:
        coefs.pop()
    if len(coefs) <= 1:
        return []
    from sympy import Poly, symbols, Rational
    y = symbols("y")
    pol = Poly(sum(Rational(c.numerator, c.denominator) * y ** i for i, c in enumerate(coefs)), y)
    return sorted(Fraction(int(r.p), int(r.q)) for r in pol.ground_roots() if r.is_rational)


def hensel(P, y0, N=None, traza=None):
    """
    Raiz y(z) de P(z, y) = 0 con y(0) = y0 simple, truncada a orden N. Exacta (Fraction).
    traza, si es lista, recibe (paso, orden_correcto_estimado).
    """
    N = N if N is not None else min(p.N for p in P)
    y0 = Fraction(y0)
    P = [p.truncar(N) for p in P]
    Py = derivada_y(P)
    if evaluar(P, _constante(y0, 0)).c[0] != 0:
        raise ValueError(f"{y0} no es raiz de P(0, y)")
    if evaluar(Py, _constante(y0, 0)).c[0] == 0:
        raise ValueError(f"{y0} es raiz multiple de P(0, y): poligono de Newton (fase 4g), no Hensel")
    y = _constante(y0, N)
    orden = 1
    paso = 0
    while orden <= N:
        paso += 1
        y = y - evaluar(P, y) / evaluar(Py, y)
        orden *= 2
        if traza is not None:
            traza.append((paso, min(orden, N + 1)))
    return y


def raiz_simple(P, y0=None, N=None, traza=None):
    """Como hensel, eligiendo y0 entre las raices racionales de P(0, y) si no se da."""
    if y0 is None:
        cands = raices_iniciales(P)
        if not cands:
            raise ValueError("P(0, y) no tiene raices racionales: pasa y0")
        y0 = cands[0]
    return hensel(P, y0, N, traza)
