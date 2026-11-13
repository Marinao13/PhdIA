"""nucleo/a_latex.py: lo que saco la quinta revision (otra pasada del revisor que hace de pdflatex)."""
import re

from nucleo import a_latex as L


def test_el_preambulo_trae_lo_que_el_modelo_usa_y_katex_pinta():
    tex = L.documento("Sea $f \\in \\mathscr{E}_{\\{M\\}}(\\Omega)$, $\\bm{x} \\coloneqq 3\\degree$.\n", nombre="x")
    pre = tex.split("\\begin{document}")[0]
    assert "\\usepackage{mathtools,mathrsfs,bm}" in pre and "\\providecommand{\\degree}{^{\\circ}}" in pre
    assert pre.index("{amsmath,amssymb,amsthm}") < pre.index("{mathtools,mathrsfs,bm}")
    assert "$f \\in \\mathscr{E}_{\\{M\\}}(\\Omega)$" in tex                # la formula, tal cual


def test_en_una_celda_o_en_un_titulo_ninguna_formula_va_en_display():
    md = ("| condicion | formula |\n|---|---|\n| (lc) | $$M_p^2 \\le M_{p-1}M_{p+1}$$ |\n"
          "| (mg) | \\[M_{p+q} \\le A^{p+q}M_pM_q\\] |\n| (dc) | $M_{p+1} \\le A^p M_p$ |\n\n"
          "## Clases $$\\mathcal{E}_M$$ y mas\n\nY fuera de la tabla:\n\n$$a \\le b$$\n")
    tex, _ = L.cuerpo_latex(md)
    tabla = tex[tex.index("\\begin{tabular}"):tex.index("\\end{tabular}")]
    assert "\\[" not in tabla and "$$" not in tabla
    assert "(lc) & $\\displaystyle M_p^2 \\le M_{p-1}M_{p+1}$ \\\\" in tabla
    assert "(mg) & $\\displaystyle M_{p+q} \\le A^{p+q}M_pM_q$ \\\\" in tabla
    assert "(dc) & $M_{p+1} \\le A^p M_p$ \\\\" in tabla
    assert "\\section{Clases $\\displaystyle \\mathcal{E}_M$ y mas}" in tex
    assert "\\[\na \\le b\n\\]" in tex and not re.search("[\ue000-\ue0ff]", tex)
    # varias lineas y un \tag dentro de una celda: aligned entre $ $, y la etiqueta como texto
    tex2, _ = L.cuerpo_latex("| a |\n|---|\n| $$x &= 1 \\\\ y &= 2 \\tag{3}$$ |\n")
    assert "$\\displaystyle \\begin{aligned}\nx &= 1 \\\\ y &= 2 \\quad\\text{(3)}\n\\end{aligned}$" in tex2


def test_un_tag_no_cae_dentro_de_aligned_y_un_corchete_no_es_su_argumento():
    tex, _ = L.cuerpo_latex("$$ \\gamma(M) > 0 \\\\ \\omega(M) > 0 \\tag{2.1} $$\n")
    assert tex.strip() == "\\begin{gather*}\n\\gamma(M) > 0 \\\\ \\omega(M) > 0 \\tag{2.1}\n\\end{gather*}"
    tex, _ = L.cuerpo_latex("$$ a &= b \\tag{1} \\\\ c &= d \\tag{2} $$\n")
    assert tex.startswith("\\begin{align*}\n") and "aligned" not in tex
    tex, _ = L.cuerpo_latex("$$ [0,\\infty) \\ni t \\mapsto h_M(t) \\\\ (0,1] \\ni s \\mapsto \\omega_M(1/s) $$\n")
    assert "\\begin{aligned}\n{}[0,\\infty) \\ni t" in tex
    tex, _ = L.cuerpo_latex("$$ x = y \\tag{2.1} $$\n")                       # una linea: \[ \] admite \tag
    assert tex.strip() == "\\[\nx = y \\tag{2.1}\n\\]"


def test_acentos_y_grados_dentro_de_una_formula():
    tex, _ = L.cuerpo_latex("El $\\operatorname{máx}_{p \\le n} m_p$ y $C_{\\mathrm{mín}}$, un sector de $90°$, $ñ$.\n")
    assert "$\\operatorname{m\\acute{a}x}_{p \\le n} m_p$" in tex and "$C_{\\mathrm{m\\acute{\\imath}n}}$" in tex
    assert "$90^{\\circ}$" in tex and "$\\tilde{n}$" in tex
    assert "El $" in tex and "máx" not in tex
    # dentro de \text{} los acentos se quedan; el grado, con \ensuremath
    tex2, _ = L.cuerpo_latex("$x \\text{ si es el máximo a 45°}$ y el texto con máximo y 45° sigue igual.\n")
    assert "\\text{ si es el máximo a 45\\ensuremath{^{\\circ}}}" in tex2
    assert "el texto con máximo y 45° sigue igual." in tex2


def test_super_y_subindices_unicode_seguidos_van_juntos():
    tex, _ = L.cuerpo_latex("Entonces $10⁻³ < x²³$ y $a₁₂ = 0$; en texto: 10⁻³, x²³, a₁₂.\n")
    assert "$10^{-3} < x^{23}$" in tex and "$a_{12} = 0$" in tex
    assert "en texto: 10$^{-3}$, x$^{23}$, a$_{12}$." in tex
    assert "} ^{" not in tex and "}$$^{" not in tex
    tex2, _ = L.cuerpo_latex("$x \\text{ con n² casos}$\n")
    assert "\\text{ con n\\ensuremath{^{2}} casos}" in tex2


def test_un_asterisco_tras_un_salto_no_es_la_forma_con_estrella():
    tex, _ = L.cuerpo_latex("| op | propiedad |\n|---|---|\n| + | conmutativa |\n| \\* | asociativa |\n")
    assert "{}* & asociativa \\\\" in tex and "+ & conmutativa \\\\" in tex
    tex2, _ = L.cuerpo_latex("Sea $M$ (lc).  \n\\* salvo $p=0$\n")
    assert "Sea $M$ (lc).\\\\\n{}* salvo $p=0$" in tex2
    tex3, _ = L.cuerpo_latex("- \\* con estrella\n")
    assert "\\item {}* con estrella" in tex3
