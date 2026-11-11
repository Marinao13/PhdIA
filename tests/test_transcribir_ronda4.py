"""`transcribir`: lo que saco la cuarta revision del 2026-11-11 en el camino de escritura, el indice y la web."""
import os
import time
import pytest
from fastapi.testclient import TestClient

from nucleo import transcribir as T
from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M
from nucleo import indice as I
from nucleo import corpus as Q
import web.servidor as S


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(C, "F_LLAMADAS", str(tmp_path / "llamadas.jsonl"))
    monkeypatch.setattr(C, "SIMULAR", True)
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)
    monkeypatch.setattr(E, "commits_todos", lambda: [])
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", E._marcas_vacias()))
    monkeypatch.setattr(K, "_abrir", lambda ruta: None)
    return tmp_path


def _pdf(ruta, paginas=3):
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}")
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


def _durante(monkeypatch, acciones):
    """M._completar que, antes de responder a la llamada k, ejecuta acciones[k]() (k desde 1)."""
    real, n = M._completar, []

    def completar(*a, **k):
        n.append(1)
        if len(n) in acciones:
            acciones[len(n)]()
        return real(*a, **k)

    monkeypatch.setattr(M, "_completar", completar)


def _unico_md(repo, trozo=""):
    (f,) = [x for x in os.listdir(repo / "transcripciones") if x.endswith(".md") and trozo in x]
    return str(repo / "transcripciones" / f)


def _escribe(ruta, texto):
    open(ruta, "w", encoding="utf-8", newline="\n").write(texto)


# ----------------------------------------------------------------------
# el fichero editado a mano durante la pasada no se rehace desde cero
# ----------------------------------------------------------------------

def test_sin_la_linea_estado_o_sin_cabecera_no_se_pierde_lo_escrito(repo, monkeypatch):
    def quita_estado_y_corrige():
        f = _unico_md(repo)
        t = open(f, encoding="utf-8").read().replace("estado: sin_revisar\n", "")
        _escribe(f, t.replace("## Apuntes (simulado)", "## CORREGIDO A MANO EN VSCODE", 1))

    def lo_cambia_por_sus_notas():
        _escribe(_unico_md(repo, "tema-2"), "# Mis notas\n\nAlgo mio que no es una transcripcion.\n")

    real = M._completar
    _durante(monkeypatch, {2: quita_estado_y_corrige})
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    t = T.leer(r["nombre"])
    assert t["estado"] == "sin_revisar" and t["paginas"] == "1,2,3"
    assert "CORREGIDO A MANO EN VSCODE" in dict(T.paginas(t["cuerpo"])[1])[1]

    monkeypatch.setattr(M, "_completar", real)            # otra pasada, con su propia cuenta de llamadas
    _durante(monkeypatch, {3: lo_cambia_por_sus_notas})
    r = T.transcribir(_pdf(repo / "b.pdf"), titulo="Tema 2")
    assert r["fallo"] is None and r["paginas"] == [1, 2, 3]
    t = T.leer(r["nombre"])
    assert "Algo mio que no es una transcripcion." in t["cuerpo"] and t["estado"] == "sin_revisar"
    assert t["paginas"] == "3" and [n for n, _ in T.paginas(t["cuerpo"])[1]] == [3]     # lo que hay de verdad


def test_si_borran_la_linea_paginas_se_recuenta_por_las_marcas(repo, monkeypatch):
    def borra_paginas():
        f = _unico_md(repo)
        _escribe(f, open(f, encoding="utf-8").read().replace("paginas: 1,2\n", ""))

    _durante(monkeypatch, {3: borra_paginas})
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    assert T.leer(r["nombre"])["paginas"] == "1,2,3"


def test_borrado_a_media_pasada_y_sin_mas_paginas_no_deja_un_fantasma(repo, monkeypatch):
    def borra_y_corta():
        os.remove(_unico_md(repo))
        raise KeyboardInterrupt

    _durante(monkeypatch, {3: borra_y_corta})
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    assert r["paginas"] == [1, 2] and r["pendientes"] == [3] and "interrumpido" in r["fallo"]
    t = T.leer(r["nombre"])                               # un fichero valido, con lo hecho
    assert t and t["paginas"] == "1,2" and [n for n, _ in T.paginas(t["cuerpo"])[1]] == [1, 2]
    assert (r["ilegibles"], r["dudosos"]) == (2, 2) and r["tex_estado"] == "escrito"


# ----------------------------------------------------------------------
# la reserva del nombre no se queda para siempre
# ----------------------------------------------------------------------

