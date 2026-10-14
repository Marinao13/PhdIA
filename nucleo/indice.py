"""
Indice y consulta del corpus (BRIEF 4.2).

Fuentes:
    paper     corpus/text/<id>/unidades.jsonl, con su entrada en bib.yaml
    proyecto  corpus/PROYECTO.md, markdown directo
    nota      lecturas/*.md y sesiones/2*.md (sin plantillas ni ejemplos)

Fragmentos de 300-800 tokens: un teorema, lema o definicion es un fragmento
por si mismo; los parrafos de una misma seccion se agrupan hasta llenar el
tamano. Cada fragmento lleva doc, pagina, seccion, tipo y label: es lo que
hace posible citar [id:pNN].

Busqueda hibrida: BM25 (rank_bm25) + coseno sobre embeddings de la API
(text-embedding-3-small), fusionados por RRF. Los embeddings se guardan en
indice/ y solo se recalculan los fragmentos cuyo hash cambia. Cada llamada
de embeddings queda en registro/llamadas.jsonl para el coste del mes.

`buscar` no llama al modelo de chat: equivale a abrir el PDF y buscar, y por
eso esta disponible en todas las fases.
"""
import os, re, json, glob, sqlite3, hashlib, datetime, unicodedata
import numpy as np
from . import config as C

MODELO_EMB = os.environ.get("DOC_MODELO_EMB", "text-embedding-3-small")
MIN_TOK, MAX_TOK, SOLAPE_TOK = 300, 800, 60
TIPOS_SOLOS = {"teorema", "lema", "proposicion", "corolario", "definicion", "demostracion",
               "ejemplo", "observacion", "conjetura", "problema", "pregunta", "resumen",
               "notacion", "hipotesis", "afirmacion"}

F_DB = os.path.join(C.DIR_INDICE, "fragmentos.sqlite")
F_VEC = os.path.join(C.DIR_INDICE, "vectores.npy")
F_VEC_IDS = os.path.join(C.DIR_INDICE, "vectores_ids.json")

_enc = None


def _tokens(texto):
    global _enc
    if _enc is None:
        import tiktoken
        _enc = tiktoken.get_encoding("cl100k_base")
    return len(_enc.encode(texto))


