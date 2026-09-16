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
