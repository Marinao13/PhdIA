"""
Mini web local del sistema de doctorado (docs/WEB.md).

    python -m web [--host 127.0.0.1] [--port 8765]
    python web/servidor.py

Sin autenticacion propia: delante va Cloudflare Access. Escucha solo en localhost por defecto.
Cada pagina llama a funciones que ya existen en nucleo/; el motor pasa por nucleo.motor.llamar
y por tanto respeta las fases (apagado en fase 1 y 3).
"""
import os, sys, re, glob, types, argparse, datetime
from urllib.parse import urlparse

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M
from nucleo import indice as I
from nucleo import corpus as Q
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
       ("/notas", "Notas"), ("/sesiones", "Sesiones"), ("/lagunas", "Lagunas"), ("/guia", "Guia")]
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
        if origen and urlparse(origen).netloc.lower() != host.lower():
            return PlainTextResponse("peticion de otro origen", status_code=403)
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "no-referrer"
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
                          doc=f.get("doc"), texto=render.latex_para_web(f.get("texto", "")), crudo=f.get("texto", "")))
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
