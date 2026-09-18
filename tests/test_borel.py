"""Test 1 del BRIEF, parte de Borel: Euler -> 1/(1+zeta), polo en -1, direccion pi, y la suma de
Borel en direccion 0 coincide con la funcion de Euler."""
from mpmath import mpf, mpc, fabs, pi, arg
import series as S
import borel as B


def test_borel_de_euler_es_la_geometrica_alternada():
    b = B.borel(S.euler(30).c, k=1)
    assert all(fabs(b[n] - (-1) ** n) < mpf("1e-30") for n in range(31))


def test_1_polo_en_menos_uno_y_direccion_pi():
    b = B.borel(S.euler(40).c, k=1)
    est = B.singularidades_estables(b)
    assert est, "Pade no encontro singularidades estables"
    z, veces = est[0]
    assert fabs(z + 1) < mpf("1e-8"), z
    assert veces >= 3
    dirs = B.direcciones_singulares(est)
    assert fabs(fabs(dirs[0][0]) - pi) < mpf("1e-6")
    assert fabs(B.radio_convergencia(est) - 1) < mpf("1e-8")


def test_singularidad_construida_donde_se_pidio():
    # dos polos, en 2 e^{i pi/3} y su conjugado: direcciones +-pi/3, radio 2
    zj = 2 * mpc(mpf(1) / 2, mpf(3).sqrt() / 2)
    f = S.desde_borel([(zj, 1), (zj.conjugate(), 1)], k=1, N=60)
    b = B.borel(f.c, k=1)
    est = B.singularidades_estables(b)
    modulos = sorted(fabs(z) for z, _ in est)
    assert len(est) >= 2 and fabs(modulos[0] - 2) < mpf("1e-6"), est
    dirs = sorted(d for d, _ in B.direcciones_singulares(est))
    assert fabs(dirs[0] + pi / 3) < mpf("1e-4") and fabs(dirs[-1] - pi / 3) < mpf("1e-4")


def test_laplace_de_vuelta_reproduce_la_funcion_de_euler():
    b = B.borel(S.euler(40).c, k=1)
    for z in (mpf("0.1"), mpf("0.3"), mpc("0.2", "0.1")):
        suma = B.laplace(b, k=1, d=0, z=z)
        exacta = B.euler_funcion(z)
        assert fabs(suma - exacta) < mpf("1e-10") * (1 + fabs(exacta)), (z, suma, exacta)


def test_serie_convergente_sin_singularidades_estables_cerca():
    # Catalan converge (radio 1/4): su Borel es entera; Pade no debe dar polos estables pequenos
    b = B.borel(S.catalan(40).c, k=1)
    est = B.singularidades_estables(b)
    assert all(fabs(z) > 5 for z, _ in est), est
