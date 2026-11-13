"""El .tex con el formato del TFM de Mariano: enunciados y demostraciones en sus entornos, a partir de
las marcas <!-- teorema --> ... <!-- fin --> del .md; y `estructura`, que las pone en lo ya transcrito."""
import os
import re
import types
import pytest

from nucleo import transcribir as T
from nucleo import a_latex as L
from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M
from nucleo import prompts as P


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(C, "F_LLAMADAS", str(tmp_path / "llamadas.jsonl"))
    monkeypatch.setattr(C, "SIMULAR", True)
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)
    monkeypatch.setattr(E, "commits_todos", lambda: [])
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", E._marcas_vacias()))
    monkeypatch.setattr(K, "_abrir", lambda ruta: None)
    return tmp_path


def _pdf(ruta, paginas=2):
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}")
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


MD = """<!-- pagina 1 -->

**30 sep, clase:**

<!-- notacion -->
**Notación:** $\\mathbb{C}^{\\mathbb{N}_0}$ son las sucesiones.
<!-- fin -->

<!-- teorema -->
**Teorema (Pringsheim):** Sea $f\\in\\mathcal{C}^\\infty([a,b])$, entonces existen $A,C>0$ tales que

$|f^{(n)}(x)|\\le CA^n n!$
<!-- fin -->

Un comentario suelto.

<!-- demostracion -->
Dem: $\\boxed{\\Leftarrow}$ Basta usar Taylor.

Y se acaba. $\\blacksquare$
<!-- fin -->

<!-- proposicion -->
**Proposición** (existencia de funciones características, Bang, tesis 1946): Sea $M$ (lc).
<!-- fin -->

<!-- demostracion -->
**Dem (th Cartan):** Es claro.

<!-- pagina 2 -->

Sigue en la pagina siguiente.
<!-- fin -->

<!-- teorema -->
## **Teorema de Gorny-Cartan (1938-1940)**

Sea $f$ $n$ veces derivable.
<!-- fin -->

<!-- ejemplo -->
Ej: $f(x)=e^{-1/x}$.
<!-- fin -->

<!-- definicion -->
**Definición 2.3:** $M\\approx L$ si pasa esto.
"""


def test_los_enunciados_salen_en_sus_entornos_con_su_nombre():
    tex, _ = L.cuerpo_latex(MD)
    assert "\\begin{notacion}\n$\\mathbb{C}^{\\mathbb{N}_0}$ son las sucesiones.\n\\end{notacion}" in tex
    assert ("\\begin{teorema}[{Pringsheim}]\nSea $f\\in\\mathcal{C}^\\infty([a,b])$, entonces existen $A,C>0$ tales que\n\n"
            "\\[\n|f^{(n)}(x)|\\le CA^n n!\n\\]\n\\end{teorema}") in tex
    assert "\\end{teorema}\n\nUn comentario suelto.\n\n\\begin{demostracion}" in tex            # el comentario, fuera
    assert "\\begin{proposicion}[{existencia de funciones características, Bang, tesis 1946}]\nSea $M$ (lc)." in tex
    assert "\\begin{teorema}[{Gorny-Cartan, 1938-1940}]\nSea $f$ $n$ veces derivable.\n\\end{teorema}" in tex
    assert "\\begin{ejemplo}\n$f(x)=e^{-1/x}$.\n\\end{ejemplo}" in tex
    assert "\\begin{definicion}[{2.3}]\n$M\\approx L$ si pasa esto.\n\\end{definicion}" in tex   # sin cerrar: se cierra al final
    assert "Teorema (Pringsheim)" not in tex and "\\section*" not in tex and "<!--" not in tex
    assert not re.search("[\ue000-\ue0ff]", tex)


def test_la_demostracion_cruza_de_pagina_y_no_duplica_el_cuadrado():
    tex, _ = L.cuerpo_latex(MD)
    assert "\\begin{demostracion}\n$\\boxed{\\Leftarrow}$ Basta usar Taylor.\n\nY se acaba.\n\\end{demostracion}" in tex
    assert ("\\begin{demostracion}[ (th Cartan)]\nEs claro.\n\n% ---------- pagina 2 ----------\n\n"
            "Sigue en la pagina siguiente.\n\\end{demostracion}") in tex
    assert "\\blacksquare" not in tex


def test_todo_casa_y_el_preambulo_es_el_del_tfm():
    tex = L.documento("# Curso\n\n" + MD, nombre="x")
    pre = tex.split("\\begin{document}")[0]
    assert "\\documentclass[12pt,a4paper]{article}" in pre
    assert "\\newtheoremstyle{tfm}{\\topsep}{\\topsep}{\\normalfont}{}{\\bfseries}{.}{ }{}" in pre
    for env, titulo in (("teorema", "Teorema"), ("lema", "Lema"), ("proposicion", "Proposición"),
                        ("corolario", "Corolario"), ("definicion", "Definición"), ("observacion", "Observación"),
                        ("ejemplo", "Ejemplo"), ("notacion", "Notación"), ("nota", "Nota")):
        assert ("\\newtheorem{%s}{%s}" % (env, titulo) in pre) or ("\\newtheorem{%s}[teorema]{%s}" % (env, titulo) in pre)
    assert "\\renewcommand{\\qedsymbol}{$\\blacksquare$}" in pre and "Demostración#1:" in pre
    cuerpo = tex.split("\\begin{document}")[1]
    for env in L.ENTORNOS:
        assert cuerpo.count("\\begin{%s}" % env) == cuerpo.count("\\end{%s}" % env)
    assert cuerpo.count("\\begin{teorema}") == 2 and cuerpo.count("\\begin{demostracion}") == 2


