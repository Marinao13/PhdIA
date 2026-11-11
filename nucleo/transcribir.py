"""
Pasar a limpio lo escrito a mano (o una foto, o un PDF): transcripcion a markdown con LaTeX.

    python doc.py transcribir FICHERO [--tipo curso|paper|duda] [--titulo T] [--paginas 1-3,5]
                                      [--motor modelo|marker] [--calidad normal|alta]
    python doc.py transcribir --lista
    python doc.py transcribir --revisado NOMBRE
    python doc.py transcribir --tex NOMBRE [--pisar]

Dos motores:
    modelo   el modelo con vision, por motor.llamar: puerta de fases, coste registrado. Defecto.
    marker   OCR local (Marker/surya en .venv-marker1, GPU): gratis y sin red. Con letra
             manuscrita puede fallar mas; para comparar.

Salida: transcripciones/AAAA-MM-DD-nombre.md con cabecera (origen, tipo, paginas, motor,
estado: sin_revisar) y una seccion por pagina (<!-- pagina N -->). El original se copia a
transcripciones/originales/ (fuera de git) para revisar lado a lado. Al lado del .md queda un
.tex exportado de el (nucleo/a_latex.py): la fuente es el .md; el .tex se rehace al marcar
revisado o con --tex, salvo que lo hayas editado a mano (entonces no se pisa sin --pisar).

Regla: una transcripcion automatica falla donde mas duele (un subindice, un cuantificador).
Nada `sin_revisar` entra en el indice ni se cita; solo lo que Mariano marca `revisado`.
"""
import os, re, glob, shutil, datetime, threading

from . import config as C

# Un cerrojo para todo lo que lee-modifica-escribe un .md: el hilo de la web que va anadiendo
# paginas y la peticion que guarda una correccion no se pisan.
_CERROJO = threading.RLock()

TIPOS = ("curso", "paper", "duda")
MARCA_PAGINA = "<!-- pagina {n} -->"
RE_PAGINA = re.compile(r"^<!-- pagina (\d+) -->[ \t]*$", re.M)
FOTOS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")          # una pagina; las abre Pillow
EXTENSIONES = (".pdf",) + FOTOS + (".tif", ".tiff")
AVISO = "> Transcripcion automatica SIN REVISAR."
RE_AVISO = re.compile(r"^" + re.escape(AVISO) + r"[^\n]*\n(?:>[^\n]*\n)*\n?", re.M)


def _dir():
    """(transcripciones/, transcripciones/originales/), calculados al usar: los tests cambian C.RAIZ."""
    d = os.path.join(C.RAIZ, "transcripciones")
    return d, os.path.join(d, "originales")


# ----------------------------------------------------------------------
# paginas
# ----------------------------------------------------------------------

def rango(texto, total):
    """'1-3,5' -> [1, 2, 3, 5] acotado a 1..total. Vacio o None -> todas."""
    if not texto:
        return list(range(1, total + 1))
    out = set()
    for trozo in str(texto).split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", trozo, re.A)
        if m:
            a, b = sorted((int(m.group(1)), int(m.group(2))))
            out.update(range(max(a, 1), min(b, total) + 1))      # se acota ANTES de expandir: 1-99999999999
        elif re.fullmatch(r"\d+", trozo, re.A):
            if 1 <= int(trozo) <= total:
                out.add(int(trozo))
        else:
            raise ValueError(f"rango de paginas no valido: {trozo!r} (ejemplo: 1-3,5)")
    return sorted(out)


def _es_foto(ruta):
    return os.path.splitext(ruta)[1].lower() in FOTOS


def n_paginas(ruta):
    if _es_foto(ruta):                                 # PyMuPDF no abre todos los formatos (webp)
        try:
            from PIL import Image
            with Image.open(ruta):
                return 1
        except Exception:
            pass                                       # sin Pillow o imagen rara: que lo diga fitz
    import fitz
    with fitz.open(ruta) as doc:
        return len(doc)


def _foto_png(ruta, max_lado):
    """PNG de una foto: orientacion EXIF aplicada (el movil la guarda tumbada) y fondo blanco si
    trae transparencia (un PNG de pizarra con trazo negro sobre transparente saldria negro)."""
    from PIL import Image, ImageOps
    import io
    with Image.open(ruta) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode.startswith(("I", "F")):             # gris de 16 o 32 bits (un escaner): convert("RGB") lo satura a blanco
            raise ValueError("profundidad de color que Pillow no convierte bien")
        if im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info:
            im = im.convert("RGBA")
            fondo = Image.new("RGB", im.size, "white")
            fondo.paste(im, mask=im.split()[-1])
            im = fondo
        else:
            im = im.convert("RGB")
        im.thumbnail((max_lado, max_lado))
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return buf.getvalue()


