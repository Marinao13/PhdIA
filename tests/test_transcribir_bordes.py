"""`transcribir`: los casos de borde que saco la revision del 2026-11-11 (uno por hallazgo)."""
import io
import os
import threading
import time
import pytest

from nucleo import transcribir as T
from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M
from nucleo import indice as I
from web import render


@pytest.fixture
def repo(tmp_path, monkeypatch):
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
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}")
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


def _texto(r):
    return open(r["ruta"], encoding="utf-8").read()


# ----------------------------------------------------------------------
# 1. lo ya transcrito no se pierde, falle lo que falle despues
# ----------------------------------------------------------------------

def test_la_fase_cambia_a_media_pasada_y_se_guarda_lo_hecho(repo, monkeypatch):
    fases = iter(["libre", "f3", "f3"])
    monkeypatch.setattr(E, "fase_actual", lambda: (next(fases), E._marcas_vacias()))
    r = T.transcribir(_pdf(repo / "a.pdf"))
    assert r["paginas"] == [1] and r["pendientes"] == [2, 3] and "motor apagado" in r["fallo"]
    assert T.partir(_texto(r))[0]["paginas"] == "1"


def test_ctrl_c_a_media_pasada_guarda_lo_hecho(repo, monkeypatch):
    real, n = M._completar, []

    def corta(*a, **k):
        n.append(1)
        if len(n) == 2:
            raise KeyboardInterrupt
        return real(*a, **k)

    monkeypatch.setattr(M, "_completar", corta)
    r = T.transcribir(_pdf(repo / "a.pdf"))
    assert r["paginas"] == [1] and r["pendientes"] == [2, 3] and "interrumpido" in r["fallo"]
    n.clear(); n.append(1)                               # en la primera pagina no hay nada que guardar
    with pytest.raises(KeyboardInterrupt):
        T.transcribir(_pdf(repo / "b.pdf"))
    assert len(T.listar()) == 1


def test_una_pagina_que_no_se_puede_leer_no_tira_las_anteriores(repo, monkeypatch):
    real = T.pagina_png

    def rota(ruta, n, max_lado=2000):
        if n == 2:
            raise RuntimeError("pagina danada")
        return real(ruta, n, max_lado)

    monkeypatch.setattr(T, "pagina_png", rota)
    r = T.transcribir(_pdf(repo / "a.pdf"))
    assert r["paginas"] == [1] and r["pendientes"] == [2, 3] and "pagina danada" in r["fallo"]


def test_si_el_original_no_se_puede_copiar_el_texto_queda(repo, monkeypatch, capsys):
    import shutil

    def falla(*a, **k):
        raise OSError("disco lleno")

    monkeypatch.setattr(shutil, "copyfile", falla)
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=1))
    assert r["sin_original"] and os.path.exists(r["ruta"]) and T.leer(r["nombre"])["original"] is None


# ----------------------------------------------------------------------
# 2 y 6. ficheros editados a mano: cabecera, aviso, marcas
# ----------------------------------------------------------------------

def test_marcar_revisado_sin_linea_en_blanco_tras_el_aviso_no_borra_la_pagina_1(repo):
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=2))
    t = _texto(r)
    pegado = t.replace("\n\n<!-- pagina 1 -->\n\n", "\n<!-- pagina 1 -->\n", 1)      # aviso, marca y texto pegados
    assert pegado != t
    open(r["ruta"], "w", encoding="utf-8", newline="\n").write(pegado)
    antes = T.paginas(T.leer(r["nombre"])["cuerpo"])[1]
    assert T.marcar_revisado(r["nombre"])
    despues = T.leer(r["nombre"])
    assert T.paginas(despues["cuerpo"])[1] == antes and [n for n, _ in antes] == [1, 2]
    assert "SIN REVISAR" not in despues["cuerpo"] and despues["estado"] == "revisado"


def test_la_cabecera_editada_a_mano_sobrevive(repo):
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=2), tipo="curso", titulo="Tema 2: sucesiones")
    t = _texto(r)
    t = "\n" + t.replace("estado: sin_revisar", "profesor: J. Sanz\nesto es una nota mia sin dos puntos\nestado: sin_revisar")
    open(r["ruta"], "w", encoding="utf-8", newline="\n").write(t)
    assert T.leer(r["nombre"])["titulo"] == "Tema 2: sucesiones"          # el titulo lleva dos puntos
    assert T.guardar_pagina(r["nombre"], 1, "corregida")
    assert T.marcar_revisado(r["nombre"])
    final = _texto(r)
    cab = final.split("---")[1]
    assert "profesor: J. Sanz" in cab and "esto es una nota mia sin dos puntos" in cab
    assert cab.count("estado:") == 1 and "estado: revisado" in cab and "revisado_el:" in cab
    assert cab.index("origen:") < cab.index("tipo:") < cab.index("profesor:") < cab.index("estado:")
    assert T.leer(r["nombre"])["tipo"] == "curso" and final.startswith("---\n")


