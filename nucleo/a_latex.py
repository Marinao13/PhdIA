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

# marcadores privados: formula, marca, pagina, formula en display
_F, _M, _P, _D = "\ue000{}\ue001", "\ue002{}\ue003", "\ue004{}\ue005", "\ue006{}\ue007"
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
    "⟺": r"\Longleftrightarrow", "⟼": r"\longmapsto", "↗": r"\nearrow", "↘": r"\searrow", "↪": r"\hookrightarrow",
    "∈": r"\in", "∉": r"\notin", "∋": r"\ni", "⊂": r"\subset", "⊆": r"\subseteq", "⊃": r"\supset", "⊇": r"\supseteq",
    "∪": r"\cup", "∩": r"\cap", "∖": r"\setminus", "∅": r"\emptyset", "∞": r"\infty",
    "∑": r"\sum", "∏": r"\prod", "∫": r"\int", "∮": r"\oint", "∂": r"\partial", "∇": r"\nabla",
    "∀": r"\forall", "∃": r"\exists", "∄": r"\nexists", "¬": r"\neg", "∧": r"\wedge", "∨": r"\vee",
    "×": r"\times", "·": r"\cdot", "⋅": r"\cdot", "±": r"\pm", "∓": r"\mp", "÷": r"\div", "∘": r"\circ",
    "⊕": r"\oplus", "⊗": r"\otimes", "√": r"\surd", "∣": r"\mid", "∥": r"\parallel", "‖": r"\|", "⊥": r"\perp",
    "⌊": r"\lfloor", "⌋": r"\rfloor", "⌈": r"\lceil", "⌉": r"\rceil", "⟨": r"\langle", "⟩": r"\rangle",
    "ℓ": r"\ell", "ℏ": r"\hbar", "ℜ": r"\Re", "ℑ": r"\Im", "ℵ": r"\aleph", "∎": r"\blacksquare", "□": r"\square",
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
# super y subindices Unicode: x² -> x^{2}
_SIMBOLOS.update({c: "^{%d}" % i for i, c in enumerate("⁰¹²³⁴⁵⁶⁷⁸⁹")})
_SIMBOLOS.update({c: "_{%d}" % i for i, c in enumerate("₀₁₂₃₄₅₆₇₈₉")})
_SIMBOLOS.update({"⁺": "^{+}", "⁻": "^{-}", "ⁿ": "^{n}", "₊": "_{+}", "₋": "_{-}"})
# lo que vale igual en texto y en formula
_COMUNES = {"′": "'", "″": "''", "−": "-", "\u00a0": "~", "\u2009": r"\,", "\u202f": r"\,", "\u200b": ""}
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
    s = _RE_SIMBOLO.sub(lambda m: "$" + _SIMBOLOS[m.group()] + "$", s)
    s = _RE_COMUN.sub(lambda m: _COMUNES[m.group()], s)
    s = _RE_TIPO.sub(lambda m: _TIPOGRAFIA[m.group()], s)
    return _comillas(s) if comillas else s.replace('"', r"\textquotedbl{}")