def _hash(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


# ======================================================================
# fragmentacion
# ======================================================================

def _partir_largo(texto, maximo=MAX_TOK, solape=SOLAPE_TOK):
    """Parte un texto que excede el maximo por frases, con solape."""
    frases = re.split(r"(?<=[.;:])\s+(?=[A-Z\\$(])", texto)
    trozos, actual = [], ""
    for f in frases:
        if actual and _tokens(actual + " " + f) > maximo:
            trozos.append(actual)
            cola = " ".join(actual.split()[-solape:])
            actual = cola + " " + f
        else:
            actual = (actual + " " + f).strip()
    if actual:
        trozos.append(actual)
    return trozos


def fragmentar(unidades):
    """Lista de dicts {pagina, seccion, tipo, label, texto} a partir de unidades ordenadas."""
    out = []
    grupo = []

    def cerrar():
        if not grupo:
            return
        texto = "\n\n".join(u["texto"] for u in grupo)
        base = dict(pagina=grupo[0].get("pagina"), seccion=grupo[0].get("seccion"),
                    tipo="parrafos" if len(grupo) > 1 else grupo[0].get("tipo"), label=None, numero=None)
        for t in (_partir_largo(texto) if _tokens(texto) > MAX_TOK else [texto]):
            out.append(dict(base, texto=t))
        grupo.clear()

    for u in unidades:
        tipo = u.get("tipo") or "parrafo"
        if tipo == "titulo":
            cerrar()
            continue
        if tipo in TIPOS_SOLOS or tipo == "pagina":
            cerrar()
            partes = _partir_largo(u["texto"]) if _tokens(u["texto"]) > MAX_TOK else [u["texto"]]
            for i, t in enumerate(partes):
                out.append(dict(pagina=u.get("pagina"), seccion=u.get("seccion"), tipo=tipo,
                                label=u.get("label") if i == 0 else None,
                                numero=u.get("numero") if i == 0 else None, texto=t))
            continue
        if grupo and (u.get("seccion") != grupo[0].get("seccion")
                      or _tokens("\n\n".join(g["texto"] for g in grupo) + u["texto"]) > MAX_TOK):
            cerrar()
        grupo.append(u)
        if _tokens("\n\n".join(g["texto"] for g in grupo)) >= MIN_TOK:
            cerrar()
    cerrar()
    return out


def _unidades_markdown(texto):
    """Un markdown (proyecto, nota) como unidades: titulos y parrafos."""
    out, seccion = [], None
    for p in re.split(r"\n\s*\n", texto):
        p = p.strip()
        if not p or p.startswith("---"):
            continue
        if p.startswith("#"):
            seccion = p.lstrip("# ").strip()
            out.append(dict(pagina=None, seccion=seccion, tipo="titulo", label=None, texto=seccion))
        else:
            out.append(dict(pagina=None, seccion=seccion, tipo="parrafo", label=None, texto=p))
    return out


def fuentes():
    """[(fuente, doc, unidades)] de todo lo indexable que existe ahora."""
    out = []
    from . import corpus as Q
    bib = Q.leer_bib()
    for ruta in sorted(glob.glob(os.path.join(C.DIR_TEXT, "*", "unidades.jsonl"))):
        doc = os.path.basename(os.path.dirname(ruta))
        with open(ruta, encoding="utf-8") as f:
            unidades = [json.loads(l) for l in f if l.strip()]
        if unidades:
            if doc not in bib:
                print(f"  AVISO: corpus/text/{doc} no tiene entrada en bib.yaml (id renombrado o bib pisada?)")
            out.append((bib.get(doc, {}).get("fuente", "paper"), doc, unidades))
    if os.path.exists(C.F_PROYECTO):
        out.append(("proyecto", "proyecto", _unidades_markdown(C.leer(C.F_PROYECTO))))
    notas = glob.glob(os.path.join(C.DIR_LECTURAS, "*.md")) + \
        [p for p in glob.glob(os.path.join(C.DIR_SESIONES, "2*.md")) if "EJEMPLO" not in p]
    for ruta in sorted(notas):
        doc = "nota:" + os.path.splitext(os.path.basename(ruta))[0]
        out.append(("nota", doc, _unidades_markdown(C.leer(ruta))))
    return out


# ======================================================================
# almacen
# ======================================================================

def _db():
    os.makedirs(C.DIR_INDICE, exist_ok=True)
    con = sqlite3.connect(F_DB)
    con.execute("""CREATE TABLE IF NOT EXISTS fragmentos (
        id TEXT PRIMARY KEY, fuente TEXT, doc TEXT, pagina INTEGER, seccion TEXT,
        tipo TEXT, label TEXT, texto TEXT, hash TEXT, n_tokens INTEGER, orden INTEGER)""")
    cols = {r[1] for r in con.execute("PRAGMA table_info(fragmentos)")}
    if "numero" not in cols:
        con.execute("ALTER TABLE fragmentos ADD COLUMN numero TEXT")
    return con


def _leer_vectores():
    if os.path.exists(F_VEC) and os.path.exists(F_VEC_IDS):
        return np.load(F_VEC), json.load(open(F_VEC_IDS, encoding="utf-8"))
    return np.zeros((0, 0), dtype=np.float32), []


def _guardar_vectores(vec, ids):
    np.save(F_VEC, vec.astype(np.float32))
    with open(F_VEC_IDS, "w", encoding="utf-8") as f:
        json.dump(ids, f)


# ======================================================================
# embeddings por API, con registro para el coste
# ======================================================================

def _registrar(comando, tokens):
    from . import estado as E
    fase, _ = E.fase_actual()
    C.anadir(C.F_LLAMADAS, json.dumps({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "comando": comando, "fase": fase, "proveedor": "openai", "modelo": MODELO_EMB,
        "tokens_in": tokens, "tokens_out": 0, "forzado": False, "simulado": C.SIMULAR,
    }, ensure_ascii=False) + "\n")


def embeber(textos, comando="indexar"):
    """Embeddings de una lista de textos. Devuelve matriz (n, d) normalizada."""
    if C.SIMULAR:
        rng = np.random.default_rng(0)
        v = rng.standard_normal((len(textos), 64)).astype(np.float32)
        return v / np.linalg.norm(v, axis=1, keepdims=True)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("sin OPENAI_API_KEY: los embeddings van por la API de OpenAI")
    from openai import OpenAI
    cli = OpenAI()
    filas = []
    for i in range(0, len(textos), 100):
        lote = [t[:30000] for t in textos[i:i + 100]]
        r = cli.embeddings.create(model=MODELO_EMB, input=lote)
        filas.extend(d.embedding for d in sorted(r.data, key=lambda d: d.index))
        _registrar(comando, getattr(r.usage, "total_tokens", 0) or 0)
    v = np.asarray(filas, dtype=np.float32)
    return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


def _texto_para_embeber(frag, doc):
    cab = " · ".join(x for x in (doc, frag.get("seccion"), frag.get("tipo"), frag.get("label")) if x)
    return f"{cab}\n{frag['texto']}"


# ======================================================================
# indexar
# ======================================================================

def indexar(rehacer=False, verbose=True):
    con = _db()
    if rehacer:
        con.execute("DELETE FROM fragmentos")
        for f in (F_VEC, F_VEC_IDS):
            if os.path.exists(f):
                os.remove(f)
    existentes = {r[0]: r[1] for r in con.execute("SELECT id, hash FROM fragmentos")}
    meta_existente = {r[0]: r[1:] for r in con.execute("SELECT id, pagina, seccion, tipo, label, numero FROM fragmentos")}
    actualizados = 0
    vec, ids = _leer_vectores()
    tiene_vec = set(ids)

    nuevos, vistos, resumen = [], set(), {}
    for fuente, doc, unidades in fuentes():
        frags = fragmentar(unidades)
        resumen[doc] = len(frags)
        for k, fr in enumerate(frags):
            if _tokens(fr["texto"]) < 20:       # pagina escaneada sin OCR, ruido
                continue
            h = _hash(fr["texto"])
            fid = f"{doc}#{k:04d}"
            vistos.add(fid)
            if existentes.get(fid) == h and fid in tiene_vec:
                nuevo_meta = (fr.get("pagina"), fr.get("seccion"), fr.get("tipo"), fr.get("label"), fr.get("numero"))
                if meta_existente.get(fid) != nuevo_meta:      # mismo texto, otra pagina: sin re-embeber
                    con.execute("UPDATE fragmentos SET pagina=?, seccion=?, tipo=?, label=?, numero=? WHERE id=?",
                                (*nuevo_meta, fid))
                    actualizados += 1
                continue
            con.execute("INSERT OR REPLACE INTO fragmentos (id, fuente, doc, pagina, seccion, tipo, label, "
                        "texto, hash, n_tokens, orden, numero) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (fid, fuente, doc, fr.get("pagina"), fr.get("seccion"), fr.get("tipo"),
                         fr.get("label"), fr["texto"], h, _tokens(fr["texto"]), k, fr.get("numero")))
            nuevos.append((fid, _texto_para_embeber(fr, doc)))
    # fragmentos que ya no existen (documento reingerido con otra particion)
    sobrantes = set(existentes) - vistos
    if sobrantes:
        con.executemany("DELETE FROM fragmentos WHERE id = ?", [(s,) for s in sobrantes])
    con.commit()

    if nuevos:
        v_nuevos = embeber([t for _, t in nuevos])
        conservar = [i for i, fid in enumerate(ids) if fid in vistos and fid not in {n[0] for n in nuevos}]
        if len(ids) and vec.shape[1] == v_nuevos.shape[1]:
            vec = np.vstack([vec[conservar], v_nuevos])
            ids = [ids[i] for i in conservar] + [fid for fid, _ in nuevos]
        else:
            vec, ids = v_nuevos, [fid for fid, _ in nuevos]
        _guardar_vectores(vec, ids)
    elif sobrantes and len(ids):
        conservar = [i for i, fid in enumerate(ids) if fid in vistos]
        _guardar_vectores(vec[conservar], [ids[i] for i in conservar])

    total = con.execute("SELECT COUNT(*) FROM fragmentos").fetchone()[0]
    con.close()
    if verbose:
        for doc, n in resumen.items():
            print(f"  {doc:<44} {n:>5} fragmentos")
        print(f"\n{total} fragmentos en el indice; {len(nuevos)} embebidos ahora; "
              f"{actualizados} con pagina/seccion actualizada; {len(sobrantes)} retirados")
    return total, len(nuevos)


