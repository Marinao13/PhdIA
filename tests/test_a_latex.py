"""nucleo/a_latex.py: de la transcripcion en markdown a un .tex. Aqui no hay pdflatex: se comprueba
la estructura (llaves y entornos casados, especiales escapados, formulas intactas)."""
import re

from nucleo import a_latex as L


def _sin_formulas(tex):
    """El .tex sin comentarios, sin verbatim y sin el interior de las formulas."""
    t = re.sub(r"\\begin\{verbatim\}.*?\\end\{verbatim\}", "", tex, flags=re.S)
    t = re.sub(r"(?m)(?<!\\)%.*$", "", t)
    t = re.sub(r"\\\[.*?\\\]", "", t, flags=re.S)
    return re.sub(r"(?<!\\)\$.*?(?<!\\)\$", "", t, flags=re.S)


def _casado(tex):
    """Llaves casadas (fuera de verbatim y comentarios) y cada \\begin con su \\end, bien anidados."""
    t = re.sub(r"\\begin\{verbatim\}.*?\\end\{verbatim\}", "", tex, flags=re.S)
    t = re.sub(r"(?m)(?<!\\)%.*$", "", t)
    nivel = 0
    for ch in re.sub(r"\\[{}\\]", "", t):
        nivel += ch == "{"
        nivel -= ch == "}"
        if nivel < 0:
            return False
    pila = []
    for m in re.finditer(r"\\(begin|end)\{([a-z*]+)\}", t):
        if m.group(1) == "begin":
            pila.append(m.group(2))
        elif not pila or pila.pop() != m.group(2):
            return False
    return nivel == 0 and not pila and t.count("\\[") == t.count("\\]")


CUERPO = """# Tema 1: sucesiones peso

> Transcripcion automatica SIN REVISAR. Revisala con el original al lado (web: /transcripciones/x), corrige aqui, y marca: python doc.py transcribir --revisado x

<!-- pagina 1 -->

## Definiciones

Sea $M=(M_p)_{p\\ge 0}$ una sucesion **fuertemente regular** y *log-convexa* [?].

$\\sum_{q\\ge p} \\dfrac{M_q}{(q+1)M_{q+1}} \\le A\\,\\dfrac{M_p}{M_{p+1}}$

- (lc): $M_p^2 \\le M_{p-1}M_{p+1}$
- (mg): existe $A>0$ con $M_{p+q} [ILEGIBLE] A^{p+q}M_pM_q$
  1. primero
  2. segundo

<!-- pagina 2 -->

### Lema 2.1

El 50% de A_1 & B #3 cuesta $5 y usa {llaves}, ~tilde y ^gorro \\ barra.
Si p ≥ 1 entonces α → β, con x ∈ ℝ…

[FIGURA: sector de abertura pi/2] y aqui [ILEGIBLE].
"""


def test_documento_completo_y_casado():
    tex = L.documento(CUERPO, nombre="2026-11-11-tema-1", estado="sin_revisar", fecha="2026-11-11")
    assert tex.startswith("% huella: ") and "\\begin{document}" in tex and tex.rstrip().endswith("\\end{document}")
    assert "\\title{Tema 1: sucesiones peso}" in tex and "\\maketitle" in tex
    assert "SIN REVISAR" not in tex and "estado: sin_revisar" in tex
    assert "% ---------- pagina 1 ----------" in tex and "% ---------- pagina 2 ----------" in tex
    assert "<!--" not in tex and not re.search("[\ue000-\ue0ff]", tex)
    assert _casado(tex), tex


def test_titulos_negritas_y_listas():
    tex, titulo = L.cuerpo_latex(CUERPO)
    assert titulo == "Tema 1: sucesiones peso"
    assert "\\section*{Definiciones}" in tex and "\\subsection*{Lema 2.1}" in tex
    assert "\\textbf{fuertemente regular}" in tex and "\\emph{log-convexa}" in tex
    assert tex.count("\\begin{itemize}") == 1 and tex.count("\\begin{enumerate}") == 1
    assert tex.index("\\begin{itemize}") < tex.index("\\begin{enumerate}") < tex.index("\\end{enumerate}") < tex.index("\\end{itemize}")
    assert tex.count("\\item ") == 4


