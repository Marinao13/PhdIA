"""preguntar v2: paper de la sesion, pegados localizados en el indice, historial sin bloques viejos."""
import pytest

from nucleo import comandos as K
from nucleo import corpus as Q
from nucleo import estado as E
from nucleo import indice as I

BIB = {"thilliez-2003": {"fuente": "paper"}, "jimenez-garrido-sanz-schindl-2019-injectivity": {"fuente": "paper"},
       "jimenez-garrido-sanz-schindl-2019-sectorial": {"fuente": "paper"}, "proyecto": {"fuente": "proyecto"}}


@pytest.fixture(autouse=True)
def bib_falsa(monkeypatch):
    monkeypatch.setattr(Q, "leer_bib", lambda: BIB)


def test_doc_de_sesion_es_el_prefijo_mas_largo_de_la_etiqueta():
    assert K._doc_de_sesion("thilliez-2003-section-2") == "thilliez-2003"
    assert K._doc_de_sesion("thilliez-2003") == "thilliez-2003"
    assert K._doc_de_sesion("jimenez-garrido-sanz-schindl-2019-sectorial-prueba") == \
        "jimenez-garrido-sanz-schindl-2019-sectorial"
    assert K._doc_de_sesion("base-conway-iv") is None
    assert K._doc_de_sesion("proyecto-x") is None
    assert K._doc_de_sesion("thilliez-20031") is None          # el prefijo acaba en guion o en el id


def test_doc_de_sesion_lee_la_sesion_abierta(monkeypatch, tmp_path):
    f = tmp_path / "2026-10-07-thilliez-2003-section-2.md"
    f.write_text("x", encoding="utf-8")
    monkeypatch.setattr(E, "sesion_hoy", lambda: str(f))
    assert K._doc_de_sesion() == "thilliez-2003"
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)
    assert K._doc_de_sesion() is None


def test_fragmento_de_pegado_quita_el_comando_tecleado_antes_de_pegar():
    frag, cmd = K._fragmento_de_pegado(["/pegar Let N be a strongly regular", "sequence. Then"])
    assert frag == "Let N be a strongly regular\nsequence. Then" and cmd == "/pegar"
    frag, cmd = K._fragmento_de_pegado(["/paso", "linea 1", "linea 2"])
    assert frag == "linea 1\nlinea 2" and cmd == "/paso"
    frag, cmd = K._fragmento_de_pegado(["linea 1", "linea 2"])
    assert frag == "linea 1\nlinea 2" and cmd is None
    frag, cmd = K._fragmento_de_pegado(["/pegar", "linea 1", "linea 2", "."])     # el punto de /pegar
    assert frag == "linea 1\nlinea 2" and cmd == "/pegar"


def test_mensajes_ignoran_las_claves_extra_de_los_turnos():
    turnos = [dict(role="user", content="p1", bloque="B1", frags=[{"id": "x"}]), dict(role="assistant", content="r1")]
    assert K._mensajes(turnos) == [{"role": "user", "content": "p1\n\nB1"}, {"role": "assistant", "content": "r1"}]


def test_recuperar_tras_ver_y_enter_usa_el_texto_visto_sin_embeddings(monkeypatch):
    llamadas = []
    monkeypatch.setattr(I, "buscar", lambda consulta, **k: llamadas.append((consulta, k.get("solo_bm25"))) or [])
    monkeypatch.setattr(I, "seguir_refs", lambda frags, maximo=4: [])
    visto = dict(FRAGS[1], via_ver=True)
    K._recuperar("t", "Desarrolla este fragmento paso a paso, con todos los pasos intermedios (regla FUENTES).", "", [visto])
    assert llamadas and llamadas[0][0].startswith("Lemma. Let N be") and llamadas[0][1] is True
    assert "(traido con /ver)" in K._bloque_corpus([visto])


FRAGS = [
    dict(id="t#0000", fuente="paper", doc="t", pagina=3, seccion="1", tipo="definicion", label="def",
         numero="1.1.2", texto="Let M be a strongly regular sequence. We define the associated function "
         "h_M(t) = inf_j M_j t^j for t > 0 and the class of ultraholomorphic functions in a sector."),
    dict(id="t#0001", fuente="paper", doc="t", pagina=7, seccion="2", tipo="lema", label="lem",
         numero="2.1.1", texto="Lemma. Let N be a strongly regular sequence and let g be the logarithm of "
         "h_N restricted to the real axis. Then the Poisson integral of g converges absolutely."),
    dict(id="t#0002", fuente="paper", doc="t", pagina=8, seccion="2", tipo="demostracion", label=None,
         numero=None, texto="Proof. Since h_N is bounded by one, g is nonpositive, so the integral of g "
         "against the Poisson kernel is finite by the previous lemma; holomorphy follows from dominated "
         "convergence applied to the integrand."),
]


