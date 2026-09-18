"""
`python doc.py lab demo` (BRIEF 4.4, aceptacion): los casos de prueba con verdad conocida,
con su informe de crecimiento y un grafico de log|a_n| por caso en lab/salidas/ (fuera de git).

  1. Euler  sum (-1)^n n! z^n            Gevrey-1. (La parte de Borel -- polo en -1,
                                         direccion pi -- va en borel.py, fase 4f.)
  2. Catalan, raiz de y^2 - y + z = 0     convergente, alpha ~ 0
  3. raiz simple de y^2 - y + z f(z) = 0  con f = Euler: alpha ~ 1
  4. raiz multiple y^2 = z (1 + z f(z))   poligono de Newton, fase 4g: aqui solo se
                                         comprueba que Hensel la rechaza.
"""
import os
from fractions import Fraction

try:
    from . import series as S, growth as G, algebraic as A
    from . import pesos as P
except ImportError:
    import series as S, growth as G, algebraic as A, pesos as P

SALIDAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salidas")


def _z(N):
    return S.Serie([Fraction(0), Fraction(1)] + [Fraction(0)] * (N - 1))


def _const(c, N):
    return S.Serie([Fraction(c)] + [Fraction(0)] * N)


def casos(N=150):
    f = S.euler(N)
    uno, menos_uno, z = _const(1, N), _const(-1, N), _z(N)
    raiz = A.raiz_simple([z * f, menos_uno, uno], y0=0, N=N)
    raiz.nombre = "raiz de y^2 - y + z*Euler(z)"
    return [("1. Euler", f, P.gevrey(1, N=N).logM, "Gevrey(1)"),
            ("2. Catalan", S.catalan(N), P.gevrey(0, N=N).logM, "Gevrey(0)"),
            ("3. raiz simple con Euler", raiz, P.gevrey(1, N=N).logM, "Gevrey(1)")]


def grafico(nombre, serie, ruta):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    pares = G._logabs(serie.coeficientes_mp())
    n = [p[0] for p in pares]
    y = [p[1] for p in pares]
    aj = G.ajuste_cola(serie.coeficientes_mp())
    import numpy as np
    nn = np.array(n[1:], dtype=float)
    ajuste = aj["alpha"] * nn * np.log(nn) + aj["logA"] * nn + aj["c"]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.plot(n, y, ".", ms=3, label="log|a_n|")
    ax.plot(nn, ajuste, "-", lw=1, label=f"ajuste de cola: alpha={aj['alpha']:.3f}")
    ax.set_xlabel("n")
    ax.set_title(nombre)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ruta, dpi=110)
    plt.close(fig)
    return ruta


def demo(N=150, graficos=True):
    os.makedirs(SALIDAS, exist_ok=True)
    print(f"laboratorio: casos con verdad conocida, N = {N}\n")
    for nombre, serie, logM, nombre_M in casos(N):
        print(nombre)
        print(G.informe(serie, logM, nombre_M))
        if graficos:
            ruta = grafico(nombre, serie, os.path.join(SALIDAS, nombre.split(".")[0] + "-coeficientes.png"))
            if ruta:
                print(f"  grafico -> {os.path.relpath(ruta, os.getcwd())}")
        print()
    print("4. raiz multiple y^2 = z(1 + z f): Hensel la rechaza (poligono de Newton, fase 4g):")
    N4 = 20
    z, cero, uno = _z(N4), _const(0, N4), _const(1, N4)
    try:
        A.hensel([-(z * (uno + z * S.euler(N4))), cero, uno], 0, N4)
        print("  ERROR: no deberia haber convergido")
    except ValueError as e:
        print("  ", e)
    try:
        from . import borel as Bo
    except ImportError:
        import borel as Bo
    from mpmath import mpf
    print("\n1 (Borel). " + Bo.informe(S.euler(40).c, k=1, nombre="Euler"))
    z = mpf("0.3")
    b = Bo.borel(S.euler(40).c)
    print(f"   suma de Borel en direccion 0, z=0.3: {Bo.laplace(b, 1, 0, z).real}"
          f"   |   funcion de Euler int e^-s/(1+zs) ds: {Bo.euler_funcion(z).real}")


if __name__ == "__main__":
    demo()
