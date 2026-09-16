"""Ingesta: parser de .tex, deteccion de ids y verificacion de titulo. Sin red."""
from nucleo import corpus as Q

TEX = r"""
\documentclass{amsart}
\newtheorem{thm}{Theorem}[section]
\newtheorem{lem}[thm]{Lemma}
\newtheorem{defi}[thm]{Definition}
\begin{document}
\maketitle
\begin{abstract}
We study strongly regular sequences and extension operators in ultraholomorphic classes.
\end{abstract}
\section{Introduction}
Let $M=(M_p)$ be a sequence of positive reals. % comentario que no debe salir
The extension problem for ultraholomorphic classes in sectors goes back to Thilliez.

\section{Strongly regular sequences}
\begin{defi}\label{def:sr}
A sequence $M$ is strongly regular if it is logarithmically convex, of moderate growth
and strongly non-quasianalytic.
\end{defi}
\begin{thm}\label{thm:ext}
If $M$ is strongly regular then the Borel map is surjective on every sector of small opening.
\end{thm}
\begin{proof}
It follows from the construction of flat functions in the class.
\end{proof}
\end{document}
"""

PAGINAS = [
    "STRONGLY REGULAR SEQUENCES\nWe study strongly regular sequences and extension operators in ultraholomorphic classes.\n"
    "1. Introduction\nLet M be a sequence of positive reals. The extension problem for ultraholomorphic classes in sectors goes back to Thilliez.",
    "2. Strongly regular sequences\nDefinition 2.1. A sequence M is strongly regular if it is logarithmically convex, of moderate growth "
    "and strongly non-quasianalytic.\nTheorem 2.2. If M is strongly regular then the Borel map is surjective on every sector of small opening.\n"
    "Proof. It follows from the construction of flat functions in the class.",
]


def test_unidades_tex_distingue_tipos_y_mapea_paginas():
    U = Q.unidades_tex(TEX, PAGINAS)
    tipos = [u["tipo"] for u in U]
    assert "resumen" in tipos and "definicion" in tipos and "teorema" in tipos and "demostracion" in tipos
    teo = next(u for u in U if u["tipo"] == "teorema")
    assert teo["label"] == "thm:ext" and teo["seccion"] == "2" and teo["pagina"] == 2
    defi = next(u for u in U if u["tipo"] == "definicion")
    assert defi["label"] == "def:sr" and defi["pagina"] == 2
    intro = next(u for u in U if u["tipo"] == "parrafo")
    assert intro["pagina"] == 1 and "comentario" not in intro["texto"]


def test_newtheorem_del_paper_amplia_los_tipos():
    tipos = Q._tipos_del_paper(TEX.split(r"\begin{document}")[0])
    assert tipos["defi"] == "definicion" and tipos["lem"] == "lema" and tipos["thm"] == "teorema"


def test_detectar_ids_en_las_primeras_paginas():
    pags = ["arXiv:0809.2057v1 [math.CV] 11 Sep 2008\nTitle", "DOI 10.1007/s00605-009-0108-0."]
    arxiv, doi = Q._detectar_ids(pags)
    assert arxiv == "0809.2057v1" and doi == "10.1007/s00605-009-0108-0"
    assert Q._detectar_ids(["nada aqui"]) == (None, None)


def test_titulo_en_texto_exige_coincidencia():
    assert Q.titulo_en_texto("Smooth solutions of quasianalytic or ultraholomorphic equations",
                             "SMOOTH SOLUTIONS OF QUASIANALYTIC OR ULTRAHOLOMORPHIC EQUATIONS\nVincent Thilliez")
    assert not Q.titulo_en_texto("Division by flat ultradifferentiable functions",
                                 "Smooth solutions of quasianalytic equations")


def test_id_desde_fichero():
    assert Q.id_desde_fichero("C:/x/Thilliez 2003 (Results).pdf") == "thilliez-2003-results"


def test_texto_plano_quita_matematicas_y_comandos():
    plano = Q._texto_plano(r"Let $M=(M_p)$ be \emph{strongly} regular \cite{T03}.")
    assert "M_p" not in plano and "emph" not in plano and "strongly" in plano
