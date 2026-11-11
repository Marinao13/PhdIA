"""`transcribir`: lo que saco la tercera revision del 2026-11-11. Corregir mientras la pasada sigue,
dos pasadas a la vez, andamiaje con el id de la nota, paginas cortas en el indice, y "La he revisado"
con correcciones sin guardar."""
import os
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


# ----------------------------------------------------------------------
# corregir (o marcar) mientras la pasada sigue no se pierde ni cuela paginas sin mirar
# ----------------------------------------------------------------------

def test_lo_corregido_durante_la_pasada_no_se_pisa(repo, monkeypatch):
    def corrige_la_1():
        nombre = T.listar()[0]["nombre"]                  # la pagina 1 ya esta en disco y es editable
        assert T.guardar_pagina(nombre, 1, "CORREGIDA A MANO: sea $M=(M_p)$")

    def edita_en_vscode_y_marca():
        t = T.listar()[0]
        texto = open(t["ruta"], encoding="utf-8").read().replace("estado: sin_revisar", "profesor: J. Sanz\nestado: sin_revisar")
        open(t["ruta"], "w", encoding="utf-8", newline="\n").write(texto)
        assert T.marcar_revisado(t["nombre"])             # prematuro: aun falta la pagina 3

    _durante(monkeypatch, {2: corrige_la_1, 3: edita_en_vscode_y_marca})
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    t = T.leer(r["nombre"])
    hojas = dict(T.paginas(t["cuerpo"])[1])
    assert hojas[1] == "CORREGIDA A MANO: sea $M=(M_p)$" and sorted(hojas) == [1, 2, 3]
    assert t["estado"] == "sin_revisar" and "revisado_el" not in t        # entro una pagina sin mirar
    assert t["paginas"] == "1,2,3" and t["profesor"] == "J. Sanz" and r["paginas"] == [1, 2, 3]
    assert (r["ilegibles"], r["dudosos"]) == (2, 2)       # las de las paginas 2 y 3; la 1 la corrigio el


def test_si_borran_el_md_a_media_pasada_se_rehace_con_lo_hecho(repo, monkeypatch):
    _durante(monkeypatch, {3: lambda: os.remove(T.listar()[0]["ruta"])})
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    assert [n for n, _ in T.paginas(T.leer(r["nombre"])["cuerpo"])[1]] == [1, 2, 3]
    assert T.leer(r["nombre"])["paginas"] == "1,2,3"


def test_dos_pasadas_a_la_vez_con_el_mismo_titulo_no_comparten_fichero(repo, monkeypatch):
    dentro = {}

    def lanza_otra():
        if "r" not in dentro:
            dentro["r"] = None                             # evita la recursion sin fin
            dentro["r"] = T.transcribir(_pdf(repo / "b.pdf", paginas=1), titulo="Apuntes")

    _durante(monkeypatch, {1: lanza_otra})                 # la segunda empieza antes de la primera pagina de la primera
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=2), titulo="Apuntes")
    otra = dentro["r"]
    assert r["nombre"] != otra["nombre"] and otra["nombre"] == r["nombre"] + "-2"
    assert T.leer(r["nombre"])["origen"] == "a.pdf" and T.leer(r["nombre"])["paginas"] == "1,2"
    assert T.leer(otra["nombre"])["origen"] == "b.pdf" and T.leer(otra["nombre"])["paginas"] == "1"
    assert os.path.exists(T.leer(r["nombre"])["original"]) and os.path.exists(T.leer(otra["nombre"])["original"])
    assert len(T.listar()) == 2


def test_si_no_sale_ninguna_pagina_no_queda_ni_la_reserva(repo, monkeypatch):
    monkeypatch.setattr(E, "fase_actual", lambda: ("f3", E._marcas_vacias()))
    with pytest.raises(M.MotorApagado):
        T.transcribir(_pdf(repo / "a.pdf"))
    d = repo / "transcripciones"
    assert [f for f in os.listdir(d) if f != "originales"] == [] and os.listdir(d / "originales") == []
    # y el nombre queda libre para el siguiente intento
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", E._marcas_vacias()))
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=1))
    assert not r["nombre"].endswith("-2")


# ----------------------------------------------------------------------
# indice
# ----------------------------------------------------------------------

