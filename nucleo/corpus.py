"""
Ingesta del corpus (BRIEF 4.1). Tres capas de extraccion, por prioridad:

    1. tex      fuente .tex de arXiv: formulas exactas.    cita [id:pNN, seccion/label]
    2. marker   Marker en GPU: markdown con LaTeX.         cita [id:pNN]
    3. pymupdf  texto por pagina. Se ejecuta SIEMPRE: es el mapa de paginas
                para las otras dos y el fallback.          cita [id:pNN]

Metadatos: solo de arXiv (pagina abs; la API de reserva), de Crossref (DOI) o
del propio PDF. Un id de arXiv o DOI leido del PDF solo se acepta si el titulo
que devuelve la red aparece en la primera pagina: asi una cita de la
bibliografia no se cuela como identidad del paper. Lo que no se confirma por
red queda `pendiente_verificar`. Nunca se completa nada de memoria.

Salida por paper, en corpus/text/<id>/:
    paginas/pNNN.txt   texto PyMuPDF de cada pagina (capa 3)
    tex/               fuente de arXiv (capa 1), si la hay
    marker.md          salida de Marker (capa 2), si la hay
    unidades.jsonl     una unidad por linea: {n, capa, pagina, seccion, tipo,
                       label, texto}. Es lo que lee `indexar`.
    meta.json          capa, paginas, avisos, fecha
"""
import os, re, io, json, glob, time, gzip, shutil, tarfile, subprocess, datetime, unicodedata
import requests, yaml, fitz
from . import config as C

UA = {"User-Agent": "doctorado-ingest/0.1 (uso personal academico)"}
PAUSA_ARXIV = 3          # segundos entre peticiones a arXiv, como piden ellos
UMBRAL_ESCANEADO = 200   # caracteres por pagina por debajo de los cuales no hay capa de texto

RE_ARXIV = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", re.I)
RE_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>,;]+)")

# entorno de teorema -> tipo de unidad. Se amplia con los \newtheorem del propio paper.
TIPOS = {"theorem": "teorema", "thm": "teorema", "lemma": "lema", "lem": "lema",
         "proposition": "proposicion", "prop": "proposicion", "corollary": "corolario",
         "cor": "corolario", "definition": "definicion", "defn": "definicion",
         "def": "definicion", "remark": "observacion", "rem": "observacion",
         "example": "ejemplo", "proof": "demostracion", "abstract": "resumen",
         "notation": "notacion", "conjecture": "conjetura", "question": "pregunta",
         "problem": "problema", "assumption": "hipotesis", "claim": "afirmacion"}
NOMBRE_A_TIPO = {"theorem": "teorema", "lemma": "lema", "proposition": "proposicion",
                 "corollary": "corolario", "definition": "definicion", "remark": "observacion",
                 "example": "ejemplo", "notation": "notacion", "conjecture": "conjetura",
                 "question": "pregunta", "problem": "problema", "assumption": "hipotesis",
                 "claim": "afirmacion"}


def hoy():
    return datetime.date.today().isoformat()


# ======================================================================
# bib.yaml
# ======================================================================

def leer_bib():
    t = C.leer(C.F_BIB)
    return (yaml.safe_load(t) or {}) if t.strip() else {}


def escribir_bib(bib):
    cab = ("# Bibliografia del corpus. Cada entrada lleva `estado`: `verificado` solo si los\n"
           "# metadatos vienen de arXiv o Crossref y el titulo aparece en el PDF; si no,\n"
           "# `pendiente_verificar`. No completar nada de memoria. `etiquetas` las pone Mariano.\n\n")
    C.escribir(C.F_BIB, cab + yaml.safe_dump(bib, allow_unicode=True, sort_keys=True, width=100))


def id_desde_fichero(pdf):
    base = os.path.splitext(os.path.basename(pdf))[0].lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


# ======================================================================
# red: arXiv y Crossref
# ======================================================================

