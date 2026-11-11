"""nucleo/a_latex.py: lo que saco la cuarta revision (un revisor haciendo de pdflatex, que aqui no hay)."""
import re

from nucleo import a_latex as L


def _privados(tex):
    return re.findall("[\ue000-\ue0ff]", tex)


def test_una_formula_dentro_de_una_figura_no_se_pierde():
    md = ("Sea $a$ y $b$.\n\n[FIGURA: sector $S_\\gamma$ de abertura $\\pi\\gamma$]\n\n"
          "[PAGINA CORTADA por el tope: revisa $x$]\n\n```\ncodigo con [FIGURA: caja $y$] dentro\n```\n")
    tex, _ = L.cuerpo_latex(md)
    assert "FIGURA: sector $S_\\gamma$ de abertura $\\pi\\gamma$}}" in tex
    assert "\\duda{[PAGINA CORTADA por el tope: revisa $x$]}" in tex
    assert "codigo con [FIGURA: caja $y$] dentro" in tex              # en verbatim, tal cual
    assert not _privados(tex) and not _privados(L.documento(md, nombre="x"))


def test_los_simbolos_que_faltaban_tienen_comando():
    tex, _ = L.cuerpo_latex("Dem. (a) ⟹ (b): trivial. ∎\n\nCon $f′(x) ≪ M_p$, x⁴, a₁ y ϕ; ℓ ↔ m; 3 − 2.\n")
    assert "(a) $\\Longrightarrow$ (b): trivial. $\\blacksquare$" in tex
    assert "$f'(x) \\ll  M_p$" in tex and "x$^{4}$" in tex and "a$_{1}$" in tex and "$\\phi$" in tex
    assert "$\\ell$ $\\leftrightarrow$ m; 3 - 2." in tex
    assert not re.search("[^\x00-\u017f]", tex)


def test_un_simbolo_dentro_de_text_en_una_formula_no_rompe_el_modo():
    tex, _ = L.cuerpo_latex("$x_n \\to 0 \\text{ y α > 0}$ pero $α > 0$.\n")
    assert "\\text{ y \\ensuremath{\\alpha} > 0}" in tex and "$\\alpha  > 0$" in tex


def test_lo_que_no_tiene_comando_se_declara_y_sale_en_rojo():
    md = "Atencion ☺ y 你 aqui, con € y • que pdflatex si conoce.\n\n```\nen codigo ⚠ tambien\n```\n"
    tex = L.documento(md, nombre="x")
    pre = tex.split("\\begin{document}")[0]
    for c in "☺你⚠":
        assert "\\DeclareUnicodeCharacter{%04X}{\\duda{[U+%04X]}}" % (ord(c), ord(c)) in pre
    assert "20AC" not in pre and "2022" not in pre
    assert pre.index("\\newcommand{\\duda}") < pre.index("\\DeclareUnicodeCharacter")
    assert "\\DeclareUnicodeCharacter" not in L.documento("Solo texto con eñes y $x$.\n", nombre="x")


def test_las_listas_numeradas_conservan_su_numero():
    tex, _ = L.cuerpo_latex("3. Tercero\n4. Cuarto\n\n   2. dentro, desde el dos\n   3. dentro\n")
    assert "\\begin{enumerate}\n\\setcounter{enumi}{2}\n\\item Tercero" in tex
    assert "\\begin{enumerate}\n\\setcounter{enumii}{1}\n\\item dentro, desde el dos" in tex
    # una formula sin sangrar entre apartados parte la lista en tres: cada trozo sigue la cuenta
    tex2, _ = L.cuerpo_latex("1. $M$ es (lc).\n\n$M_p^2 \\le M_{p-1}M_{p+1}$\n\n2. $M$ es (mg).\n\n$x$\n\n3. Tercero.\n")
    assert tex2.count("\\begin{enumerate}") == 3
    assert "\\setcounter{enumi}{1}\n\\item $M$ es (mg)." in tex2 and "\\setcounter{enumi}{2}\n\\item Tercero." in tex2
    assert "\\setcounter" not in L.cuerpo_latex("1. uno\n2. dos\n")[0]


def test_una_formula_sola_dentro_de_una_negrita_no_deja_lineas_en_blanco():
    md = "**Si $M$ es fuertemente regular, entonces\n$\\gamma(M) > 0$\ny la clase es no casi analitica.**\n"
    tex, _ = L.cuerpo_latex(md)
    dentro = tex[tex.index("\\textbf{"):]
    assert "\n\n" not in dentro.strip() and "$\\gamma(M) > 0$" in dentro and "\\[" not in dentro
    tex2, _ = L.cuerpo_latex("*Entonces\n$a \\le b$\nsiempre.*\n\nY fuera:\n$c \\le d$\nsi.\n")
    assert "\\emph{Entonces\n$a \\le b$\nsiempre.}" in tex2 and "\\[\nc \\le d\n\\]" in tex2


def test_las_comillas_rectas_no_activan_los_atajos_de_babel():
    tex = L.documento('Llamamos "casi analitica" a la clase y ("admisible") a la sucesion; `"c"` en codigo.\n', nombre="x")
    assert "Llamamos ``casi analitica'' a la clase y (``admisible'') a la sucesion" in tex
    assert "\\texttt{\\textquotedbl{}c\\textquotedbl{}}" in tex
    cuerpo = tex.split("\\begin{document}")[1]
    assert '"' not in cuerpo
    assert "\\usepackage[spanish,es-noshorthands,es-nodecimaldot]{babel}" in tex


def test_un_corchete_no_se_toma_por_argumento_opcional():
    tex, _ = L.cuerpo_latex("- [JSS] Jimenez-Garrido, Sanz, Schindl.\n- normal\n\n1. [a, b] es compacto\n2. [0,1) no\n")
    assert "\\item {}[JSS] Jimenez-Garrido" in tex and "\\item normal" in tex
    assert "\\item {}[a, b] es compacto" in tex and "\\item {}[0,1) no" in tex
    tex2, _ = L.cuerpo_latex("Por el lema  \n[a, b] es compacto.\n")
    assert "Por el lema\\\\\n{}[a, b] es compacto." in tex2
    tex3, _ = L.cuerpo_latex("| x | y |\n|---|---|\n| [0,1] | uno |\n")
    assert "{}[0,1] & uno \\\\" in tex3
    # una marca o una formula al empezar no necesitan guarda
    tex4, _ = L.cuerpo_latex("- [?] dudoso\n- $x$ formula\n")
    assert "\\item \\duda{[?]} dudoso" in tex4 and "\\item $x$ formula" in tex4


def test_el_titulo_con_formula_y_especiales():
    tex = L.documento("# Clase $\\mathcal{E}_M$ al 50% & mas\n\n<!-- pagina 1 -->\n\nTexto.\n", nombre="x")
    assert "\\title{Clase $\\mathcal{E}_M$ al 50\\% \\& mas}" in tex


def test_una_figura_larga_parte_linea_y_dentro_de_una_formula_no():
    tex, _ = L.cuerpo_latex("[FIGURA: " + "una descripcion muy larga " * 6 + "]\n\nSea $x [FIGURA: flecha] y$ aqui.\n")
    assert "\\fbox{\\parbox{\\dimexpr\\linewidth-2\\fboxsep-2\\fboxrule\\relax}{FIGURA: una descripcion" in tex
    assert "$x \\text{\\fbox{FIGURA: flecha}} y$" in tex
