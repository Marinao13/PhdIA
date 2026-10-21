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
Nunca lanza: ante una entrada rara (barra suelta, llave sin cerrar) degrada, no rompe.
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
    "ker": "ker", "Re": "Re", "Im": "Im", "sgn": "sgn", "bmod": "mod", "pmod": "mod", "mod": "mod",
    "gcd": "gcd", "deg": "deg", "ord": "ord", "supp": "supp", "dist": "dist", "diam": "diam",
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
    """Argumento de un comando a partir de s[i]: {...} equilibrado, [...] opcional, \\cmd o
    un caracter. Devuelve (contenido, indice tras el argumento). Nunca lanza."""
    while i < len(s) and s[i] == " ":
        i += 1
    if i >= len(s):
        return "", i
    if s[i] in "{[":
        abre, cierra = s[i], "}" if s[i] == "{" else "]"
        prof, j = 0, i
        while j < len(s):
            if s[j] == abre:
                prof += 1
            elif s[j] == cierra:
                prof -= 1
                if prof == 0:
                    return s[i + 1:j], j + 1
            j += 1
        return s[i + 1:], len(s)          # sin cerrar: hasta el final
    if s[i] == "\\":
        m = re.match(r"\\([A-Za-z]+|.)", s[i:], re.S)
        if m is None:                     # barra suelta al final (respuesta cortada)
            return "", i + 1
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
        # \x05 separa lo sustituido del comando anterior: \in\frac{a}{b} no debe leerse \ina/b
        out.append("\x05" + _paren(_mat(num)) + "/" + _paren(_mat(den), denominador=True))
        i = j
    return "".join(out)


def _raices(s):
    """\\sqrt{x} -> √x o √(x); \\sqrt[n]{x} -> n√(x)."""
    out, i = [], 0
    while True:
        m = re.search(r"\\sqrt(?![A-Za-z])", s[i:])
        if not m:
            out.append(s[i:])
            return "".join(out)
        out.append(s[i:i + m.start()])
        j = i + m.end()
        indice = ""
        k = j
        while k < len(s) and s[k] == " ":
            k += 1
        if k < len(s) and s[k] == "[":
            indice, j = _grupo(s, k)
            indice = _mat(indice)
        arg, j = _grupo(s, j)
        arg = _mat(arg)
        cuerpo = f"√{arg}" if _atomo(arg) and not indice else f"√({arg})"
        out.append("\x05" + ((indice + cuerpo) if indice else cuerpo))
        i = j


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
        out.append("\x05" + fmt(arg if crudo else _mat(arg)))     # \in\mathcal{E} -> ∈ E, no \inE
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
    s = _raices(s)
    for nombre in ("text", "textrm", "mathrm", "operatorname"):
        s = _con_arg(s, nombre, lambda x: x, crudo=True)       # texto literal, espacios incluidos
    for nombre in ("mathit", "mathbf", "mathcal", "mathsf", "mathfrak", "mathscr", "mathtt", "textbf",
                   "textit", "emph", "boxed", "underbrace", "overbrace"):
        s = _con_arg(s, nombre, lambda x: x)
    for nombre, fmt in (("hat", "hat({})"), ("bar", "bar({})"), ("overline", "bar({})"),
                        ("tilde", "tilde({})"), ("vec", "vec({})"), ("dot", "dot({})")):
        s = _con_arg(s, nombre, lambda x, f=fmt: f.format(x))
    s = re.sub(r"\\begin\{[a-z*]+\}|\\end\{[a-z*]+\}", "", s)
    s = s.replace("\\\\", "\x03\n").replace("&", " ").replace("\\|", "‖")   # \x03 = fila nueva
    s = re.sub(r"\\[,;:!]|\\ ", " ", s)
    s = re.sub(r"\\([A-Za-z]+)", _simbolo, s)
    s = re.sub(r"(?<=\w)\x05(?=\w)", " ", s).replace("\x05", "")   # a\bmod\mathfrak m -> a mod m
    s = re.sub(r"\\([{}%$#&_])", r"\1", s)
    s = re.sub(r"([_^])\{(\w)\}", r"\1\2", s)              # x^{2} -> x^2, a_{j} -> a_j
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(rf" ?([{_RELACIONES}]) ?", r" \1 ", s)      # aire alrededor de relaciones
    s = s.replace("\x02", "  ")
    return "\n".join(l.strip() for l in s.strip().splitlines())


