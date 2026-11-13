"""Las figuras de una transcripcion se recortan del original: en el .md, en la web y en el .tex."""
import os
import types
import pytest
from fastapi.testclient import TestClient

from nucleo import transcribir as T
from nucleo import a_latex as L
from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M
from nucleo import prompts as P
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
    """Paginas con un rectangulo negro en el cuadrante superior izquierdo (10%-50% x 10%-40%)."""
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        pag = doc.new_page(width=600, height=800)
        pag.draw_rect(fitz.Rect(60, 80, 300, 320), color=(0, 0, 0), fill=(0, 0, 0))
        pag.insert_text((72, 700), f"pagina {n + 1}")
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


def _args(**kw):
    base = dict(fichero=None, tipo="paper", titulo=None, paginas=None, motor="modelo", calidad="alta",
                lista=False, revisado=None, tex=None, pisar=False, figuras=None)
    base.update(kw)
    return types.SimpleNamespace(**base)


def _con_marcas(repo, monkeypatch, texto_pagina):
    """Una transcripcion de 2 paginas cuya pagina 1 es `texto_pagina`."""
    textos = iter([texto_pagina, "Pagina dos, sin dibujos."])
    monkeypatch.setattr(M, "_completar", lambda *a, **k: (next(textos), 100, 50, 0, {}))
    return T.transcribir(_pdf(repo / "a.pdf"), tipo="curso", titulo="Tema 1")


def test_la_caja_se_lee_aunque_la_descripcion_lleve_corchetes_y_barras():
    assert T._caja(" curva nula fuera de $[-2,2]$ con $|x|$ | 10, 20.5,60,45 ") == \
        ("curva nula fuera de $[-2,2]$ con $|x|$", (10.0, 20.5, 60.0, 45.0))
    assert T._caja(" sin caja ") == ("sin caja", None)
    for mala in ("x | 60,10,10,40", "x | 0,0,100,100", "x | 10,10,120,40"):       # al reves, toda la pagina, fuera
        assert T._caja(mala)[1] is None
    m = T.RE_FIGURA.search("antes [FIGURA: intervalo $[0,1)$ y $(a,b]$ | 1,2,30,40] despues")
    assert m and T._caja(m.group(1)) == ("intervalo $[0,1)$ y $(a,b]$", (1.0, 2.0, 30.0, 40.0))