def test_un_md_ajeno_ni_se_sirve_ni_se_marca_ni_se_corrige(repo):
    d = repo / "transcripciones"
    d.mkdir()
    ajeno = d / "notas-mias.md"
    ajeno.write_text("# cosas\n\n<!-- pagina 1 -->\n\ntexto\n", encoding="utf-8")
    assert T.leer("notas-mias") is None and T.marcar_revisado("notas-mias") is None
    assert T.guardar_pagina("notas-mias", 1, "pisado") is False
    assert ajeno.read_text(encoding="utf-8") == "# cosas\n\n<!-- pagina 1 -->\n\ntexto\n"
    assert T.listar() == []


# ----------------------------------------------------------------------
# 7. guardar_pagina
# ----------------------------------------------------------------------

def test_guardar_pagina_solo_toca_su_tramo(repo):
    r = T.transcribir(_pdf(repo / "a.pdf"))
    antes = _texto(r)
    _, hojas = T.paginas(T.leer(r["nombre"])["cuerpo"])
    assert T.guardar_pagina(r["nombre"], 2, dict(hojas)[2])           # guardar lo mismo: fichero identico
    assert _texto(r) == antes
    assert T.guardar_pagina(r["nombre"], 2, "linea uno\r<!-- pagina 7 -->\rlinea dos")     # \r suelto
    _, hojas2 = T.paginas(T.leer(r["nombre"])["cuerpo"])
    assert [n for n, _ in hojas2] == [1, 2, 3] and dict(hojas2)[2] == "linea uno\n\nlinea dos"
    assert dict(hojas2)[1] == dict(hojas)[1] and dict(hojas2)[3] == dict(hojas)[3]
    assert T.guardar_pagina(r["nombre"], 3, "la ultima") and _texto(r).endswith("<!-- pagina 3 -->\n\nla ultima\n")


def test_con_una_marca_duplicada_a_mano_no_se_pierde_la_otra(repo):
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=2))
    with open(r["ruta"], "a", encoding="utf-8", newline="\n") as f:
        f.write("\n<!-- pagina 2 -->\n\nsegunda copia, con cosas distintas\n")
    assert T.guardar_pagina(r["nombre"], 2, "corregida")
    _, hojas = T.paginas(T.leer(r["nombre"])["cuerpo"])
    assert [(n, t) for n, t in hojas][1:] == [(2, "corregida"), (2, "segunda copia, con cosas distintas")]


# ----------------------------------------------------------------------
# 3 y 4. imagenes
# ----------------------------------------------------------------------

def test_un_png_transparente_no_llega_negro(repo):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (300, 200), (0, 0, 0, 0))
    ImageDraw.Draw(im).line((20, 100, 280, 100), fill=(0, 0, 0, 255), width=6)
    im.save(str(repo / "pizarra.png"))
    out = Image.open(io.BytesIO(T.pagina_png(str(repo / "pizarra.png"), 1))).convert("RGB")
    assert out.getpixel((5, 5)) == (255, 255, 255) and out.getpixel((150, 100)) == (0, 0, 0)


def test_webp_funciona_de_punta_a_punta(repo):
    from PIL import Image
    Image.new("RGB", (320, 200), "white").save(str(repo / "foto.webp"))
    assert T.n_paginas(str(repo / "foto.webp")) == 1
    r = T.transcribir(str(repo / "foto.webp"), tipo="duda")
    assert r["paginas"] == [1] and T.leer(r["nombre"])["original"].endswith(".webp")
    assert T.pagina_png(T.leer(r["nombre"])["original"], 1)[:4] == b"\x89PNG"


def test_un_original_huerfano_con_el_mismo_nombre_no_se_ensena(repo):
    d_orig = repo / "transcripciones" / "originales"
    d_orig.mkdir(parents=True)
    import datetime
    nombre = datetime.date.today().isoformat() + "-tema-1"
    (d_orig / (nombre + ".jpg")).write_bytes(b"foto vieja de una transcripcion borrada")
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=2), titulo="Tema 1")
    assert r["nombre"] == nombre
    assert T.leer(nombre)["original"].endswith(".pdf") and not (d_orig / (nombre + ".jpg")).exists()


# ----------------------------------------------------------------------
# 5 y 9. indice y rango
# ----------------------------------------------------------------------

def test_un_enunciado_pegado_a_su_titulo_entra_en_el_indice():
    us = T.unidades("# Tema\n\n<!-- pagina 3 -->\n\n## Teorema 2\nSea $M$ fuertemente regular.\n\nDem. Trivial.\n")
    assert [(u["tipo"], u["texto"]) for u in us] == [
        ("titulo", "Tema"), ("titulo", "Teorema 2"), ("parrafo", "Sea $M$ fuertemente regular."),
        ("parrafo", "Dem. Trivial.")]
    assert us[2]["seccion"] == "Teorema 2" and us[2]["pagina"] == 3
    assert any("fuertemente regular" in f["texto"] for f in I.fragmentar(us))