# ======================================================================
# buscar
# ======================================================================

def _tokenizar(texto):
    s = unicodedata.normalize("NFKC", texto).lower()
    s = re.sub(r"\\([a-z]+)", r" \1 ", s)        # \gamma -> gamma
    return [t for t in re.findall(r"[a-z0-9]+", s) if len(t) > 1]


def _cargar(fuente=None, doc=None):
    con = _db()
    q, args = "SELECT id, fuente, doc, pagina, seccion, tipo, label, texto, numero FROM fragmentos", []
    cond = []
    if fuente:
        cond.append("fuente = ?"); args.append(fuente)
    if doc:
        cond.append("doc = ?"); args.append(doc)
    if cond:
        q += " WHERE " + " AND ".join(cond)
    filas = con.execute(q, args).fetchall()
    con.close()
    claves = ("id", "fuente", "doc", "pagina", "seccion", "tipo", "label", "texto", "numero")
    return [dict(zip(claves, f)) for f in filas]


F_GLOSARIO = os.path.join(C.DIR_META, "glosario.yaml")
PESO_COSENO = 1.5   # los embeddings cruzan idiomas; BM25 no
BOOST_TIPO = {"teorema": 1.5, "definicion": 1.5, "lema": 1.3, "proposicion": 1.3,
              "corolario": 1.2, "notacion": 1.2}


