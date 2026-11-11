"""
De una transcripcion (markdown con las formulas entre $...$) a un .tex para pdflatex.

    python doc.py transcribir --tex NOMBRE        escribe transcripciones/NOMBRE.tex desde el .md de ahora

La fuente sigue siendo el .md: es lo que se revisa, lo que se indexa y lo que se cita. El .tex
es una exportacion para llevarla a un documento; lo que se corrija en el no vuelve al .md.

Que hace: titulos a \\section* / \\subsection*, negritas, cursivas, listas, citas, tablas
sencillas y codigo; las formulas pasan tal cual (una formula sola en su linea, a \\[ ... \\]);
los caracteres especiales del texto se escapan; los simbolos Unicode sueltos (<=, flechas,
letras griegas) se pasan a su comando; las marcas [ILEGIBLE] y [?] salen en rojo con \\duda{}
para que no se pierdan de vista; cada pagina del original queda senalada con un comentario.

La primera linea del .tex lleva una huella del resto: si lo editas a mano, la huella deja de
casar y una nueva exportacion no lo pisa sin que se lo pidas.
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

# marcadores privados: formula, marca, pagina, formula en display
_F, _M, _P, _D = "\ue000{}\ue001", "\ue002{}\ue003", "\ue004{}\ue005", "\ue006{}\ue007"
_RE_F = re.compile("\ue000(\\d+)\ue001")
_RE_M = re.compile("\ue002(\\d+)\ue003")
_RE_P = re.compile("\ue004(\\d+)\ue005")
_RE_D = re.compile("\ue006(\\d+)\ue007")
_RE_SOLO_F = re.compile("\\s*\ue000(\\d+)\ue001\\s*")

_ESPECIALES = {"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "&": r"\&", "%": r"\%", "#": r"\#",
               "_": r"\_", "^": r"\textasciicircum{}", "~": r"\textasciitilde{}", "$": r"\$"}

# simbolos Unicode que pdflatex con inputenc no trae: su comando (en texto, entre $ $)
_SIMBOLOS = {
    "≤": r"\le", "≥": r"\ge", "≠": r"\ne", "≈": r"\approx", "∼": r"\sim", "≡": r"\equiv",
    "→": r"\to", "←": r"\leftarrow", "↦": r"\mapsto", "⇒": r"\Rightarrow", "⇐": r"\Leftarrow", "⇔": r"\Leftrightarrow",
    "∈": r"\in", "∉": r"\notin", "⊂": r"\subset", "⊆": r"\subseteq", "⊃": r"\supset", "∪": r"\cup", "∩": r"\cap",
    "∅": r"\emptyset", "∞": r"\infty", "∑": r"\sum", "∏": r"\prod", "∫": r"\int", "∂": r"\partial", "∇": r"\nabla",
    "∀": r"\forall", "∃": r"\exists", "¬": r"\neg", "∧": r"\wedge", "∨": r"\vee",
    "×": r"\times", "·": r"\cdot", "±": r"\pm", "∘": r"\circ", "√": r"\surd", "∣": r"\mid", "‖": r"\|",
    "ℕ": r"\mathbb{N}", "ℤ": r"\mathbb{Z}", "ℚ": r"\mathbb{Q}", "ℝ": r"\mathbb{R}", "ℂ": r"\mathbb{C}",
    "²": r"^{2}", "³": r"^{3}",
}
_GRIEGAS = dict(zip("αβγδεζηθικλμνξπρστυφχψω",
                    ["alpha", "beta", "gamma", "delta", "varepsilon", "zeta", "eta", "theta", "iota", "kappa",
                     "lambda", "mu", "nu", "xi", "pi", "rho", "sigma", "tau", "upsilon", "varphi", "chi", "psi",
                     "omega"]))
_GRIEGAS.update(dict(zip("ΓΔΘΛΞΠΣΦΨΩ", ["Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi",
                                         "Omega"])))
_SIMBOLOS.update({k: "\\" + v for k, v in _GRIEGAS.items()})
_TIPOGRAFIA = {"…": r"\dots{}", "–": "--", "—": "---", "“": "``", "”": "''", "‘": "`", "’": "'", "\u00a0": "~"}
_RE_ESPECIAL = re.compile(r"[\\{}&%#_^~$]")
_RE_SIMBOLO = re.compile("[" + re.escape("".join(_SIMBOLOS)) + "]")
_RE_TIPO = re.compile("[" + re.escape("".join(_TIPOGRAFIA)) + "]")


def _texto(s):
    """Texto corriente: especiales escapados, simbolos Unicode a su comando entre $ $."""
    s = _RE_ESPECIAL.sub(lambda m: _ESPECIALES[m.group()], s)
    s = _RE_SIMBOLO.sub(lambda m: "$" + _SIMBOLOS[m.group()] + "$", s)
    return _RE_TIPO.sub(lambda m: _TIPOGRAFIA[m.group()], s)


def _marca(m):
    """[ILEGIBLE], [?] y [PAGINA CORTADA ...] en rojo; [FIGURA: ...] en un recuadro."""
    if m.startswith("[FIGURA:"):
        return r"\fbox{" + _texto(m[1:-1]) + "}"
    return r"\duda{" + _texto(m) + "}"


def _formula(f, display=False):
    """Una formula tal como esta escrita, con sus delimitadores puestos para LaTeX."""
    if f.startswith("$$"):
        cuerpo, display = f[2:-2], True
    elif f.startswith("\\["):
        cuerpo, display = f[2:-2], True
    elif f.startswith("\\("):
        cuerpo = f[2:-2]
    else:
        cuerpo = f[1:-1]
    cuerpo = _RE_SIMBOLO.sub(lambda m: _SIMBOLOS[m.group()] + " ", cuerpo)
    cuerpo = RE_MARCA.sub(lambda m: r"\text{" + _marca(m.group(0)) + "}", cuerpo)
    if not display:
        return "$" + cuerpo.strip() + "$"
    cuerpo = cuerpo.strip()
    if re.match(r"\\begin\{(align|equation|gather|multline|eqnarray|flalign|alignat)\*?\}", cuerpo):
        return cuerpo                                  # ya es un entorno de display
    if ("\\\\" in cuerpo or "&" in cuerpo) and "\\begin{" not in cuerpo:
        cuerpo = "\\begin{aligned}\n" + cuerpo + "\n\\end{aligned}"
    return "\\[\n" + cuerpo + "\n\\]"


def _en_linea(hijos, display=True):
    """display=False en titulos y celdas de tabla: ahi una formula sola no puede ir en display."""
    out, n, enlace = [], len(hijos), None
    for i, h in enumerate(hijos):
        t = h.type
        if t == "text":
            m = _RE_SOLO_F.fullmatch(h.content)
            sola = (display and m and (i == 0 or hijos[i - 1].type == "softbreak")
                    and (i == n - 1 or hijos[i + 1].type == "softbreak"))
            out.append(_D.format(m.group(1)) if sola else _texto(h.content))
        elif t == "softbreak":
            out.append("\n")
        elif t == "hardbreak":
            out.append("\\\\\n")
        elif t == "strong_open":
            out.append(r"\textbf{")
        elif t == "em_open":
            out.append(r"\emph{")
        elif t in ("strong_close", "em_close"):
            out.append("}")
        elif t == "code_inline":
            out.append(r"\texttt{" + _texto(h.content) + "}")
        elif t == "link_open":
            enlace = h.attrGet("href")
        elif t == "link_close":
            if enlace:
                out.append(r" (\texttt{" + _texto(enlace) + "})")
            enlace = None
        elif t == "image":
            out.append("[imagen: " + _texto(h.content or "") + "]")
        elif t in ("s_open", "s_close"):
            pass                                       # lo tachado, como texto normal
        else:
            out.append(_texto(getattr(h, "content", "") or ""))
    return "".join(out)


_TITULOS = {1: r"\section*{", 2: r"\section*{", 3: r"\subsection*{", 4: r"\subsubsection*{"}


def _bloques(tokens):
    out, fila, celdas, columnas, en_titulo = [], None, None, 0, False
    for i, tok in enumerate(tokens):
        t = tok.type
        if t == "heading_open":
            en_titulo = True
            out.append(_TITULOS.get(int(tok.tag[1]), r"\paragraph{"))
        elif t == "heading_close":
            en_titulo = False
            out.append("}\n\n")
        elif t == "inline":
            texto = _en_linea(tok.children or [], display=not en_titulo and celdas is None)
            if celdas is not None:
                celdas.append(texto.replace("\n", " "))
            else:
                out.append(texto)
        elif t == "paragraph_close":
            out.append("\n" if tok.hidden else "\n\n")
        elif t == "bullet_list_open":
            out.append("\\begin{itemize}\n")
        elif t == "bullet_list_close":
            out.append("\\end{itemize}\n\n")
        elif t == "ordered_list_open":
            out.append("\\begin{enumerate}\n")
        elif t == "ordered_list_close":
            out.append("\\end{enumerate}\n\n")
        elif t == "list_item_open":
            out.append("\\item ")
        elif t == "blockquote_open":
            out.append("\\begin{quote}\n")
        elif t == "blockquote_close":
            out.append("\\end{quote}\n\n")
        elif t in ("fence", "code_block"):
            out.append("\\begin{verbatim}\n" + tok.content.replace("\\end{verbatim}", "\\end {verbatim}")
                       + ("" if tok.content.endswith("\n") else "\n") + "\\end{verbatim}\n\n")
        elif t == "hr":
            out.append("\\medskip\\hrule\\medskip\n\n")
        elif t == "table_open":
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
            out.append(" & ".join(fila) + " \\\\\n")
            fila = None
        elif t == "thead_close":
            out.append("\\hline\n")
        elif t == "table_close":
            out.append("\\hline\n\\end{tabular}\n\\end{center}\n\n")
    return "".join(out)


PREAMBULO = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage{amsmath,amssymb,amsthm}
\usepackage{xcolor}
% las marcas de la transcripcion ([ILEGIBLE], [?]) salen en rojo: cuando no quede ninguna, sobra
\newcommand{\duda}[1]{\textcolor{red}{\textbf{#1}}}
"""


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
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)

    formulas, marcas = [], []

    def guarda_formula(m):
        formulas.append(m.group(0))
        return _F.format(len(formulas) - 1)

    def guarda_marca(m):
        marcas.append(m.group(0))
        return _M.format(len(marcas) - 1)

    t = RE_MARCA.sub(guarda_marca, RE_MATH.sub(guarda_formula, t))
    tex = _bloques(md.parse(t))

    def repone_bruto(s):                               # dentro de verbatim: tal como estaba escrito
        s = _RE_F.sub(lambda m: formulas[int(m.group(1))], s)
        return _RE_M.sub(lambda m: marcas[int(m.group(1))], s)

    partes = re.split(r"(\\begin\{verbatim\}\n.*?\\end\{verbatim\})", tex, flags=re.S)
    for i, parte in enumerate(partes):
        if i % 2:
            partes[i] = repone_bruto(parte)
            continue
        parte = _RE_D.sub(lambda m: "\n" + _formula(formulas[int(m.group(1))], display=True) + "\n", parte)
        parte = _RE_F.sub(lambda m: _formula(formulas[int(m.group(1))]), parte)
        parte = _RE_M.sub(lambda m: _marca(marcas[int(m.group(1))]), parte)
        partes[i] = _RE_P.sub(lambda m: "% ---------- pagina " + m.group(1) + " ----------", parte)
    tex = re.sub(r"\n{3,}", "\n\n", "".join(partes)).strip() + "\n"
    return tex, _texto(titulo)


