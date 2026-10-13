"""
Salida legible en consola: markdown + LaTeX ligero (lo que devuelven `preguntar` y
los demas comandos) -> texto plano.

  \\( x \\) y $x$        -> $x$ con los simbolos convertidos (≤ ∞ ℝ ∫ ...)
  \\[ ... \\] y $$ ... $$ -> bloque sangrado en lineas propias
  ## Titulo            -> titulo subrayado
  **x**, *x*, `x`      -> x
  parrafos             -> envueltos a `ancho` columnas sin partir dentro de $...$
  \\frac{a}{b}          -> a/b con parentesis si hace falta; \\mathbb{R} -> ℝ

Sin dependencias (re y textwrap). Con perdida: las macros privadas de un paper (\\M, \\Mb)
quedan como letras; el registro de consultas guarda siempre la respuesta cruda. Con
`unicode=False` todo se degrada a ASCII (tuberias con cp1252, fuentes sin glifos).
"""
import re
import textwrap

# ---------------------------------------------------------------- tablas
_SIMB = {
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "ll": "≪", "gg": "≫",
    "infty": "∞", "to": "→", "rightarrow": "→", "longrightarrow": "→", "mapsto": "↦",
    "Rightarrow": "⇒", "Leftrightarrow": "⇔", "iff": "⇔", "in": "∈", "notin": "∉",
    "subset": "⊂", "subseteq": "⊆", "supset": "⊃", "cup": "∪", "cap": "∩", "setminus": "∖",
    "cdot": "·", "times": "×", "pm": "±", "mp": "∓", "circ": "∘", "partial": "∂",
    "nabla": "∇", "int": "∫", "iint": "∬", "oint": "∮", "sum": "∑", "prod": "∏",
    "forall": "∀", "exists": "∃", "emptyset": "∅", "varnothing": "∅", "ldots": "...",
    "cdots": "···", "dots": "...", "vdots": "⋮", "equiv": "≡", "sim": "∼",
    "simeq": "≃", "approx": "≈", "propto": "∝", "perp": "⊥", "mid": "|", "lvert": "|",
    "rvert": "|", "lVert": "‖", "rVert": "‖", "langle": "⟨", "rangle": "⟩",
    "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", "prime": "′",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π",
    "rho": "ρ", "varrho": "ϱ", "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ",
    "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ",
    "Psi": "Ψ", "Omega": "Ω",
    # operadores con nombre: se quedan con su nombre
    "log": "log", "ln": "ln", "exp": "exp", "inf": "inf", "sup": "sup", "lim": "lim",
    "limsup": "limsup", "liminf": "liminf", "min": "min", "max": "max", "sin": "sin",
    "cos": "cos", "tan": "tan", "arg": "arg", "deg": "deg", "det": "det", "dim": "dim",
    "ker": "ker", "Re": "Re", "Im": "Im", "sgn": "sgn",
    # espaciado y tamanos
    "quad": "\x02", "qquad": "\x02\x02", "left": "", "right": "", "big": "", "Big": "",
    "bigg": "", "Bigg": "", "bigl": "", "bigr": "", "Bigl": "", "Bigr": "",
    "displaystyle": "", "textstyle": "", "nonumber": "", "notag": "",
}
_BB = {"R": "ℝ", "C": "ℂ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "K": "K"}
_GRANDES = "∫∬∮∑∏"                      # operadores que piden aire delante
_RELACIONES = "=≤≥≠<>→↦∈∉⊂⊆⊃≡∼≃≈"
# degradacion a ASCII puro (tuberias con cp1252, fuentes sin glifos)
_ASCII = {
    "≤": "<=", "≥": ">=", "≠": "!=", "≪": "<<", "≫": ">>", "∞": "inf", "→": "->", "↦": "|->",
    "⇒": "=>", "⇔": "<=>", "∈": "in", "∉": "notin", "⊂": "sub", "⊆": "sub=",
    "⊃": "sup", "∪": " U ", "∩": " n ", "∖": " \\ ", "·": "*", "×": "x", "±": "+-",
    "∓": "-+", "∘": "o", "∂": "d", "∇": "grad", "∫": "int", "∬": "iint", "∮": "oint",
    "∑": "sum", "∏": "prod", "∀": "forall", "∃": "exists", "∅": "{}", "···": "...",
    "⋮": ":", "≡": "==", "∼": "~", "≃": "~=", "≈": "~~", "∝": "prop", "⊥": "perp",
    "‖": "||", "⟨": "<", "⟩": ">", "⌊": "floor(", "⌋": ")", "⌈": "ceil(", "⌉": ")",
    "′": "'", "√": "sqrt", "ℝ": "R", "ℂ": "C", "ℕ": "N", "ℤ": "Z", "ℚ": "Q",
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "eps", "ζ": "zeta",
    "η": "eta", "θ": "theta", "ϑ": "theta", "ι": "iota", "κ": "kappa", "λ": "lambda",
    "μ": "mu", "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho", "ϱ": "rho", "σ": "sigma",
    "τ": "tau", "υ": "upsilon", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Γ": "Gamma", "Δ": "Delta", "Θ": "Theta", "Λ": "Lambda", "Ξ": "Xi", "Π": "Pi",
    "Σ": "Sigma", "Φ": "Phi", "Ψ": "Psi", "Ω": "Omega",
}


# ---------------------------------------------------------------- grupos
def _grupo(s, i):
    """Argumento de un comando a partir de s[i]: {...} equilibrado, \\cmd o un caracter.
    Devuelve (contenido, indice tras el argumento)."""
    while i < len(s) and s[i] == " ":
        i += 1
    if i >= len(s):
        return "", i
    if s[i] == "{":
        prof, j = 0, i
        while j < len(s):
            if s[j] == "{":
                prof += 1
            elif s[j] == "}":
                prof -= 1
                if prof == 0:
                    return s[i + 1:j], j + 1
            j += 1
        return s[i + 1:], len(s)          # llave sin cerrar: hasta el final
    if s[i] == "\\":
        m = re.match(r"\\([A-Za-z]+|.)", s[i:])
        return m.group(0), i + len(m.group(0))
    return s[i], i + 1


def _atomo(s):
    return bool(re.fullmatch(r"[\w^'.]+|\|[^|]+\||\([^()]*\)", s))


def _operador_nivel0(s):
    """Hay + - = < > , o espacio fuera de parentesis/corchetes."""
    prof = 0
    for c in s:
        if c in "([":
            prof += 1
        elif c in ")]":
            prof -= 1
        elif prof == 0 and c in "+-=<>≤≥ ,":
            return True
    return False


def _paren(s, denominador=False):
    if denominador:
        return s if re.fullmatch(r"\w+|\w\^\w|\w'*", s) else f"({s})"
    return f"({s})" if (not _atomo(s) and _operador_nivel0(s)) else s


def _fracciones(s):
    out, i = [], 0
    while True:
        m = re.search(r"\\[dt]?frac(?![A-Za-z])", s[i:])
        if not m:
            out.append(s[i:])
            break
        out.append(s[i:i + m.start()])
        num, j = _grupo(s, i + m.end())
        den, j = _grupo(s, j)
        out.append(_paren(_mat(num)) + "/" + _paren(_mat(den), denominador=True))
        i = j
    return "".join(out)


def _con_arg(s, nombre, fmt, crudo=False):
    """\\nombre{x} -> fmt(x). Recursivo en el argumento salvo crudo (texto literal)."""
    out, i = [], 0
    while True:
        m = re.search(r"\\" + nombre + r"(?![A-Za-z])", s[i:])
        if not m:
            out.append(s[i:])
            return "".join(out)
        out.append(s[i:i + m.start()])
        arg, j = _grupo(s, i + m.end())
        out.append(fmt(arg if crudo else _mat(arg)))
        i = j


def _simbolo(m):
    """Sustituye \\cmd; mete un espacio si el resultado es una palabra u operador grande
    pegado a algo alfanumerico (2^m\\log -> 2^m log, \\pi\\int -> π ∫)."""
    nombre, s = m.group(1), m.string
    r = _SIMB.get(nombre, nombre)
    prev = s[m.start() - 1] if m.start() else ""
    if r and (r[0].isalpha() or r[0] in _GRANDES) and (prev.isalnum() or prev in ")]|"):
        r = " " + r
    return r


def _mat(s):
    """Interior de una formula -> texto."""
    s = _fracciones(s)
    s = _con_arg(s, "mathbb", lambda x: _BB.get(x.strip(), x))
    s = _con_arg(s, "sqrt", lambda x: f"√({x})" if not _atomo(x) else f"√{x}")
    for nombre in ("text", "textrm", "mathrm", "operatorname"):
        s = _con_arg(s, nombre, lambda x: x, crudo=True)       # texto literal, espacios incluidos
    for nombre in ("mathit", "mathbf", "mathcal", "mathsf", "boxed", "underbrace", "overbrace"):
        s = _con_arg(s, nombre, lambda x: x)
    for nombre, fmt in (("hat", "hat({})"), ("bar", "bar({})"), ("overline", "bar({})"),
                        ("tilde", "tilde({})"), ("vec", "vec({})"), ("dot", "dot({})")):
        s = _con_arg(s, nombre, lambda x, f=fmt: f.format(x))
    s = re.sub(r"\\begin\{[a-z*]+\}|\\end\{[a-z*]+\}", "", s)
    s = s.replace("\\\\", "\x03\n").replace("&", " ").replace("\\|", "‖")   # \x03 = fila nueva
    s = re.sub(r"\\[,;:!]|\\ ", " ", s)
    s = re.sub(r"\\([A-Za-z]+)", _simbolo, s)
    s = re.sub(r"\\([{}%$#&_])", r"\1", s)
    s = re.sub(r"([_^])\{(\w)\}", r"\1\2", s)              # x^{2} -> x^2, a_{j} -> a_j
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(rf" ?([{_RELACIONES}]) ?", r" \1 ", s)      # aire alrededor de relaciones
    s = s.replace("\x02", "  ")
    return "\n".join(l.strip() for l in s.strip().splitlines())


# ---------------------------------------------------------------- texto
_MD_INLINE = [(r"\*\*(.+?)\*\*", r"\1"), (r"__(.+?)__", r"\1"), (r"(?<!\w)\*(?!\s)(.+?)\*", r"\1"),
              (r"(?<!\w)_(?!\s)([^_$]+?)_(?!\w)", r"\1"), (r"`([^`]+)`", r"\1")]


def _inline(texto):
    """\\( \\) y $ $ -> $...$ convertido; quita negritas/cursivas/codigo."""
    def _f(m):
        return "$" + _mat(m.group(1)).replace("\x03", "").replace("\n", " ") + "$"
    texto = re.sub(r"\\\((.+?)\\\)", _f, texto, flags=re.S)
    texto = re.sub(r"(?<!\$)\$(?!\$)([^$\n]+?)\$", _f, texto)
    for pat, rep in _MD_INLINE:
        texto = re.sub(pat, rep, texto)
    return texto


def _envolver(parrafo, ancho, sangria=""):
    """Envuelve sin partir dentro de $...$: los espacios de las formulas se protegen."""
    protegido = re.sub(r"\$[^$]*\$", lambda m: m.group(0).replace(" ", "\x00"), parrafo)
    lineas = textwrap.wrap(protegido, width=ancho, initial_indent=sangria,
                           subsequent_indent=sangria, break_long_words=False,
                           break_on_hyphens=False)
    return "\n".join(l.replace("\x00", " ") for l in lineas)


def latex_a_consola(texto, ancho=90, unicode=True):
    """
    Markdown + LaTeX ligero (lo que devuelve `preguntar`) -> texto plano legible.
    Bloques \\[ \\] y $$ $$ -> sangrados 4 espacios (en una linea si caben); \\( \\) -> $...$;
    ## -> titulo subrayado; ** * ` fuera; parrafos envueltos a `ancho` sin partir $...$.
    """
    texto = texto.replace("\r\n", "\n")
    # una respuesta cortada a mitad de formula deja \( o \[ sin cerrar: se cierra al final
    if texto.count("\\[") > texto.count("\\]"):
        texto += "\\]"
    if texto.count("\\(") > texto.count("\\)"):
        texto += "\\)"
    if texto.count("$") % 2:
        texto += "$"
    bloques = []

    def _guardar(m):
        """Bloque: cada fila (\\\\) en su linea; los saltos blandos se juntan si caben."""
        filas = []
        for fila in _mat((m.group(1) or m.group(2)).strip()).split("\x03"):
            lineas = [l.strip() for l in fila.splitlines() if l.strip()]
            junto = " ".join(lineas)
            filas.append(junto if len(junto) <= ancho - 4 else "\n".join(lineas))
        bloques.append("\n".join(f for f in filas if f))
        return f"\n\x01{len(bloques) - 1}\x01\n"

    texto = re.sub(r"\\\[(.+?)\\\]|\$\$(.+?)\$\$", _guardar, texto, flags=re.S)
    texto = _inline(texto)
    salida = []
    for parrafo in re.split(r"\n\s*\n", texto.strip()):
        parrafo = parrafo.strip()
        if not parrafo:
            continue
        m = re.fullmatch(r"\x01(\d+)\x01", parrafo)
        if m:                                              # formula en bloque
            salida.append(textwrap.indent(bloques[int(m.group(1))], "    "))
            continue
        m = re.match(r"(#{1,6})\s*(.+)", parrafo)
        if m:                                              # cabecera -> subrayado
            titulo = m.group(2).strip()
            salida.append(titulo + "\n" + ("=" if len(m.group(1)) == 1 else "-") * min(len(titulo), ancho))
            continue
        if re.match(r"\s*([-*+]|\d+[.)])\s", parrafo):   # lista: sangria colgante por item
            items = re.split(r"\n(?=\s*(?:[-*+]|\d+[.)])\s)", parrafo)
            salida.append("\n".join(_envolver(" ".join(i.split()), ancho, "  ")[2:] for i in items))
            continue
        # parrafo normal: puede llevar bloques pegados sin linea en blanco
        trozos = re.split(r"\n?\x01(\d+)\x01\n?", parrafo)
        partes = []
        for k, trozo in enumerate(trozos):
            if k % 2:
                partes.append(textwrap.indent(bloques[int(trozo)], "    "))
            elif trozo.strip():
                partes.append(_envolver(" ".join(trozo.split()), ancho))
        salida.append("\n".join(partes))
    res = "\n\n".join(salida)
    if not unicode:
        for u, a in _ASCII.items():
            res = res.replace(u, a)
    return res