def _get(url, timeout=60, **kw):
    r = requests.get(url, headers=UA, timeout=timeout, **kw)
    r.raise_for_status()
    return r


def meta_arxiv(aid):
    """Titulo, autores, fecha y DOI desde la pagina abs. La API XML da 503 a menudo."""
    aid = re.sub(r"v\d+$", "", aid)
    r = _get(f"https://arxiv.org/abs/{aid}")
    autores, d = [], {}
    for k, v in re.findall(r'<meta name="(citation_[a-z_]+)" content="([^"]*)"', r.text):
        if k == "citation_author":
            autores.append(v)
        else:
            d.setdefault(k, v)
    if not d.get("citation_title"):
        raise ValueError(f"arXiv {aid}: la pagina abs no trae citation_title")
    return dict(titulo=" ".join(d["citation_title"].split()), autores=autores,
                fecha=d.get("citation_date"), doi=d.get("citation_doi") or None, arxiv=aid)


def meta_crossref(doi):
    m = _get(f"https://api.crossref.org/works/{doi}").json()["message"]
    autores = [", ".join(x for x in (a.get("family", ""), a.get("given", "")) if x)
               for a in m.get("author", [])]
    fecha = (m.get("issued") or m.get("published-print") or m.get("published-online") or {})
    ano = (fecha.get("date-parts") or [[None]])[0][0]
    return dict(titulo=" ".join((m.get("title") or [""])[0].split()), autores=autores,
                venue=(m.get("container-title") or [""])[0] or None, ano=ano, doi=doi,
                volumen=m.get("volume"), paginas_revista=m.get("page"))


# ======================================================================
# texto: normalizacion y mapa de paginas
# ======================================================================

def _norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def titulo_en_texto(titulo, texto):
    """True si al menos el 60% de las palabras largas del titulo estan en el texto."""
    palabras = [w for w in _norm(titulo).split() if len(w) > 3]
    if not palabras:
        return False
    t = _norm(texto)
    return sum(w in t for w in palabras) / len(palabras) >= 0.6


def _texto_plano(latex):
    """Quita matematicas y comandos para poder buscar el fragmento en el texto del PDF."""
    s = re.sub(r"\\begin\{(equation|align|gather|multline|eqnarray)\*?\}.*?\\end\{\1\*?\}", " ",
               latex, flags=re.S)
    s = re.sub(r"\$\$.*?\$\$|\\\[.*?\\\]|\$[^$]*\$", " ", s, flags=re.S)
    s = re.sub(r"\\(label|ref|eqref|cite|index)\{[^}]*\}", " ", s)
    s = re.sub(r"\\[a-zA-Z]+\*?", " ", s)
    return re.sub(r"[{}~\[\]]", " ", s)