def expandir(pregunta):
    """Anade a la consulta la traduccion EN de los terminos ES del glosario."""
    if not os.path.exists(F_GLOSARIO):
        return pregunta
    import yaml, unicodedata as ud
    glos = yaml.safe_load(C.leer(F_GLOSARIO)) or {}
    plana = ud.normalize("NFKD", pregunta.lower()).encode("ascii", "ignore").decode()
    extra = [en for es, en in sorted(glos.items(), key=lambda kv: -len(kv[0])) if es in plana]
    return pregunta + (" " + " ".join(extra) if extra else "")


def buscar(pregunta, k=8, fuente=None, doc=None, solo_bm25=False, por_doc=2):
    """Fragmentos mas relevantes, con puntuaciones. Sin modelo de chat."""
    frags = _cargar(fuente, doc)
    if not frags:
        return []
    from rank_bm25 import BM25Okapi
    consulta = expandir(pregunta)
    bm25 = BM25Okapi([_tokenizar(f["texto"]) for f in frags])
    s_bm = bm25.get_scores(_tokenizar(consulta))
    orden_bm = np.argsort(-s_bm)

    rrf = {}
    for r, i in enumerate(orden_bm[:50]):
        if s_bm[i] > 0:
            rrf[i] = rrf.get(i, 0) + 1 / (60 + r)
    if not solo_bm25:
        vec, ids = _leer_vectores()
        pos = {fid: j for j, fid in enumerate(ids)}
        idx = [pos[f["id"]] for f in frags if f["id"] in pos]
        q = embeber([consulta], comando="buscar")[0] if idx else None
        if idx and vec.shape[1] != q.shape[0]:          # vectores de otra dimension (simulacion): solo BM25
            idx = []
        if idx:
            sims = vec[idx] @ q
            orden = np.argsort(-sims)
            filas_con_vec = [i for i, f in enumerate(frags) if f["id"] in pos]
            for r, j in enumerate(orden[:50]):
                i = filas_con_vec[j]
                rrf[i] = rrf.get(i, 0) + PESO_COSENO / (60 + r)
                frags[i]["coseno"] = float(sims[j])
    for i in rrf:
        rrf[i] *= BOOST_TIPO.get(frags[i].get("tipo"), 1.0)
    mejores, vistos_doc = [], {}
    for i in sorted(rrf, key=lambda i: -rrf[i]):
        d = frags[i]["doc"]
        if por_doc and vistos_doc.get(d, 0) >= por_doc and not doc:
            continue
        vistos_doc[d] = vistos_doc.get(d, 0) + 1
        mejores.append(i)
        if len(mejores) >= k:
            break
    out = []
    for i in mejores:
        f = dict(frags[i])
        f["rrf"] = round(rrf[i], 4)
        f["bm25"] = round(float(s_bm[i]), 2)
        out.append(f)
    return out