def pagina_png(ruta, n, max_lado=2000):
    """PNG de la pagina n (1-based) de un PDF o una imagen, con el lado mayor <= max_lado."""
    if _es_foto(ruta):
        try:
            return _foto_png(ruta, max_lado)
        except ImportError:
            pass                                       # sin Pillow: fitz
        except Exception:
            if os.path.splitext(ruta)[1].lower() == ".webp":
                raise                                  # fitz no lo abre: mejor el error de Pillow
    import fitz
    with fitz.open(ruta) as doc:
        page = doc[n - 1]
        lado = max(page.rect.width, page.rect.height) or 1
        z = min(max_lado / lado, 3.0)                 # un PDF (72 dpi) sube; una foto grande baja
        pix = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
        return pix.tobytes("png")


# ----------------------------------------------------------------------
# cabecera y ficheros
# ----------------------------------------------------------------------

def _slug(texto):
    import unicodedata as ud
    s = ud.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "apuntes"


RE_CABECERA = re.compile(r"\A\s*---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)


def _trocear(texto):
    """(cabecera cruda, cuerpo): el bloque '---' tal cual esta en el fichero, y lo demas."""
    m = RE_CABECERA.match(texto)
    return (m.group(1), texto[m.end():]) if m else ("", texto)


def partir(texto):
    """(meta, cuerpo) de un markdown con cabecera '---'."""
    cab, cuerpo = _trocear(texto)
    meta = {}
    for l in cab.splitlines():
        if ":" in l:
            k, _, v = l.partition(":")
            meta[k.strip()] = v.strip()
    return meta, cuerpo


def _cabecera(meta):
    orden = ("origen", "tipo", "titulo", "fecha", "paginas", "motor", "estado", "revisado_el")
    claves = [k for k in orden if k in meta] + [k for k in meta if k not in orden]
    return "\n".join(f"{k}: {meta[k]}" for k in claves)


def _poner(cab, clave, valor):
    """La linea `clave: valor` de la cabecera cruda: sustituida si existe, anadida si no. Lo
    demas (lineas tuyas, comentarios, el orden) no se toca."""
    linea = f"{clave}: {valor}"
    nuevo, n = re.subn(rf"^{re.escape(clave)}[ \t]*:.*$", lambda m: linea, cab, count=1, flags=re.M)
    return nuevo if n else cab.rstrip("\n") + "\n" + linea


def _quitar(cab, clave):
    """La cabecera cruda sin la linea `clave: ...`."""
    return re.sub(rf"^{re.escape(clave)}[ \t]*:.*\n?", "", cab, count=1, flags=re.M)


def _escribir(ruta, cab, cuerpo):
    C.escribir(ruta, "---\n" + cab.strip("\n") + "\n---\n" + cuerpo)


def listar():
    """[dict(nombre, ruta, origen, tipo, titulo, fecha, paginas, motor, estado, cuerpo)] por fecha."""
    d, _ = _dir()
    out = []
    for ruta in sorted(glob.glob(os.path.join(d, "*.md"))):
        meta, cuerpo = partir(C.leer(ruta))
        if not meta.get("estado"):
            continue                                   # no es una transcripcion del sistema
        out.append(dict(meta, nombre=os.path.basename(ruta)[:-3], ruta=ruta, cuerpo=cuerpo))
    return out


def leer(nombre):
    """dict de una transcripcion por nombre (sin .md), con 'original' = ruta del original o None.
    None si no existe o si el fichero no es una transcripcion del sistema (sin `estado` en la
    cabecera): un .md ajeno de la carpeta ni se sirve ni se puede marcar o corregir."""
    d, d_orig = _dir()
    nombre = os.path.basename(nombre)
    if nombre.endswith(".md"):
        nombre = nombre[:-3]
    ruta = os.path.join(d, nombre + ".md")
    if not os.path.exists(ruta):
        return None
    meta, cuerpo = partir(C.leer(ruta))
    if not meta.get("estado"):
        return None
    originales = sorted(glob.glob(os.path.join(d_orig, glob.escape(nombre) + ".*")))
    ext = os.path.splitext(meta.get("origen", ""))[1].lower()
    original = next((p for p in originales if ext and p.lower().endswith(ext)), None)
    return dict(meta, nombre=nombre, ruta=ruta, cuerpo=cuerpo,
                original=original or (originales[0] if originales else None))


def marcar_revisado(nombre):
    """estado: revisado en la cabecera (sin tocar el resto) y fuera el aviso. La ruta, o None.
    El .tex se rehace con el texto revisado si no lo has editado a mano."""
    with _CERROJO:
        t = leer(nombre)
        if not t:
            return None
        cab, cuerpo = _trocear(C.leer(t["ruta"]))
        cab = _poner(_poner(cab, "estado", "revisado"), "revisado_el", datetime.date.today().isoformat())
        _escribir(t["ruta"], cab, RE_AVISO.sub("", cuerpo, count=1))     # solo las lineas del aviso
    exportar_tex(t["nombre"])
    return t["ruta"]


def exportar_tex(nombre, pisar=False):
    """Escribe transcripciones/NOMBRE.tex desde el .md tal como esta ahora. Devuelve (ruta, que):
    que = 'escrito'; 'tuyo' si el .tex que habia tiene cambios hechos a mano y no se ha pisado
    (pisar=True lo fuerza); 'fallo' si no se pudo generar. (None, None) si no hay tal transcripcion.
    Nunca lanza: la exportacion es un anadido y no debe tirar una transcripcion ni un revisado."""
    t = leer(nombre)
    if not t:
        return None, None
    ruta = os.path.join(_dir()[0], t["nombre"] + ".tex")
    try:
        from . import a_latex as L
        if os.path.exists(ruta) and not pisar and not L.intacto(C.leer(ruta)):
            return ruta, "tuyo"
        C.escribir(ruta, L.documento(t["cuerpo"], nombre=t["nombre"], estado=t.get("estado", "sin_revisar")))
        return ruta, "escrito"
    except Exception:
        return ruta, "fallo"


def dudas(cuerpo):
    """(ilegibles, dudosos): cuantas marcas [ILEGIBLE] y [?] quedan."""
    return len(re.findall(r"\[ILEGIBLE\]", cuerpo)), len(re.findall(r"\[\?\]", cuerpo))


def paginas(cuerpo):
    """(prefacio, [(n, texto)]): el cuerpo partido por las marcas <!-- pagina N -->."""
    trozos = RE_PAGINA.split(cuerpo)                   # [antes, n1, texto1, n2, texto2, ...]
    return trozos[0], [(int(trozos[i]), trozos[i + 1].strip("\n")) for i in range(1, len(trozos) - 1, 2)]


def guardar_pagina(nombre, n, texto):
    """Sustituye el texto de la pagina n (la correccion a mano desde la web). True si existia.
    Solo cambia ese tramo del fichero: la cabecera, el prefacio y las demas paginas quedan byte
    a byte. Con una marca duplicada a mano, se corrige la primera."""
    with _CERROJO:
        t = leer(nombre)
        if not t:
            return False
        cab, cuerpo = _trocear(C.leer(t["ruta"]))
        marcas = list(RE_PAGINA.finditer(cuerpo))
        i = next((k for k, m in enumerate(marcas) if int(m.group(1)) == n), None)
        if i is None:
            return False
        texto = (texto or "").replace("\r\n", "\n").replace("\r", "\n")
        texto = RE_PAGINA.sub("", texto).strip("\n")       # una marca pegada no parte el fichero
        ultima = i + 1 == len(marcas)
        fin = len(cuerpo) if ultima else marcas[i + 1].start()
        cuerpo = cuerpo[:marcas[i].end()] + "\n\n" + texto + ("\n" if ultima else "\n\n") + cuerpo[fin:]
        _escribir(t["ruta"], cab, cuerpo)
        return True


def sin_revisar():
    """Nombres de las transcripciones que siguen sin revisar."""
    return [t["nombre"] for t in listar() if t.get("estado") != "revisado"]


def unidades(cuerpo):
    """Unidades para el indice: parrafos y titulos, con la pagina de su marca <!-- pagina N -->."""
    out, seccion = [], None
    prefacio, pares = paginas(cuerpo)
    pares.insert(0, (pares[0][0] if pares else None, prefacio))       # el titulo va con la primera pagina
    for pagina, texto in pares:
        for p in re.split(r"\n\s*\n", texto):
            p = p.strip()
            if not p or p.startswith(AVISO) or p.startswith("<!--"):
                continue
            if p.startswith("#"):                      # "## Teorema 2\nSea M..." sin linea en blanco:
                cabeza, _, p = p.partition("\n")       # el titulo es la primera linea; lo demas, texto
                seccion = cabeza.lstrip("# ").strip()
                out.append(dict(pagina=pagina, seccion=seccion, tipo="titulo", label=None, texto=seccion))
                p = p.strip()
                if not p:
                    continue
            # corte_pagina: `fragmentar` no junta parrafos de paginas distintas, y la cita lleva la pagina buena
            out.append(dict(pagina=pagina, seccion=seccion, tipo="parrafo", label=None, texto=p, corte_pagina=True))
    return out


# ----------------------------------------------------------------------
# motores
# ----------------------------------------------------------------------

def _con_modelo(ruta, paginas, calidad, forzar, progreso, al_avanzar=None):
    """[(n, markdown)] con el modelo con vision, pagina a pagina, y el coste. Si algo falla con
    paginas ya hechas (red, cuota, la fase cambia a media pasada, Ctrl+C, una pagina que no se
    puede leer) se devuelve lo hecho y el motivo en coste['fallo']; si falla la primera, se lanza.
    al_avanzar(hojas) se llama tras cada pagina: quien llama escribe ya el fichero, y matar el
    proceso (cerrar la ventana, reiniciar el servidor web) no pierde lo pagado."""
    from . import motor as M
    from . import prompts as P
    modelo = C.MODELO if calidad == "alta" else None
    total = n_paginas(ruta)
    salida, coste = [], dict(tokens_in=0, tokens_out=0, tokens_cache=0, segundos=0.0, cortadas=0, modelo=None,
                             fallo=None)
    for n in paginas:
        if progreso:
            progreso(f"pagina {n} de {total}...")
        try:
            mensaje = M.mensaje_con_imagenes(f"Pagina {n} de {total}. Transcribela.", [pagina_png(ruta, n)])
            texto = M.llamar("transcribir", P.TRANSCRIBIR, [mensaje], forzar=forzar, modelo=modelo, contexto=False)
        except (Exception, KeyboardInterrupt) as e:
            if isinstance(e, M.MotorApagado):
                motivo = f"motor apagado ({e})"
            elif isinstance(e, KeyboardInterrupt):
                motivo = "interrumpido"
            else:
                motivo = f"{type(e).__name__}: {e}"
            if not salida:                             # nada que conservar
                if isinstance(e, (M.MotorApagado, KeyboardInterrupt)):
                    raise
                raise RuntimeError(f"fallo en la pagina {n}: {motivo}") from e
            coste["fallo"] = f"pagina {n}: {motivo}"
            break
        u = dict(M.ULTIMA)                             # por hilo: no se mezcla con un /ask de la web
        for k in ("tokens_in", "tokens_out", "tokens_cache"):
            coste[k] += u.get(k) or 0
        coste["segundos"] += u.get("segundos") or 0
        coste["cortadas"] += 1 if u.get("cortada") else 0
        coste["modelo"] = u.get("modelo")
        if u.get("cortada"):
            texto += "\n\n[PAGINA CORTADA por el tope de salida: revisa el final contra el original]"
        salida.append((n, texto.strip()))
        if al_avanzar:
            al_avanzar(salida)
    return salida, coste


def _con_marker(ruta, paginas, progreso):
    """[(n, markdown)] con Marker en local (OCR forzado). Una sola pasada sobre las paginas pedidas."""
    import fitz, tempfile
    from . import corpus as Q
    ok, motivo = Q.marker_disponible()
    if not ok:
        raise RuntimeError("Marker no disponible: " + motivo)
    tmp = tempfile.mkdtemp(prefix="transcribir_")
    try:
        pdf = os.path.join(tmp, "paginas.pdf")
        with fitz.open() as nuevo:                    # un PDF con solo las paginas pedidas, en orden
            if os.path.splitext(ruta)[1].lower() == ".pdf":
                with fitz.open(ruta) as doc:
                    for n in paginas:
                        nuevo.insert_pdf(doc, from_page=n - 1, to_page=n - 1)
            else:                                      # imagen: la misma que veria el modelo
                for n in paginas:
                    png = pagina_png(ruta, n, max_lado=3000)
                    with fitz.open(stream=png, filetype="png") as img:
                        r = img[0].rect
                    pag = nuevo.new_page(width=r.width, height=r.height)
                    pag.insert_image(pag.rect, stream=png)
            nuevo.save(pdf)
        if progreso:
            progreso(f"Marker (local) sobre {len(paginas)} paginas: carga los modelos, puede tardar...")
        md = os.path.join(tmp, "salida.md")
        Q.extraer_marker(pdf, md, escaneado=True)
        texto = C.leer(md)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # --paginate_output separa con '{k}----...' (k desde 0)
    trozos = re.split(r"\n*\{(\d+)\}-{10,}\n*", texto)
    if len(trozos) < 3:
        return [(paginas[0], texto.strip())], None
    out = []
    for i in range(1, len(trozos) - 1, 2):
        k = int(trozos[i])
        if k < len(paginas):
            out.append((paginas[k], trozos[i + 1].strip()))
    return out, None


def coste_eur(coste):
    """EUR aproximados de una pasada con el modelo, segun config.PRECIOS; None si no hay precio."""
    if not coste or not coste.get("modelo"):
        return None
    p = C.PRECIOS.get(coste["modelo"])
    if not p or any(p.get(k) is None for k in ("entrada", "cacheada", "salida")):
        return None
    nuevos = coste["tokens_in"] - coste["tokens_cache"]
    usd = (nuevos * p["entrada"] + coste["tokens_cache"] * p["cacheada"] + coste["tokens_out"] * p["salida"]) / 1e6
    return round(usd * C.EUR_POR_USD, 3)


# ----------------------------------------------------------------------
# transcribir
# ----------------------------------------------------------------------

def _guardar_original(ruta, d_orig, nombre, ext):
    """Copia el original a originales/nombre.ext. Devuelve (ruta o None si no se pudo, copiado_ahora).
    Borra antes los originales huerfanos con ese nombre (los de una transcripcion borrada), pero
    nunca el propio fichero de entrada: se puede retranscribir desde originales/."""
    destino = os.path.join(d_orig, nombre + ext)
    try:
        for viejo in glob.glob(os.path.join(d_orig, glob.escape(nombre) + ".*")):
            if not os.path.samefile(viejo, ruta):
                os.remove(viejo)
        if os.path.exists(destino):                    # es la entrada: ya esta en su sitio
            return destino, False
        shutil.copyfile(ruta, destino)
        return destino, True
    except OSError:
        return None, False


def transcribir(ruta, tipo="paper", titulo=None, paginas=None, motor="modelo", calidad="normal",
                forzar=False, progreso=None):
    """
    Transcribe un PDF o imagen. Devuelve dict(ruta, nombre, paginas, pendientes, coste, fallo,
    ilegibles, dudosos, motor, sin_original, tex, tex_estado). Si el modelo falla a media pasada
    se guarda lo hecho: `pendientes` son las paginas que faltan y `fallo` el motivo.
    Lanza FileNotFoundError / ValueError / RuntimeError con mensajes para el usuario;
    motor.MotorApagado si la fase no permite el motor (solo con motor='modelo').
    """
    ruta = os.path.abspath(ruta)
    if not os.path.exists(ruta):
        raise FileNotFoundError(ruta)
    ext = os.path.splitext(ruta)[1].lower()
    if ext not in EXTENSIONES:
        raise ValueError(f"formato no admitido: {os.path.basename(ruta)} (PDF o imagen)")
    if tipo not in TIPOS:
        raise ValueError(f"tipo debe ser uno de {TIPOS}")
    total = n_paginas(ruta)
    cuales = rango(paginas, total)
    if not cuales:
        raise ValueError(f"ninguna pagina en ese rango (el fichero tiene {total})")
    titulo = " ".join((titulo or os.path.splitext(os.path.basename(ruta))[0]).split()) or "apuntes"

    d, d_orig = _dir()
    os.makedirs(d_orig, exist_ok=True)
    hoy = datetime.date.today().isoformat()
    base, k = f"{hoy}-{_slug(titulo)}", 1
    while True:                                        # el nombre se RESERVA al elegirlo (un .md vacio, que
        nombre = base if k == 1 else f"{base}-{k}"     # listar y leer ignoran): dos pasadas a la vez con el
        destino = os.path.join(d, nombre + ".md")      # mismo titulo no comparten fichero ni original
        try:
            open(destino, "x").close()
            break
        except FileExistsError:
            k += 1
    escritas = []

    def vuelca(hojas, etiqueta_motor):
        """Lleva al disco las paginas de `hojas` que aun no estan. La primera crea el fichero; las
        siguientes se ANADEN a lo que haya en disco, sin reescribirlo: lo que se corrija mientras la
        pasada sigue (en la web o en VS Code) no se pisa. Si entretanto se marco revisada, vuelve a
        sin_revisar: ha entrado una pagina que nadie ha mirado."""
        with _CERROJO:
            for n, texto in hojas:
                if n in escritas:
                    continue
                cab, cuerpo = _trocear(C.leer(destino)) if os.path.exists(destino) else ("", "")
                if not partir("---\n" + cab + "\n---\n")[0].get("estado"):
                    # recien reservado (o lo han borrado a media pasada): se crea con lo hecho hasta aqui
                    hechas = [(m, x) for m, x in hojas if m in escritas or m == n]
                    cab = _cabecera(dict(origen=os.path.basename(ruta), tipo=tipo, titulo=titulo, fecha=hoy,
                                         paginas="", motor=etiqueta_motor, estado="sin_revisar"))
                    cuerpo = (f"# {titulo}\n\n"
                              f"{AVISO} Revisala con el original al lado (web: /transcripciones/{nombre}), "
                              f"corrige aqui, y marca: python doc.py transcribir --revisado {nombre}\n\n")
                    cuerpo += "\n\n".join(MARCA_PAGINA.format(n=m) + "\n\n" + x for m, x in hechas) + "\n"
                    numeros = [m for m, _ in hechas]
                else:
                    ya = [int(x) for x in re.findall(r"\d+", partir("---\n" + cab + "\n---\n")[0].get("paginas", ""))]
                    cuerpo = cuerpo.rstrip("\n") + "\n\n" + MARCA_PAGINA.format(n=n) + "\n\n" + texto + "\n"
                    cab = _quitar(_poner(cab, "estado", "sin_revisar"), "revisado_el")
                    numeros = ya + [n]
                _escribir(destino, _poner(cab, "paginas", ",".join(str(m) for m in numeros)), cuerpo)
                escritas.append(n)

    def limpia():                                      # no salio ninguna pagina: ni reserva ni original sueltos
        for sobra in ([destino] if os.path.exists(destino) and os.path.getsize(destino) == 0 else []) + \
                ([original] if copiado else []):
            try:
                os.remove(sobra)
            except OSError:
                pass

    # El original, a su sitio antes de empezar (para revisar al lado aunque la pasada se corte), y el
    # .md, tras CADA pagina: lo pagado esta en disco aunque maten el proceso.
    original, copiado = _guardar_original(ruta, d_orig, nombre, ext)
    try:
        if motor == "marker":
            hojas, coste = _con_marker(ruta, cuales, progreso)
            etiqueta_motor = "marker (local)"
        else:
            previsto = C.MODELO if calidad == "alta" else C.modelo_para("transcribir")
            hojas, coste = _con_modelo(ruta, cuales, calidad, forzar, progreso,
                                       al_avanzar=lambda hs: vuelca(hs, f"modelo ({previsto})"))
            etiqueta_motor = f"modelo ({coste.get('modelo') or previsto})"
        vuelca(hojas, etiqueta_motor)
        if not escritas:
            raise RuntimeError("el motor no devolvio ninguna pagina")
    except BaseException:
        if not escritas:
            limpia()
        raise
    with _CERROJO:                                     # el modelo que de verdad respondio, sin tocar lo demas
        cab, cuerpo = _trocear(C.leer(destino))
        if _poner(cab, "motor", etiqueta_motor) != cab:
            _escribir(destino, _poner(cab, "motor", etiqueta_motor), cuerpo)
    hechas = [n for n, _ in hojas]
    pendientes = [n for n in cuales if n not in hechas]
    sin_original = original is None
    il, du = dudas(cuerpo)
    tex, tex_estado = exportar_tex(nombre)
    return dict(ruta=destino, nombre=nombre, paginas=hechas, pendientes=pendientes, coste=coste,
                fallo=(coste or {}).get("fallo"), ilegibles=il, dudosos=du, motor=etiqueta_motor,
                sin_original=sin_original, tex=tex, tex_estado=tex_estado)