def test_localizar_encuentra_el_fragmento_que_contiene_el_pegado(monkeypatch):
    monkeypatch.setattr(I, "_cargar", lambda fuente=None, doc=None: [dict(f) for f in FRAGS])
    pegado = ("Lemma 2.1.1. Let N be a strongly regular sequence and let g be the logarithm of h_N "
              "restricted to the real axis. Then the Poisson integral of g converges absolutely.")
    loc = I.localizar("t", pegado)
    assert loc and loc["fragmentos"][0]["id"] == "t#0001" and loc["cobertura"] >= 0.9
    assert loc["fragmentos"][0]["localizado"]
    # un pegado que cruza el lema y su demostracion trae los dos
    cruce = ("Then the Poisson integral of g converges absolutely. Proof. Since h_N is bounded by one, "
             "g is nonpositive, so the integral of g against the Poisson kernel is finite")
    loc = I.localizar("t", cruce)
    assert loc and [f["id"] for f in loc["fragmentos"]] == ["t#0001", "t#0002"]


def test_despegar_palabras_pegadas_del_pdf():
    vocab = {"let", "strongly", "regular", "sequence", "with", "then", "there", "exist"}
    assert I._despegar("letnbeastronglyregularsequencewith", vocab) == ["let", "strongly", "regular", "sequence", "with"]
    assert I._despegar("zzzz", vocab) == []


def test_localizar_un_pegado_con_palabras_pegadas_y_numero_impreso(monkeypatch):
    monkeypatch.setattr(I, "_cargar", lambda fuente=None, doc=None: [dict(f) for f in FRAGS])
    monkeypatch.setattr(I, "por_numero", lambda doc, numero: [dict(f) for f in FRAGS if f["numero"] == numero])
    # "Lemma 2.1.1" al principio: busqueda exacta por numero impreso, aunque el resto este pegado
    loc = I.localizar("t", "Lemma2.1.1. LetNbeastronglyregularsequence andletgbethelogarithm")
    assert loc and loc["fragmentos"][0]["numero"] == "2.1.1" and loc["cobertura"] == 1.0
    # sin numero: las palabras pegadas se despegan con el vocabulario del documento
    monkeypatch.setattr(I, "por_numero", lambda doc, numero: [])
    loc = I.localizar("t", "LetNbeastronglyregularsequence andletgbethelogarithmof h_N restrictedtotherealaxis. "
                           "ThenthePoissonintegralofg convergesabsolutely.")
    assert loc and loc["fragmentos"][0]["id"] == "t#0001"


def test_localizar_devuelve_none_si_nada_cubre_el_pegado(monkeypatch):
    monkeypatch.setattr(I, "_cargar", lambda fuente=None, doc=None: [dict(f) for f in FRAGS])
    assert I.localizar("t", "Newton polygon of an algebraic equation with Puiseux branches and ramification "
                            "index computed from the lower convex hull of the support") is None
    assert I.localizar("t", "muy corto") is None


def test_mensajes_solo_llevan_el_bloque_del_ultimo_turno():
    turnos = [dict(role="user", content="p1", bloque="B1"), dict(role="assistant", content="r1"),
              dict(role="user", content="p2", bloque="B2")]
    msgs = K._mensajes(turnos)
    assert [m["content"] for m in msgs] == ["p1", "r1", "p2\n\nB2"]
    assert all(set(m) == {"role", "content"} for m in msgs)


def test_recuperar_respeta_el_tope_de_tokens(monkeypatch):
    grandes = [dict(f, texto="palabra " * 900) for f in FRAGS]
    monkeypatch.setattr(I, "buscar", lambda *a, **k: [dict(f) for f in grandes])
    monkeypatch.setattr(I, "seguir_refs", lambda frags, maximo=4: [])
    out = K._recuperar("t", "que dice el lema", "", [], tope=1000)
    assert len(out) == 1                      # el primero entra siempre; el segundo no cabe
    out = K._recuperar(None, "pregunta", "", [dict(FRAGS[1], localizado=True)])
    assert [f["id"] for f in out] == ["t#0001"]      # sin doc, solo lo localizado