RE_REF = re.compile(r"\\(?:ref|eqref|autoref|cref)\{([^}]+)\}")


def seguir_refs(resultados, maximo=4):
    """Anade los fragmentos etiquetados a los que los resultados remiten con \ref, mismo doc."""
    con = _db()
    extra, vistos = [], {f["id"] for f in resultados}
    for f in resultados:
        for lab in RE_REF.findall(f["texto"]):
            fila = con.execute("SELECT id, fuente, doc, pagina, seccion, tipo, label, texto, numero FROM fragmentos "
                               "WHERE doc = ? AND label = ? LIMIT 1", (f["doc"], lab)).fetchone()
            if fila and fila[0] not in vistos:
                vistos.add(fila[0])
                g = dict(zip(("id", "fuente", "doc", "pagina", "seccion", "tipo", "label", "texto", "numero"), fila))
                g["via_ref"] = f["id"]
                extra.append(g)
                if len(extra) >= maximo:
                    con.close()
                    return extra
    con.close()
    return extra


def vecinos_anteriores(fid, n=2):
    """Textos de los n fragmentos anteriores del mismo documento (por orden), para leer la
    atribucion que precede a un enunciado."""
    doc, _, k = fid.rpartition("#")
    try:
        k = int(k)
    except ValueError:
        return []
    con = _db()
    filas = con.execute("SELECT texto FROM fragmentos WHERE doc = ? AND orden < ? AND orden >= ? ORDER BY orden",
                        (doc, k, max(0, k - n))).fetchall()
    con.close()
    return [f[0] for f in filas]


def cita(f):
    """
    Cita legible: pagina verificada en el PDF + tipo de entorno con su numero impreso;
    si el numero no se resolvio, la etiqueta LaTeX marcada como tal. Nada de "sec N.N".
        [thilliez-2003:p7, Teorema 3.2]
        [jimenez-garrido-sanz-2016:p21, proposicion, etiqueta LaTeX: pro.gamma.menor.omega]
        [balser-2000:p143]
    """
    from .corpus import NOMBRE_ES
    base = f["doc"] + (f":p{f['pagina']}" if f.get("pagina") else "")
    tipo = f.get("tipo")
    if tipo in NOMBRE_ES and tipo not in ("demostracion", "resumen"):
        if f.get("numero"):
            cuerpo = f"{base}, {NOMBRE_ES[tipo]} {f['numero']}"
        elif f.get("label"):
            cuerpo = f"{base}, {tipo}, etiqueta LaTeX: {f['label']}"
        else:
            cuerpo = f"{base}, {tipo}"
    elif tipo == "demostracion":
        cuerpo = f"{base}, demostracion" + (f", etiqueta LaTeX: {f['label']}" if f.get("label") else "")
    else:
        cuerpo = base
    # el texto de capa tex es el de arXiv; la pagina, la del PDF de revista: se dice la version
    return f"[{cuerpo}{_marca_version(f['doc'])}]"


