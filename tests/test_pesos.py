"""lab/pesos.py: verdades conocidas sobre sucesiones peso, con N pequeno."""
from mpmath import mpf, log
import pesos as P


def test_gevrey_normalizada_y_log_convexa():
    M = P.gevrey(1, N=120)
    assert M.logM[0] == 0
    lc, _ = M.es_log_convexa()
    assert lc


def test_gevrey_tiene_crecimiento_moderado_y_dc():
    # (p+q)! <= 2^(p+q) p! q!, luego A_mg <= 2 para Gevrey-1.
    # A_dc = sup_p (p+1)^(1/(p+1)), que se alcanza en p+1 = 3: 3^(1/3) = 1.442...
    M = P.gevrey(1, N=120)
    amg, _ = M.constante_mg()
    adc, _ = M.constante_dc()
    assert amg <= 2 + mpf("1e-20")
    assert abs(adc - mpf(3) ** (mpf(1) / 3)) < mpf("1e-20")


def test_q_gevrey_rompe_mg():
    # M_p = q^(p^2): logM[p+q]-logM[p]-logM[q] = 2pq log q, sin cota lineal
    M = P.q_gevrey(2, N=120)
    a150, _ = P.SucesionPeso(M.logM[:61], "q").constante_mg()
    a300, _ = M.constante_mg()
    assert a300 > a150 * 1.5


def test_gevrey_0_no_es_fuertemente_no_cuasianalitica():
    # M_p = 1: la cola sum 1/(q+1) diverge, gamma_1 no puede ser acotada
    A_chico, _, _ = P.SucesionPeso([mpf(0)] * 121, "1").constante_gamma1()
    A_grande, _, _ = P.SucesionPeso([mpf(0)] * 401, "1").constante_gamma1()
    assert A_grande > A_chico


def test_refutar_encuentra_el_contraejemplo():
    contras = P.refutar(lambda p: p < 5, {"p": range(10)}, nombre="p<5", verbose=False)
    assert contras and contras[0][0]["p"] == 5


def test_refutar_no_prueba_nada_cuando_sobrevive():
    assert P.refutar(lambda p: p >= 0, {"p": range(10)}, verbose=False) == []


def test_casi_creciente():
    assert P.casi_creciente([1, 2, 3, 4]) == 1
    assert P.casi_creciente([4, 1, 1, 1]) == 4


def test_misma_clase_gevrey_en_las_dos_convenciones_da_el_mismo_omega():
    # Gevrey-1: M_p = p! (fuera) o (p!)^2 (dentro). omega(M) = 1 en ambas: se calcula sobre la fuera.
    fuera = P.gevrey(1, N=300)
    dentro = P.gevrey(1, N=300, factorial="dentro")
    assert fuera.factorial == "fuera" and dentro.factorial == "dentro"
    assert abs(fuera.indice_omega() - 1) < mpf("0.01")
    assert abs(dentro.indice_omega() - fuera.indice_omega()) < mpf("1e-20")
    # la conversion es exacta en logaritmos: M_dentro[p] = p! M_fuera[p]
    assert all(abs(a - b) < mpf("1e-25") for a, b in zip(dentro.en("fuera").logM, fuera.logM))
    assert all(abs(a - b) < mpf("1e-25") for a, b in zip(fuera.en("dentro").logM, dentro.logM))
    assert fuera.en("fuera") is fuera


def test_omega_de_gevrey_alpha_es_alpha_y_gamma1_usa_la_convencion_fuera():
    assert abs(P.gevrey(mpf(1) / 2, N=300).indice_omega() - mpf(1) / 2) < mpf("0.01")
    assert P.gevrey(0, N=300).indice_omega() == 0
    # (gamma_1) en forma de Thilliez: la misma A para la clase escrita en las dos convenciones
    A_f, _, _ = P.gevrey(1, N=200).constante_gamma1()
    A_d, _, _ = P.gevrey(1, N=200, factorial="dentro").constante_gamma1()
    assert abs(A_f - A_d) < mpf("1e-20")


def test_convencion_invalida():
    import pytest
    with pytest.raises(ValueError):
        P.SucesionPeso([0, 0, 0], "x", factorial="a veces")
    with pytest.raises(ValueError):
        P.gevrey(1, N=10).en("a veces")
