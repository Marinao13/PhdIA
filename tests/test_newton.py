"""Test 4 del BRIEF: raiz multiple y^2 = z (1 + z f(z)); el poligono de Newton detecta r = 2."""
from fractions import Fraction
import series as S
import newton as Nw


def _z(N):
    return S.Serie([Fraction(0), Fraction(1)] + [Fraction(0)] * (N - 1))


def _const(c, N):
    return S.Serie([Fraction(c)] + [Fraction(0)] * N)


def test_poligono_de_una_raiz_simple_tiene_mu_entero():
    N = 12
    P = [_z(N), _const(-1, N), _const(1, N)]                 # y^2 - y + z: puntos (0,1), (1,0), (2,0)
    aristas = Nw.poligono(P)
    assert [a["mu"] for a in aristas][0] == 1                 # y ~ c z: arista (0,1)-(1,0)
    assert aristas[0]["mu"].denominator == 1                  # sin ramificacion


def test_4_raiz_doble_ramifica_con_r_igual_a_2():
    N = 24
    f = S.euler(N)                                            # f Gevrey-1
    z, uno = _z(N), _const(1, N)
    P = [-(z * (uno + z * f)), _const(0, N), uno]             # y^2 - z(1 + z f) = 0
    aristas = Nw.poligono(P)
    assert len(aristas) == 1 and aristas[0]["mu"] == Fraction(1, 2)
    traza = []
    rs = Nw.ramas(P, N=N, traza=traza)
    assert sorted(r_["c"] for r_ in rs) == [-1, 1]
    assert all(r_["r"] == 2 and r_["a"] == 1 and r_["multiplicidad"] == 1 for r_ in rs)
    for r_ in rs:
        assert all(c == 0 for c in Nw.comprobar(P, r_, N).c), "la rama no anula P(t^2, y(t))"
    # y = +- t sqrt(1 + t^2 f(t^2)) = +- t (1 + t^2/2 - ...): el coeficiente de t^3 es f_0/2 = 1/2
    pos = next(r_ for r_ in rs if r_["c"] == 1)
    assert pos["y_t"].c[1] == 1 and pos["y_t"].c[2] == 0 and pos["y_t"].c[3] == Fraction(1, 2)
    assert any("mu = 1/2" in l for l in traza) and any("Hensel" in l for l in traza)


def test_ramificacion_de_orden_tres():
    N = 18
    z, uno = _z(N), _const(1, N)
    P = [-z, _const(0, N), _const(0, N), uno]                # y^3 = z: mu = 1/3, r = 3, c = 1
    rs = Nw.ramas(P, N=N)
    assert len(rs) == 1 and rs[0]["r"] == 3 and rs[0]["c"] == 1
    assert all(c == 0 for c in Nw.comprobar(P, rs[0], N).c)
    assert rs[0]["y_t"].c[1] == 1 and all(c == 0 for c in rs[0]["y_t"].c[2:])   # y = t exactamente
