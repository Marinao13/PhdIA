"""nucleo/a_latex.py: la sexta revision, con paginas realistas del campo. Ninguna linea dejaba de
compilar; esto es composicion: lo que salia claramente mal en apuntes de verdad."""
import argparse

from nucleo import a_latex as L
from nucleo import prompts as P
from nucleo import transcribir as T


def test_una_cadena_de_desigualdades_no_parte_el_parrafo():
    md = ("Entonces\n$|G^{(p)}(z)|\\le p!\\,\\varepsilon^{-p}|z|^{-p}\\sup|G|$\n$\\le p!\\,A^pM_p$\n"
          "para todo $z\\in S_\\gamma$.\n\nOtro parrafo.\n")
    tex, _ = L.cuerpo_latex(md)
    assert ("Entonces\n\\[\n|G^{(p)}(z)|\\le p!\\,\\varepsilon^{-p}|z|^{-p}\\sup|G|\n\\]\n\\[\n\\le p!\\,A^pM_p\n\\]\n"
            "para todo $z\\in S_\\gamma$.\n\nOtro parrafo.") in tex
    # una formula en su propio parrafo sigue siendo un parrafo aparte
    tex2, _ = L.cuerpo_latex("Antes.\n\n$a \\le b$\n\nDespues.\n")
    assert "Antes.\n\n\\[\na \\le b\n\\]\n\nDespues." in tex2


def test_la_formula_que_abre_un_apartado_se_queda_en_linea():
    tex, _ = L.cuerpo_latex("- $M_p^2\\le M_{p-1}M_{p+1}$\n- $M_{p+q}\\le A^{p+q}M_pM_q$\n- Texto:\n  $x \\le y$\n- $$z = 1$$\n")
    assert "\\item $M_p^2\\le M_{p-1}M_{p+1}$" in tex and "\\item $M_{p+q}\\le A^{p+q}M_pM_q$" in tex
    assert "\\item Texto:\n\\[\nx \\le y\n\\]" in tex                 # dentro del apartado, tras texto, si
    assert "\\item \\[\nz = 1\n\\]" in tex                            # y un $$ explicito se respeta


def test_rayas_vistos_y_guiones_dentro_y_fuera_de_una_formula():
    tex = L.documento("Sea $\\sum_p \\frac{M_p}{M_{p+1}}<\\infty$ $\\text{(Denjoy–Carleman)}$, log\u2011convexa.\n\n"
                      "| cond | vale |\n|---|---|\n| (mg) | ✓ |\n| (dc) | ✗ |\n", nombre="x")
    assert "\\text{(Denjoy--Carleman)}" in tex and "log-convexa" in tex
    assert "(mg) & $\\checkmark$ \\\\" in tex and "(dc) & $\\times$ \\\\" in tex
    assert "\\DeclareUnicodeCharacter" not in tex


def test_el_recuadro_de_la_figura_no_lleva_sangria():
    tex, _ = L.cuerpo_latex("[FIGURA: sector $S_\\gamma$ con un subsector sombreado]\n")
    assert tex.startswith("\\noindent\\fbox{\\parbox{")


def test_una_frase_que_sigue_en_la_pagina_siguiente_no_se_parte():
    md = ("<!-- pagina 2 -->\n\nEntonces existe una cte. $b>0$ que solo depende de\n\n<!-- pagina 3 -->\n\n"
          "$\\mathbb{M}$ y de $\\delta$ tal que $|G(z)|\\le h(b|z|)$.\n\n<!-- pagina 4 -->\n\n## Otro tema\n\nTexto.\n")
    tex, _ = L.cuerpo_latex(md)
    assert "solo depende de\n% ---------- pagina 3 ----------\n$\\mathbb{M}$ y de" in tex
    # tras un punto, o antes de un titulo, la marca sigue separando parrafos
    assert "h(b|z|)$.\n\n% ---------- pagina 4 ----------\n\n\\section*{Otro tema}" in tex


def test_el_prompt_pide_un_parrafo_por_apartado_y_sabe_de_hojas_dobles():
    assert "en su propio parrafo" in P.TRANSCRIBIR and "lado a lado" in P.TRANSCRIBIR
    assert "se transparenta" in P.TRANSCRIBIR and "nota al margen" in P.TRANSCRIBIR.lower()


def test_la_calidad_por_defecto_es_la_alta():
    # 2026-11-12, con la letra de Mariano: el modelo barato cambiaba simbolos y subindices sin avisar
    import inspect
    assert inspect.signature(T.transcribir).parameters["calidad"].default == "alta"
    import doc
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    fuente = inspect.getsource(doc.main)
    assert 'choices=["normal", "alta"], default="alta"' in fuente
