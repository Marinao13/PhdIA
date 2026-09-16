"""
Series formales truncadas (BRIEF 4.4, series.py).

Una `Serie` es una lista de coeficientes a_0..a_N. Los coeficientes son lo que le
des: `Fraction` para aritmetica exacta (algebraic.py, Euler, Catalan) o `mpf` de
mpmath para crecimiento prescrito no racional ((n!)^alpha con alpha real). No se
mezclan tipos dentro de una serie.

Generadores con crecimiento prescrito y SEMILLA FIJA (reproducible):
    gevrey(alpha)                    a_n = eps_n (n!)^alpha,  eps_n en [1/2, 2]
    fuertemente_regular(alpha, beta) a_n = eps_n (n!)^alpha (log(n+e))^(beta n)
    q_gevrey(q)                      a_n = eps_n q^(n^2)         (falla (mg): frontera)
    euler()                          sum (-1)^n n! z^n, exacta
    catalan()                        raiz de y^2 - y + z = 0, exacta (convergente)

Construccion desde una transformada de Borel dada, con singularidades donde se
quiera. Normalizacion de Balser: la transformada de Borel formal de orden k es
    (B_k f)(z) = sum_n f_n z^n / Gamma(1 + n/k)        [balser-2000:p97]
asi que, dada B(zeta) = sum_n b_n zeta^n con polos simples en zeta_j,
    f_n = b_n Gamma(1 + n/k),   b_n = sum_j r_j / zeta_j^(n+1)   (residuo r_j en zeta_j)
Para k = 1 y un polo en -1 con residuo -1 se recupera la serie de Euler.
"""
import random
from fractions import Fraction
from mpmath import mp, mpf, gamma, loggamma, log, e, factorial

mp.dps = 40
SEMILLA = 20260917


class Serie:
    """Serie formal truncada a orden N: coeficientes c[0..N]."""

    def __init__(self, coefs, nombre="f"):
        self.c = list(coefs)
        self.nombre = nombre

    @property
    def N(self):
        return len(self.c) - 1

    def __getitem__(self, n):
        return self.c[n] if 0 <= n <= self.N else 0

    def __len__(self):
        return len(self.c)

    def __repr__(self):
        cab = ", ".join(str(x) for x in self.c[:4])
        return f"Serie({self.nombre}: {cab}, ... N={self.N})"

    # --- aritmetica truncada ------------------------------------------------

    def _alinear(self, otra):
        N = min(self.N, otra.N)
        return N

    def __add__(self, otra):
        if not isinstance(otra, Serie):
            c = list(self.c)
            c[0] = c[0] + otra
            return Serie(c, self.nombre)
        N = self._alinear(otra)
        return Serie([self.c[n] + otra.c[n] for n in range(N + 1)])

    def __sub__(self, otra):
        if not isinstance(otra, Serie):
            c = list(self.c)
            c[0] = c[0] - otra
            return Serie(c, self.nombre)
        N = self._alinear(otra)
        return Serie([self.c[n] - otra.c[n] for n in range(N + 1)])

    def __neg__(self):
        return Serie([-x for x in self.c], self.nombre)

    def __mul__(self, otra):
        if not isinstance(otra, Serie):
            return Serie([x * otra for x in self.c], self.nombre)
        N = self._alinear(otra)
        out = []
        for n in range(N + 1):
            s = 0
            for i in range(n + 1):
                s = s + self.c[i] * otra.c[n - i]
            out.append(s)
        return Serie(out)

    __rmul__ = __mul__

    def potencia(self, k):
        assert k >= 0
        r = Serie([1] + [0] * self.N)
        for _ in range(k):
            r = r * self
        return r

    def inversa(self):
        """1/f, exige a_0 != 0."""
        if self.c[0] == 0:
            raise ZeroDivisionError("la serie tiene termino constante nulo")
        a0 = self.c[0]
        inv = [1 / Fraction(a0) if isinstance(a0, (int, Fraction)) else 1 / a0]
        for n in range(1, self.N + 1):
            s = 0
            for i in range(1, n + 1):
                s = s + self.c[i] * inv[n - i]
            inv.append(-s / a0)
        return Serie(inv)

    def __truediv__(self, otra):
        if not isinstance(otra, Serie):
            return Serie([x / otra for x in self.c], self.nombre)
        return self * otra.inversa()

    def derivada(self):
        return Serie([n * self.c[n] for n in range(1, self.N + 1)] + [0])

    def evaluar_en(self, otra):
        """f(g(z)) con g(0) = 0, truncada."""
        if otra.c[0] != 0:
            raise ValueError("la composicion exige g(0) = 0")
        r = Serie([0] * (self.N + 1))
        pot = Serie([1] + [0] * self.N)
        for n in range(self.N + 1):
            r = r + pot * self.c[n]
            pot = pot * otra
        return r

    def truncar(self, N):
        return Serie(self.c[:N + 1], self.nombre)

    def coeficientes_mp(self):
        """Los coeficientes como mpf, para growth.py."""
        return [mpf(x.numerator) / mpf(x.denominator) if isinstance(x, Fraction) else mpf(x) for x in self.c]