def mapear_pagina(texto, paginas_norm):
    """Pagina (1-based) donde aparece un trozo del texto de la unidad, o None."""
    palabras = _norm(_texto_plano(texto)).split()
    if len(palabras) < 4:
        return None
    for ini in (0, len(palabras) // 3, (2 * len(palabras)) // 3):
        for n in (8, 6, 4):
            frag = " ".join(palabras[ini:ini + n])
            if len(frag) < 18:
                continue
            for i, p in enumerate(paginas_norm):
                if frag in p:
                    return i + 1
    return None


# ======================================================================
# capa 3: PyMuPDF
# ======================================================================

def extraer_paginas(pdf):
    with fitz.open(pdf) as doc:
        return [p.get_text() for p in doc]


def unidades_pymupdf(paginas):
    out = []
    for i, t in enumerate(paginas, 1):
        if t.strip():
            out.append(dict(capa="pymupdf", pagina=i, seccion=None, tipo="pagina",
                            label=None, texto=t.strip()))
    return out


# ======================================================================
# capa 1: fuente .tex de arXiv
# ======================================================================

def descargar_tex(aid, destino):
    """arxiv.org/e-print/<id>: tar.gz con varios ficheros, o un .tex.gz. Devuelve los .tex."""
    b = _get(f"https://arxiv.org/e-print/{aid}", timeout=180).content
    os.makedirs(destino, exist_ok=True)
    try:
        with tarfile.open(fileobj=io.BytesIO(b)) as tf:
            for m in tf.getmembers():
                nombre = m.name.replace("\\", "/")
                if nombre.startswith("/") or ".." in nombre.split("/"):
                    continue
                tf.extract(m, destino)
    except tarfile.ReadError:
        try:
            txt = gzip.decompress(b)
        except OSError:
            txt = b
        with open(os.path.join(destino, "main.tex"), "wb") as f:
            f.write(txt)
    return sorted(glob.glob(os.path.join(destino, "**", "*.tex"), recursive=True))


def _leer_tex(ruta):
    for enc in ("utf-8", "latin-1"):
        try:
            return open(ruta, encoding=enc).read()
        except UnicodeDecodeError:
            continue
    return open(ruta, encoding="utf-8", errors="replace").read()


def _sin_comentarios(tex):
    return re.sub(r"(?<!\\)%.*", "", tex)


def tex_principal(ficheros):
    """El .tex con \\begin{document}, con sus \\input e \\include resueltos."""
    principal = None
    for f in ficheros:
        if r"\begin{document}" in _leer_tex(f):
            principal = f
            break
    if principal is None:
        return None
    base = os.path.dirname(principal)
    texto = _leer_tex(principal)

    def sustituir(m, _prof=[0]):
        if _prof[0] > 5:
            return ""
        nombre = m.group(2).strip()
        for cand in (nombre, nombre + ".tex"):
            ruta = os.path.join(base, cand)
            if os.path.exists(ruta):
                _prof[0] += 1
                try:
                    return "\n" + re.sub(r"\\(input|include)\{([^}]*)\}", sustituir, _leer_tex(ruta)) + "\n"
                finally:
                    _prof[0] -= 1
        return ""
    return re.sub(r"\\(input|include)\{([^}]*)\}", sustituir, texto)


def _tipos_del_paper(preambulo):
    """Amplia TIPOS con los \\newtheorem{env}{Nombre} del propio paper."""
    tipos = dict(TIPOS)
    for env, nombre in re.findall(r"\\newtheorem\*?\{([^}]+)\}(?:\[[^\]]*\])?\{([^}]+)\}", preambulo):
        clave = _norm(nombre).split()
        if clave:
            tipos[env] = NOMBRE_A_TIPO.get(clave[0], _norm(nombre).replace(" ", "-"))
    return tipos


def unidades_tex(tex, paginas):
    """Recorre el cuerpo en orden: secciones, entornos de teorema y parrafos."""
    tex = _sin_comentarios(tex)
    pre, _, cuerpo = tex.partition(r"\begin{document}")
    cuerpo = cuerpo.split(r"\end{document}")[0]
    tipos = _tipos_del_paper(pre)
    paginas_norm = [_norm(p) for p in paginas]

    envs = "|".join(re.escape(e) for e in tipos)
    patron = re.compile(
        r"\\(section|subsection|subsubsection)\*?\{((?:[^{}]|\{[^{}]*\})*)\}"
        r"|\\begin\{(" + envs + r")\}(?:\[[^\]]*\])?(.*?)\\end\{\3\}", re.S)

    unidades, sec, sub, subsub, titulo_sec, pos = [], 0, 0, 0, None, 0

    def seccion():
        if not sec:
            return None
        return ".".join(str(x) for x in (sec, sub, subsub) if x)

    def parrafos(trozo):
        for p in re.split(r"\n\s*\n", trozo):
            p = p.strip()
            if len(_norm(_texto_plano(p))) < 60:      # ruido: \maketitle, etiquetas sueltas
                continue
            unidades.append(dict(capa="tex", pagina=None, seccion=seccion(), tipo="parrafo",
                                 label=None, texto=p))

    for m in patron.finditer(cuerpo):
        parrafos(cuerpo[pos:m.start()])
        pos = m.end()
        if m.group(1):
            nivel, titulo_sec = m.group(1), " ".join(m.group(2).split())
            if nivel == "section":
                sec, sub, subsub = sec + 1, 0, 0
            elif nivel == "subsection":
                sub, subsub = sub + 1, 0
            else:
                subsub += 1
            unidades.append(dict(capa="tex", pagina=None, seccion=seccion(), tipo="titulo",
                                 label=None, texto=titulo_sec))
        else:
            env, contenido = m.group(3), m.group(4).strip()
            lab = re.search(r"\\label\{([^}]*)\}", contenido)
            unidades.append(dict(capa="tex", pagina=None, seccion=seccion(), tipo=tipos[env],
                                 label=lab.group(1) if lab else None, texto=contenido))
    parrafos(cuerpo[pos:])

    ultima = None
    for u in unidades:
        pag = mapear_pagina(u["texto"], paginas_norm)
        if pag is None and u["tipo"] == "titulo":
            pag = ultima
        u["pagina"] = pag if pag is not None else ultima
        u["pagina_estimada"] = pag is None
        ultima = u["pagina"]
    return unidades


# ======================================================================
# capa 2: Marker
# ======================================================================

def marker_disponible():
    """marker_single en el PATH y, si su OCR va por Docker, Docker respondiendo."""
    if shutil.which("marker_single") is None:
        return False, "marker_single no esta en el PATH"
    if os.environ.get("SURYA_INFERENCE_BACKEND", "") == "llamacpp":
        return True, ""
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=8)
        if r.returncode == 0:
            return True, ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False, "Docker Desktop apagado: el OCR de Marker (surya) corre en Docker. Arrancalo o usa SURYA_INFERENCE_BACKEND=llamacpp"