def test_transcribir_recorta_las_figuras_que_traen_caja(repo, monkeypatch):
    r = _con_marcas(repo, monkeypatch, "Texto.\n\n[FIGURA: rectangulo negro $[0,1)$ | 10,10,50,40]\n\n"
                                       "[FIGURA: otro sin caja]\n\nMas texto.")
    t = T.leer(r["nombre"])
    pagina1 = dict(T.paginas(t["cuerpo"])[1])[1]
    fichero = f"{r['nombre']}-p1-1.jpg"
    assert f'![figura](figuras/{fichero} "0.43")\n*Figura: rectangulo negro $[0,1)$*' in pagina1
    assert "[FIGURA: otro sin caja]" in pagina1                         # sin caja, se queda como estaba
    from PIL import Image
    im = Image.open(repo / "transcripciones" / "figuras" / fichero).convert("L")
    assert im.getpixel((im.width // 2, im.height // 2)) < 40            # el centro del recorte es el rectangulo
    assert im.getpixel((2, 2)) > 200 and im.width < 1401                # con su margen blanco alrededor
    # el indice ve el pie, no la imagen
    textos = [u["texto"] for u in T.unidades(t["cuerpo"])]
    assert "*Figura: rectangulo negro $[0,1)$*" in textos and not any("![figura]" in x for x in textos)


def test_figuras_localiza_las_de_una_transcripcion_ya_hecha(repo, monkeypatch, capsys):
    r = _con_marcas(repo, monkeypatch, "Uno.\n\n[FIGURA: discos sobre $[a,b]$]\n\nDos.\n\n[FIGURA: una banda]\n\nTres.")
    assert "![figura]" not in T.leer(r["nombre"])["cuerpo"]
    monkeypatch.undo()                                                    # vuelve el motor simulado de verdad
    monkeypatch.setattr(C, "RAIZ", str(repo))
    monkeypatch.setattr(C, "F_LLAMADAS", str(repo / "llamadas.jsonl"))
    monkeypatch.setattr(C, "SIMULAR", True)
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", E._marcas_vacias()))
    monkeypatch.setattr(K, "_abrir", lambda ruta: None)
    T.guardar_pagina(r["nombre"], 2, "Esta pagina la he corregido yo.")
    res = T.figuras(r["nombre"])
    assert res["hechas"] == 2 and res["pendientes"] == 0 and res["paginas"] == [1]
    hojas = dict(T.paginas(T.leer(r["nombre"])["cuerpo"])[1])
    assert hojas[1].count("![figura](figuras/") == 2 and "*Figura: discos sobre $[a,b]$*" in hojas[1]
    assert hojas[1].startswith("Uno.") and "Dos." in hojas[1] and hojas[1].endswith("Tres.")
    assert hojas[2] == "Esta pagina la he corregido yo."                 # lo demas no se toca
    assert sorted(os.listdir(repo / "transcripciones" / "figuras")) == [f"{r['nombre']}-p1-1.jpg", f"{r['nombre']}-p1-2.jpg"]
    tex = open(r["tex"], encoding="utf-8").read()
    assert tex.count("\\includegraphics") == 2 and "\\usepackage{graphicx}" in tex
    # otra vez: ya no hay nada que hacer ni se llama al modelo
    antes = len(open(C.F_LLAMADAS, encoding="utf-8").readlines())
    assert T.figuras(r["nombre"])["hechas"] == 0
    assert len(open(C.F_LLAMADAS, encoding="utf-8").readlines()) == antes
    # el comando
    K.cmd_transcribir(_args(figuras=r["nombre"]))
    assert "0 figura(s)" in capsys.readouterr().out
    K.cmd_transcribir(_args(figuras="no-existe"))
    assert "no existe" in capsys.readouterr().out


def test_figuras_sin_original_o_con_el_motor_apagado(repo, monkeypatch, capsys):
    r = _con_marcas(repo, monkeypatch, "[FIGURA: algo]")
    monkeypatch.setattr(E, "fase_actual", lambda: ("f3", E._marcas_vacias()))
    K.cmd_transcribir(_args(figuras=r["nombre"]))
    assert "MOTOR APAGADO" in capsys.readouterr().out and "![figura]" not in T.leer(r["nombre"])["cuerpo"]
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", E._marcas_vacias()))
    os.remove(T.leer(r["nombre"])["original"])
    with pytest.raises(RuntimeError):
        T.figuras(r["nombre"])
    K.cmd_transcribir(_args(figuras=r["nombre"]))
    assert "no esta el original" in capsys.readouterr().out


def test_el_tex_incluye_la_figura_con_su_pie():
    md = ('Antes.\n\n![figura](figuras/x-p1-1.jpg "0.45")\n*Figura: sector $S_\\gamma$ al 50%*\n\nDespues.\n\n'
          "[FIGURA: sin recortar | 10,10,50,40]\n\n![otra](https://ejemplo.org/a.png)\n")
    tex = L.documento(md, nombre="x")
    assert ("Antes.\n\n\\begin{center}\n\\includegraphics[width=0.45\\linewidth]{figuras/x-p1-1.jpg}\\\\[0.5ex]\n"
            "{\\small \\emph{Figura: sector $S_\\gamma$ al 50\\%}}\n\\end{center}\n\nDespues.") in tex
    assert "\\usepackage{graphicx}" in tex.split("\\begin{document}")[0]
    assert "{FIGURA: sin recortar}}" in tex and "10,10,50,40" not in tex   # la marca sin recortar, sin sus numeros
    assert "[imagen: otra]" in tex and tex.count("\\includegraphics") == 1  # una imagen ajena no se incluye
    import re
    assert not re.search("[-]", tex)


def test_la_web_sirve_las_figuras_y_solo_eso(repo, monkeypatch):
    r = _con_marcas(repo, monkeypatch, "[FIGURA: rectangulo | 10,10,50,40]")
    fichero = f"{r['nombre']}-p1-1.jpg"
    cliente = TestClient(S.app)
    html = cliente.get(f"/transcripciones/{r['nombre']}").text
    assert f'<img src="figuras/{fichero}"' in html and "<em>Figura: rectangulo</em>" in html
    resp = cliente.get(f"/transcripciones/figuras/{fichero}")
    assert resp.status_code == 200 and resp.headers["content-type"] == "image/jpeg" and resp.content[:2] == b"\xff\xd8"
    (repo / "transcripciones" / "secreto.jpg").write_bytes(b"no")
    for malo in ("no-esta.jpg", "..%2Fsecreto.jpg", "x.md", "%2E%2E%2F" + r["nombre"] + ".md"):
        assert cliente.get(f"/transcripciones/figuras/{malo}").status_code == 404


def test_el_prompt_pide_la_caja_de_cada_dibujo():
    assert "[FIGURA: descripcion de una linea | x0,y0,x1,y1]" in P.TRANSCRIBIR and "tantos por ciento" in P.TRANSCRIBIR
    assert "MODO_FIGURAS" in P.FIGURAS