def _marca(m, en_formula=False):
    """[ILEGIBLE], [?] y [PAGINA CORTADA ...] en rojo; [FIGURA: ...] en un recuadro que parte linea."""
    if m.startswith("[FIGURA:"):
        if en_formula:
            return r"\fbox{" + _texto(m[1:-1]) + "}"
        return r"\fbox{\parbox{\dimexpr\linewidth-2\fboxsep-2\fboxrule\relax}{" + _texto(m[1:-1]) + "}}"
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
    # un simbolo Unicode dentro de la formula: su comando; si la formula lleva \text{...}, con
    # \ensuremath, que vale tanto dentro como fuera del \text
    if _RE_EN_TEXTO.search(cuerpo):
        cuerpo = _RE_SIMBOLO.sub(lambda m: r"\ensuremath{" + _SIMBOLOS[m.group()] + "}", cuerpo)
    else:
        cuerpo = _RE_SIMBOLO.sub(lambda m: _SIMBOLOS[m.group()] + " ", cuerpo)
    cuerpo = _RE_COMUN.sub(lambda m: _COMUNES[m.group()], cuerpo)
    cuerpo = RE_MARCA.sub(lambda m: r"\text{" + _marca(m.group(0), en_formula=True) + "}", cuerpo)
    if not display:
        return "$" + cuerpo.strip() + "$"
    cuerpo = cuerpo.strip()
    if re.match(r"\\begin\{(align|equation|gather|multline|eqnarray|flalign|alignat)\*?\}", cuerpo):
        return cuerpo                                  # ya es un entorno de display
    if ("\\\\" in cuerpo or "&" in cuerpo) and "\\begin{" not in cuerpo:
        cuerpo = "\\begin{aligned}\n" + cuerpo + "\n\\end{aligned}"
    return "\\[\n" + cuerpo + "\n\\]"


def _en_linea(hijos, display=True):
    """display=False en titulos y celdas de tabla: ahi una formula sola no puede ir en display.
    Tampoco dentro de una negrita o cursiva: dejaria una linea en blanco dentro de \\textbf{}."""
    out, n, enlace, anidado = [], len(hijos), None, 0
    for i, h in enumerate(hijos):
        t = h.type
        if t == "text":
            m = _RE_SOLO_F.fullmatch(h.content)
            sola = (display and not anidado and m and (i == 0 or hijos[i - 1].type == "softbreak")
                    and (i == n - 1 or hijos[i + 1].type == "softbreak"))
            out.append(_D.format(m.group(1)) if sola else _texto(h.content))
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
            out.append("[imagen: " + _texto(h.content or "") + "]")
        elif t in ("s_open", "s_close"):
            pass                                       # lo tachado, como texto normal
        else:
            out.append(_texto(getattr(h, "content", "") or ""))
    # un [ justo tras un salto forzado se tomaria por el argumento opcional de \\
    return re.sub(r"\\\\\n\[", lambda m: "\\\\\n{}[", "".join(out))


def _sin_opcional(texto):
    """Un texto que empieza por [ tras \\item o al empezar una fila: LaTeX lo leeria como argumento opcional."""
    return "{}" + texto if texto.lstrip().startswith("[") else texto


_TITULOS = {1: r"\section*{", 2: r"\section*{", 3: r"\subsection*{", 4: r"\subsubsection*{"}
_CONTADORES = ("enumi", "enumii", "enumiii", "enumiv")


def _bloques(tokens):
    out, fila, celdas, columnas, en_titulo, numeradas, tras_item = [], None, None, 0, False, 0, False
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
PREAMBULO = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-noshorthands,es-nodecimaldot]{babel}
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
        parte = _RE_D.sub(lambda m: "\n" + _formula(formulas[int(m.group(1))], display=True) + "\n", parte)
        parte = _RE_F.sub(lambda m: _formula(formulas[int(m.group(1))]), parte)
        partes[i] = _RE_P.sub(lambda m: "% ---------- pagina " + m.group(1) + " ----------", parte)
    tex = re.sub(r"\n{3,}", "\n\n", "".join(partes)).strip() + "\n"
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


def documento(cuerpo, nombre="", estado="sin_revisar", fecha=None):
    """El .tex completo de una transcripcion. La primera linea lleva la huella del resto."""
    tex, titulo = cuerpo_latex(cuerpo)
    fecha = fecha or datetime.date.today().isoformat()
    resto = (f"% Exportado de transcripciones/{nombre}.md el {fecha} (estado: {estado}).\n"
             "% La fuente es el .md: lo que corrijas aqui no vuelve al .md ni al indice.\n"
             f"% Para rehacerlo desde el .md: python doc.py transcribir --tex {nombre}\n"
             + PREAMBULO
             + _declaraciones(titulo + tex)
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
