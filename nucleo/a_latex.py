"""
De una transcripcion (markdown con las formulas entre $...$) a un .tex para pdflatex.

    python doc.py transcribir --tex NOMBRE        escribe transcripciones/NOMBRE.tex desde el .md de ahora

La fuente sigue siendo el .md: es lo que se revisa, lo que se indexa y lo que se cita. El .tex
es una exportacion para llevarla a un documento; lo que se corrija en el no vuelve al .md.

Que hace: titulos a \\section* / \\subsection*, negritas, cursivas, listas (las numeradas
conservan su numero), citas, tablas sencillas y codigo; las formulas pasan tal cual (una formula
sola en su linea, a \\[ ... \\]); los caracteres especiales del texto se escapan; los simbolos
Unicode sueltos (<=, flechas, letras griegas) se pasan a su comando, y el que no tenga comando
conocido se declara en el preambulo para que compile y salga en rojo; las marcas [ILEGIBLE] y
[?] salen en rojo con \\duda{} para que no se pierdan de vista; cada pagina del original queda
senalada con un comentario.

La primera linea del .tex lleva una huella del resto: si lo editas a mano, la huella deja de
casar y una nueva exportacion no lo pisa sin que se lo pidas.

Aviso: en la torre no hay pdflatex. Lo de aqui esta razonado y revisado, no compilado.
"""
import re, hashlib, datetime

# las mismas formulas que reconoce la web (web/render.py): $$...$$ | \[...\] | \(...\) | $...$
RE_MATH = re.compile(
    r"\$\$[\s\S]+?\$\$"
    r"|\\\[[\s\S]+?\\\]"
    r"|\\\([\s\S]+?\\\)"
    r"|(?<![\\$])\$(?![\s$])(?:\\.|[^$\\\n]|\n(?![ \t]*\n))+?(?<![\s\\])\$")
RE_MARCA = re.compile(r"\[ILEGIBLE\]|\[\?\]|\[PAGINA CORTADA[^\]]*\]|\[FIGURA:[^\]]*\]")
RE_PAGINA = re.compile(r"^<!-- pagina (\d+) -->[ \t]*$", re.M)
RE_AVISO = re.compile(r"^> Transcripcion automatica SIN REVISAR\.[^\n]*\n(?:>[^\n]*\n)*\n?", re.M)

# marcadores privados: formula, marca, pagina, formula en display, formula forzada en linea
_F, _M, _P, _D = "\ue000{}\ue001", "\ue002{}\ue003", "\ue004{}\ue005", "\ue006{}\ue007"
_L = "\ue008{}\ue009"
_G = "\ue00a{}\ue00b"                                  # una figura recortada: ancho|ruta
_RE_G = re.compile("\ue00a([0-9.]+)\\|([^\ue00b]+)\ue00b\\n?")
_RE_L = re.compile("\ue008(\\d+)\ue009")
_RE_F = re.compile("\ue000(\\d+)\ue001")
_RE_M = re.compile("\ue002(\\d+)\ue003")
_RE_P = re.compile("\ue004(\\d+)\ue005")
_RE_D = re.compile("\ue006(\\d+)\ue007")
_RE_SOLO_F = re.compile("\\s*\ue000(\\d+)\ue001\\s*")

_ESPECIALES = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "&": r"\&", "%": r"\%", "#": r"\#",
               "_": r"\_", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}", "$": r"\$"}

