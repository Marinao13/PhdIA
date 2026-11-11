"""web/: transcripciones. Subir, ver el original al lado, corregir pagina a pagina y marcar revisado.
Motor simulado y todo en tmp_path: nada toca el repo."""
import os
import pytest
from fastapi.testclient import TestClient

from nucleo import config as C
from nucleo import estado as E
from nucleo import transcribir as T
import web.servidor as S
from web import render


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(C, "F_LLAMADAS", str(tmp_path / "llamadas.jsonl"))
    monkeypatch.setattr(C, "SIMULAR", True)
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)
    monkeypatch.setattr(E, "commits_todos", lambda: [])
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", E._marcas_vacias()))
    S._TRABAJO.clear()
    yield TestClient(S.app)
    if S._HILO is not None:
        S._HILO.join(20)
    S._TRABAJO.clear()


def _pdf_bytes(paginas=2):
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}")
    datos = doc.tobytes()
    doc.close()
    return datos


def _subir(cliente, nombre="apuntes.pdf", datos=None, **campos):
    r = cliente.post("/transcripciones", files={"fichero": (nombre, datos or _pdf_bytes(), "application/pdf")},
                     data=campos, follow_redirects=False)
    if S._HILO is not None:
        S._HILO.join(20)
    return r


def test_lista_vacia_y_formulario(cliente):
    r = cliente.get("/transcripciones")
    assert r.status_code == 200 and "no hay transcripciones" in r.text
    assert 'enctype="multipart/form-data"' in r.text and 'http-equiv="refresh"' not in r.text


def test_subir_transcribe_en_segundo_plano_y_queda_sin_revisar(cliente, tmp_path):
    r = _subir(cliente, tipo="curso", titulo="Tema 1", paginas="1-2")
    assert r.status_code == 303 and r.headers["location"] == "/transcripciones"
    ts = T.listar()
    assert len(ts) == 1 and ts[0]["estado"] == "sin_revisar" and ts[0]["tipo"] == "curso"
    assert ts[0]["nombre"].endswith("-tema-1") and ts[0]["origen"] == "apuntes.pdf"
    assert S._TRABAJO["estado"] == "hecho" and S._TRABAJO["nombre"] == ts[0]["nombre"]
    # la subida temporal se borra; queda el original junto a la transcripcion
    d_orig = tmp_path / "transcripciones" / "originales"
    assert os.path.exists(d_orig / (ts[0]["nombre"] + ".pdf"))
    assert not os.path.exists(d_orig / "_subidas") or not any(os.scandir(d_orig / "_subidas"))
    r = cliente.get("/transcripciones")
    assert "Hecho" in r.text and "SIN REVISAR" in r.text and "Tema 1" in r.text
    assert 'http-equiv="refresh"' not in r.text


def test_la_lista_se_refresca_mientras_hay_un_trabajo(cliente):
    S._TRABAJO.update(estado="en curso", origen="a.pdf", mensaje="pagina 2 de 9...", motor="modelo")
    r = cliente.get("/transcripciones")
    assert 'http-equiv="refresh"' in r.text and "pagina 2 de 9" in r.text
    r = _subir(cliente)
    assert r.headers["location"].endswith("aviso=ocupado") and T.listar() == []
    assert "ya hay una transcripcion en curso" in cliente.get("/transcripciones?aviso=ocupado").text


def test_detalle_lado_a_lado_con_las_marcas_resaltadas(cliente):
    _subir(cliente)
    nombre = T.listar()[0]["nombre"]
    r = cliente.get(f"/transcripciones/{nombre}")
    assert r.status_code == 200
    assert f'src="/transcripciones/{nombre}/pagina/1"' in r.text and f'src="/transcripciones/{nombre}/pagina/2"' in r.text
    assert '<mark class="duda">[ILEGIBLE]</mark>' in r.text and '<mark class="duda">[?]</mark>' in r.text
    assert "<textarea" in r.text and "La he revisado contra el original" in r.text
    assert "$M=(M_p)_{p\\ge 0}$" in r.text              # la formula llega intacta a KaTeX
    png = cliente.get(f"/transcripciones/{nombre}/pagina/1")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png" and png.content[:4] == b"\x89PNG"
    assert cliente.get(f"/transcripciones/{nombre}/pagina/9").status_code == 404