_META_DOC = {}


def _marca_version(doc):
    if doc not in _META_DOC:
        from .corpus import leer_bib
        e = leer_bib().get(doc, {})
        _META_DOC[doc] = (f" | texto: arXiv {e.get('arxiv_version') or 'v?'}"
                          if e.get("capa") == "tex" else "")
    return _META_DOC[doc]


def imprimir(resultados, ancho=420, columnas=90):
    import textwrap
    for n, f in enumerate(resultados, 1):
        cab = f"{n}. {cita(f)}  {f.get('tipo') or ''}"
        if "coseno" in f:
            cab += f"   bm25 {f['bm25']}  cos {f['coseno']:.2f}"
        print(cab)
        t = " ".join(f["texto"].split())
        t = t[:ancho] + ("..." if len(t) > ancho else "")
        print(textwrap.fill(t, columnas, initial_indent="   ", subsequent_indent="   ") + "\n")


# ======================================================================
# acceso directo para `preguntar`: localizar un pegado, traer un numero o una pagina
# ======================================================================

def _bolsa(texto):
    """Palabras de >= 3 letras de un texto (PDF pegado o fragmento tex), sin comandos."""
    s = unicodedata.normalize("NFKC", texto).lower()
    s = re.sub(r"\\[a-z]+", " ", s)
    return [t for t in re.findall(r"[a-z]+", s) if len(t) >= 3]


def _despegar(pegada, vocab, maximo=18):
    """
    'letnbeastronglyregularsequence' -> ['strongly', 'regular', 'sequence']: segmentacion
    por programacion dinamica con el vocabulario del documento (palabras de >= 3 letras);
    las letras que no caen en ninguna palabra se descartan.
    """
    n = len(pegada)
    mejor = [(0, [])] + [None] * n          # (letras cubiertas, palabras) hasta la posicion i
    for i in range(1, n + 1):
        cand = (mejor[i - 1][0], mejor[i - 1][1])          # letra suelta: no cubre
        for l in range(3, min(maximo, i) + 1):
            w = pegada[i - l:i]
            if w in vocab and mejor[i - l] is not None:
                c = (mejor[i - l][0] + l, mejor[i - l][1] + [w])
                if c[0] > cand[0]:
                    cand = c
        mejor[i] = cand
    return mejor[n][1]


