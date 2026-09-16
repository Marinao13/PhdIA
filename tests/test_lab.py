"""Tests 1-3 del BRIEF (parte de crecimiento) y aritmetica de series. Sin red."""
from fractions import Fraction
import pytest
from mpmath import mpf, loggamma, log
import series as S
import growth as G
import algebraic as A
import pesos as P


# ---------------------------------------------------------------- series: aritmetica exacta

def test_producto_e_inversa_exactos():
    uno_menos_z = S.Serie([Fraction(1), Fraction(-1)] + [Fraction(0)] * 8)
    geom = uno_menos_z.inversa()                       # 1/(1-z) = sum z^n
    assert all(c == 1 for c in geom.c)
    assert (uno_menos_z * geom).c == [1] + [0] * 9


def test_catalan_es_raiz_de_su_ecuacion():
    y = S.catalan(40)
    assert y.c[1:6] == [1, 1, 2, 5, 14]
    r = y * y - y + S.Serie([Fraction(0), Fraction(1)] + [Fraction(0)] * 39)
    assert all(c == 0 for c in r.c)


def test_euler_y_su_borel_por_construccion():
    # Euler: a_n = (-1)^n n!. Su Borel (k=1, Balser [balser-2000:p97]) es 1/(1+zeta):
    # polo en -1 con residuo -1 en la forma r/(zeta_j - zeta)  ->  b_n = -1/(-1)^(n+1) = (-1)^n
    f = S.desde_borel([(mpf(-1), mpf(-1))], k=1, N=12)
    e = S.euler(12).coeficientes_mp()
    assert all(abs(f.c[n] - e[n]) < mpf("1e-25") * (1 + abs(e[n])) for n in range(13))


def test_generadores_son_reproducibles():
    a = S.gevrey(1, N=30).coeficientes_mp()
    b = S.gevrey(1, N=30).coeficientes_mp()
    assert a == b
    assert S.gevrey(1, N=30, semilla=1).coeficientes_mp() != a


# ---------------------------------------------------------------- BRIEF test 1: Euler es Gevrey-1

def test_1_euler_es_gevrey_1():
    aj = G.ajuste_cola(S.euler(200).coeficientes_mp())
    assert abs(aj["alpha"] - 1) < 0.05, aj
    q = G.cocientes(S.euler(200).coeficientes_mp())
    assert abs(q["alpha"] - 1) < 0.05, q


def test_gevrey_alpha_se_recupera_pese_al_ruido():
    for alpha in (mpf(1) / 2, 2):
        aj = G.ajuste_cola(S.gevrey(alpha, N=300).coeficientes_mp())
        assert abs(aj["alpha"] - float(alpha)) < 0.08, (alpha, aj)


# ---------------------------------------------------------------- BRIEF test 2: algebraica convergente, alpha ~ 0

def test_2_catalan_convergente_alpha_cero():
    aj = G.ajuste_cola(S.catalan(200).coeficientes_mp())
    assert abs(aj["alpha"]) < 0.05, aj


def test_hensel_reproduce_catalan():
    N = 30
    z = S.Serie([Fraction(0), Fraction(1)] + [Fraction(0)] * (N - 1))
    uno, menos_uno = S.Serie([Fraction(1)] + [Fraction(0)] * N), S.Serie([Fraction(-1)] + [Fraction(0)] * N)
    P = [z, menos_uno, uno]                       # y^2 - y + z
    traza = []
    y = A.raiz_simple(P, y0=0, N=N, traza=traza)      # la rama con y(0) = 0; la otra es (1+sqrt(1-4z))/2
    assert y.c == S.catalan(N).c
    assert traza[-1][1] == N + 1 and len(traza) <= 6   # convergencia cuadratica: ~log2(N) pasos


def test_hensel_rechaza_raiz_multiple():
    N = 10
    z = S.Serie([Fraction(0), Fraction(1)] + [Fraction(0)] * (N - 1))
    cero = S.Serie([Fraction(0)] * (N + 1))
    uno = S.Serie([Fraction(1)] + [Fraction(0)] * N)
    with pytest.raises(ValueError, match="multiple"):
        A.hensel([-z, cero, uno], 0, N)           # y^2 = z: raiz doble en y = 0


# ---------------------------------------------------------------- BRIEF test 3: raiz simple con f Gevrey-1 -> alpha ~ 1

def test_3_raiz_simple_hereda_gevrey_1():
    N = 120
    f = S.euler(N)                                # Gevrey-1 exacta
    z = S.Serie([Fraction(0), Fraction(1)] + [Fraction(0)] * (N - 1))
    uno, menos_uno = S.Serie([Fraction(1)] + [Fraction(0)] * N), S.Serie([Fraction(-1)] + [Fraction(0)] * N)
    P = [z * f, menos_uno, uno]                   # y^2 - y + z f(z)
    y = A.raiz_simple(P, N=N)
    aj = G.ajuste_cola(y.coeficientes_mp())
    assert abs(aj["alpha"] - 1) < 0.1, aj


# ---------------------------------------------------------------- Roumieu / Beurling frente a M

def test_roumieu_frente_a_su_propia_clase_y_beurling_frente_a_una_mayor():
    a = S.gevrey(1, N=300).coeficientes_mp()
    M1 = P.gevrey(1, N=300).logM                 # misma clase: c_n acotada, pendiente ~ 0
    r1 = G.roumieu_beurling(a, M1)
    assert abs(r1["pendiente_log"]) < 0.15 and r1["sup_cola"] < 3, r1
    M2 = P.gevrey(mpf(3) / 2, N=300).logM        # clase mayor: c_n -> 0, pendiente negativa
    r2 = G.roumieu_beurling(a, M2)
    assert r2["pendiente_log"] < -0.3, r2