# ---------------------------------------------------------------- texto
_MD_INLINE = [(r"\*\*(.+?)\*\*", r"\1"), (r"__(.+?)__", r"\1"), (r"(?<![\w^])\*(?!\s)([^*$\n]+?)\*(?!\w)", r"\1"),
              (r"(?<!\w)_(?!\s)([^_$\n]+?)_(?!\w)", r"\1"), (r"`([^`]+)`", r"\1")]


def _inline(texto):
    """\\( \\) y $ $ -> $...$ convertido; quita negritas/cursivas/codigo fuera de las formulas."""
    def _f(m):
        return "$" + _mat(m.group(1)).replace("\x03", "").replace("\n", " ") + "$"
    texto = re.sub(r"\\\((.+?)\\\)", _f, texto, flags=re.S)
    texto = re.sub(r"(?<!\$)\$(?!\$)([^$\n]+?)\$", _f, texto)
    # las formulas ya convertidas no pasan por las reglas de markdown (T^* no es cursiva)
    formulas = []

    def _guardar(m):
        formulas.append(m.group(0))
        return f"\x04{len(formulas) - 1}\x04"
    texto = re.sub(r"\$[^$\n]*\$", _guardar, texto)
    for pat, rep in _MD_INLINE:
        texto = re.sub(pat, rep, texto)
    return re.sub(r"\x04(\d+)\x04", lambda m: formulas[int(m.group(1))], texto)


def _envolver(parrafo, ancho, sangria="", primera=None):
    """Envuelve sin partir dentro de $...$: los espacios de las formulas se protegen."""
    protegido = re.sub(r"\$[^$]*\$", lambda m: m.group(0).replace(" ", "\x00"), parrafo)
    lineas = textwrap.wrap(protegido, width=ancho, initial_indent=sangria if primera is None else primera,
                           subsequent_indent=sangria, break_long_words=False,
                           break_on_hyphens=False)
    return "\n".join(l.replace("\x00", " ") for l in lineas)


def _con_bloques(trozo, bloques, ancho, sangria=""):
    """Parrafo con marcadores \\x01N\\x01 dentro: texto envuelto y bloques sangrados."""
    partes = []
    for k, t in enumerate(re.split(r"\n?\x01(\d+)\x01\n?", trozo)):
        if k % 2:
            partes.append(textwrap.indent(bloques[int(t)], sangria + "    "))
        elif t.strip():
            partes.append(_envolver(" ".join(t.split()), ancho, sangria))
    return "\n".join(partes)


def _lista(parrafo, bloques, ancho):
    """Lista con sangria colgante por item; conserva la anidacion por la sangria original."""
    items = re.split(r"\n(?=\s*(?:[-*+]|\d+[.)])\s)", parrafo)
    salida = []
    for it in items:
        nivel = len(it) - len(it.lstrip(" "))
        cuerpo = it.strip()
        m = re.match(r"([-*+]|\d+[.)])\s+", cuerpo)
        marca = m.group(0) if m else ""
        resto = cuerpo[len(marca):]
        sangria = " " * nivel
        colgante = sangria + " " * len(marca)
        if "\x01" in resto:                 # item con una formula en bloque dentro
            salida.append(sangria + marca + _con_bloques(resto, bloques, ancho, colgante).lstrip())
        else:
            salida.append(_envolver(" ".join(resto.split()), ancho, colgante, primera=sangria + marca))
    return "\n".join(salida)


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
    pendientes = [p for p in re.split(r"\n\s*\n", texto.strip())]
    while pendientes:
        parrafo = pendientes.pop(0).strip()
        if not parrafo:
            continue
        m = re.fullmatch(r"\x01(\d+)\x01", parrafo)
        if m:                                              # formula en bloque
            salida.append(textwrap.indent(bloques[int(m.group(1))], "    "))
            continue
        cab, _, resto = parrafo.partition("\n")
        m = re.match(r"(#{1,6})\s*(.+)", cab)
        if m:                                              # cabecera -> subrayado; el resto sigue aparte
            titulo = m.group(2).strip()
            salida.append(titulo + "\n" + ("=" if len(m.group(1)) == 1 else "-") * min(len(titulo), ancho))
            if resto.strip():
                pendientes.insert(0, resto)
            continue
        lineas = parrafo.splitlines()
        if all(l.strip().startswith("|") for l in lineas):   # tabla markdown: tal cual
            salida.append("\n".join(l.strip() for l in lineas))
            continue
        if re.match(r"\s*([-*+]|\d+[.)])\s", parrafo):   # lista
            salida.append(_lista(parrafo, bloques, ancho))
            continue
        salida.append(_con_bloques(parrafo, bloques, ancho))
    res = "\n\n".join(salida)
    if not unicode:
        for u, a in _ASCII.items():
            res = res.replace(u, a)
    return res
