"""
Mini web local del sistema de doctorado (docs/WEB.md).

    python -m web [--host 127.0.0.1] [--port 8765]
    python web/servidor.py

Sin autenticacion propia: delante va Cloudflare Access. Escucha solo en localhost por defecto.
Cada pagina llama a funciones que ya existen en nucleo/; el motor pasa por nucleo.motor.llamar
y por tanto respeta las fases (apagado en fase 1 y 3).
"""
import os, sys, re, glob, types, argparse, datetime, shutil, threading, uuid
from urllib.parse import urlparse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M
from nucleo import indice as I
from nucleo import corpus as Q
from nucleo import transcribir as T
from web import captura, render, hilos

AQUI = os.path.dirname(os.path.abspath(__file__))
HOST_DEFECTO, PUERTO_DEFECTO = "127.0.0.1", 8765

app = FastAPI(title="doctorado", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=os.path.join(AQUI, "static")), name="static")
plantillas = Jinja2Templates(directory=os.path.join(AQUI, "templates"))

CSP = ("default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
       "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; font-src https://cdn.jsdelivr.net; "
       "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'self'")

NAV = [("/", "Panel"), ("/buscar", "Buscar"), ("/ask", "Ask"), ("/preguntar", "Preguntar"),
       ("/notas", "Notas"), ("/sesiones", "Sesiones"), ("/transcripciones", "Transcripciones"),
       ("/lagunas", "Lagunas"), ("/guia", "Guia")]
NOMBRES_FASE = dict(libre="libre", f1="fase 1", f2="fase 2", f3="fase 3", f4="fase 4")


@app.middleware("http")
async def _cabeceras(request, call_next):
    # un POST desde otro origen no entra: Access autentica, pero no evita un formulario ajeno
    if request.method == "POST":
        sitio = request.headers.get("sec-fetch-site")
        origen = request.headers.get("origin")
        host = request.headers.get("host", "")
        if sitio and sitio not in ("same-origin", "none"):
            return PlainTextResponse("peticion de otro origen", status_code=403)
        # Sec-Fetch-Site lo pone el navegador y una pagina ajena no puede falsearlo: con same-origin
        # basta. Sin el, el Origin tiene que ser el nuestro ("null" no lo es).
        if sitio != "same-origin" and origen and urlparse(origen).netloc.lower() != host.lower():
            return PlainTextResponse("peticion de otro origen", status_code=403)
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    # same-origin y no no-referrer: con no-referrer el navegador manda `Origin: null` en los POST
    # de formulario y la comprobacion de arriba los rechazaba todos (visto el 2026-11-11).
    r.headers["Referrer-Policy"] = "same-origin"
    r.headers["Content-Security-Policy"] = CSP
    if not request.url.path.startswith("/static/"):
        r.headers["Cache-Control"] = "no-store"
    return r


# ----------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------

def _hoy():
    """comandos.HOY se fija al importar; un servidor que vive dias lo refresca antes de escribir."""
    K.HOY = datetime.date.today().isoformat()


def estado_breve():
    try:
        fase, m = E.fase_actual()
    except Exception as e:
        return dict(fase="?", nombre=f"estado no disponible ({type(e).__name__})", motor=False,
                    pausada=False, simulado=C.SIMULAR, explicacion="")
    return dict(fase=fase, nombre=NOMBRES_FASE.get(fase, fase), motor=fase in E.MOTOR_PERMITIDO,
                pausada=bool(m.get("pausada")), simulado=C.SIMULAR,
                explicacion=E.EXPLICACION.get(fase, ""))


def _pagina(request, nombre, **ctx):
    ctx.setdefault("avisos", [])
    ctx.update(request=request, estado=estado_breve(), ruta=request.url.path, nav=NAV)
    return plantillas.TemplateResponse(request, nombre, ctx)


def _ids_bib():
    try:
        return sorted(k for k, e in Q.leer_bib().items() if (e or {}).get("fuente") != "proyecto")
    except Exception:
        return []