def test_corregir_una_pagina_no_toca_las_demas(cliente):
    _subir(cliente)
    nombre = T.listar()[0]["nombre"]
    antes = dict(T.paginas(T.leer(nombre)["cuerpo"])[1])
    r = cliente.post(f"/transcripciones/{nombre}/pagina/2",
                     data={"texto": "Sea $M$ fuertemente regular.\r\n\r\n<!-- pagina 7 -->\r\n$\\gamma(M) > 0$"},
                     follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("aviso=guardada#p2")
    t = T.leer(nombre)
    prefacio, hojas = T.paginas(t["cuerpo"])
    assert [n for n, _ in hojas] == [1, 2]              # la marca pegada no ha partido el fichero
    assert dict(hojas)[1] == antes[1] and "$\\gamma(M) > 0$" in dict(hojas)[2] and "\r" not in t["cuerpo"]
    assert "SIN REVISAR" in prefacio and t["estado"] == "sin_revisar"
    r = cliente.post(f"/transcripciones/{nombre}/pagina/5", data={"texto": "x"}, follow_redirects=False)
    assert r.headers["location"].endswith("aviso=nopagina#p5")


def test_marcar_revisada_desde_la_web(cliente):
    _subir(cliente)
    nombre = T.listar()[0]["nombre"]
    r = cliente.post(f"/transcripciones/{nombre}/revisado", follow_redirects=False)
    assert r.status_code == 303
    assert T.leer(nombre)["estado"] == "revisado" and T.sin_revisar() == []
    r = cliente.get(f"/transcripciones/{nombre}?aviso=revisada")
    assert "python doc.py indexar" in r.text and "La he revisado contra el original" not in r.text
    assert "revisada" in cliente.get("/transcripciones").text


def test_motor_apagado_en_fase_3_no_transcribe(cliente, monkeypatch):
    monkeypatch.setattr(E, "fase_actual", lambda: ("f3", E._marcas_vacias()))
    r = _subir(cliente)
    assert r.headers["location"].endswith("aviso=apagado")
    assert T.listar() == [] and not S._TRABAJO and not os.path.exists(C.F_LLAMADAS)
    assert "MOTOR APAGADO" in cliente.get("/transcripciones?aviso=apagado").text


def test_subidas_no_validas(cliente):
    r = _subir(cliente, nombre="notas.txt", datos=b"hola")
    assert r.headers["location"].endswith("aviso=formato")
    r = _subir(cliente, paginas="8")
    assert r.headers["location"].endswith("aviso=paginas")
    r = _subir(cliente, nombre="roto.pdf", datos=b"esto no es un pdf")
    assert r.headers["location"].endswith("aviso=formato")
    assert T.listar() == [] and not S._TRABAJO


def test_un_nombre_no_sale_de_la_carpeta(cliente, tmp_path):
    (tmp_path / "secreto.md").write_text("---\nestado: revisado\n---\nno\n", encoding="utf-8")
    for malo in ("..%2Fsecreto", "%2E%2E%2Fsecreto", "no-existe"):
        assert cliente.get(f"/transcripciones/{malo}").status_code == 404
        assert cliente.post(f"/transcripciones/{malo}/revisado", follow_redirects=False).status_code == 404
    assert "estado: revisado" in (tmp_path / "secreto.md").read_text(encoding="utf-8")


def test_el_nombre_del_fichero_subido_se_limpia(cliente, tmp_path):
    _subir(cliente, nombre="../../fuera de sitio.pdf")
    ts = T.listar()
    assert len(ts) == 1 and ts[0]["origen"] == "fuera de sitio.pdf"
    assert not os.path.exists(tmp_path.parent / "fuera de sitio.pdf")


def test_render_no_parte_una_formula_con_marca():
    h = render.transcripcion("Sea $a_p [?] b_p$ y [ILEGIBLE] aqui.\n\n[PAGINA CORTADA por el tope: revisa]")
    assert '<span class="formula-duda"' in h and "$a_p [?] b_p$" in h
    assert h.count('<mark class="duda">') == 2 and "<mark" not in h.split("$a_p")[1].split("b_p$")[0]


def test_ahora_recuerda_lo_que_esta_sin_revisar(cliente):
    assert T.sin_revisar() == [] and "sin revisar (no entran en el indice)" not in cliente.get("/").text
    _subir(cliente)
    assert len(T.sin_revisar()) == 1
    assert "1 sin revisar (no entran en el indice)" in cliente.get("/").text      # el panel pinta `ahora`


def test_la_guia_tiene_la_seccion_que_enlaza_la_pagina(cliente):
    ancla = "guia-pasar-a-limpio-lo-escrito-a-mano-transcribir"
    assert f'href="/guia#{ancla}"' in cliente.get("/transcripciones").text
    assert f'id="{ancla}"' in cliente.get("/guia").text


def test_un_trabajo_que_muere_no_bloquea_los_siguientes(cliente, monkeypatch):
    def muere(*a, **k):
        raise SystemExit("falta el paquete openai")
    monkeypatch.setattr(T, "transcribir", muere)
    _subir(cliente)
    assert S._TRABAJO["estado"] == "error" and "falta el paquete" in S._TRABAJO["mensaje"]
    assert "No se pudo transcribir" in cliente.get("/transcripciones").text


def test_los_restos_de_una_subida_muerta_se_borran_en_la_siguiente(cliente, tmp_path):
    resto = tmp_path / "transcripciones" / "originales" / "_subidas" / "abc123"
    resto.mkdir(parents=True)
    (resto / "viejo.pdf").write_bytes(b"x" * 100)
    _subir(cliente)
    assert not resto.exists() and len(T.listar()) == 1


def test_un_md_ajeno_en_la_carpeta_da_404(cliente, tmp_path):
    d = tmp_path / "transcripciones"
    d.mkdir()
    (d / "LEEME.md").write_text("# mio\n\n<!-- pagina 1 -->\n\ntexto\n", encoding="utf-8")
    assert cliente.get("/transcripciones/LEEME").status_code == 404
    assert cliente.post("/transcripciones/LEEME/revisado", follow_redirects=False).status_code == 404
    assert cliente.post("/transcripciones/LEEME/pagina/1", data={"texto": "x"}, follow_redirects=False).status_code == 404
    assert (d / "LEEME.md").read_text(encoding="utf-8").startswith("# mio")