def test_las_notas_indexan_el_texto_pegado_al_titulo():
    md = ("## Fase 1 - Intento a ciegas\nMi reconstruccion: Cauchy acota las derivadas.\n\n"
          "### Lema clave\n\nEl lema 2.1.1.\n\n### Hipotesis\n(mg) y (snq) implican (dc)\n")
    us = I._unidades_markdown(md)
    assert [(u["tipo"], u["texto"]) for u in us] == [
        ("titulo", "Fase 1 - Intento a ciegas"), ("parrafo", "Mi reconstruccion: Cauchy acota las derivadas."),
        ("titulo", "Lema clave"), ("parrafo", "El lema 2.1.1."),
        ("titulo", "Hipotesis"), ("parrafo", "(mg) y (snq) implican (dc)")]
    assert us[1]["seccion"] == "Fase 1 - Intento a ciegas"


def test_las_plantillas_de_lecturas_no_son_notas(tmp_path, monkeypatch):
    from nucleo import corpus as Q
    d = tmp_path / "lecturas"
    d.mkdir()
    (d / "PLANTILLA.md").write_text("## Sintesis\nQue hace el paper en tres frases.\n", encoding="utf-8")
    (d / "PLANTILLA-resultado.md").write_text("### Enunciado\n(pista)\n", encoding="utf-8")
    (d / "thilliez-2003.md").write_text("## Dudas\nEl limite inductivo.\n", encoding="utf-8")
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(C, "DIR_LECTURAS", str(d))
    monkeypatch.setattr(C, "DIR_SESIONES", str(tmp_path / "sesiones"))
    monkeypatch.setattr(C, "DIR_TEXT", str(tmp_path / "text"))
    monkeypatch.setattr(C, "F_PROYECTO", str(tmp_path / "PROYECTO.md"))
    monkeypatch.setattr(Q, "leer_bib", lambda: {})
    fs = I.fuentes()
    assert [d_ for _, d_, _ in fs] == ["nota:thilliez-2003"]
    assert any(u["texto"] == "El limite inductivo." for u in fs[0][2])


def test_rango_acota_antes_de_expandir():
    t0 = time.perf_counter()
    assert T.rango("1-99999999999999, 3, 999999999999", 5) == [1, 2, 3, 4, 5]
    assert T.rango("0-2,9-7", 8) == [1, 2, 7, 8]
    assert time.perf_counter() - t0 < 0.5
    with pytest.raises(ValueError):
        T.rango("1-", 5)


def test_coste_sin_precio_completo_no_explota(monkeypatch):
    coste = dict(modelo="x", tokens_in=10, tokens_out=5, tokens_cache=0)
    monkeypatch.setitem(C.PRECIOS, "x", dict(entrada=1.0, cacheada=None, salida=None))
    assert T.coste_eur(coste) is None
    monkeypatch.setitem(C.PRECIOS, "x", dict(entrada=1.0, cacheada=0.1, salida=2.0))
    assert T.coste_eur(coste) is not None


# ----------------------------------------------------------------------
# 8. render
# ----------------------------------------------------------------------

def test_una_marca_pegada_a_un_parentesis_no_se_vuelve_enlace():
    h = render.transcripcion("Entonces f[?](x) es plana y [ILEGIBLE](y) tambien.")
    assert "<a " not in h and h.count('<mark class="duda">') == 2 and "f<mark" in h


def test_una_linea_que_empieza_por_marca_no_desaparece():
    h = render.transcripcion("[ILEGIBLE]: $x>0$\n\nY aqui [ILEGIBLE] otra vez.")
    assert h.count('<mark class="duda">[ILEGIBLE]</mark>') == 2 and "$x&gt;0$" in h


def test_nada_se_cuela_en_un_atributo():
    h = render.transcripcion('![$" onerror="alert(1)$](x.png) y ![foto [?]](y.png "titulo [ILEGIBLE]")')
    assert '" onerror="' not in h and "<mark" not in h.split("<img")[1].split(">")[0]
    assert "<mark" not in h.split("<img")[2].split(">")[0] and h.count("<img") == 2
    assert render.markdown('![$" onerror="alert(1)$](x.png)').count('" onerror="') == 0


def test_las_marcas_en_codigo_quedan_como_texto():
    h = render.transcripcion("`a [?] b` y fuera [?]")
    assert "<code>a [?] b</code>" in h and h.count("<mark") == 1


# ----------------------------------------------------------------------
# 11. el hilo de la web y la ultima llamada
# ----------------------------------------------------------------------

def test_ultima_es_de_cada_hilo(repo):
    M.llamar("ask", "MODO_ASK", [{"role": "user", "content": "q"}])
    mia = dict(M.ULTIMA)
    vistos = {}

    def otro():
        vistos["antes"] = dict(M.ULTIMA)
        M.llamar("transcribir", "MODO_TRANSCRIBIR", [{"role": "user", "content": "p"}], contexto=False)
        vistos["despues"] = M.ULTIMA["comando"]

    h = threading.Thread(target=otro)
    h.start(); h.join(10)
    assert vistos == {"antes": {}, "despues": "transcribir"}
    assert dict(M.ULTIMA) == mia and M.ULTIMA["comando"] == "ask" and M.ULTIMA.get("no-esta") is None