# simbolos Unicode que pdflatex con inputenc no trae: su comando de modo matematico
_SIMBOLOS = {
    "≤": r"\le", "≥": r"\ge", "≠": r"\ne", "≈": r"\approx", "∼": r"\sim", "≃": r"\simeq", "≡": r"\equiv",
    "≪": r"\ll", "≫": r"\gg", "≺": r"\prec", "≻": r"\succ", "≼": r"\preceq", "≽": r"\succeq", "∝": r"\propto",
    "→": r"\to", "←": r"\leftarrow", "↔": r"\leftrightarrow", "↦": r"\mapsto", "↑": r"\uparrow", "↓": r"\downarrow",
    "⇒": r"\Rightarrow", "⇐": r"\Leftarrow", "⇔": r"\Leftrightarrow",
    "⟶": r"\longrightarrow", "⟵": r"\longleftarrow", "⟹": r"\Longrightarrow", "⟸": r"\Longleftarrow",
    "⟺": r"\Longleftrightarrow", "⟼": r"\longmapsto", "↗": r"\nearrow", "↘": r"\searrow", "↙": r"\swarrow", "↖": r"\nwarrow", "↪": r"\hookrightarrow",
    "∈": r"\in", "∉": r"\notin", "∋": r"\ni", "⊂": r"\subset", "⊆": r"\subseteq", "⊃": r"\supset", "⊇": r"\supseteq",
    "∪": r"\cup", "∩": r"\cap", "∖": r"\setminus", "∅": r"\emptyset", "∞": r"\infty",
    "∑": r"\sum", "∏": r"\prod", "∫": r"\int", "∮": r"\oint", "∂": r"\partial", "∇": r"\nabla",
    "∀": r"\forall", "∃": r"\exists", "∄": r"\nexists", "¬": r"\neg", "∧": r"\wedge", "∨": r"\vee",
    "×": r"\times", "·": r"\cdot", "⋅": r"\cdot", "±": r"\pm", "∓": r"\mp", "÷": r"\div", "∘": r"\circ",
    "⊕": r"\oplus", "⊗": r"\otimes", "√": r"\surd", "∣": r"\mid", "∥": r"\parallel", "‖": r"\|", "⊥": r"\perp",
    "⌊": r"\lfloor", "⌋": r"\rfloor", "⌈": r"\lceil", "⌉": r"\rceil", "⟨": r"\langle", "⟩": r"\rangle",
    "ℓ": r"\ell", "ℏ": r"\hbar", "ℜ": r"\Re", "ℑ": r"\Im", "ℵ": r"\aleph", "∎": r"\blacksquare", "□": r"\square",
    "✓": r"\checkmark", "✔": r"\checkmark", "✗": r"\times", "✘": r"\times",
    "…": r"\dots", "⋯": r"\cdots", "⋮": r"\vdots", "⋱": r"\ddots",
    "ℕ": r"\mathbb{N}", "ℤ": r"\mathbb{Z}", "ℚ": r"\mathbb{Q}", "ℝ": r"\mathbb{R}", "ℂ": r"\mathbb{C}",
}
_GRIEGAS = dict(zip("αβγδεζηθικλμνξπρστυφχψω",
                    ["alpha", "beta", "gamma", "delta", "varepsilon", "zeta", "eta", "theta", "iota", "kappa",
                     "lambda", "mu", "nu", "xi", "pi", "rho", "sigma", "tau", "upsilon", "varphi", "chi", "psi",
                     "omega"]))
_GRIEGAS.update(dict(zip("ΓΔΘΛΞΠΣΦΨΩ", ["Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi",
                                         "Omega"])))
_GRIEGAS.update({"ϕ": "phi", "ϵ": "epsilon", "ϑ": "vartheta", "ϱ": "varrho", "ς": "varsigma", "ϖ": "varpi"})
_SIMBOLOS.update({k: "\\" + v for k, v in _GRIEGAS.items()})
# super y subindices Unicode, por rachas: x²³ -> x^{23} (uno a uno daria "double superscript")
_SUPER = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻ⁿ", "0123456789+-n"))
_SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉₊₋", "0123456789+-"))
_RE_SUPER = re.compile("[" + "".join(_SUPER) + "]+")
_RE_SUB = re.compile("[" + "".join(_SUB) + "]+")
# dentro de una formula (fuera de \text{}): los acentos de texto no valen en modo matematico
_ACENTOS = {"á": r"\acute{a}", "é": r"\acute{e}", "í": r"\acute{\imath}", "ó": r"\acute{o}", "ú": r"\acute{u}",
            "Á": r"\acute{A}", "É": r"\acute{E}", "Í": r"\acute{I}", "Ó": r"\acute{O}", "Ú": r"\acute{U}",
            "ñ": r"\tilde{n}", "Ñ": r"\tilde{N}", "ü": r"\ddot{u}", "Ü": r"\ddot{U}"}
_RE_ACENTO = re.compile("[" + "".join(_ACENTOS) + "]")
# lo que vale igual en texto y en formula
_COMUNES = {"′": "'", "″": "''", "−": "-", "\u00a0": "~", "\u2009": r"\,", "\u202f": r"\,", "\u200b": "",
            "\u2011": "-", "\u2010": "-"}
_TIPOGRAFIA = {"–": "--", "—": "---", "“": "``", "”": "''", "‘": "`", "’": "'"}
_RE_ESPECIAL = re.compile(r"[\\{}&%#_^~$]")
_RE_SIMBOLO = re.compile("[" + re.escape("".join(_SIMBOLOS)) + "]")
_RE_COMUN = re.compile("[" + re.escape("".join(_COMUNES)) + "]")
_RE_TIPO = re.compile("[" + re.escape("".join(_TIPOGRAFIA)) + "]")
_RE_EN_TEXTO = re.compile(r"\\(?:text|mbox|hbox|textrm|textit|textbf|textsf|texttt|intertext)\b")
# por encima del latin extendido, lo que pdflatex (inputenc utf8 + T1 + textcomp del nucleo) si conoce
_CONOCIDOS = set("‚„†‡•‰‹›€™")


def _comillas(s):
    """Comillas rectas a comillas de LaTeX: de apertura tras blanco o parentesis, de cierre si no."""
    return re.sub(r'"', lambda m: "``" if m.start() == 0 or s[m.start() - 1] in " \t\n([{\u00bf\u00a1" else "''", s)


