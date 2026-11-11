"""
Markdown a HTML (markdown-it-py) con las formulas intactas para KaTeX, y utilidades de texto.

Las formulas ($...$, $$...$$, \\(...\\), \\[...\\]) se sacan antes de pasar por markdown-it,
que de otro modo convierte `_` y `*` en cursivas y `\\(` en `(`, y se reponen escapadas en el
HTML. KaTeX (auto-render, en static/app.js) las pinta en el navegador.
"""
import re, html, unicodedata

from markdown_it import MarkdownIt
from markdown_it.token import Token

_md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
_md.enable(["table", "strikethrough"])

# $$...$$ | \[...\] | \(...\) | $...$ (sin espacio tras el $ de apertura ni antes del de cierre;
# puede cruzar un salto de linea, no un parrafo). Un \$ no abre formula.
RE_MATH = re.compile(
    r"\$\$[\s\S]+?\$\$"
    r"|\\\[[\s\S]+?\\\]"
    r"|\\\([\s\S]+?\\\)"
    r"|(?<![\\$])\$(?![\s$])(?:\\.|[^$\\\n]|\n(?![ \t]*\n))+?(?<![\s\\])\$")

_MARCA = "\ue000{}\ue001"
_RE_MARCA = re.compile("\ue000(\\d+)\ue001")


def _proteger(texto):
    formulas = []

    def sub(m):
        formulas.append(m.group(0))
        return _MARCA.format(len(formulas) - 1)
    return RE_MATH.sub(sub, texto), formulas


def _reponer(html_, formulas, escapar=True):
    # con comillas escapadas: una formula puede caer en un atributo (el alt de una imagen), y en
    # un nodo de texto el navegador las devuelve tal cual a KaTeX
    return _RE_MARCA.sub(lambda m: (html.escape(formulas[int(m.group(1))], quote=True) if escapar
                                    else formulas[int(m.group(1))]), html_)


RE_COMENTARIO = re.compile(r"<!--.*?-->", re.S)


def markdown(texto):
    """HTML de un markdown con formulas. Los comentarios HTML (los de las plantillas) no se ven."""
    t, formulas = _proteger(RE_COMENTARIO.sub("", texto or ""))
    return _reponer(_md.render(t), formulas)


RE_DUDA = re.compile(r"\[ILEGIBLE\]|\[\?\]|\[PAGINA CORTADA[^\]]*\]")


_MARCA_DUDA = "\ue002{}\ue003"
_RE_TROZO = re.compile("\ue000(\\d+)\ue001|\ue002(\\d+)\ue003")
_RE_MARCA_DUDA = re.compile("\ue002(\\d+)\ue003")


def _token(tipo, contenido):
    t = Token(tipo, "", 0)
    t.content = contenido
    return t


def transcripcion(texto):
    """Una pagina transcrita: markdown con las marcas [ILEGIBLE] y [?] resaltadas. Dentro de una
    formula no se parte el texto (KaTeX dejaria de pintarla): se enmarca la formula entera.

    Las marcas se sacan ANTES de pasar por markdown (como las formulas) y se resaltan en los
    nodos de texto del arbol, no sobre el HTML: asi `f[?](x)` no se vuelve un enlace, una linea
    `[ILEGIBLE]: ...` no se toma por una definicion de enlace, y una marca o una formula que
    caigan en un atributo (el alt de una imagen) quedan como texto escapado, sin etiquetas."""
    t, formulas = _proteger(RE_COMENTARIO.sub("", texto or ""))
    marcas = []

    def guardar(m):
        marcas.append(m.group(0))
        return _MARCA_DUDA.format(len(marcas) - 1)
    tokens = _md.parse(RE_DUDA.sub(guardar, t))
    for tok in tokens:
        if tok.type != "inline" or not tok.children:
            continue
        hijos = []
        for h in tok.children:
            if h.type != "text" or not _RE_TROZO.search(h.content):
                hijos.append(h)
                continue
            pos = 0
            for m in _RE_TROZO.finditer(h.content):
                if m.start() > pos:
                    hijos.append(_token("text", h.content[pos:m.start()]))
                if m.group(1) is None:                 # una marca suelta
                    hijos.append(_token("html_inline", '<mark class="duda">'
                                        + html.escape(marcas[int(m.group(2))]) + "</mark>"))
                elif RE_DUDA.search(formulas[int(m.group(1))]):      # una formula con marca dentro
                    hijos.append(_token("html_inline", '<span class="formula-duda" title="formula con una '
                                        'marca dentro">' + html.escape(formulas[int(m.group(1))]) + "</span>"))
                else:
                    hijos.append(_token("text", m.group(0)))         # formula normal: la repone _reponer
                pos = m.end()
            if pos < len(h.content):
                hijos.append(_token("text", h.content[pos:]))
        tok.children = hijos
    h = _md.renderer.render(tokens, _md.options, {})
    h = _RE_MARCA_DUDA.sub(lambda m: html.escape(marcas[int(m.group(1))]), h)     # en atributos y codigo
    return _reponer(h, formulas)


