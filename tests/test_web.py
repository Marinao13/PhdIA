"""web/: la mini web sirve lo mismo que doc.py, con el motor simulado (conftest: DOC_SIMULAR=1) y sin red.
Nada escribe en el repo: llamadas, consultas, lagunas, notas y sesiones van a tmp_path."""
import os, re, json
import pytest
from fastapi.testclient import TestClient

from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import indice as I
import web.servidor as S
from web import render

FRAGS = [
    dict(id="t#0000", fuente="paper", doc="t", pagina=3, seccion="1", tipo="definicion", label="def",
         numero="1.1.2", texto="Let M be a strongly regular sequence. We define the associated function "
         "$h_M(t) = \\inf_j M_j t^j$ for $t > 0$.\n\\begin{equation}\\label{eq:h} h_M(t) \\le 1 \\end{equation}"),
    dict(id="t#0001", fuente="paper", doc="t", pagina=7, seccion="2", tipo="lema", label="lem",
         numero="2.1.1", texto="Lemma. Let N be a strongly regular sequence and let g be the logarithm of "
         "h_N restricted to the real axis. Then the Poisson integral of g converges absolutely."),
]


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "F_LLAMADAS", str(tmp_path / "llamadas.jsonl"))
    monkeypatch.setattr(C, "DIR_CONSULTAS", str(tmp_path / "consultas"))
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)
    monkeypatch.setattr(E, "commits_todos", lambda: [])
    return TestClient(S.app)


def _fase(monkeypatch, fase):
    monkeypatch.setattr(E, "fase_actual", lambda: (fase, E._marcas_vacias()))


def _consultas(tmp_path):
    d = tmp_path / "consultas"
    return sorted(os.listdir(d)) if d.exists() else []


# ----------------------------------------------------------------------
# panel
# ----------------------------------------------------------------------

def test_panel_muestra_la_fase_y_lo_que_toca(cliente, monkeypatch):
    _fase(monkeypatch, "libre")
    r = cliente.get("/")
    assert r.status_code == 200
    assert "libre" in r.text and "Te toca ahora" in r.text and "motor ON" in r.text
    _fase(monkeypatch, "f3")
    r = cliente.get("/")
    assert r.status_code == 200 and "fase 3" in r.text and "motor OFF" in r.text


# ----------------------------------------------------------------------
# buscar: sin modelo, en toda fase
# ----------------------------------------------------------------------

def test_buscar_con_indice_vacio_no_explota(cliente, monkeypatch):
    monkeypatch.setattr(I, "buscar", lambda *a, **k: [])
    r = cliente.get("/buscar", params=dict(q="sucesion fuertemente regular"))
    assert r.status_code == 200 and "indice vacio" in r.text

    def rompe(*a, **k):
        raise RuntimeError("sin indice")
    monkeypatch.setattr(I, "buscar", rompe)
    r = cliente.get("/buscar", params=dict(q="x"))
    assert r.status_code == 200 and "indice no disponible" in r.text


def test_buscar_muestra_la_cita_y_el_texto_preparado_para_katex(cliente, monkeypatch):
    llamadas = []
    monkeypatch.setattr(I, "buscar", lambda q, **k: llamadas.append((q, k)) or [dict(f) for f in FRAGS])
    r = cliente.get("/buscar", params=dict(q="Poisson integral", doc="t", k="2"))
    assert r.status_code == 200
    assert llamadas[0][0] == "Poisson integral" and llamadas[0][1]["doc"] == "t" and llamadas[0][1]["k"] == 2
    assert "[t:p7, Lema 2.1.1]" in r.text and "[t:p3, Definicion 1.1.2]" in r.text
    assert "Poisson integral of g converges" in r.text
    # \begin{equation} pasa a \[ \] y pierde el \label: KaTeX no los conoce
    assert "\\[" in r.text and "\\begin{equation}" not in r.text.split("texto crudo")[0] and "\\label" not in r.text.split("texto crudo")[0]
    assert "GET" not in r.text and r.status_code == 200


def test_buscar_sin_pregunta_es_el_formulario(cliente):
    r = cliente.get("/buscar")
    assert r.status_code == 200 and 'name="q"' in r.text


# ----------------------------------------------------------------------
# ask: el comando entero, capturado; respeta la fase
# ----------------------------------------------------------------------

def test_ask_con_motor_simulado_devuelve_la_respuesta(cliente, monkeypatch, tmp_path):
    _fase(monkeypatch, "libre")
    monkeypatch.setattr(I, "buscar", lambda *a, **k: [dict(f) for f in FRAGS])
    monkeypatch.setattr(I, "seguir_refs", lambda frags, maximo=4: [])
    r = cliente.post("/ask", data=dict(pregunta="que es h_M", k="4"))
    assert r.status_code == 200
    assert "[SIMULADO]" in r.text and "MOTOR APAGADO" not in r.text
    assert len(_consultas(tmp_path)) == 1                       # la consulta queda registrada como en consola
    guardada = json.loads((tmp_path / "consultas" / _consultas(tmp_path)[0]).read_text(encoding="utf-8"))
    assert guardada["pregunta"] == "que es h_M" and guardada["k"] == 4
    assert (tmp_path / "llamadas.jsonl").exists()


