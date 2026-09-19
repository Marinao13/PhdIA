"""Campos manuales de bib.yaml (etiquetas, factorial) sobreviven a una reingesta; `ask` los muestra."""
import json
import pytest

from nucleo import corpus as Q
from nucleo import comandos as K
from nucleo import config as C


@pytest.fixture
def corpus_falso(tmp_path, monkeypatch):
    raiz = tmp_path / "corpus"
    (raiz / "raw").mkdir(parents=True)
    (raiz / "text").mkdir()
    (raiz / "meta").mkdir()
    monkeypatch.setattr(C, "DIR_CORPUS", str(raiz))
    monkeypatch.setattr(C, "DIR_RAW", str(raiz / "raw"))
    monkeypatch.setattr(C, "DIR_TEXT", str(raiz / "text"))
    monkeypatch.setattr(C, "F_BIB", str(raiz / "meta" / "bib.yaml"))
    (raiz / "meta" / "bib.yaml").write_text("", encoding="utf-8")
    pdf = raiz / "raw" / "autor-2020.pdf"
    pdf.write_bytes(b"%PDF-1.4 falso")
    # sin red, sin PyMuPDF, sin Marker: paginas y metadatos simulados
    monkeypatch.setattr(Q, "extraer_paginas", lambda p: ["Un titulo cualquiera\nAutor\n" + "texto " * 200] * 3)
    monkeypatch.setattr(Q, "_metadatos", lambda paginas, sin_red, avisos:
                        ({"titulo": "Un titulo cualquiera", "autores": ["Autor, A."], "estado": "verificado"}, None))
    monkeypatch.setattr(Q, "marker_disponible", lambda: (False, "sin marker"))
    return str(pdf)


def test_etiquetas_y_factorial_sobreviven_a_rehacer(corpus_falso):
    ent = Q.ingerir(corpus_falso, verbose=False, etiquetas=["citado"], factorial="fuera")
    assert ent["etiquetas"] == ["citado"] and ent["factorial"] == "fuera"
    ent2 = Q.ingerir(corpus_falso, verbose=False, rehacer=True)
    assert ent2["etiquetas"] == ["citado"], "la reingesta perdio las etiquetas"
    assert ent2["factorial"] == "fuera", "la reingesta perdio el factorial"
    ent3 = Q.ingerir(corpus_falso, verbose=False, rehacer=True, etiquetas=["citado", "directores"])
    assert ent3["etiquetas"] == ["citado", "directores"]          # se anaden, sin duplicar
    with open(C.DIR_TEXT + "/autor-2020/meta.json", encoding="utf-8") as f:
        assert json.load(f)["id"] == "autor-2020"


def test_factorial_por_defecto_pendiente_y_valores_validos(corpus_falso):
    ent = Q.ingerir(corpus_falso, verbose=False)
    assert ent["factorial"] == "pendiente"
    with pytest.raises(ValueError):
        Q.ingerir(corpus_falso, verbose=False, rehacer=True, factorial="a veces")
    assert set(Q.FACTORIAL_VALORES) == {"dentro", "fuera", "no_aplica", "pendiente"}


def test_descargar_pdf_no_pisa_un_fichero_existente(corpus_falso):
    with pytest.raises(FileExistsError):
        Q.descargar_pdf("1234.5678", "autor-2020.pdf")


def test_cabecera_de_ask_indica_el_factorial():
    assert "p! M_p" in K._factorial_texto({"factorial": "fuera"})
    assert "p! M_p" not in K._factorial_texto({"factorial": "dentro"})
    assert "sin comprobar" in K._factorial_texto({})
    assert "no aplica" in K._factorial_texto({"factorial": "no_aplica"})