def test_las_formulas_pasan_tal_cual_y_la_que_va_sola_es_display():
    tex, _ = L.cuerpo_latex(CUERPO)
    assert "$M=(M_p)_{p\\ge 0}$" in tex and "$M_p^2 \\le M_{p-1}M_{p+1}$" in tex
    assert "\\[\n\\sum_{q\\ge p} \\dfrac{M_q}{(q+1)M_{q+1}} \\le A\\,\\dfrac{M_p}{M_{p+1}}\n\\]" in tex
    # dentro de un parrafo, una formula sola en su linea tambien
    tex2, _ = L.cuerpo_latex("Entonces\n$a_p \\le b_p$\npara todo $p$.\n")
    assert "Entonces\n\n\\[\na_p \\le b_p\n\\]\n\npara todo $p$." in tex2
    # $$...$$ y varias lineas alineadas
    tex3, _ = L.cuerpo_latex("$$a &= b \\\\ c &= d$$\n\n\\[x = y\\]\n\ny \\(z\\) en linea.\n")
    assert "\\begin{aligned}\na &= b \\\\ c &= d\n\\end{aligned}" in tex3 and "\\[\nx = y\n\\]" in tex3 and "$z$" in tex3
    tex4, _ = L.cuerpo_latex("$$\\begin{align}a &= b\\end{align}$$\n")
    assert tex4.strip() == "\\begin{align}a &= b\\end{align}"


def test_el_texto_se_escapa_y_las_formulas_no():
    tex, _ = L.cuerpo_latex(CUERPO)
    assert "El 50\\% de A\\_1 \\& B \\#3 cuesta \\$5 y usa \\{llaves\\}" in tex
    assert "\\textasciitilde{}tilde y \\textasciicircum{}gorro \\textbackslash{} barra" in tex
    fuera = _sin_formulas(tex)
    assert not re.search(r"(?<!\\)[&%#_^~]", fuera), fuera


def test_los_simbolos_unicode_van_a_su_comando():
    tex, _ = L.cuerpo_latex(CUERPO)
    assert "Si p $\\ge$ 1 entonces $\\alpha$ $\\to$ $\\beta$, con x $\\in$ $\\mathbb{R}$\\dots{}" in tex
    tex2, _ = L.cuerpo_latex("$M_p ≤ A^p · M_{p+1}$, γ(M) > 0\n")
    assert "$M_p \\le  A^p \\cdot  M_{p+1}$" in tex2 and "$\\gamma$(M) > 0" in tex2
    assert not re.search("[≤≥→αβ∈ℝ…·γ]", tex + tex2)


def test_las_marcas_salen_en_rojo_tambien_dentro_de_una_formula():
    tex, _ = L.cuerpo_latex(CUERPO)
    assert "\\emph{log-convexa} \\duda{[?]}" in tex and "y aqui \\duda{[ILEGIBLE]}." in tex
    assert "$M_{p+q} \\text{\\duda{[ILEGIBLE]}} A^{p+q}M_pM_q$" in tex
    assert "\\fbox{\\parbox{\\dimexpr\\linewidth-2\\fboxsep-2\\fboxrule\\relax}{FIGURA: sector de abertura pi/2}}" in tex
    tex2, _ = L.cuerpo_latex("Final.\n\n[PAGINA CORTADA por el tope de salida: revisa el final contra el original]\n")
    assert "\\duda{[PAGINA CORTADA por el tope de salida: revisa el final contra el original]}" in tex2


def test_codigo_citas_tablas_y_enlaces():
    md = ("> una cita con $x$\n\n```\nuno $y$ [?] 50%\n```\n\n| a | b |\n|---|---|\n| $M_p$ | 50% |\n\n"
          "`codigo_x` y [un enlace](https://arxiv.org/abs/1001.4064) y ---\n\n---\n")
    tex, _ = L.cuerpo_latex(md)
    assert "\\begin{quote}\nuna cita con $x$\n\n\\end{quote}" in tex
    assert "\\begin{verbatim}\nuno $y$ [?] 50%\n\\end{verbatim}" in tex              # el codigo, tal cual
    assert "\\begin{tabular}{ll}" in tex and "a & b \\\\" in tex and "$M_p$ & 50\\% \\\\" in tex
    assert "\\texttt{codigo\\_x}" in tex and "(\\texttt{https://arxiv.org/abs/1001.4064})" in tex
    assert "\\hrule" in tex and _casado(L.documento(md, nombre="x"))


def test_sin_titulo_no_hay_maketitle_y_un_titulo_de_pagina_es_seccion():
    tex = L.documento("<!-- pagina 3 -->\n\n# Tema 2\n\nTexto.\n", nombre="x")
    assert "\\maketitle" not in tex and "\\title" not in tex and "\\section*{Tema 2}" in tex
    assert "% ---------- pagina 3 ----------" in tex and _casado(tex)


def test_la_huella_delata_una_edicion_a_mano():
    tex = L.documento(CUERPO, nombre="x", fecha="2026-11-11")
    assert L.intacto(tex) and tex == L.documento(CUERPO, nombre="x", fecha="2026-11-11")
    assert not L.intacto(tex.replace("\\section*{Definiciones}", "\\section{Definiciones}"))
    assert not L.intacto("\\documentclass{article}\n") and not L.intacto("")