def test_una_marca_dentro_de_una_lista_no_rompe_el_tex():
    md = "- uno\n\n<!-- teorema -->\n**Teorema:** con lista\n\n- a\n- b\n<!-- fin -->\n\nFuera.\n"
    tex, _ = L.cuerpo_latex(md)
    assert tex.count("\\begin{itemize}") == tex.count("\\end{itemize}")
    assert tex.count("\\begin{teorema}") == tex.count("\\end{teorema}")
    # un <!-- fin --> sin nada abierto, o dos seguidos, no hacen nada
    tex2, _ = L.cuerpo_latex("Texto.\n<!-- fin -->\n\n<!-- lema -->\n**Lema:** x.\n<!-- fin -->\n<!-- fin -->\nMas.\n")
    assert tex2.count("\\begin{lema}") == 1 == tex2.count("\\end{lema}") and "\\end{teorema}" not in tex2


def test_sin_marcas_el_tex_sigue_como_antes():
    tex, _ = L.cuerpo_latex("**Teorema:** Sea $M$.\n\nDem: trivial.\n")
    assert "\\textbf{Teorema:} Sea $M$." in tex and "\\begin{teorema}" not in tex


def test_el_preambulo_propio_sustituye_al_de_serie(repo):
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=1), titulo="Tema 1")
    assert "\\newtheoremstyle{tfm}" in open(r["tex"], encoding="utf-8").read()
    (repo / "transcripciones" / "preambulo.tex").write_text(
        "\\documentclass[11pt]{book}\n\\usepackage{mis-macros}\n\\newcommand{\\duda}[1]{#1}\n", encoding="utf-8")
    assert T.exportar_tex(r["nombre"])[1] == "escrito"
    tex = open(r["tex"], encoding="utf-8").read()
    assert "\\documentclass[11pt]{book}\n\\usepackage{mis-macros}" in tex and "\\newtheoremstyle{tfm}" not in tex
    assert "\\begin{document}" in tex and L.intacto(tex)


def test_estructura_marca_lo_ya_transcrito_sin_cambiar_el_texto(repo, monkeypatch, capsys):
    textos = iter(["**Teorema:** Sea $M$ (lc).\n\n$M_p^2\\le M_{p-1}M_{p+1}$\n\n**Dem.** Es claro.\n\nComentario.",
                   "Sin nada que marcar."])
    monkeypatch.setattr(M, "_completar", lambda *a, **k: (next(textos), 100, 50, 0, {}))
    r = T.transcribir(_pdf(repo / "a.pdf"), tipo="curso", titulo="Tema 1")
    monkeypatch.setattr(M, "_completar", lambda *a, **k: ("1-2: teorema\n3: demostracion\n4-9: lema\n2-3: nota", 500, 20, 0, {}))
    antes = dict(T.paginas(T.leer(r["nombre"])["cuerpo"])[1])
    res = T.estructura(r["nombre"])
    # los rangos fuera de la pagina (4-9) o desordenados (2-3 tras el 3) se descartan; en la pagina 2 no cabe ninguno
    assert res["bloques"] == 2 and res["paginas"] == [1]
    hojas = dict(T.paginas(T.leer(r["nombre"])["cuerpo"])[1])
    assert hojas[1] == ("<!-- teorema -->\n**Teorema:** Sea $M$ (lc).\n\n$M_p^2\\le M_{p-1}M_{p+1}$\n<!-- fin -->\n\n"
                        "<!-- demostracion -->\n**Dem.** Es claro.\n<!-- fin -->\n\nComentario.")
    sin_marcas = [l for l in hojas[1].splitlines() if l.strip() and not T.RE_BLOQUE.match(l)]
    assert sin_marcas == [l for l in antes[1].splitlines() if l.strip()]                         # ni una palabra cambiada
    tex = open(r["tex"], encoding="utf-8").read()
    assert "\\begin{teorema}\nSea $M$ (lc)." in tex and "\\begin{demostracion}\nEs claro.\n\\end{demostracion}" in tex
    # el indice no ve las marcas
    assert not any("<!--" in u["texto"] for u in T.unidades(T.leer(r["nombre"])["cuerpo"]))
    # segunda vez: la pagina ya marcada se deja; solo se vuelve a preguntar por la que no tenia ningun bloque
    n = len(open(C.F_LLAMADAS, encoding="utf-8").readlines())
    assert T.estructura(r["nombre"])["bloques"] == 0 and len(open(C.F_LLAMADAS, encoding="utf-8").readlines()) == n + 1
    assert dict(T.paginas(T.leer(r["nombre"])["cuerpo"])[1]) == hojas
    K.cmd_transcribir(types.SimpleNamespace(fichero=None, tipo="paper", titulo=None, paginas=None, motor="modelo",
                                            calidad="alta", lista=False, revisado=None, tex=None, pisar=False,
                                            figuras=None, estructura="no-existe"))
    assert "no existe" in capsys.readouterr().out


def test_el_prompt_pide_las_marcas_de_bloque():
    assert "<!-- teorema -->" in P.TRANSCRIBIR and "<!-- demostracion -->" in P.TRANSCRIBIR and "<!-- fin -->" in P.TRANSCRIBIR
    assert "MODO_ESTRUCTURA" in P.ESTRUCTURA and "a-b: tipo" in P.ESTRUCTURA
