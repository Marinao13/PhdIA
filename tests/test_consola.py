"""nucleo/consola.py: markdown + LaTeX ligero de las respuestas -> texto legible en consola."""
import re
from nucleo.consola import latex_a_consola

MUESTRA = r"""Escribamos
\[
g(t)=\log h_N(|t|),\qquad w=u+iv,\quad u>0.
\]

[!] Usaré la definición \(h_N(r)=\inf_{j\ge0}N_jr^j\), ausente del fragmento. De ella se deduce que **\(h_N\) es no decreciente**: cada función \(r\mapsto N_jr^j\) lo es.

## 1. La construcción de \(F\) y las funciones exteriores

Como \(h_N(|t|)\le1\), tenemos \(g(t)\le0\). Por tanto, el lema 2.1.2 implica
\[
\int_{\mathbb R}\frac{|g(t)|}{1+t^2}\,dt<\infty.
\]
"""


def test_quita_delimitadores_latex_y_markdown():
    t = latex_a_consola(MUESTRA)
    assert "\\(" not in t and "\\[" not in t and "**" not in t and "## " not in t
    assert "\\frac" not in t and "\\log" not in t and "\\infty" not in t


def test_bloques_en_lineas_propias_sangradas_y_simbolos_unicode():
    t = latex_a_consola(MUESTRA)
    assert "    g(t) = log h_N(|t|)" in t
    assert "∫" in t and "ℝ" in t and "∞" in t and "≤" in t
    assert "|g(t)|/(1+t^2) dt < ∞" in t


def test_cabecera_subrayada_y_formulas_en_linea_entre_dolares():
    t = latex_a_consola(MUESTRA)
    assert "1. La construcción de $F$ y las funciones exteriores\n----" in t
    assert "$h_N$ es no decreciente" in t


def test_envuelve_a_90_sin_partir_formulas():
    largo = "Texto " * 40 + r"\(\sum_{j\ge 0} N_j r^j \le C A^j\)" + " y sigue " * 20
    t = latex_a_consola(largo, ancho=90)
    assert all(len(l) <= 90 for l in t.splitlines())
    formulas = re.findall(r"\$[^$]*\$", t)
    assert formulas and all("\n" not in f for f in formulas)


def test_modo_ascii_para_tuberias():
    t = latex_a_consola(r"\(x\le\infty\) y \(\mathbb{R}\)", unicode=False)
    assert "<=" in t and "inf" in t and "R" in t
    assert all(ord(c) < 128 for c in t if c not in "áéíóúñÁÉÍÓÚÑ")


def test_listas_y_lineas_ya_planas_se_respetan():
    t = latex_a_consola("- primero $a_j$\n- segundo\n\nUSADOS: [x:p3]; [!] lema de Schwarz")
    assert t.startswith("- primero $a_j$\n- segundo")
    assert "USADOS: [x:p3]; [!] lema de Schwarz" in t