def _texto(s, comillas=True):
    """Texto corriente: especiales escapados, simbolos Unicode a su comando entre $ $."""
    s = _RE_ESPECIAL.sub(lambda m: _ESPECIALES[m.group()], s).replace("…", r"\dots{}")
    s = _RE_SUPER.sub(lambda m: "$^{" + "".join(_SUPER[c] for c in m.group()) + "}$", s)
    s = _RE_SUB.sub(lambda m: "$_{" + "".join(_SUB[c] for c in m.group()) + "}$", s)
    s = _RE_SIMBOLO.sub(lambda m: "$" + _SIMBOLOS[m.group()] + "$", s)
    s = _RE_COMUN.sub(lambda m: _COMUNES[m.group()], s)
    s = _RE_TIPO.sub(lambda m: _TIPOGRAFIA[m.group()], s)
    return _comillas(s) if comillas else s.replace('"', r"\textquotedbl{}")


def _marca(m, en_formula=False):
    """[ILEGIBLE], [?] y [PAGINA CORTADA ...] en rojo; [FIGURA: ...] en un recuadro que parte linea."""
    if m.startswith("[FIGURA:"):
        m = re.sub(r"\s*\|\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*\]$", "]", m)
        if en_formula:
            return r"\fbox{" + _texto(m[1:-1]) + "}"
        return r"\noindent\fbox{\parbox{\dimexpr\linewidth-2\fboxsep-2\fboxrule\relax}{" + _texto(m[1:-1]) + "}}"
    return r"\duda{" + _texto(m) + "}"


def _formula(f, display=False, en_linea=False):
    """Una formula tal como esta escrita, con sus delimitadores puestos para LaTeX.
    en_linea=True: el sitio no admite display (una celda de tabla, un titulo); aunque venga con
    $$...$$ o \\[...\\], sale entre $ $ con \\displaystyle."""
    if f.startswith("$$"):
        cuerpo, display = f[2:-2], True
    elif f.startswith("\\["):
        cuerpo, display = f[2:-2], True
    elif f.startswith("\\("):
        cuerpo = f[2:-2]
    else:
        cuerpo = f[1:-1]
    # un simbolo Unicode dentro de la formula: su comando; si la formula lleva \text{...}, con
    # \ensuremath, que vale tanto dentro como fuera del \text
    con_texto = bool(_RE_EN_TEXTO.search(cuerpo))
    mates = (lambda s: r"\ensuremath{" + s + "}") if con_texto else (lambda s: s)
    cuerpo = _RE_SUPER.sub(lambda m: mates("^{" + "".join(_SUPER[c] for c in m.group()) + "}"), cuerpo)
    cuerpo = _RE_SUB.sub(lambda m: mates("_{" + "".join(_SUB[c] for c in m.group()) + "}"), cuerpo)
    cuerpo = _RE_SIMBOLO.sub(lambda m: mates(_SIMBOLOS[m.group()]) + ("" if con_texto else " "), cuerpo)
    cuerpo = cuerpo.replace("°", mates(r"^{\circ}"))
    if not con_texto:                                  # dentro de \text{} los acentos estan bien como estan
        cuerpo = _RE_ACENTO.sub(lambda m: _ACENTOS[m.group()], cuerpo)
    cuerpo = _RE_COMUN.sub(lambda m: _COMUNES[m.group()], cuerpo)
    cuerpo = _RE_TIPO.sub(lambda m: _TIPOGRAFIA[m.group()], cuerpo)       # una raya dentro de \text{(Denjoy–Carleman)}
    cuerpo = RE_MARCA.sub(lambda m: r"\text{" + _marca(m.group(0), en_formula=True) + "}", cuerpo)
    cuerpo = cuerpo.strip()
    varias = ("\\\\" in cuerpo or "&" in cuerpo) and "\\begin{" not in cuerpo
    if en_linea or not display:
        if not display:
            return "$" + cuerpo + "$"
        cuerpo = re.sub(r"\\tag\*?\{([^{}]*)\}", lambda m: r"\quad\text{(" + m.group(1) + ")}", cuerpo)
        if varias:
            cuerpo = "\\begin{aligned}\n" + _sin_opcional(cuerpo) + "\n\\end{aligned}"
        return "$\\displaystyle " + cuerpo + "$"
    if re.match(r"\\begin\{(align|equation|gather|multline|eqnarray|flalign|alignat)\*?\}", cuerpo):
        return cuerpo                                  # ya es un entorno de display
    if varias and "\\tag" in cuerpo:                   # aligned no admite \tag; gather* y align*, uno por fila
        entorno = "align*" if "&" in cuerpo else "gather*"
        return "\\begin{%s}\n%s\n\\end{%s}" % (entorno, cuerpo, entorno)
    if varias:
        cuerpo = "\\begin{aligned}\n" + _sin_opcional(cuerpo) + "\n\\end{aligned}"
    return "\\[\n" + cuerpo + "\n\\]"