def respuesta(texto):
    """Respuesta del modelo (texto plano para consola, formulas en $...$): una formula que va sola
    en su linea se muestra en modo display; el resto, como markdown."""
    t = re.sub(r"^[ \t]*\$(?!\$)(.+?)\$[ \t]*$", r"$$\1$$", texto or "", flags=re.M)
    return markdown(t)


def _slug(texto):
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "seccion"


def markdown_con_indice(texto, prefijo=""):
    """(html, [(nivel, titulo, id)]) con un id en cada cabecera, para un indice lateral."""
    t, formulas = _proteger(texto or "")
    tokens = _md.parse(t)
    indice, usados = [], set()
    for i, tok in enumerate(tokens):
        if tok.type != "heading_open":
            continue
        titulo = tokens[i + 1].content if i + 1 < len(tokens) else ""
        base = (prefijo + "-" if prefijo else "") + _slug(_reponer(titulo, formulas, escapar=False))
        sid, n = base, 2
        while sid in usados:
            sid, n = f"{base}-{n}", n + 1
        usados.add(sid)
        tok.attrSet("id", sid)
        indice.append((int(tok.tag[1:]), _reponer(titulo, formulas, escapar=False), sid))
    html_ = _md.renderer.render(tokens, _md.options, {})
    return _reponer(html_, formulas), indice


# ----------------------------------------------------------------------
# notas y sesiones: frontmatter + secciones '## ', con los bloques '## Rn — ...' plegables
# ----------------------------------------------------------------------

RE_FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)
RE_H2 = re.compile(r"^## (.+?)[ \t]*$", re.M)
RE_RN = re.compile(r"^(R\d+)\s*[—–-]+\s*(.+?)\s*$")        # el mismo patron que comandos.RE_BLOQUE


def frontmatter(texto):
    """(dict o None, resto del texto)."""
    m = RE_FRONT.match(texto or "")
    if not m:
        return None, texto or ""
    try:
        import yaml
        datos = yaml.safe_load(m.group(1))
        if not isinstance(datos, dict):
            datos = {"frontmatter": m.group(1)}
    except Exception:
        datos = {"frontmatter": m.group(1)}
    return datos, texto[m.end():]


def secciones(texto):
    """[(titulo o None, cuerpo)] partiendo por las cabeceras '## '."""
    out, pos, titulo = [], 0, None
    for m in RE_H2.finditer(texto):
        out.append((titulo, texto[pos:m.start()]))
        titulo, pos = m.group(1), m.end()
    out.append((titulo, texto[pos:]))
    return [(t, c) for t, c in out if t is not None or c.strip()]


def documento(texto):
    """dict(front, bloques=[dict(titulo, rid, resto, html)]): los '## Rn — titulo' llevan rid."""
    front, cuerpo = frontmatter(texto)
    bloques = []
    for titulo, c in secciones(cuerpo):
        m = RE_RN.match(titulo) if titulo else None
        bloques.append(dict(titulo=titulo, rid=m.group(1).upper() if m else None,
                            resto=m.group(2) if m else titulo, html=markdown(c)))
    return dict(front=front, bloques=bloques)


# ----------------------------------------------------------------------
# texto de la capa tex (fragmentos del corpus): entornos que KaTeX no conoce
# ----------------------------------------------------------------------

_ENTORNOS = {"equation": None, "displaymath": None, "align": "aligned", "gather": "gathered",
             "multline": "gathered", "eqnarray": "aligned", "alignat": "aligned", "flalign": "aligned"}


def latex_para_web(texto):
    """\\begin{equation}...\\end{equation} -> \\[...\\]; align/gather -> \\[\\begin{aligned}...\\]; sin \\label."""
    t = texto or ""
    for env, interno in _ENTORNOS.items():
        patron = re.compile(r"\\begin\{" + env + r"\*?\}(?:\{[^}]*\})?([\s\S]*?)\\end\{" + env + r"\*?\}")
        if interno:
            t = patron.sub(lambda m, i=interno: "\\[\\begin{" + i + "}" + m.group(1) + "\\end{" + i + "}\\]", t)
        else:
            t = patron.sub(lambda m: "\\[" + m.group(1) + "\\]", t)
    t = re.sub(r"\\label\{[^}]*\}", "", t)
    # macros de texto fuera de las formulas: \emph{x}, \textit{x}, \textbf{x} -> x; \cite{k} -> [k];
    # \ref{x}/\eqref{x} sin resolver -> (etiqueta x), como pide la regla 9 de ask
    t = re.sub(r"\\(?:emph|textit|textbf|textsc|underline)\{([^{}]*)\}", r"\1", t)
    t = re.sub(r"\\cite[tp]?\{([^}]*)\}", r"[\1]", t)
    t = re.sub(r"\\(?:eq|auto|c)?ref\{([^}]*)\}", r"(etiqueta \1)", t)
    return t
