"""Fragmentacion y expansion de consultas. Sin red: DOC_SIMULAR=1 en conftest."""
from nucleo import indice as I


def u(tipo, texto, seccion="1", label=None, pagina=1):
    return dict(tipo=tipo, texto=texto, seccion=seccion, label=label, pagina=pagina)


def test_un_teorema_es_un_fragmento_propio():
    frags = I.fragmentar([u("parrafo", "a " * 50), u("teorema", "if M then B", label="thm:1"),
                          u("parrafo", "b " * 50)])
    teo = [f for f in frags if f["tipo"] == "teorema"]
    assert len(teo) == 1 and teo[0]["label"] == "thm:1" and teo[0]["texto"] == "if M then B"


def test_los_parrafos_de_una_seccion_se_agrupan_hasta_el_minimo():
    frags = I.fragmentar([u("parrafo", "palabra " * 40, seccion="1") for _ in range(12)])
    assert 1 <= len(frags) <= 3
    assert all(f["tipo"] == "parrafos" for f in frags)


def test_cambiar_de_seccion_cierra_el_grupo():
    frags = I.fragmentar([u("parrafo", "x " * 30, seccion="1"), u("titulo", "Seccion 2", seccion="2"),
                          u("parrafo", "y " * 30, seccion="2")])
    assert len(frags) == 2 and frags[0]["seccion"] == "1" and frags[1]["seccion"] == "2"


def test_nada_supera_el_maximo_de_tokens():
    largo = ". ".join("This is sentence number %d of a very long proof" % k for k in range(400))
    frags = I.fragmentar([u("demostracion", largo)])
    assert len(frags) > 1
    assert all(I._tokens(f["texto"]) <= I.MAX_TOK + I.SOLAPE_TOK * 2 for f in frags)


def test_expandir_anade_terminos_del_glosario():
    q = I.expandir("condiciones sobre la sucesión fuertemente regular")
    assert "strongly regular sequence" in q and q.startswith("condiciones")


def test_tokenizar_saca_los_comandos_latex_como_palabras():
    assert "gamma" in I._tokenizar(r"la condicion $(\gamma_1)$ de Thilliez")


def test_cita_para_humanos(monkeypatch):
    # pagina + tipo con numero impreso; sin numero, la etiqueta LaTeX marcada; nunca "sec N.N".
    # Documentos ficticios (no estan en bib.yaml): sin marca de version.
    monkeypatch.setattr(I, "_META_DOC", {"doc-x": "", "doc-y": "", "libro-z": "", "propio": ""})
    assert I.cita(dict(doc="doc-x", pagina=7, tipo="teorema", numero="3.2", label="thm:main")) == \
        "[doc-x:p7, Teorema 3.2]"
    assert I.cita(dict(doc="doc-y", pagina=21, tipo="proposicion", numero=None, label="pro.gamma")) == \
        "[doc-y:p21, proposicion, etiqueta LaTeX: pro.gamma]"
    assert I.cita(dict(doc="libro-z", pagina=143, tipo="pagina", seccion="2.1")) == "[libro-z:p143]"
    assert I.cita(dict(doc="propio", pagina=None, seccion=None, label=None, tipo="parrafo")) == "[propio]"


def test_cita_de_capa_tex_dice_la_version_de_arxiv(monkeypatch):
    # el texto es el de arXiv y la pagina la del PDF de revista: la cita lo dice
    monkeypatch.setattr(I, "_META_DOC", {"paper-tex": " | texto: arXiv v1"})
    assert I.cita(dict(doc="paper-tex", pagina=20, tipo="corolario", numero="4.14")) == \
        "[paper-tex:p20, Corolario 4.14 | texto: arXiv v1]"