def extraer_marker(pdf, destino_md, escaneado, timeout=3600):
    """Ejecuta marker_single y deja el markdown paginado en destino_md."""
    tmp = os.path.join(os.path.dirname(destino_md), "_marker_tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    cmd = [shutil.which("marker_single"), pdf, "--output_dir", tmp,
           "--output_format", "markdown", "--paginate_output"]
    if escaneado:
        cmd.append("--force_ocr")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout)
    mds = glob.glob(os.path.join(tmp, "**", "*.md"), recursive=True)
    if r.returncode != 0 or not mds:
        cola = (r.stderr or r.stdout or "").strip().splitlines()[-3:]
        raise RuntimeError("marker fallo: " + " | ".join(cola))
    shutil.move(mds[0], destino_md)
    shutil.rmtree(tmp, ignore_errors=True)


RE_TITULO_MD = re.compile(
    r"^\*{0,2}(Theorem|Lemma|Proposition|Corollary|Definition|Remark|Example|Proof|Notation|Conjecture)"
    r"\b[^\n]{0,40}?\*{0,2}[.:]?", re.I)


def unidades_marker(md, paginas):
    """Separa por los cortes de pagina de Marker y despues por parrafos."""
    paginas_norm = [_norm(p) for p in paginas]
    trozos = re.split(r"\n\{(\d+)\}-{5,}\s*\n", "\n" + md)
    if len(trozos) == 1:
        bloques = [(None, md)]
    else:
        bloques = [(int(trozos[i]) + 1, trozos[i + 1]) for i in range(1, len(trozos) - 1, 2)]
        if trozos[0].strip():
            bloques.insert(0, (None, trozos[0]))
    unidades, seccion = [], None
    for pag, texto in bloques:
        for p in re.split(r"\n\s*\n", texto):
            p = p.strip()
            if not p:
                continue
            if p.startswith("#"):
                seccion = p.lstrip("# ").strip()
                unidades.append(dict(capa="marker", pagina=pag, seccion=seccion, tipo="titulo",
                                     label=None, texto=seccion))
                continue
            if len(_norm(p)) < 40:
                continue
            m = RE_TITULO_MD.match(p)
            tipo = NOMBRE_A_TIPO.get(m.group(1).lower(), "demostracion") if m else "parrafo"
            if pag is None:
                pag = mapear_pagina(p, paginas_norm)
            unidades.append(dict(capa="marker", pagina=pag, seccion=seccion, tipo=tipo,
                                 label=None, texto=p))
    return unidades


