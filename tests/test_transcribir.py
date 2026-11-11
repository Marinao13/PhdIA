"""`transcribir`: lo manuscrito a markdown con LaTeX; nada sin revisar entra en el indice."""
import os
import types
import pytest

from nucleo import transcribir as T
from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M
from nucleo import indice as I


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Un repo vacio en tmp: nada toca el arbol real ni el log de llamadas."""
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(C, "F_LLAMADAS", str(tmp_path / "llamadas.jsonl"))
    monkeypatch.setattr(C, "SIMULAR", True)
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", E._marcas_vacias()))
    monkeypatch.setattr(K, "_abrir", lambda ruta: None)
    return tmp_path


def _pdf(ruta, paginas=3):
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}: sea M una sucesion peso")
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


def _foto(ruta, ancho=400, alto=200, orientacion=None):
    from PIL import Image
    im = Image.new("RGB", (ancho, alto), "white")
    if orientacion:
        exif = Image.Exif()
        exif[0x0112] = orientacion
        im.save(str(ruta), exif=exif)
    else:
        im.save(str(ruta))
    return str(ruta)


def _args(**kw):
    base = dict(fichero=None, tipo="paper", titulo=None, paginas=None, motor="modelo", calidad="normal",
                lista=False, revisado=None)
    base.update(kw)
    return types.SimpleNamespace(**base)


def test_rango_de_paginas():
    assert T.rango(None, 4) == [1, 2, 3, 4]
    assert T.rango("1-3,5", 10) == [1, 2, 3, 5]
    assert T.rango("3-1, 2", 10) == [1, 2, 3]
    assert T.rango("2,9", 4) == [2]                      # fuera del fichero, se descarta
    with pytest.raises(ValueError):
        T.rango("uno", 4)


def test_transcribe_un_pdf_y_queda_sin_revisar(repo):
    pdf = _pdf(repo / "Apuntes del curso.pdf")
    vistos = []
    r = T.transcribir(pdf, tipo="curso", paginas="1-2", progreso=vistos.append)
    assert r["paginas"] == [1, 2] and r["pendientes"] == [] and r["fallo"] is None
    assert os.path.dirname(r["ruta"]) == str(repo / "transcripciones")
    assert r["nombre"].endswith("-apuntes-del-curso") and len(vistos) == 2
    texto = open(r["ruta"], encoding="utf-8").read()
    meta, cuerpo = T.partir(texto)
    assert meta["estado"] == "sin_revisar" and meta["tipo"] == "curso" and meta["paginas"] == "1,2"
    assert meta["origen"] == "Apuntes del curso.pdf" and meta["motor"].startswith("modelo")
    assert "<!-- pagina 1 -->" in cuerpo and "<!-- pagina 2 -->" in cuerpo and "<!-- pagina 3 -->" not in cuerpo
    assert "SIN REVISAR" in cuerpo
    assert (r["ilegibles"], r["dudosos"]) == (2, 2)      # una marca de cada por pagina simulada
    assert os.path.exists(repo / "transcripciones" / "originales" / (r["nombre"] + ".pdf"))
    # la llamada paso por la puerta y quedo registrada, una por pagina
    log = [l for l in open(C.F_LLAMADAS, encoding="utf-8") if l.strip()]
    assert len(log) == 2 and all('"comando": "transcribir"' in l for l in log)


def test_dos_transcripciones_del_mismo_fichero_no_se_pisan(repo):
    pdf = _pdf(repo / "duda.pdf", paginas=1)
    a = T.transcribir(pdf, tipo="duda")
    b = T.transcribir(pdf, tipo="duda")
    assert a["nombre"] != b["nombre"] and b["nombre"].endswith("-2")
    assert len(T.listar()) == 2


def test_formato_no_admitido_y_fichero_inexistente(repo):
    (repo / "notas.txt").write_text("hola", encoding="utf-8")
    with pytest.raises(ValueError):
        T.transcribir(str(repo / "notas.txt"))
    with pytest.raises(FileNotFoundError):
        T.transcribir(str(repo / "no-existe.pdf"))
    with pytest.raises(ValueError):
        T.transcribir(_pdf(repo / "a.pdf", paginas=2), paginas="7")


def test_la_foto_del_movil_se_endereza(repo):
    foto = _foto(repo / "foto.jpg", ancho=400, alto=200, orientacion=6)     # 6 = girar 90 grados
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(T.pagina_png(foto, 1)))
    assert im.size == (200, 400)
    r = T.transcribir(foto, tipo="duda", titulo="Duda del lema 2.1")
    assert r["nombre"].endswith("-duda-del-lema-2-1") and r["paginas"] == [1]


def test_motor_apagado_en_fase_1(repo, monkeypatch, capsys):
    monkeypatch.setattr(E, "fase_actual", lambda: ("f1", E._marcas_vacias()))
    pdf = _pdf(repo / "a.pdf", paginas=1)
    with pytest.raises(M.MotorApagado):
        T.transcribir(pdf)
    K.cmd_transcribir(_args(fichero=pdf))
    salida = capsys.readouterr().out
    assert "MOTOR APAGADO" in salida and "--motor marker" in salida
    assert T.listar() == [] and not os.path.exists(C.F_LLAMADAS)


def test_un_fallo_a_media_pasada_guarda_lo_hecho(repo, monkeypatch, capsys):
    pdf = _pdf(repo / "largo.pdf", paginas=3)
    real, n = M._completar, []

    def falla_a_la_segunda(*a, **k):
        n.append(1)
        if len(n) == 2:
            raise ConnectionError("sin red")
        return real(*a, **k)

    monkeypatch.setattr(M, "_completar", falla_a_la_segunda)
    r = T.transcribir(pdf)
    assert r["paginas"] == [1] and r["pendientes"] == [2, 3] and "sin red" in r["fallo"]
    assert T.partir(open(r["ruta"], encoding="utf-8").read())[0]["paginas"] == "1"
    # si falla la primera, no queda nada a medias
    n.clear(); n.append(1)
    with pytest.raises(RuntimeError):
        T.transcribir(pdf)
    assert len(T.listar()) == 1
    n.clear()
    K.cmd_transcribir(_args(fichero=pdf))
    salida = capsys.readouterr().out
    assert "Faltan las paginas 2,3" in salida and "--paginas 2,3" in salida


def test_pagina_cortada_queda_marcada(repo, monkeypatch):
    monkeypatch.setattr(M, "_completar", lambda *a, **k: ("media pagi", 900, 6000, 0, dict(cortada=True)))
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=1))
    assert r["coste"]["cortadas"] == 1
    assert "PAGINA CORTADA" in open(r["ruta"], encoding="utf-8").read()


def test_solo_lo_revisado_entra_en_el_indice(repo, monkeypatch):
    monkeypatch.setattr(C, "DIR_TEXT", str(repo / "corpus" / "text"))
    monkeypatch.setattr(C, "F_PROYECTO", str(repo / "PROYECTO.md"))
    monkeypatch.setattr(C, "DIR_LECTURAS", str(repo / "lecturas"))
    monkeypatch.setattr(C, "DIR_SESIONES", str(repo / "sesiones"))
    from nucleo import corpus as Q
    monkeypatch.setattr(Q, "leer_bib", lambda: {})
    curso = T.transcribir(_pdf(repo / "curso.pdf", paginas=2), tipo="curso")
    duda = T.transcribir(_pdf(repo / "duda.pdf", paginas=1), tipo="duda")
    assert I.fuentes() == []                             # nada sin revisar
    assert T.marcar_revisado(curso["nombre"]) == curso["ruta"]
    fs = I.fuentes()
    assert [(f, d) for f, d, _ in fs] == [("curso", "transcripcion:" + curso["nombre"])]
    us = fs[0][2]
    assert {u["pagina"] for u in us} == {1, 2}
    assert not any("SIN REVISAR" in u["texto"] or "pagina 1 -->" in u["texto"] for u in us)
    frags = I.fragmentar(us)                             # el indexador real las trocea con su pagina
    assert frags and {f["pagina"] for f in frags} <= {1, 2} and any("M_p" in f["texto"] for f in frags)
    assert T.marcar_revisado(duda["nombre"])
    assert sorted(f for f, _, _ in I.fuentes()) == ["curso", "nota"]
    meta, cuerpo = T.partir(open(curso["ruta"], encoding="utf-8").read())
    assert meta["estado"] == "revisado" and meta["revisado_el"] and "SIN REVISAR" not in cuerpo
    assert T.marcar_revisado("no-existe") is None


def test_comando_lista_y_revisado(repo, capsys):
    pdf = _pdf(repo / "a.pdf", paginas=1)
    K.cmd_transcribir(_args(lista=True))
    assert "no hay transcripciones" in capsys.readouterr().out
    K.cmd_transcribir(_args(fichero=pdf, tipo="curso", titulo="Tema 1"))
    salida = capsys.readouterr().out
    assert "SIN REVISAR" in salida and "1 paginas" in salida and "[ILEGIBLE]" in salida
    nombre = T.listar()[0]["nombre"]
    K.cmd_transcribir(_args(lista=True))
    assert nombre in capsys.readouterr().out
    K.cmd_transcribir(_args(revisado=nombre))
    salida = capsys.readouterr().out
    assert "revisado" in salida and "OJO: quedan 1 [ILEGIBLE] y 1 [?]" in salida and "fuente curso" in salida
    K.cmd_transcribir(_args(revisado="otra"))
    assert "no existe" in capsys.readouterr().out
    K.cmd_transcribir(_args())
    assert "uso:" in capsys.readouterr().out
    K.cmd_transcribir(_args(fichero=str(repo / "no-esta.pdf")))
    assert "no existe el fichero" in capsys.readouterr().out


def test_un_md_ajeno_en_la_carpeta_no_es_una_transcripcion(repo):
    d = repo / "transcripciones"
    d.mkdir()
    (d / "LEEME.md").write_text("# notas mias\n", encoding="utf-8")
    assert T.listar() == []


def test_mensaje_con_imagenes_por_proveedor(monkeypatch):
    monkeypatch.setattr(C, "PROVEEDOR", "openai")
    m = M.mensaje_con_imagenes("hola", [b"\x89PNG"])
    assert m["role"] == "user" and m["content"][0] == {"type": "input_text", "text": "hola"}
    assert m["content"][1]["type"] == "input_image" and m["content"][1]["image_url"].startswith("data:image/png;base64,")
    monkeypatch.setattr(C, "PROVEEDOR", "anthropic")
    m = M.mensaje_con_imagenes("hola", [b"\x89PNG"])
    assert m["content"][1]["source"]["media_type"] == "image/png"


def test_el_prompt_prohibe_rellenar_por_contexto():
    # 2026-11-11: sin esta regla el modelo ponia \le y \exists donde la pagina tenia un simbolo ilegible
    from nucleo import prompts as P
    assert "MODO_TRANSCRIBIR" in P.TRANSCRIBIR and "[ILEGIBLE]" in P.TRANSCRIBIR and "[?]" in P.TRANSCRIBIR
    assert "no lo que deberia haber" in P.TRANSCRIBIR and "aunque por el contexto" in P.TRANSCRIBIR
