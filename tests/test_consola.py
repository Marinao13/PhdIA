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


def test_una_barra_suelta_al_final_no_lanza():
    # respuesta cortada por el tope justo tras una barra: degrada, no rompe
    for t in ("Por tanto $\\frac{M_p}\\", "\\[ \\frac{a}\\", "Sea $\\sqrt \\", "\\[\n\\sqrt\\\nb\n\\]", "x $\\hat\\"):
        assert isinstance(latex_a_consola(t), str)


def test_cabecera_no_se_traga_lo_que_la_sigue():
    t = latex_a_consola("## Pasos\n- uno\n- dos\n\nfin")
    assert "Pasos\n-----" in t and "- uno\n- dos" in t and t.endswith("fin")
    t = latex_a_consola("## Titulo\nTexto que sigue sin blanco")
    assert "Texto que sigue sin blanco" in t


def test_bloque_dentro_de_un_item_de_lista_se_expande():
    t = latex_a_consola("- item uno $$x^2$$\n- item dos \\[ y \\]\n- tres")
    assert "\x01" not in t and "x^2" in t and "- tres" in t


def test_asteriscos_dentro_de_formulas_se_conservan():
    t = latex_a_consola("El dual $T^*$ y el adjunto $S^*$ cumplen $T^{**}=T$.")
    assert "$T^*$" in t and "$S^*$" in t and "T^{**}" in t


def test_listas_anidadas_y_tablas():
    t = latex_a_consola("1. Primero\n   - detalle a\n   - detalle b\n2. Segundo")
    assert "1. Primero\n   - detalle a\n   - detalle b\n2. Segundo" in t
    t = latex_a_consola("| autor | (mg) |\n|---|---|\n| Thilliez | $M_p$ |")
    assert t == "| autor | (mg) |\n|---|---|\n| Thilliez | $M_p$ |"


def test_un_comando_seguido_de_mathcal_o_frac_no_se_pega():
    # \in\mathcal{E}_p(M) se leia como el comando \inE: salida real de la sesion del 2026-10-20
    t = latex_a_consola(r"$f\in\mathcal{E}_p(M)$ y $g_1,\dots,g_p\in\mathcal{E}_n(M)$, con $x\in\frac{a}{b}$ y $y\in\mathbb{R}$")
    assert "$f ∈ E_p(M)$" in t and "g_p ∈ E_n(M)" in t and "x ∈ a/b" in t and "y ∈ ℝ" in t
    assert "inE" not in t and "ina/b" not in t and "\x05" not in t
    assert "∈ √2" in latex_a_consola(r"$x\in\sqrt{2}$")


def test_mathfrak_bmod_y_bar():
    # salida real de la sesion del 2026-10-21: "mathfrak m", "bmod", "bar(P)"
    t = latex_a_consola(r"ideal maximal $\mathfrak m$, $\bar{P}\in(A/\mathfrak{m})[T]$ y $a\bmod\mathfrak m=\alpha$")
    assert "$m$" in t and "mathfrak" not in t and "bmod" not in t
    assert "bar(P) ∈ (A/m)[T]" in t and "a mod m = α" in t


def test_raiz_con_indice():
    assert "3√(x)" in latex_a_consola(r"\(\sqrt[3]{x}\)")
    assert "√(a+b)" in latex_a_consola(r"\(\sqrt{a+b}\)")


def test_texto_largo_es_rapido_y_no_rompe():
    import time
    t0 = time.perf_counter()
    out = latex_a_consola("Texto $x\\le y$ y \\[\\int_0^1 f\\] " * 400)
    assert time.perf_counter() - t0 < 2 and "∫" in out


def test_listas_y_lineas_ya_planas_se_respetan():
    t = latex_a_consola("- primero $a_j$\n- segundo\n\nUSADOS: [x:p3]; [!] lema de Schwarz")
    assert t.startswith("- primero $a_j$\n- segundo")
    assert "USADOS: [x:p3]; [!] lema de Schwarz" in t