# ======================================================================
# orquestacion
# ======================================================================

def _detectar_ids(paginas):
    cabeza = "\n".join(paginas[:2])
    a = RE_ARXIV.search(cabeza)
    d = RE_DOI.search(cabeza)
    return (a.group(1) if a else None), (d.group(1).rstrip(".") if d else None)


def _metadatos(paginas, sin_red, avisos):
    """Devuelve (entrada_bib, arxiv_verificado). Solo red o PDF; nada de memoria."""
    arxiv, doi = _detectar_ids(paginas)
    cabeza = "\n".join(paginas[:2])
    ent = {}
    verificado_arxiv = None
    if sin_red:
        avisos.append("sin red: metadatos sin verificar")
    if arxiv and not sin_red:
        try:
            m = meta_arxiv(arxiv)
            time.sleep(PAUSA_ARXIV)
            if titulo_en_texto(m["titulo"], cabeza):
                ent.update(titulo=m["titulo"], autores=m["autores"], arxiv=m["arxiv"])
                if m.get("fecha"):
                    ent["ano_arxiv"] = int(m["fecha"][:4])
                doi = doi or m.get("doi")
                verificado_arxiv = m["arxiv"]
            else:
                avisos.append(f"arXiv {arxiv} leido en el PDF no es este paper (titulo distinto); ignorado")
        except Exception as e:
            avisos.append(f"arXiv {arxiv}: {type(e).__name__}: {str(e)[:80]}")
    if doi and not sin_red:
        try:
            m = meta_crossref(doi)
            if ent.get("titulo") or titulo_en_texto(m["titulo"], cabeza):
                for k in ("venue", "ano", "doi", "volumen", "paginas_revista"):
                    if m.get(k) is not None:
                        ent[k] = m[k]
                ent.setdefault("titulo", m["titulo"])
                ent.setdefault("autores", m["autores"])
            else:
                avisos.append(f"DOI {doi} leido en el PDF no es este paper (titulo distinto); ignorado")
        except Exception as e:
            avisos.append(f"Crossref {doi}: {type(e).__name__}: {str(e)[:80]}")
    if ent.get("titulo"):
        ent["estado"] = "verificado"
    else:
        lineas = [l.strip() for l in cabeza.splitlines() if len(l.strip()) > 8][:3]
        ent["titulo_pdf_sin_verificar"] = " / ".join(lineas)[:200] or None
        ent["estado"] = "pendiente_verificar"
    return ent, verificado_arxiv