def _anotar_laguna(texto, defecto):
    """Una linea en registro/lagunas.md con _anadir_lagunas, como /laguna en el REPL. Devuelve el origen."""
    texto = " ".join((texto or "").split())
    if not texto:
        return None
    _hoy()
    fase, _ = E.fase_actual()
    origen = hilos.origen_sesion(defecto)
    K._anadir_lagunas([texto], origen, fase)
    return origen


RE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,120}$")


def _fichero_md(directorio, id_):
    """Ruta de directorio/id.md, o 404. El id no sale del directorio."""
    if not RE_ID.match(id_ or "") or ".." in id_ or id_.startswith("PLANTILLA"):
        raise HTTPException(404)
    base = os.path.realpath(directorio)
    ruta = os.path.realpath(os.path.join(base, id_ + ".md"))
    if not ruta.startswith(base + os.sep) or not os.path.isfile(ruta):
        raise HTTPException(404)
    return ruta


def _listar_md(directorio):
    out = []
    for ruta in sorted(glob.glob(os.path.join(directorio, "*.md")), reverse=True):
        nombre = os.path.basename(ruta)
        if nombre.startswith("PLANTILLA"):
            continue
        texto = C.leer(ruta)
        front, _ = render.frontmatter(texto)
        out.append(dict(id=nombre[:-3], nombre=nombre, front=front or {},
                        bloques=len(K._bloques_nota(texto)), lineas=texto.count("\n"),
                        modificado=datetime.datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%Y-%m-%d %H:%M")))
    return out


SECCIONES_AHORA = ("TE TOCA AHORA", "MATERIAL", "PENDIENTE")


def _trocear_ahora(texto):
    """La salida de `ahora --breve` en partes: cabecera (mapa del ciclo), toca, material, pendiente."""
    partes, actual, nombre = {}, [], "cabecera"
    for l in texto.splitlines():
        t = l.strip()
        if t in SECCIONES_AHORA:
            partes[nombre] = "\n".join(actual).strip("\n")
            actual, nombre = [], t
            continue
        actual.append(l)
    partes[nombre] = "\n".join(actual).strip("\n")
    for k in partes:
        partes[k] = "\n".join(l[4:] if l.startswith("    ") else l.lstrip() for l in partes[k].splitlines())
    return partes


# ----------------------------------------------------------------------
# paginas
# ----------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def panel(request: Request):
    s_ahora = captura.ejecutar(K.cmd_ahora, types.SimpleNamespace(breve=True))
    s_estado = captura.ejecutar(K.cmd_estado, types.SimpleNamespace())
    partes = _trocear_ahora(s_ahora.texto)
    toca = partes.get("TE TOCA AHORA", "").splitlines()
    return _pagina(request, "panel.html", avisos=s_ahora.avisos + s_estado.avisos,
                   estado_texto=s_estado.texto.strip("\n"), cabecera=partes.get("cabecera", ""),
                   comando=(toca[0] if toca else ""), toca="\n".join(toca[1:]),
                   material=partes.get("MATERIAL", ""), pendiente=partes.get("PENDIENTE", ""),
                   crudo=s_ahora.texto if "TE TOCA AHORA" not in s_ahora.texto else "")


@app.get("/buscar", response_class=HTMLResponse)
def buscar(request: Request, q: str = "", doc: str = "", k: int = 8, bm25: str = ""):
    q, doc = " ".join(q.split()), doc.strip() or None
    k = max(1, min(int(k or 8), 30))
    resultados, aviso, vacio = [], None, False
    if q:
        try:
            resultados = I.buscar(q, k=k, doc=doc, solo_bm25=bool(bm25), por_doc=2)
        except Exception as e:                          # sin embeddings (clave, red): solo BM25, como --bm25
            try:
                resultados = I.buscar(q, k=k, doc=doc, solo_bm25=True, por_doc=2)
                aviso = f"sin embeddings ({type(e).__name__}: {str(e)[:120]}): resultados solo por BM25"
            except Exception as e2:
                aviso = f"indice no disponible: {type(e2).__name__}: {str(e2)[:160]}"
        vacio = not resultados and not aviso
    items = []
    for f in resultados:
        try:
            cita = I.cita(f)
        except Exception:
            cita = f"[{f.get('doc')}:p{f.get('pagina')}]"
        items.append(dict(cita=cita, tipo=f.get("tipo") or "", bm25=f.get("bm25"), coseno=f.get("coseno"),
                          doc=f.get("doc"), fuente=f.get("fuente") or "paper",
                          texto=render.latex_para_web(f.get("texto", "")), crudo=f.get("texto", "")))
    return _pagina(request, "buscar.html", q=q, doc=doc or "", k=k, bm25=bool(bm25), items=items,
                   aviso=aviso, vacio=vacio, docs=_ids_bib())


@app.get("/ask", response_class=HTMLResponse)
def ask_formulario(request: Request):
    return _pagina(request, "ask.html", pregunta="", doc="", k=8, con_propios=False, docs=_ids_bib(),
                   respuesta_html=None, resto="", apagado=not estado_breve()["motor"])


@app.post("/ask", response_class=HTMLResponse)
def ask(request: Request, pregunta: str = Form(""), doc: str = Form(""), k: int = Form(8),
        con_propios: str = Form("")):
    pregunta, doc = " ".join(pregunta.split()), doc.strip() or None
    k = max(1, min(int(k or 8), 30))
    ctx = dict(pregunta=pregunta, doc=doc or "", k=k, con_propios=bool(con_propios), docs=_ids_bib(),
               respuesta_html=None, resto="", apagado=False)
    if not pregunta:
        return _pagina(request, "ask.html", avisos=["escribe una pregunta"], **ctx)
    _hoy()
    # la misma firma que doc.py ask: pregunta como lista de palabras, sin --forzar
    args = types.SimpleNamespace(pregunta=pregunta.split(), k=k, fuente=None, doc=doc, por_doc=2,
                                 con_propios=bool(con_propios), forzar=False)
    s = captura.ejecutar(K.cmd_ask, args)
    apagado = isinstance(s.error, M.MotorApagado) or any("MOTOR APAGADO" in a for a in s.avisos)
    ctx.update(respuesta_html=render.respuesta(s.cuerpos[0]) if s.cuerpos else None,
               resto=s.texto.strip("\n"), apagado=apagado, ultima=dict(M.ULTIMA) if s.cuerpos else None)
    return _pagina(request, "ask.html", avisos=s.avisos, **ctx)


@app.get("/preguntar", response_class=HTMLResponse)
def preguntar(request: Request, hilo: str = "", doc: str = ""):
    h = hilos.o_nuevo(hilo)
    if doc and not hilo:                       # enlace desde /buscar: hilo nuevo con ese paper
        hilos.fijar_doc(h, doc)
    avisos, h["avisos"] = h["avisos"], []
    vista = [dict(t, respuesta_html=render.respuesta(t["respuesta"])) for t in h["vista"]]
    return _pagina(request, "preguntar.html", avisos=avisos, hilo=h, vista=vista, docs=_ids_bib(),
                   n_frags=hilos.fragmentos_en_indice(h["doc"]),
                   plantillas=[("", "sin plantilla"), ("notacion", "/notacion"), ("lema", "/lema"), ("paso", "/paso")],
                   puede_seguir=h["ultima_cortada"] or h["ultima_sigue"],
                   tokens_entrada=(h["vista"][-1]["u"].get("tokens_in") if h["vista"] else None))


@app.post("/preguntar")
def preguntar_turno(request: Request, hilo: str = Form(""), doc: str = Form(""), pregunta: str = Form(""),
                    fragmento: str = Form(""), plantilla: str = Form(""), accion: str = Form("preguntar")):
    h = hilos.o_nuevo(hilo)
    if accion == "nuevo":
        h = hilos.nuevo(h["doc"])
        h["avisos"].append("hilo nuevo")
        return RedirectResponse(f"/preguntar?hilo={h['id']}", status_code=303)
    _hoy()
    hilos.fijar_doc(h, doc)
    if accion == "sigue":
        hilos.turno(h, "", "", "", sigue=True)
    else:
        hilos.turno(h, pregunta, fragmento, plantilla)
    return RedirectResponse(f"/preguntar?hilo={h['id']}", status_code=303)


@app.post("/preguntar/laguna")
def preguntar_laguna(request: Request, hilo: str = Form(""), laguna: str = Form("")):
    h = hilos.o_nuevo(hilo)
    if _anotar_laguna(laguna, "preguntar"):
        h["avisos"].append("laguna anotada en registro/lagunas.md. Sigue con el paper; el viernes, python doc.py lagunas")
    else:
        h["avisos"].append("uso: una linea con el hueco de grado/master. No se resuelve ahora.")
    return RedirectResponse(f"/preguntar?hilo={h['id']}", status_code=303)


@app.get("/notas", response_class=HTMLResponse)
def notas(request: Request):
    return _pagina(request, "lista.html", tipo="nota", titulo="Notas de lectura", base="/notas",
                   directorio=os.path.relpath(C.DIR_LECTURAS, RAIZ), items=_listar_md(C.DIR_LECTURAS))


@app.get("/notas/{id_}", response_class=HTMLResponse)
def nota(request: Request, id_: str):
    ruta = _fichero_md(C.DIR_LECTURAS, id_)
    return _pagina(request, "documento.html", tipo="nota", base="/notas", id=id_,
                   ruta=os.path.relpath(ruta, RAIZ), doc=render.documento(C.leer(ruta)))


@app.get("/sesiones", response_class=HTMLResponse)
def sesiones(request: Request):
    return _pagina(request, "lista.html", tipo="sesion", titulo="Sesiones", base="/sesiones",
                   directorio=os.path.relpath(C.DIR_SESIONES, RAIZ), items=_listar_md(C.DIR_SESIONES))


@app.get("/sesiones/{id_}", response_class=HTMLResponse)
def sesion(request: Request, id_: str):
    ruta = _fichero_md(C.DIR_SESIONES, id_)
    return _pagina(request, "documento.html", tipo="sesion", base="/sesiones", id=id_,
                   ruta=os.path.relpath(ruta, RAIZ), doc=render.documento(C.leer(ruta)))


@app.get("/guia", response_class=HTMLResponse)
def guia(request: Request):
    partes = []
    for nombre in ("USO.md", "GUIA.md"):
        ruta = os.path.join(RAIZ, "docs", nombre)
        if os.path.exists(ruta):
            html_, indice = render.markdown_con_indice(C.leer(ruta), prefijo=nombre[:-3].lower())
            partes.append(dict(nombre=nombre, html=html_, indice=indice))
    return _pagina(request, "guia.html", partes=partes)


@app.get("/lagunas", response_class=HTMLResponse)
def lagunas(request: Request, ok: str = ""):
    try:
        pendientes, estructurales = K._cuenta_lagunas()
    except Exception:
        pendientes, estructurales = 0, 0
    avisos = {"1": ["laguna anotada en registro/lagunas.md. Se resuelve aparte: viernes, python doc.py lagunas"],
              "0": ["escribe una linea con el hueco"]}.get(ok, [])
    return _pagina(request, "lagunas.html", avisos=avisos, html=render.markdown(C.leer(C.F_LAGUNAS)),
                   pendientes=pendientes, estructurales=estructurales,
                   ruta=os.path.relpath(C.F_LAGUNAS, RAIZ))


@app.post("/lagunas")
def lagunas_anadir(request: Request, texto: str = Form("")):
    ok = "1" if _anotar_laguna(texto, "web") else "0"
    return RedirectResponse(f"/lagunas?ok={ok}", status_code=303)


# ----------------------------------------------------------------------
# transcripciones: lo manuscrito pasado a limpio (nucleo/transcribir.py, docs/GUIA.md)
# ----------------------------------------------------------------------

MAX_SUBIDA = 40 * 1024 * 1024
# Una transcripcion tarda mas de lo que aguanta una peticion (el tunel corta a los 100 s): va en
# un hilo, de una en una, y la pagina de la lista se refresca sola mientras dura.
_TRABAJO = {}
_HILO = None
_CERROJO = threading.Lock()
AVISOS_TRANSCRIBIR = {
    "formato": "formato no admitido: sube un PDF o una imagen (png, jpg, webp). Las fotos HEIC del iPhone, "
               "exportalas como JPG o PDF",
    "grande": "el fichero pasa de 40 MB: partelo o subelo por consola (python doc.py transcribir)",
    "ocupado": "ya hay una transcripcion en curso: espera a que acabe",
    "paginas": "rango de paginas no valido o fuera del fichero (ejemplo: 1-3,5)",
    "apagado": "MOTOR APAGADO en esta fase: el modelo no transcribe en fase 1 ni 3. Sella antes, o usa Marker "
               "(OCR local, no es el motor)",
    "guardada": "cambios guardados",
    "sincambios": "no habia cambios que guardar",
    "nuevas": "han entrado paginas nuevas desde que abriste esta: no la he marcado. Lo que tenias corregido esta "
              "guardado; revisa las nuevas y marca otra vez",
    "revisada": "marcada como revisada. Entra en el indice con: python doc.py indexar",
    "nopagina": "esa pagina no existe en la transcripcion",
}


def _transcripcion(nombre):
    if not RE_ID.match(nombre or "") or ".." in nombre:
        raise HTTPException(404)
    t = T.leer(nombre)
    if not t:
        raise HTTPException(404)
    return t


def _transcribir_en_hilo(ruta, kw):
    try:
        r = T.transcribir(ruta, progreso=lambda s: _TRABAJO.update(mensaje=s), **kw)
        _TRABAJO.update(estado="hecho", nombre=r["nombre"], pendientes=r["pendientes"], fallo=r["fallo"],
                        mensaje=f"{len(r['paginas'])} paginas, {r['ilegibles']} [ILEGIBLE], {r['dudosos']} [?]")
    except M.MotorApagado as e:
        _TRABAJO.update(estado="error", mensaje="MOTOR APAGADO: " + str(e))
    except BaseException as e:                         # tambien un sys.exit del motor (falta un paquete)
        _TRABAJO.update(estado="error", mensaje=f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(os.path.dirname(ruta), ignore_errors=True)


@app.get("/transcripciones", response_class=HTMLResponse)
def transcripciones(request: Request, aviso: str = ""):
    items = []
    for t in reversed(T.listar()):
        il, du = T.dudas(t["cuerpo"])
        items.append(dict(nombre=t["nombre"], titulo=t.get("titulo", ""), tipo=t.get("tipo", "?"),
                          estado=t.get("estado", "?"), paginas=t.get("paginas", ""), motor=t.get("motor", ""),
                          ilegibles=il, dudosos=du))
    return _pagina(request, "transcripciones.html", items=items, tipos=T.TIPOS,
                   trabajo=dict(_TRABAJO) if _TRABAJO else None,
                   avisos=[AVISOS_TRANSCRIBIR[aviso]] if aviso in AVISOS_TRANSCRIBIR else [])


@app.post("/transcripciones")
def transcripciones_subir(request: Request, fichero: UploadFile = File(...), tipo: str = Form("paper"),
                          titulo: str = Form(""), paginas: str = Form(""), motor: str = Form("modelo"),
                          calidad: str = Form("normal")):
    global _HILO

    def vuelve(aviso):
        return RedirectResponse(f"/transcripciones?aviso={aviso}", status_code=303)

    # \w es Unicode: "Análisis armónico.pdf" conserva sus letras; fuera separadores y lo demas
    nombre = re.sub(r"[^\w. -]", "_", os.path.basename((fichero.filename or "").replace("\\", "/"))).strip(" .") or "subida"
    if os.path.splitext(nombre)[1].lower() not in T.EXTENSIONES:
        return vuelve("formato")
    tipo = tipo if tipo in T.TIPOS else "paper"
    motor = motor if motor in ("modelo", "marker") else "modelo"
    calidad = calidad if calidad in ("normal", "alta") else "normal"
    if motor == "modelo" and E.fase_actual()[0] not in E.MOTOR_PERMITIDO:
        return vuelve("apagado")
    with _CERROJO:
        if _TRABAJO.get("estado") == "en curso":
            return vuelve("ocupado")
        subidas = os.path.join(T._dir()[1], "_subidas")
        shutil.rmtree(subidas, ignore_errors=True)     # restos de un servidor que murio a media pasada
        carpeta = os.path.join(subidas, uuid.uuid4().hex)
        ruta, total, aviso = os.path.join(carpeta, nombre), 0, None
        try:
            os.makedirs(carpeta, exist_ok=True)
            with open(ruta, "wb") as f:
                while total <= MAX_SUBIDA:
                    trozo = fichero.file.read(1 << 20)
                    if not trozo:
                        break
                    total += len(trozo)
                    f.write(trozo)
            if total > MAX_SUBIDA:
                aviso = "grande"
            else:
                hojas = T.n_paginas(ruta)              # un fichero que no se abre: formato
                try:
                    if not T.rango(paginas.strip() or None, hojas):
                        aviso = "paginas"
                except ValueError:
                    aviso = "paginas"
        except Exception:
            aviso = "formato"
        if aviso:
            shutil.rmtree(carpeta, ignore_errors=True)
            return vuelve(aviso)
        _TRABAJO.clear()
        _TRABAJO.update(estado="en curso", origen=nombre, mensaje="empezando...", motor=motor)
        kw = dict(tipo=tipo, titulo=" ".join(titulo.split()) or None, paginas=paginas.strip() or None,
                  motor=motor, calidad=calidad)
        _HILO = threading.Thread(target=_transcribir_en_hilo, args=(ruta, kw), daemon=True)
        _HILO.start()
    return RedirectResponse("/transcripciones", status_code=303)


@app.get("/transcripciones/{nombre}", response_class=HTMLResponse)
def transcripcion(request: Request, nombre: str, aviso: str = ""):
    t = _transcripcion(nombre)
    _, hojas = T.paginas(t["cuerpo"])
    il, du = T.dudas(t["cuerpo"])
    return _pagina(request, "transcripcion.html", t=t, ilegibles=il, dudosos=du,
                   hojas=[dict(n=n, crudo=texto, html=render.transcripcion(texto), huella=_huella_texto(texto),
                               filas=min(40, max(8, texto.count("\n") + 3))) for n, texto in hojas],
                   avisos=[AVISOS_TRANSCRIBIR[aviso]] if aviso in AVISOS_TRANSCRIBIR else [])


@app.get("/transcripciones/{nombre}/pagina/{n}")
def transcripcion_original(nombre: str, n: int):
    """La pagina n del original (PDF o foto) como PNG, para revisar lado a lado."""
    t = _transcripcion(nombre)
    if not t.get("original"):
        raise HTTPException(404)
    try:
        if not 1 <= n <= T.n_paginas(t["original"]):
            raise HTTPException(404)
        png = T.pagina_png(t["original"], n, max_lado=1800)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(404)
    return Response(png, media_type="image/png")


@app.post("/transcripciones/{nombre}/pagina/{n}")
def transcripcion_guardar(nombre: str, n: int, texto: str = Form("")):
    _transcripcion(nombre)
    ok = T.guardar_pagina(nombre, n, texto)
    return RedirectResponse(f"/transcripciones/{nombre}?aviso={'guardada' if ok else 'nopagina'}#p{n}",
                            status_code=303)


@app.get("/transcripciones/{nombre}/tex")
def transcripcion_tex(nombre: str):
    """El .tex del texto tal como esta ahora, para descargar. Se genera al vuelo: no escribe nada."""
    from nucleo import a_latex as L
    t = _transcripcion(nombre)
    tex = L.documento(t["cuerpo"], nombre=t["nombre"], estado=t.get("estado", "sin_revisar"))
    return Response(tex.encode("utf-8"), media_type="application/x-tex; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{t["nombre"]}.tex"'})


def _huella_texto(texto):
    """Huella del texto de una pagina tal como lo devuelve un textarea (saltos normalizados)."""
    import hashlib
    limpio = (texto or "").replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    return hashlib.sha1(limpio.encode("utf-8")).hexdigest()[:16]


@app.post("/transcripciones/{nombre}/paginas")
async def transcripcion_guardar_cambios(request: Request, nombre: str):
    """Guarda de una vez todas las paginas cuyo texto ha cambiado en el navegador. Las que no se
    han tocado no se reescriben: asi no se pierde la correccion a medias de otra pagina ni se pisa
    lo que se haya editado entretanto en VS Code. Con accion=revisado (el boton "La he revisado"),
    despues de guardar marca la transcripcion: lo corregido sin guardar no se queda fuera."""
    _transcripcion(nombre)
    form = await request.form()
    vistas, guardadas = set(), 0
    for clave, valor in form.multi_items():
        m = re.fullmatch(r"texto_(\d{1,6})", clave)
        if not m or not isinstance(valor, str) or int(m.group(1)) in vistas:
            continue
        n = int(m.group(1))
        vistas.add(n)
        if _huella_texto(valor) != form.get(f"h_{n}"):
            guardadas += 1 if T.guardar_pagina(nombre, n, valor) else 0
    if form.get("accion") == "revisado":
        # el formulario puede ser de antes de que entrara otra pagina (la pasada seguia): no se da
        # por revisado lo que esa pagina no llego a ensenar
        en_disco = {n for n, _ in T.paginas(T.leer(nombre)["cuerpo"])[1]}
        if not en_disco <= vistas:
            return RedirectResponse(f"/transcripciones/{nombre}?aviso=nuevas", status_code=303)
        T.marcar_revisado(nombre)
        return RedirectResponse(f"/transcripciones/{nombre}?aviso=revisada", status_code=303)
    ancla = str(form.get("ancla", ""))
    return RedirectResponse(f"/transcripciones/{nombre}?aviso={'guardada' if guardadas else 'sincambios'}"
                            + (f"#p{ancla}" if ancla.isdigit() else ""), status_code=303)


@app.post("/transcripciones/{nombre}/revisado")
def transcripcion_revisada(nombre: str):
    _transcripcion(nombre)
    T.marcar_revisado(nombre)
    return RedirectResponse(f"/transcripciones/{nombre}?aviso=revisada", status_code=303)


# ----------------------------------------------------------------------
# arranque
# ----------------------------------------------------------------------

def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="python -m web",
                                 description="mini web local del sistema de doctorado (docs/WEB.md). "
                                             "Sin autenticacion propia: delante va Cloudflare Access.")
    ap.add_argument("--host", default=HOST_DEFECTO)
    ap.add_argument("--port", type=int, default=PUERTO_DEFECTO)
    a = ap.parse_args(argv)
    import uvicorn
    e = estado_breve()
    print(f"sistema de doctorado en http://{a.host}:{a.port}   ({e['nombre']}, motor {'ON' if e['motor'] else 'OFF'}"
          + (", SIMULACION" if C.SIMULAR else "") + ")")
    if a.host not in ("127.0.0.1", "localhost", "::1"):
        print("AVISO: escuchando fuera de localhost SIN autenticacion propia. Solo detras de Cloudflare Access (docs/WEB.md).")
    uvicorn.run(app, host=a.host, port=a.port, log_level="info")


if __name__ == "__main__":
    main()