def test_ask_con_motor_apagado_avisa_y_enlaza_a_buscar(cliente, monkeypatch, tmp_path):
    _fase(monkeypatch, "f1")
    monkeypatch.setattr(I, "buscar", lambda *a, **k: [dict(f) for f in FRAGS])
    r = cliente.post("/ask", data=dict(pregunta="que es h_M"))
    assert r.status_code == 200
    assert "MOTOR APAGADO" in r.text and "[SIMULADO]" not in r.text and 'href="/buscar' in r.text
    assert _consultas(tmp_path) == [] and not (tmp_path / "llamadas.jsonl").exists()
    r = cliente.get("/ask")
    assert r.status_code == 200 and "MOTOR APAGADO" in r.text


# ----------------------------------------------------------------------
# preguntar: hilo en memoria, turno como el REPL
# ----------------------------------------------------------------------

def _hilo(texto):
    return re.search(r'name="hilo" value="([0-9a-f]+)"', texto).group(1)


def test_preguntar_un_turno_simulado_queda_en_el_hilo_y_en_el_registro(cliente, monkeypatch, tmp_path):
    _fase(monkeypatch, "libre")
    r = cliente.get("/preguntar")
    assert r.status_code == 200
    hid = _hilo(r.text)
    r = cliente.post("/preguntar", data=dict(hilo=hid, doc="", pregunta="que significa $h_M$", fragmento="",
                                             plantilla="notacion"))
    assert r.status_code == 200 and _hilo(r.text) == hid
    assert "[SIMULADO]" in r.text and "/notacion" in r.text
    lineas = (tmp_path / "consultas" / f"{K.HOY}-preguntar.jsonl").read_text(encoding="utf-8").splitlines()
    reg = json.loads(lineas[-1])
    assert reg["pregunta"] == "que significa $h_M$" and reg["turno"] == 1 and reg["fase"] == "libre"
    assert reg["plantilla"].startswith("Uso (a)")
    # un fragmento pegado sin pregunta -> "Desarrolla este fragmento..." como con Enter en el REPL
    r = cliente.post("/preguntar", data=dict(hilo=hid, doc="", pregunta="", fragmento="Let M be a sequence\nwith h_M"))
    assert "Desarrolla este fragmento" in r.text and r.text.count("[SIMULADO]") == 2
    # nuevo hilo: otro id, vacio
    r = cliente.post("/preguntar", data=dict(hilo=hid, accion="nuevo"))
    assert _hilo(r.text) != hid and "[SIMULADO]" not in r.text


def test_preguntar_con_motor_apagado_no_llama(cliente, monkeypatch, tmp_path):
    _fase(monkeypatch, "f3")
    r = cliente.get("/preguntar")
    assert r.status_code == 200 and "MOTOR APAGADO" in r.text
    r = cliente.post("/preguntar", data=dict(hilo=_hilo(r.text), doc="", pregunta="hola"))
    assert r.status_code == 200 and "MOTOR APAGADO" in r.text and "[SIMULADO]" not in r.text
    assert _consultas(tmp_path) == [] and not (tmp_path / "llamadas.jsonl").exists()


def test_preguntar_laguna_escribe_una_linea(cliente, monkeypatch, tmp_path):
    _fase(monkeypatch, "f2")
    f = tmp_path / "lagunas.md"
    f.write_text("# Lagunas\n\n## Pendientes\n\n## Resueltas\n", encoding="utf-8")
    monkeypatch.setattr(C, "F_LAGUNAS", str(f))
    hid = _hilo(cliente.get("/preguntar").text)
    r = cliente.post("/preguntar/laguna", data=dict(hilo=hid, laguna="Phragmen-Lindelof en un sector"))
    assert r.status_code == 200 and "laguna anotada" in r.text
    t = f.read_text(encoding="utf-8")
    assert "- [ ] " in t and "| preguntar | f2 | Phragmen-Lindelof en un sector" in t


# ----------------------------------------------------------------------
# notas, sesiones, guia, lagunas
# ----------------------------------------------------------------------

NOTA = ("---\nid: x-2020\ntitulo: Prueba\n---\n\n# Nota de lectura: x-2020\n\n## Mapa\n- R1 — Lema 2.1.1\n\n"
        "## R1 — Lema 2.1.1\n\n### Enunciado\nSea $M_p$ con *hipotesis* y \\(h_M\\).\n\n## Sintesis\nTres frases.\n")


def test_notas_lista_sin_plantillas_y_bloques_r_plegables(cliente, monkeypatch, tmp_path):
    d = tmp_path / "lecturas"
    d.mkdir()
    (d / "PLANTILLA.md").write_text("# plantilla\n", encoding="utf-8")
    (d / "PLANTILLA-resultado.md").write_text("# plantilla\n", encoding="utf-8")
    (d / "x-2020.md").write_text(NOTA, encoding="utf-8")
    monkeypatch.setattr(C, "DIR_LECTURAS", str(d))
    r = cliente.get("/notas")
    assert r.status_code == 200 and "x-2020" in r.text and "PLANTILLA" not in r.text and "1 bloque R" in r.text
    r = cliente.get("/notas/x-2020")
    assert r.status_code == 200
    assert '<details class="bloque" id="R1"' in r.text and "Lema 2.1.1" in r.text
    assert "$M_p$" in r.text and "<em>hipotesis</em>" in r.text and "\\(h_M\\)" in r.text
    assert "<dt>titulo</dt><dd>Prueba</dd>" in r.text                 # frontmatter como tabla
    assert cliente.get("/notas/PLANTILLA").status_code == 404
    assert cliente.get("/notas/no-existe").status_code == 404
    assert cliente.get("/notas/..%2Fx-2020").status_code == 404