def test_el_andamiaje_con_el_id_de_la_nota_tampoco_se_indexa(tmp_path, monkeypatch):
    lecturas, sesiones = tmp_path / "lecturas", tmp_path / "sesiones"
    lecturas.mkdir(); sesiones.mkdir()
    plantilla = ("# Nota de lectura: ID\n\n"
                 "La redaccion es tuya. El sistema no rellena nada de aqui. Un bloque `## R<n>` por\n"
                 "resultado (`python doc.py nota add ID \"R2 — Teorema 2.3\"`), con los ocho campos de\n"
                 "`lecturas/PLANTILLA-resultado.md`; `nota quiz ID --resultado R2` te interroga sobre ese\n"
                 "resultado y `nota check ID --resultado R2` busca agujeros en su `### Reconstruccion`.\n"
                 "Las secciones de paper van una sola vez, al final. Cita siempre con pagina: [ID:pNN].\n\n"
                 "## Dudas\n")
    (lecturas / "PLANTILLA.md").write_text(plantilla, encoding="utf-8")
    (lecturas / "thilliez-2003.md").write_text(
        plantilla.replace("ID", "thilliez-2003") + "- Que era un limite inductivo?\n", encoding="utf-8")
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(C, "DIR_LECTURAS", str(lecturas))
    monkeypatch.setattr(C, "DIR_SESIONES", str(sesiones))
    monkeypatch.setattr(C, "DIR_TEXT", str(tmp_path / "text"))
    monkeypatch.setattr(C, "F_PROYECTO", str(tmp_path / "PROYECTO.md"))
    monkeypatch.setattr(Q, "leer_bib", lambda: {})
    (fuente, doc, us), = I.fuentes()
    assert doc == "nota:thilliez-2003"
    assert [u["texto"] for u in us if u["tipo"] == "parrafo"] == ["- Que era un limite inductivo?"]


def test_una_pagina_corta_tambien_entra_en_el_indice(repo, monkeypatch):
    monkeypatch.setattr(C, "DIR_INDICE", str(repo / "indice"))
    monkeypatch.setattr(I, "F_DB", str(repo / "indice" / "fragmentos.sqlite"))
    monkeypatch.setattr(I, "F_VEC", str(repo / "indice" / "vectores.npy"))
    monkeypatch.setattr(I, "F_VEC_IDS", str(repo / "indice" / "vectores_ids.json"))
    monkeypatch.setattr(C, "DIR_TEXT", str(repo / "text"))
    monkeypatch.setattr(C, "F_PROYECTO", str(repo / "PROYECTO.md"))
    monkeypatch.setattr(C, "DIR_LECTURAS", str(repo / "lecturas"))
    monkeypatch.setattr(C, "DIR_SESIONES", str(repo / "sesiones"))
    monkeypatch.setattr(Q, "leer_bib", lambda: {})
    textos = iter([" ".join("Sea M una sucesion peso fuertemente regular con indice gamma(M) positivo." for _ in range(8)),
                   "Corolario: $(\\gamma_1)$ implica (snq).",
                   " ".join("La funcion plana se construye con el nucleo de Poisson en el sector." for _ in range(8))])
    monkeypatch.setattr(M, "_completar", lambda *a, **k: (next(textos), 100, 200, 0, {}))
    r = T.transcribir(_pdf(repo / "a.pdf"), tipo="curso", titulo="Apuntes")
    T.marcar_revisado(r["nombre"])
    assert I.indexar(verbose=False)[0] == 3
    corta = I.por_pagina("transcripcion:" + r["nombre"], 2)
    assert len(corta) == 1 and "implica (snq)" in corta[0]["texto"]
    # el filtro de ruido sigue valiendo para lo demas (una pagina escaneada sin OCR)
    assert "corto_ok" not in I.fragmentar([dict(pagina=1, seccion=None, tipo="parrafo", label=None, texto="x y z")])[0]


# ----------------------------------------------------------------------
# web: "La he revisado" con correcciones sin guardar
# ----------------------------------------------------------------------

def test_la_he_revisado_guarda_antes_lo_corregido_sin_guardar(repo):
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=2), titulo="Tema 1")
    hojas = dict(T.paginas(T.leer(r["nombre"])["cuerpo"])[1])
    cliente = TestClient(S.app)
    resp = cliente.post(f"/transcripciones/{r['nombre']}/paginas", follow_redirects=False, data={
        "accion": "revisado",
        "h_1": S._huella_texto(hojas[1]), "texto_1": "Pagina 1 corregida y sin guardar.",
        "h_2": S._huella_texto(hojas[2]), "texto_2": hojas[2]})
    assert resp.status_code == 303 and resp.headers["location"].endswith("aviso=revisada")
    t = T.leer(r["nombre"])
    assert t["estado"] == "revisado" and dict(T.paginas(t["cuerpo"])[1])[1] == "Pagina 1 corregida y sin guardar."
    assert "Pagina 1 corregida y sin guardar." in open(r["tex"], encoding="utf-8").read()     # y el .tex, al dia