def _en_linea(hijos, display=True, tras_item=False):
    """display=False en titulos y celdas de tabla: ahi una formula sola no puede ir en display.
    Tampoco dentro de una negrita o cursiva: dejaria una linea en blanco dentro de \\textbf{}."""
    out, n, enlace, anidado = [], len(hijos), None, 0
    for i, h in enumerate(hijos):
        t = h.type
        if t == "text":
            m = _RE_SOLO_F.fullmatch(h.content)
            # la formula que abre un apartado de lista se queda en linea: en display, la vineta
            # quedaria sola en su renglon y la formula centrada debajo
            sola = (display and not anidado and m and not (tras_item and i == 0)
                    and (i == 0 or hijos[i - 1].type == "softbreak")
                    and (i == n - 1 or hijos[i + 1].type == "softbreak"))
            if sola:
                out.append(_D.format(m.group(1)))
            elif display:
                out.append(_texto(h.content))
            else:                                      # titulo o celda: las formulas, forzadas en linea
                out.append(_RE_F.sub(lambda f: _L.format(f.group(1)), _texto(h.content)))
        elif t == "softbreak":
            out.append("\n")
        elif t == "hardbreak":
            out.append("\\\\\n")
        elif t == "strong_open":
            anidado += 1
            out.append(r"\textbf{")
        elif t == "em_open":
            anidado += 1
            out.append(r"\emph{")
        elif t in ("strong_close", "em_close"):
            anidado -= 1
            out.append("}")
        elif t == "code_inline":
            out.append(r"\texttt{" + _texto(h.content, comillas=False) + "}")
        elif t == "link_open":
            enlace = h.attrGet("href")
        elif t == "link_close":
            if enlace:
                out.append(r" (\texttt{" + _texto(enlace, comillas=False) + "})")
            enlace = None
        elif t == "image":
            src = h.attrGet("src") or ""
            if src.startswith("figuras/") and re.fullmatch(r"[\w./-]+", src):
                try:
                    ancho = min(0.95, max(0.1, float(h.attrGet("title") or 0.6)))
                except ValueError:
                    ancho = 0.6
                out.append(_G.format("%.2f|%s" % (ancho, src)))
            else:
                out.append("[imagen: " + _texto(h.content or "") + "]")
        elif t in ("s_open", "s_close"):
            pass                                       # lo tachado, como texto normal
        else:
            out.append(_texto(getattr(h, "content", "") or ""))
    # un [ o un * justo tras un salto forzado se tomarian por el argumento opcional o la estrella de \\
    return re.sub(r"\\\\\n([\[*])", lambda m: "\\\\\n{}" + m.group(1), "".join(out))


def _sin_opcional(texto):
    """Un texto que empieza por [ o por * tras \\item, tras \\\\ o al abrir aligned: LaTeX lo leeria como
    argumento opcional o como la forma con estrella."""
    return "{}" + texto if texto.lstrip().startswith(("[", "*")) else texto


_TITULOS = {1: r"\section{", 2: r"\section{", 3: r"\subsection{", 4: r"\subsubsection{"}
# con clases marcadas, la clase es la seccion y los titulos manuscritos bajan un nivel
_TITULOS_BAJO_CLASE = {1: r"\subsection{", 2: r"\subsection{", 3: r"\subsubsection{"}


def _limpia_titulo(s):
    """El titulo de una seccion: sin la negrita que lo envuelve entero ni los dos puntos del final."""
    s = s.strip()
    m = re.fullmatch(r"\\textbf\{((?:[^{}]|\{[^{}]*\})*)\}\s*[:.]?", s)
    if m:
        s = m.group(1)
    return s.rstrip(" :")
_CONTADORES = ("enumi", "enumii", "enumiii", "enumiv")


def _bloques(tokens, bajo_clase=False):
    out, fila, celdas, columnas, en_titulo, numeradas, tras_item = [], None, None, 0, False, 0, False
    niveles, i_titulo = (_TITULOS_BAJO_CLASE if bajo_clase else _TITULOS), 0
    for i, tok in enumerate(tokens):
        t = tok.type
        if t == "heading_open":
            en_titulo = True
            out.append(niveles.get(int(tok.tag[1]), r"\paragraph{"))
            i_titulo = len(out)
        elif t == "heading_close":
            en_titulo = False
            out[i_titulo:] = [_limpia_titulo("".join(out[i_titulo:]))]
            out.append("}\n\n")
        elif t == "inline":
            texto = _en_linea(tok.children or [], display=not en_titulo and celdas is None, tras_item=tras_item)
            if celdas is not None:
                celdas.append(texto.replace("\n", " "))
            else:
                out.append(_sin_opcional(texto) if tras_item else texto)
            tras_item = False
        elif t == "paragraph_close":
            out.append("\n" if tok.hidden else "\n\n")
        elif t == "bullet_list_open":
            tras_item = False
            out.append("\\begin{itemize}\n")
        elif t == "bullet_list_close":
            out.append("\\end{itemize}\n\n")
        elif t == "ordered_list_open":
            tras_item = False
            out.append("\\begin{enumerate}\n")
            empieza = tok.attrGet("start")             # markdown-it solo lo pone si la lista no empieza en 1
            if empieza is not None and numeradas < len(_CONTADORES):
                out.append("\\setcounter{%s}{%d}\n" % (_CONTADORES[numeradas], int(empieza) - 1))
            numeradas += 1
        elif t == "ordered_list_close":
            numeradas -= 1
            out.append("\\end{enumerate}\n\n")
        elif t == "list_item_open":
            out.append("\\item ")
            tras_item = True
        elif t == "blockquote_open":
            tras_item = False
            out.append("\\begin{quote}\n")
        elif t == "blockquote_close":
            out.append("\\end{quote}\n\n")
        elif t in ("fence", "code_block"):
            tras_item = False
            out.append("\\begin{verbatim}\n" + tok.content.replace("\\end{verbatim}", "\\end {verbatim}")
                       + ("" if tok.content.endswith("\n") else "\n") + "\\end{verbatim}\n\n")
        elif t == "hr":
            out.append("\\medskip\\hrule\\medskip\n\n")
        elif t == "table_open":
            tras_item = False
            columnas = 0
            for otro in tokens[i + 1:]:                # las columnas: los th de la primera fila
                if otro.type == "th_open":
                    columnas += 1
                elif otro.type == "tr_close":
                    break
            out.append("\\begin{center}\n\\begin{tabular}{" + "l" * max(columnas, 1) + "}\n\\hline\n")
        elif t == "tr_open":
            fila = []
        elif t in ("th_open", "td_open"):
            celdas = []
        elif t in ("th_close", "td_close"):
            fila.append(" ".join(celdas))
            celdas = None
        elif t == "tr_close":
            out.append(_sin_opcional(" & ".join(fila)) + " \\\\\n")
            fila = None
        elif t == "thead_close":
            out.append("\\hline\n")
        elif t == "table_close":
            out.append("\\hline\n\\end{tabular}\n\\end{center}\n\n")
    return "".join(out)