def test_una_reserva_vieja_de_un_proceso_muerto_se_reutiliza(repo):
    d = repo / "transcripciones"
    d.mkdir()
    import datetime
    nombre = datetime.date.today().isoformat() + "-tema-1"
    (d / (nombre + ".md")).write_text("", encoding="utf-8")
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=1), titulo="Tema 1")
    assert r["nombre"] == nombre + "-2"                   # reciente: puede ser de otra pasada en marcha
    viejo = time.time() - T.RESERVA_CADUCA - 60
    os.utime(d / (nombre + ".md"), (viejo, viejo))
    r = T.transcribir(_pdf(repo / "b.pdf", paginas=1), titulo="Tema 1")
    assert r["nombre"] == nombre and T.leer(nombre)["origen"] == "b.pdf"


def test_ctrl_c_copiando_el_original_no_deja_la_reserva(repo, monkeypatch):
    def cortan(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(T, "_guardar_original", cortan)
    with pytest.raises(KeyboardInterrupt):
        T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    assert [f for f in os.listdir(repo / "transcripciones") if f.endswith(".md")] == []


# ----------------------------------------------------------------------
# indice: paginas que son solo formulas de una letra
# ----------------------------------------------------------------------

def test_buscar_no_divide_por_cero_con_paginas_sin_palabras(repo, monkeypatch):
    monkeypatch.setattr(C, "DIR_INDICE", str(repo / "indice"))
    monkeypatch.setattr(I, "F_DB", str(repo / "indice" / "fragmentos.sqlite"))
    monkeypatch.setattr(I, "F_VEC", str(repo / "indice" / "vectores.npy"))
    monkeypatch.setattr(I, "F_VEC_IDS", str(repo / "indice" / "vectores_ids.json"))
    monkeypatch.setattr(C, "DIR_TEXT", str(repo / "text"))
    monkeypatch.setattr(C, "F_PROYECTO", str(repo / "PROYECTO.md"))
    monkeypatch.setattr(C, "DIR_LECTURAS", str(repo / "lecturas"))
    monkeypatch.setattr(C, "DIR_SESIONES", str(repo / "sesiones"))
    monkeypatch.setattr(Q, "leer_bib", lambda: {})
    textos = iter(["$x^2 + y^2 = z^2$", "$a + b = c$"])
    monkeypatch.setattr(M, "_completar", lambda *a, **k: (next(textos), 100, 50, 0, {}))
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=2), tipo="curso", titulo="Formulas")
    T.marcar_revisado(r["nombre"])
    assert I.indexar(verbose=False)[0] == 0               # sin ninguna palabra que buscar, no entran
    assert I.buscar("pitagoras", fuente="curso", solo_bm25=True) == []
    # y si algo asi ya estuviera en el indice, buscar no revienta
    monkeypatch.setattr(I, "_cargar", lambda fuente=None, doc=None: [
        dict(id="x#0", fuente="curso", doc="x", pagina=1, seccion=None, tipo="parrafo", label=None,
             texto="$x^2 + y^2 = z^2$", numero=None)])
    assert I.buscar("pitagoras", solo_bm25=True) == []


# ----------------------------------------------------------------------
# web: "La he revisado" con un formulario de antes de que entrara otra pagina
# ----------------------------------------------------------------------

def test_no_se_marca_revisada_si_han_entrado_paginas_que_el_formulario_no_enseno(repo):
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=3), titulo="Tema 1")
    hojas = dict(T.paginas(T.leer(r["nombre"])["cuerpo"])[1])
    cliente = TestClient(S.app)
    viejo = {"accion": "revisado",                         # el formulario se abrio cuando solo habia dos paginas
             "h_1": S._huella_texto(hojas[1]), "texto_1": "Pagina 1 corregida.",
             "h_2": S._huella_texto(hojas[2]), "texto_2": hojas[2]}
    resp = cliente.post(f"/transcripciones/{r['nombre']}/paginas", data=viejo, follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"].endswith("aviso=nuevas")
    t = T.leer(r["nombre"])
    assert t["estado"] == "sin_revisar" and dict(T.paginas(t["cuerpo"])[1])[1] == "Pagina 1 corregida."
    assert "no la he marcado" in cliente.get(f"/transcripciones/{r['nombre']}?aviso=nuevas").text
    completo = dict(viejo, h_1=S._huella_texto("Pagina 1 corregida."), h_3=S._huella_texto(hojas[3]), texto_3=hojas[3])
    resp = cliente.post(f"/transcripciones/{r['nombre']}/paginas", data=completo, follow_redirects=False)
    assert resp.headers["location"].endswith("aviso=revisada") and T.leer(r["nombre"])["estado"] == "revisado"