def test_sesiones_solo_lectura(cliente, monkeypatch, tmp_path):
    d = tmp_path / "sesiones"
    d.mkdir()
    (d / "PLANTILLA.md").write_text("# plantilla\n", encoding="utf-8")
    (d / "2026-10-07-x-2020-section-2.md").write_text(
        "---\nfecha: 2026-10-07\npaper: x-2020-section-2\n---\n\n## Fase 1 - Intento a ciegas\nTexto con $M_p$.\n",
        encoding="utf-8")
    monkeypatch.setattr(C, "DIR_SESIONES", str(d))
    r = cliente.get("/sesiones")
    assert r.status_code == 200 and "2026-10-07-x-2020-section-2" in r.text and "PLANTILLA" not in r.text
    r = cliente.get("/sesiones/2026-10-07-x-2020-section-2")
    assert r.status_code == 200 and "Fase 1 - Intento a ciegas" in r.text and "$M_p$" in r.text


def test_guia_sirve_uso_md_con_indice(cliente):
    r = cliente.get("/guia")
    assert r.status_code == 200 and "Uso en una pagina" in r.text
    assert 'id="uso-' in r.text and 'href="#uso-' in r.text         # cabeceras con id y enlaces del indice


def test_lagunas_anade_una_linea_al_fichero(cliente, monkeypatch, tmp_path):
    _fase(monkeypatch, "f2")
    f = tmp_path / "lagunas.md"
    f.write_text("# Lagunas\n\n## Pendientes\n\n- [ ] 2026-09-01 | diagnostico | - | vieja\n\n## Resueltas\n",
                 encoding="utf-8")
    monkeypatch.setattr(C, "F_LAGUNAS", str(f))
    r = cliente.get("/lagunas")
    assert r.status_code == 200 and "vieja" in r.text and "1 pendientes" in r.text
    r = cliente.post("/lagunas", data=dict(texto="Transformada de Borel formal: definicion exacta"))
    assert r.status_code == 200 and "laguna anotada" in r.text
    t = f.read_text(encoding="utf-8")
    nuevas = [l for l in t.splitlines() if "Borel formal" in l]
    assert len(nuevas) == 1 and nuevas[0].startswith("- [ ] ") and "| web | f2 |" in nuevas[0]
    assert t.index("Borel formal") < t.index("vieja")
    r = cliente.post("/lagunas", data=dict(texto="   "))
    assert r.status_code == 200 and "Borel formal" in r.text and t.count("- [ ]") == 2


def test_post_desde_otro_origen_se_rechaza(cliente, monkeypatch, tmp_path):
    f = tmp_path / "lagunas.md"
    f.write_text("# Lagunas\n", encoding="utf-8")
    monkeypatch.setattr(C, "F_LAGUNAS", str(f))
    r = cliente.post("/lagunas", data=dict(texto="x"), headers={"Origin": "https://otro.example"})
    assert r.status_code == 403 and "x" not in f.read_text(encoding="utf-8")
    r = cliente.post("/lagunas", data=dict(texto="x"), headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403


# ----------------------------------------------------------------------
# render: las formulas no pasan por markdown
# ----------------------------------------------------------------------

def test_markdown_protege_las_formulas():
    h = render.markdown("Sea $M_p$ y $M_q^*$ con *enfasis* y \\(a_1\\), ademas $$\\sum_{p} M_p$$ y \\[x_1 < y\\].")
    assert "$M_p$" in h and "$M_q^*$" in h and "<em>enfasis</em>" in h and "\\(a_1\\)" in h
    assert "$$\\sum_{p} M_p$$" in h and "\\[x_1 &lt; y\\]" in h and "<em>" not in h.split("$M_q^*$")[0].split("$M_p$")[1]
    # una formula sola en su linea sale en modo display
    assert "$$h_M(t) = \\inf_j M_j t^j$$" in render.respuesta("Entonces\n\n$h_M(t) = \\inf_j M_j t^j$\n\ny sigue.")
    # entornos de la capa tex
    assert render.latex_para_web("\\begin{align}a&=b\\label{x}\\end{align}") == "\\[\\begin{aligned}a&=b\\end{aligned}\\]"


def test_documento_parte_por_secciones_y_marca_los_r():
    d = render.documento(NOTA)
    assert d["front"]["id"] == "x-2020"
    assert [(b["titulo"], b["rid"]) for b in d["bloques"]][1:] == [("Mapa", None), ("R1 — Lema 2.1.1", "R1"), ("Sintesis", None)]
