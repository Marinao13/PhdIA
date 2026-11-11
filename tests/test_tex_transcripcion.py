"""El .tex que acompana a una transcripcion: se exporta del .md, se rehace al revisar, y nunca se
pisa lo que Mariano haya editado a mano en el."""
import os
import types
import pytest
from fastapi.testclient import TestClient

from nucleo import transcribir as T
from nucleo import a_latex as L
from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
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


def _pdf(ruta, paginas=2):
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}")
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


def _args(**kw):
    base = dict(fichero=None, tipo="paper", titulo=None, paginas=None, motor="modelo", calidad="normal",
                lista=False, revisado=None, tex=None, pisar=False)
    base.update(kw)
    return types.SimpleNamespace(**base)


def _lee(ruta):
    return open(ruta, encoding="utf-8").read()


def test_transcribir_deja_el_tex_junto_al_md(repo):
    r = T.transcribir(_pdf(repo / "a.pdf"), tipo="curso", titulo="Tema 1")
    assert r["tex"] == r["ruta"][:-3] + ".tex" and r["tex_estado"] == "escrito"
    tex = _lee(r["tex"])
    assert L.intacto(tex) and "\\title{Tema 1}" in tex and "estado: sin_revisar" in tex
    assert "% ---------- pagina 1 ----------" in tex and "% ---------- pagina 2 ----------" in tex
    assert "\\duda{[ILEGIBLE]}" in tex and "SIN REVISAR" not in tex
    assert [t["nombre"] for t in T.listar()] == [r["nombre"]]           # el .tex no es otra transcripcion


def test_al_revisar_se_rehace_el_tex_con_el_texto_corregido(repo):
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    assert T.guardar_pagina(r["nombre"], 1, "Sea $M$ fuertemente regular, corregido.")
    assert "corregido" not in _lee(r["tex"])                              # el .tex no se entera solo
    T.marcar_revisado(r["nombre"])
    tex = _lee(r["tex"])
    assert "Sea $M$ fuertemente regular, corregido." in tex and "estado: revisado" in tex and L.intacto(tex)


def test_un_tex_editado_a_mano_no_se_pisa(repo, capsys):
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    mio = _lee(r["tex"]).replace("\\begin{document}", "\\newtheorem{teorema}{Teorema}\n\\begin{document}")
    open(r["tex"], "w", encoding="utf-8", newline="\r\n").write(mio)      # editado, y con saltos de Windows
    T.marcar_revisado(r["nombre"])
    assert "\\newtheorem{teorema}{Teorema}" in _lee(r["tex"])
    assert T.exportar_tex(r["nombre"]) == (r["tex"], "tuyo")
    K.cmd_transcribir(_args(tex=r["nombre"]))
    salida = capsys.readouterr().out
    assert "tiene cambios tuyos" in salida and "--pisar" in salida
    assert "\\newtheorem{teorema}{Teorema}" in _lee(r["tex"])
    K.cmd_transcribir(_args(tex=r["nombre"], pisar=True))
    assert "exportado del .md" in capsys.readouterr().out
    assert "\\newtheorem" not in _lee(r["tex"]) and "estado: revisado" in _lee(r["tex"])


def test_solo_cambiar_los_saltos_de_linea_no_cuenta_como_edicion(repo):
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    tal_cual = _lee(r["tex"])
    open(r["tex"], "w", encoding="utf-8", newline="\r\n").write(tal_cual)
    assert b"\r\n" in open(r["tex"], "rb").read()
    assert T.exportar_tex(r["nombre"]) == (r["tex"], "escrito")


def test_comando_tex_y_mensajes(repo, capsys):
    K.cmd_transcribir(_args(tex="no-existe"))
    assert "no existe" in capsys.readouterr().out
    K.cmd_transcribir(_args(fichero=_pdf(repo / "a.pdf"), titulo="Tema 1"))
    salida = capsys.readouterr().out
    assert "LaTeX: " in salida and "Tema 1".lower().replace(" ", "-") + ".tex" in salida
    nombre = T.listar()[0]["nombre"]
    os.remove(os.path.join(str(repo), "transcripciones", nombre + ".tex"))
    K.cmd_transcribir(_args(tex=nombre))
    assert "exportado del .md" in capsys.readouterr().out
    assert os.path.exists(os.path.join(str(repo), "transcripciones", nombre + ".tex"))
    K.cmd_transcribir(_args(revisado=nombre))
    assert "LaTeX: " in capsys.readouterr().out


def test_si_la_exportacion_falla_la_transcripcion_sigue(repo, monkeypatch, capsys):
    def rompe(*a, **k):
        raise RuntimeError("markdown raro")
    monkeypatch.setattr(L, "documento", rompe)
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    assert r["tex_estado"] == "fallo" and os.path.exists(r["ruta"]) and not os.path.exists(r["tex"])
    assert T.marcar_revisado(r["nombre"]) == r["ruta"] and T.leer(r["nombre"])["estado"] == "revisado"


def test_la_web_descarga_el_tex_del_texto_de_ahora_sin_escribir_nada(repo):
    r = T.transcribir(_pdf(repo / "a.pdf"), titulo="Tema 1")
    os.remove(r["tex"])
    cliente = TestClient(S.app)
    assert f'href="/transcripciones/{r["nombre"]}/tex"' in cliente.get(f"/transcripciones/{r['nombre']}").text
    T.guardar_pagina(r["nombre"], 2, "Lo ultimo que he corregido: $\\gamma(M) > 0$.")
    resp = cliente.get(f"/transcripciones/{r['nombre']}/tex")
    assert resp.status_code == 200 and "attachment" in resp.headers["content-disposition"]
    assert f'{r["nombre"]}.tex' in resp.headers["content-disposition"]
    assert "Lo ultimo que he corregido: $\\gamma(M) > 0$." in resp.text and "\\begin{document}" in resp.text
    assert not os.path.exists(r["tex"])
    assert cliente.get("/transcripciones/no-existe/tex").status_code == 404