def localizar(doc, texto):
    """
    Donde esta en el indice un trozo PEGADO del PDF (texto literal, formulas deformadas):
    dict(fragmentos=[...], cobertura=float) con el fragmento que mas palabras del pegado
    contiene (y el siguiente si el pegado lo desborda), o None si ninguno cubre bastante.
    Sin modelo ni API: bolsa de palabras del pegado contra cada fragmento del documento.
    La cita del fragmento es la del sistema (pagina verificada), no se inventa nada.
    """
    frags = sorted(_cargar(doc=doc), key=lambda f: f["id"])
    if not frags:
        return None
    conj = [set(_bolsa(f["texto"])) for f in frags]
    vocab = set().union(*conj)
    # las palabras frecuentes en el documento (en mas de un tercio de los fragmentos) no
    # discriminan: "strongly regular sequence" esta en casi todos
    df = {}
    for c in conj:
        for w in c:
            df[w] = df.get(w, 0) + 1
    comunes = {w for w, n in df.items() if n > len(frags) / 3} if len(frags) >= 12 else set()
    texto_n = unicodedata.normalize("NFKC", texto)
    cabecera = re.match(r"\s*(lemma|theorem|proposition|corollary|definition|remark|example)\s*(\d+(?:\.\d+)*)\.?",
                        texto_n, re.I)
    bolsa = _bolsa(texto_n[cabecera.end():] if cabecera else texto_n)
    pegadas = {w for w in bolsa if len(w) >= 7 and w not in vocab}
    if pegadas:                                   # copia del PDF con las palabras pegadas
        bolsa = [w for w in bolsa if w not in pegadas] + [s for w in bolsa if w in pegadas
                                                           for s in _despegar(w, vocab)]
    bolsa = [w for w in bolsa if w not in comunes]
    if len(bolsa) < 5:
        return None
    umbral = 0.7 if len(bolsa) < 25 else 0.6

    def cobertura(palabras):
        return sum(w in palabras for w in bolsa) / len(bolsa)

    propios = [cobertura(c) for c in conj]
    candidatos = range(len(frags))
    # el pegado empieza por "Lemma 2.1.3" / "Theorem 3.4": el numero impreso acota los candidatos
    # (el indice tiene numeros repetidos: se exige que el texto pegado este en el elegido, solo
    # o con su demostracion, que suele ser el fragmento siguiente)
    if cabecera:
        con_numero = [j for j, f in enumerate(frags) if f.get("numero") == cabecera.group(2)]

        def con_siguiente(j):
            return max(propios[j], cobertura(conj[j] | conj[j + 1]) if j + 1 < len(frags) else 0.0)
        if con_numero and max(con_siguiente(j) for j in con_numero) >= 0.3:
            candidatos, umbral = con_numero, 0.3
    i = max(candidatos, key=lambda j: propios[j])
    mejor, idx = propios[i], [i]
    # el pegado puede cruzar dos fragmentos consecutivos (enunciado + demostracion)
    sig = cobertura(conj[i] | conj[i + 1]) if i + 1 < len(frags) else 0.0
    ant = cobertura(conj[i - 1] | conj[i]) if i > 0 else 0.0
    if sig >= mejor + 0.15 and sig >= ant:
        mejor, idx = sig, [i, i + 1]
    elif ant >= mejor + 0.15:
        mejor, idx = ant, [i - 1, i]
    if mejor < umbral:
        return None
    return dict(fragmentos=[dict(frags[j], localizado=True) for j in idx], cobertura=round(mejor, 2))


def por_numero(doc, numero):
    """Fragmentos del documento con ese numero impreso, de cualquier tipo. Acepta '2.1.3',
    '2.1.3.' o 'Lemma 2.1.3': se queda con el numero."""
    m = re.search(r"\d+(?:\.\d+)*", str(numero))
    if not m:
        return []
    con = _db()
    filas = con.execute("SELECT id, fuente, doc, pagina, seccion, tipo, label, texto, numero FROM fragmentos "
                        "WHERE doc = ? AND numero = ? ORDER BY orden", (doc, m.group(0))).fetchall()
    con.close()
    claves = ("id", "fuente", "doc", "pagina", "seccion", "tipo", "label", "texto", "numero")
    return [dict(zip(claves, f)) for f in filas]


def por_pagina(doc, pagina):
    """Fragmentos del documento cuya pagina (la del PDF) es esa."""
    con = _db()
    filas = con.execute("SELECT id, fuente, doc, pagina, seccion, tipo, label, texto, numero FROM fragmentos "
                        "WHERE doc = ? AND pagina = ? ORDER BY orden", (doc, int(pagina))).fetchall()
    con.close()
    claves = ("id", "fuente", "doc", "pagina", "seccion", "tipo", "label", "texto", "numero")
    return [dict(zip(claves, f)) for f in filas]