def ingerir(pdf, id_=None, capa=None, sin_red=False, rehacer=False, verbose=True):
    """Ingiere un PDF. Devuelve la entrada de bib.yaml."""
    pdf = os.path.abspath(pdf)
    if not os.path.exists(pdf):
        raise FileNotFoundError(pdf)
    id_ = id_ or id_desde_fichero(pdf)
    bib = leer_bib()
    if id_ in bib and not rehacer:
        if verbose:
            print(f"{id_}: ya ingerido ({bib[id_].get('capa')}). --rehacer para repetir")
        return bib[id_]

    dir_id = os.path.join(C.DIR_TEXT, id_)
    dir_pag = os.path.join(dir_id, "paginas")
    os.makedirs(dir_pag, exist_ok=True)
    avisos = []

    # capa 3 siempre: mapa de paginas y fallback
    paginas = extraer_paginas(pdf)
    for i, t in enumerate(paginas, 1):
        C.escribir(os.path.join(dir_pag, f"p{i:03d}.txt"), t)
    media = sum(len(p) for p in paginas) / max(len(paginas), 1)
    escaneado = media < UMBRAL_ESCANEADO
    if escaneado:
        avisos.append(f"escaneado: {media:.0f} caracteres/pagina; solo OCR (Marker --force_ocr)")

    ent, arxiv_ok = _metadatos(paginas, sin_red, avisos)

    # eleccion de capa
    unidades, capa_usada = [], None
    if capa in (None, "tex") and arxiv_ok and not sin_red:
        try:
            ficheros = descargar_tex(arxiv_ok, os.path.join(dir_id, "tex"))
            time.sleep(PAUSA_ARXIV)
            principal = tex_principal(ficheros)
            if principal is None:
                avisos.append("e-print sin \\begin{document}; no se usa la capa tex")
            else:
                unidades = unidades_tex(principal, paginas)
                if len(unidades) < 5:
                    avisos.append(f"capa tex con solo {len(unidades)} unidades; se descarta")
                    unidades = []
                else:
                    capa_usada = "tex"
                    avisos.append("tex de arXiv: puede diferir de la version publicada")
        except Exception as e:
            avisos.append(f"e-print {arxiv_ok}: {type(e).__name__}: {str(e)[:80]}")
    if capa_usada is None and capa in (None, "marker"):
        ok, motivo = marker_disponible()
        if ok:
            try:
                destino = os.path.join(dir_id, "marker.md")
                extraer_marker(pdf, destino, escaneado)
                unidades = unidades_marker(C.leer(destino), paginas)
                capa_usada = "marker" + ("-ocr" if escaneado else "")
            except Exception as e:
                avisos.append(f"marker: {str(e)[:160]}")
        else:
            avisos.append(motivo)
    if capa_usada is None:
        unidades = unidades_pymupdf(paginas)
        capa_usada = "pymupdf"
        if capa != "pymupdf":
            ent["reextraer"] = "marker"
        if not unidades:
            avisos.append("sin texto: pendiente de extraccion por OCR")

    for n, u in enumerate(unidades, 1):
        u["n"] = n
    with open(os.path.join(dir_id, "unidades.jsonl"), "w", encoding="utf-8", newline="\n") as f:
        for u in unidades:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    con_pagina = sum(1 for u in unidades if u.get("pagina"))
    meta = dict(id=id_, capa=capa_usada, paginas=len(paginas), unidades=len(unidades),
                unidades_con_pagina=con_pagina, escaneado=escaneado, avisos=avisos, fecha=hoy())
    C.escribir(os.path.join(dir_id, "meta.json"), json.dumps(meta, ensure_ascii=False, indent=1))

    ent.update(fichero=os.path.relpath(pdf, C.DIR_CORPUS).replace("\\", "/"), capa=capa_usada,
               paginas=len(paginas), unidades=len(unidades), ingerido=hoy())
    ent.setdefault("etiquetas", [])
    if avisos:
        ent["avisos"] = avisos
    bib[id_] = ent
    escribir_bib(bib)

    if verbose:
        est = ent["estado"]
        print(f"{id_:<42} {capa_usada:<11} {len(paginas):>4} pag  {len(unidades):>4} unidades "
              f"({con_pagina} con pagina)  {est}")
        for a in avisos:
            print(f"    - {a}")
    return ent


def ingerir_todo(**kw):
    bib = leer_bib()
    pdfs = sorted(glob.glob(os.path.join(C.DIR_RAW, "*.pdf")))
    hechos = 0
    for pdf in pdfs:
        id_ = id_desde_fichero(pdf)
        if id_ in bib and not kw.get("rehacer"):
            continue
        try:
            ingerir(pdf, **kw)
            hechos += 1
        except Exception as e:
            print(f"{id_}: FALLO {type(e).__name__}: {e}")
    print(f"\n{hechos} ingeridos; {len(leer_bib())} en bib.yaml de {len(pdfs)} PDFs")