def _huella(resto):
    return hashlib.sha1(resto.encode("utf-8")).hexdigest()[:16]


def documento(cuerpo, nombre="", estado="sin_revisar", fecha=None):
    """El .tex completo de una transcripcion. La primera linea lleva la huella del resto."""
    tex, titulo = cuerpo_latex(cuerpo)
    fecha = fecha or datetime.date.today().isoformat()
    resto = (f"% Exportado de transcripciones/{nombre}.md el {fecha} (estado: {estado}).\n"
             "% La fuente es el .md: lo que corrijas aqui no vuelve al .md ni al indice.\n"
             f"% Para rehacerlo desde el .md: python doc.py transcribir --tex {nombre}\n"
             + PREAMBULO
             + (f"\\title{{{titulo}}}\n\\date{{}}\n" if titulo else "")
             + "\\begin{document}\n"
             + ("\\maketitle\n\n" if titulo else "\n")
             + tex
             + "\\end{document}\n")
    return f"% huella: {_huella(resto)}\n" + resto


def intacto(texto_tex):
    """True si el .tex esta tal como lo escribio `documento` (nadie lo ha editado a mano)."""
    m = re.match(r"% huella: ([0-9a-f]{16})\n", texto_tex or "")
    return bool(m) and _huella(texto_tex[m.end():]) == m.group(1)