# ======================================================================
# generadores con crecimiento prescrito (semilla fija)
# ======================================================================

def _epsilon(N, semilla):
    """eps_n en [1/2, 2], reproducibles: ruido acotado que no cambia la clase."""
    rng = random.Random(semilla)
    return [mpf(rng.uniform(0.5, 2.0)) for _ in range(N + 1)]


def gevrey(alpha, N=200, semilla=SEMILLA, signos=False):
    """a_n = eps_n (n!)^alpha. Gevrey de orden alpha (alpha = 0: convergente)."""
    eps = _epsilon(N, semilla)
    rng = random.Random(semilla + 1)
    c = [eps[n] * e ** (mpf(alpha) * loggamma(n + 1)) for n in range(N + 1)]
    if signos:
        c = [x if rng.random() < 0.5 else -x for x in c]
    return Serie(c, f"Gevrey({float(alpha):.3g})")


def fuertemente_regular(alpha, beta, N=200, semilla=SEMILLA):
    """a_n = eps_n (n!)^alpha (log(n+e))^(beta n): fuertemente regular, no Gevrey."""
    eps = _epsilon(N, semilla)
    c = [eps[n] * e ** (mpf(alpha) * loggamma(n + 1) + mpf(beta) * n * log(log(n + e))) for n in range(N + 1)]
    return Serie(c, f"SR({float(alpha):.3g},{float(beta):.3g})")


def q_gevrey(q, N=200, semilla=SEMILLA):
    """a_n = eps_n q^(n^2): mas rapido que cualquier Gevrey; (mg) falla. Caso frontera."""
    eps = _epsilon(N, semilla)
    c = [eps[n] * e ** (mpf(n) ** 2 * log(mpf(q))) for n in range(N + 1)]
    return Serie(c, f"q-Gevrey({q})")


def euler(N=200):
    """sum (-1)^n n! z^n, exacta. Gevrey-1; su Borel (k=1) es 1/(1+zeta), polo en -1."""
    c, f = [], 1
    for n in range(N + 1):
        c.append(Fraction((-1) ** n * f))
        f *= n + 1
    return Serie(c, "Euler")


def catalan(N=200):
    """y(z) = (1 - sqrt(1-4z))/2 = sum_{n>=1} C_{n-1} z^n, raiz de y^2 - y + z = 0. Exacta, convergente."""
    c = [Fraction(0)]
    C = Fraction(1)
    for n in range(1, N + 1):
        c.append(C)                          # C_{n-1}
        C = C * 2 * (2 * n - 1) / (n + 1)    # C_n = C_{n-1} 2(2n-1)/(n+1)
    return Serie(c, "Catalan")


def desde_borel(polos, k=1, N=200):
    """
    Serie cuya Borel formal de orden k (normalizacion de Balser, [balser-2000:p97])
    es sum_j r_j / (zeta_j - zeta): polos simples en zeta_j con residuo r_j.
        polos = [(zeta_j, r_j), ...]   (complejos o reales; mpf/mpc)
    f_n = Gamma(1 + n/k) * sum_j r_j / zeta_j^(n+1).
    """
    c = []
    for n in range(N + 1):
        b = 0
        for zj, rj in polos:
            b = b + mpf(rj) / (zj ** (n + 1)) if not isinstance(zj, complex) else b + rj / (zj ** (n + 1))
        c.append(b * gamma(1 + mpf(n) / k))
    return Serie(c, f"Borel^-1(k={k}, polos={len(polos)})")