# es-noshorthands: sin el, babel en espanol hace activa la comilla " ("c es una cedilla), ~, < y >;
# es-nodecimaldot: sin el, cambia 2.1 por 2,1 en las formulas.
# El formato sigue el TFM de Mariano (visto en su PDF el 2026-11-13): 12 pt, A4, margenes de la
# clase; enunciados con la etiqueta en negrita, numeracion corrida y comun a todos, cuerpo en
# redonda; "Demostracion:" en negrita y cuadrado negro al final.
PREAMBULO = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-noshorthands,es-nodecimaldot]{babel}
\usepackage{amsmath,amssymb,amsthm}
\newtheoremstyle{tfm}{\topsep}{\topsep}{\normalfont}{}{\bfseries}{.}{ }{}
\theoremstyle{tfm}
\newtheorem{teorema}{Teorema}
\newtheorem{lema}[teorema]{Lema}
\newtheorem{proposicion}[teorema]{Proposición}
\newtheorem{corolario}[teorema]{Corolario}
\newtheorem{definicion}[teorema]{Definición}
\newtheorem{observacion}[teorema]{Observación}
\newtheorem{ejemplo}[teorema]{Ejemplo}
\newtheorem{notacion}[teorema]{Notación}
\newtheorem{nota}[teorema]{Nota}
\renewcommand{\qedsymbol}{$\blacksquare$}
\newenvironment{demostracion}[1][]{\begin{proof}[{\normalfont\bfseries Demostración#1:}]}{\end{proof}}
% comentarios de clase y reflexiones propias (lo dicho de palabra, notas al margen): aparte del
% desarrollo, sangrados, en cursiva y con una barra a la izquierda
\newenvironment{comentario}{\par\smallskip\noindent\hspace{1em}\vrule width 1.5pt\hspace{0.8em}%
  \begin{minipage}{\dimexpr\linewidth-3em\relax}\small\itshape}{\end{minipage}\par\smallskip}
\usepackage{mathtools,mathrsfs,bm}  % \coloneqq y dcases, \mathscr, \bm: la web (KaTeX) los pinta sin mas
\providecommand{\degree}{^{\circ}}
\usepackage{graphicx}                % las figuras recortadas del original (transcripciones/figuras/)
\usepackage{xcolor}
% las marcas de la transcripcion ([ILEGIBLE], [?]) salen en rojo: cuando no quede ninguna, sobra
\newcommand{\duda}[1]{\textcolor{red}{\textbf{#1}}}
\usepackage[colorlinks=true,linkcolor=blue,urlcolor=blue]{hyperref}  % el indice, con enlaces azules como en el TFM
"""

SUBTITULOS = {"curso": "Apuntes de clase", "paper": "Notas de lectura", "duda": "Dudas"}


def _portada(titulo, meta, cuerpo):
    """Portada e indice. meta: lo que diga la cabecera del .md (tipo, autor, profesor, asignatura, fecha)."""
    meta = meta or {}
    lineas = ["\\begin{titlepage}", "\\centering", "\\vspace*{3cm}", "{\\Huge\\bfseries " + titulo + "\\par}"]
    if meta.get("asignatura"):
        lineas += ["\\vspace{0.8cm}", "{\\Large " + _texto(meta["asignatura"]) + "\\par}"]
    lineas += ["\\vspace{1cm}", "{\\Large " + SUBTITULOS.get(meta.get("tipo"), "Apuntes") + "\\par}"]
    if meta.get("profesor"):
        lineas += ["\\vspace{0.4cm}", "{\\large Profesor: " + _texto(meta["profesor"]) + "\\par}"]
    fechas = [m.group(0) for m in (RE_FECHA.match(c) for c in clases(cuerpo)) if m]
    if fechas:
        lineas += ["\\vspace{0.4cm}", "{\\large " + ("Clases del " + _texto(fechas[0]) + " al " + _texto(fechas[-1])
                                                    if len(fechas) > 1 else "Clase del " + _texto(fechas[0])) + "\\par}"]
    if meta.get("autor"):
        lineas += ["\\vspace{2.5cm}", "{\\Large " + _texto(meta["autor"]) + "\\par}"]
    pie = "Transcrito de los apuntes manuscritos" + (" el " + _texto(meta["fecha"]) if meta.get("fecha") else "")
    pie += ". " + ("Revisado contra el original." if meta.get("estado") == "revisado"
                   else "Sin revisar contra el original: puede tener errores de transcripcion.")
    lineas += ["\\vfill", "{\\small " + pie + "\\par}", "\\end{titlepage}", "\\tableofcontents", "\\clearpage", ""]
    return "\n".join(lineas) + "\n"


# ----------------------------------------------------------------------
# enunciados y demostraciones: en el .md van entre una linea <!-- teorema --> (o lema, proposicion,
# corolario, definicion, observacion, ejemplo, notacion, nota, demostracion) y una linea <!-- fin -->
# ----------------------------------------------------------------------

ENTORNOS = ("teorema", "lema", "proposicion", "corolario", "definicion", "observacion", "ejemplo",
            "notacion", "nota", "demostracion", "comentario")
# `clase` no es un entorno: la linea con la fecha de la clase pasa a ser el titulo de una seccion
BLOQUES = ENTORNOS + ("clase",)
RE_ABRE = re.compile(r"^<!-- (%s) -->[ \t]*$" % "|".join(BLOQUES), re.M)
RE_FECHA = re.compile(r"\d{1,2}\s*(?:de\s+)?[A-Za-zÁÉÍÓÚáéíóú]{3,10}\.?(?:\s+(?:de\s+)?\d{4})?|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?")


def clases(cuerpo):
    """Los titulos de las clases (la linea que sigue a cada <!-- clase -->), sin negritas ni dos puntos."""
    out = []
    lineas = (cuerpo or "").split("\n")
    for i, l in enumerate(lineas):
        if l.strip() == "<!-- clase -->":
            sig = next((x for x in lineas[i + 1:] if x.strip()), "")
            out.append(_titulo_clase(sig))
    return out


def _titulo_clase(linea):
    linea = re.sub(r"^[ \t]*#+[ \t]*", "", linea).replace("**", "")
    return " ".join(linea.split()).rstrip(" :.")
RE_CIERRA = re.compile(r"^<!-- fin -->[ \t]*$", re.M)
_A, _Z = "\ue00c{}\ue00d", "\ue00e\ue00f"
_RE_AZ = re.compile("\ue00c([a-z]+)\\|(\\d*)\ue00d\\n*|\\n*\ue00e\ue00f")
_PALABRA = (r"Teoremas?|Lemas?|Proposici[oó]n(?:es)?|Prop\.?|Corolarios?|Definici[oó]n(?:es)?|Def\.?|"
            r"Observaci[oó]n(?:es)?|Obs\.?|Ejemplos?|Ejs?\.?|Notaci[oó]n(?:es)?|Notas?|Demostraci[oó]n|Dem\.?|Th\.?|Tma\.?")
# la etiqueta manuscrita con la que empieza el bloque: "**Teorema (Pringsheim):**", "Dem:", "## **Teorema de Borel**"
_RE_ETIQUETA = re.compile(
    r"^[ \t]*(?:#+[ \t]*)?(?P<b>\*\*)?(?:" + _PALABRA + r")(?=[\s:.*(]|$)"
    r"(?:[ \t]+(?P<num>\d+(?:\.\d+)*))?\.?"
    r"(?:[ \t]+de[ \t]+(?P<de>[^*:\n]+?))?"
    r"(?:[ \t]*\((?P<n1>(?:[^()\n]|\([^()\n]*\))*)\))?[ \t]*[:.]?[ \t]*(?(b)\*\*)[ \t]*"
    r"(?:\((?P<n2>(?:[^()$\n]|\([^()\n]*\))*)\)[ \t]*(?=[:.]))?[:.]?[ \t]*")


def _estructura(t, nombres):
    """Las marcas de bloque del markdown, cambiadas por marcadores privados en su propio parrafo; la
    etiqueta manuscrita del principio del bloque se quita (el entorno pone la suya) y su nombre
    entre parentesis, si lo trae, se guarda en `nombres` para el argumento opcional. De una
    <!-- clase --> se guarda la linea entera: sera el titulo de la seccion."""
    lineas, out, i = t.split("\n"), [], 0
    while i < len(lineas):
        m = RE_ABRE.match(lineas[i])
        if not m:
            out.append("\n\n" + _Z + "\n\n" if RE_CIERRA.match(lineas[i]) else lineas[i])
            i += 1
            continue
        j = i + 1
        while j < len(lineas) and not lineas[j].strip():
            j += 1
        nombre = ""
        if j < len(lineas) and not RE_ABRE.match(lineas[j]) and not RE_CIERRA.match(lineas[j]):
            if m.group(1) == "clase":
                nombre, lineas[j] = _titulo_clase(lineas[j]), ""
            elif m.group(1) != "comentario":
                e = _RE_ETIQUETA.match(lineas[j])
                if e:
                    partes = [e.group("num"), e.group("de"), e.group("n1"), e.group("n2")]
                    nombre = ", ".join(p.strip() for p in partes if p and p.strip())
                    lineas[j] = lineas[j][e.end():]
        nombres.append(nombre)
        out.append("\n\n" + _A.format(m.group(1) + "|" + str(len(nombres) - 1)) + "\n\n")
        i += 1
    return "\n".join(out)


_RE_ANIDA = re.compile(r"\\(begin|end)\{(itemize|enumerate|quote|center|tabular|verbatim)\}")


def _entornos(tex, nombres):
    """Los marcadores de bloque, cambiados por \\begin{teorema}[nombre] ... \\end{teorema}. Un bloque sin
    cerrar se cierra donde empieza el siguiente o al final. Un comentario puede ir dentro de otro
    bloque (una nota al margen en mitad de una demostracion) sin cerrarlo. Una clase abre seccion.
    Si dentro de un bloque no casan las listas (la marca cayo dentro de una), ese bloque se deja
    sin entorno, con su etiqueta en negrita."""
    trozos, pos = [], 0
    for m in _RE_AZ.finditer(tex):
        trozos.append(("texto", tex[pos:m.start()]))
        trozos.append(("abre", m.group(1), m.group(2)) if m.group(1) else ("cierra",))
        pos = m.end()
    trozos.append(("texto", tex[pos:]))
    out, pila = [], []                                 # pila: [tipo, nombre, indice en out]
    titulos = {"proposicion": "Proposición", "definicion": "Definición", "observacion": "Observación",
               "notacion": "Notación", "demostracion": "Demostración"}

    def cierra():
        tipo, nombre, desde = pila.pop()
        dentro = "".join(out[desde + 1:])
        saldo = sum(1 if x.group(1) == "begin" else -1 for x in _RE_ANIDA.finditer(dentro))
        if saldo:                                      # no casa: sin entorno
            out[desde] = ("\\noindent\\textbf{" + titulos.get(tipo, tipo.capitalize())
                          + (" (" + nombre + ")" if nombre else "") + ".} ")
            return
        if tipo == "demostracion":
            out[desde] = "\\begin{demostracion}" + ("[ (" + nombre + ")]" if nombre else "") + "\n"
            out[-1] = re.sub(r"\s*(?:\$\s*)?\\(?:blacksquare|square|Box|qed)\b(?:\s*\$)?\s*$", "", out[-1])
        else:
            out[desde] = "\\begin{" + tipo + "}" + ("[{" + nombre + "}]" if nombre else "") + "\n"
        out[-1] = out[-1].rstrip("\n")
        out.append("\n\\end{" + tipo + "}\n\n")

    for tz in trozos:
        if tz[0] == "texto":
            out.append(tz[1])
        elif tz[0] == "abre":
            tipo, nombre = tz[1], (_titulo(nombres[int(tz[2])]) if tz[2] else "")
            if tipo == "clase":
                while pila:
                    cierra()
                out.append("\\section{" + (nombre or "Clase") + "}\n\n")
                continue
            if tipo == "comentario":
                if pila and pila[-1][0] == "comentario":
                    cierra()
            else:
                while pila:
                    cierra()
            pila.append([tipo, nombre, len(out)])
            out.append("")
        elif pila:
            cierra()
        else:
            out.append("\n\n")
    while pila:
        cierra()
    return "".join(out)


def cuerpo_latex(cuerpo):
    """El cuerpo de una transcripcion (sin cabecera ---) como LaTeX, sin preambulo. (latex, titulo)."""
    from markdown_it import MarkdownIt
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    md.enable(["table", "strikethrough"])

    t = RE_AVISO.sub("", cuerpo or "", count=1)
    titulo = ""
    m = re.match(r"\s*# +(.+?)[ \t]*\n", t)
    if m and not RE_PAGINA.search(t[:m.start()]):
        titulo, t = m.group(1).strip(), t[m.end():]
    t = RE_PAGINA.sub(lambda m: "\n\n" + _P.format(m.group(1)) + "\n\n", t)
    nombres = []
    t = _estructura(t, nombres)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)

    formulas, marcas = [], []

    def guarda_formula(m):
        formulas.append(m.group(0))
        return _F.format(len(formulas) - 1)

    def guarda_marca(m):
        marcas.append(m.group(0))
        return _M.format(len(marcas) - 1)

    t = RE_MARCA.sub(guarda_marca, RE_MATH.sub(guarda_formula, t))
    tex = _bloques(md.parse(t), bajo_clase=bool(clases(cuerpo)))

    # Primero las marcas y despues las formulas: una marca puede llevar formulas dentro
    # ([FIGURA: sector $S_\gamma$]) y su marcador tiene que seguir ahi cuando se repongan.
    def repone_bruto(s):                               # dentro de verbatim: tal como estaba escrito
        s = _RE_M.sub(lambda m: marcas[int(m.group(1))], s)
        return _RE_F.sub(lambda m: formulas[int(m.group(1))], s)

    partes = re.split(r"(\\begin\{verbatim\}\n.*?\\end\{verbatim\})", tex, flags=re.S)
    for i, parte in enumerate(partes):
        if i % 2:
            partes[i] = repone_bruto(parte)
            continue
        parte = _RE_M.sub(lambda m: _marca(marcas[int(m.group(1))]), parte)
        # la figura y su pie (la linea que la sigue en el mismo parrafo), centrados
        parte = re.sub("\ue00a([0-9.]+)\\|([^\ue00b]+)\ue00b(?:\n([^\n]+))?",
                       lambda m: ("\\begin{center}\n\\includegraphics[width=%s\\linewidth]{%s}" % (m.group(1), m.group(2))
                                  + ("\\\\[0.5ex]\n{\\small " + m.group(3) + "}" if m.group(3) else "")
                                  + "\n\\end{center}"), parte)
        parte = _RE_D.sub(lambda m: _formula(formulas[int(m.group(1))], display=True), parte)
        parte = _RE_L.sub(lambda m: _formula(formulas[int(m.group(1))], en_linea=True), parte)
        parte = _RE_F.sub(lambda m: _formula(formulas[int(m.group(1))]), parte)
        parte = _RE_P.sub(lambda m: "% ---------- pagina " + m.group(1) + " ----------", parte)
        # la marca de pagina va entre lineas en blanco; si la frase de antes no ha terminado y lo que
        # sigue es texto corrido, el comentario se queda dentro del parrafo
        partes[i] = re.sub(r"(?<=[^\s.:;?!\]}])\n\n(% -{10} pagina \d+ -{10})\n\n(?=[a-z$(])",
                           lambda m: "\n" + m.group(1) + "\n", parte)
    tex = _entornos("".join(partes), nombres)
    tex = re.sub(r"\n{3,}", "\n\n", tex).strip() + "\n"
    return tex, _titulo(titulo)


def _titulo(titulo):
    """El titulo del documento para \\title{}: sus formulas tal cual y el resto escapado."""
    trozos, pos = [], 0
    for m in RE_MATH.finditer(titulo):
        trozos.append(_texto(titulo[pos:m.start()]))
        trozos.append(_formula(m.group(0)))
        pos = m.end()
    trozos.append(_texto(titulo[pos:]))
    return "".join(trozos)


def _declaraciones(tex):
    """Un \\DeclareUnicodeCharacter por cada caracter que pdflatex no conoceria: asi el .tex compila
    y el hueco se ve en rojo, en vez de un error por caracter y un simbolo que desaparece."""
    raros = sorted({c for c in tex if ord(c) > 0x017F and c not in _CONOCIDOS})
    if not raros:
        return ""
    return ("% caracteres sin comando conocido: salen en rojo con su codigo; sustituyelos por su comando\n"
            + "".join("\\DeclareUnicodeCharacter{%04X}{\\duda{[U+%04X]}}\n" % (ord(c), ord(c)) for c in raros))


def _huella(resto):
    return hashlib.sha1(resto.encode("utf-8")).hexdigest()[:16]


def documento(cuerpo, nombre="", estado="sin_revisar", fecha=None, preambulo=None, meta=None):
    """El .tex completo de una transcripcion: portada, indice y cuerpo. La primera linea lleva la
    huella del resto. preambulo: el tuyo (transcripciones/preambulo.tex) en vez del de aqui; tiene
    que definir los entornos teorema, lema, ..., demostracion, comentario y el comando \\duda.
    meta: la cabecera del .md (tipo, autor, profesor, asignatura, fecha) para la portada."""
    tex, titulo = cuerpo_latex(cuerpo)
    meta = dict(meta or {}, estado=estado)
    fecha = fecha or datetime.date.today().isoformat()
    resto = (f"% Exportado de transcripciones/{nombre}.md el {fecha} (estado: {estado}).\n"
             "% La fuente es el .md: lo que corrijas aqui no vuelve al .md ni al indice.\n"
             f"% Para rehacerlo desde el .md: python doc.py transcribir --tex {nombre}\n"
             + (preambulo.rstrip("\n") + "\n" if preambulo and preambulo.strip() else PREAMBULO)
             + _declaraciones(titulo + tex)
             + (f"\\title{{{titulo}}}\n\\date{{}}\n" if titulo else "")
             + "\\begin{document}\n"
             + (_portada(titulo, meta, cuerpo) + "\n" if titulo else "\n")
             + tex
             + "\\end{document}\n")
    return f"% huella: {_huella(resto)}\n" + resto


def intacto(texto_tex):
    """True si el .tex esta tal como lo escribio `documento` (nadie lo ha editado a mano)."""
    m = re.match(r"% huella: ([0-9a-f]{16})\n", texto_tex or "")
    return bool(m) and _huella(texto_tex[m.end():]) == m.group(1)
