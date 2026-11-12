"""`transcribir`: lo que saco la segunda revision del 2026-11-11 (formularios desde un navegador real,
escritura pagina a pagina, indice por pagina, andamiaje de plantilla, guardado de varias paginas)."""
import io
import os
import types
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


@pytest.fixture
def cliente(repo):
    S._TRABAJO.clear()
    yield TestClient(S.app)
    if S._HILO is not None:
        S._HILO.join(20)
    S._TRABAJO.clear()


def _pdf(ruta, paginas=3):
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}")
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


def _pdf_bytes(paginas=2):
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}")
    datos = doc.tobytes()
    doc.close()
    return datos


def _subir(cliente, nombre="apuntes.pdf", **campos):
    r = cliente.post("/transcripciones", files={"fichero": (nombre, _pdf_bytes(), "application/pdf")},
                     data=campos, follow_redirects=False)
    if S._HILO is not None:
        S._HILO.join(20)
    return r


# ----------------------------------------------------------------------
# los formularios desde un navegador de verdad (Origin: null con Referrer-Policy: no-referrer)
# ----------------------------------------------------------------------

def test_un_post_del_propio_sitio_entra_aunque_el_origin_sea_null(cliente):
    r = T.transcribir(_pdf(os.path.join(C.RAIZ, "a.pdf"), paginas=1))
    url = f"/transcripciones/{r['nombre']}/revisado"
    # lo que mandaba Chrome/Firefox/Safari con la politica antigua: 403 en todos los formularios
    ok = cliente.post(url, headers={"Origin": "null", "Sec-Fetch-Site": "same-origin"}, follow_redirects=False)
    assert ok.status_code == 303 and T.leer(r["nombre"])["estado"] == "revisado"
    # con la politica nueva: el Origin de verdad
    ok = cliente.post(url, headers={"Origin": "http://testserver", "Sec-Fetch-Site": "same-origin"},
                      follow_redirects=False)
    assert ok.status_code == 303
    assert cliente.post(url, headers={"Origin": "http://testserver"}, follow_redirects=False).status_code == 303


def test_un_post_ajeno_sigue_sin_entrar(cliente):
    r = T.transcribir(_pdf(os.path.join(C.RAIZ, "a.pdf"), paginas=1))
    url = f"/transcripciones/{r['nombre']}/revisado"
    for cabeceras in ({"Origin": "null"},                                   # sin Sec-Fetch-Site: no se sabe de donde
                      {"Origin": "https://otro.example"},
                      {"Origin": "http://testserver", "Sec-Fetch-Site": "cross-site"},
                      {"Origin": "null", "Sec-Fetch-Site": "same-site"}):
        assert cliente.post(url, headers=cabeceras, follow_redirects=False).status_code == 403, cabeceras
    assert T.leer(r["nombre"])["estado"] == "sin_revisar"


def test_la_politica_de_referrer_no_provoca_origin_null(cliente):
    assert cliente.get("/transcripciones").headers["referrer-policy"] == "same-origin"


# ----------------------------------------------------------------------
# lo pagado esta en disco tras cada pagina
# ----------------------------------------------------------------------

def test_matar_el_proceso_a_media_pasada_deja_lo_hecho_en_disco(repo, monkeypatch):
    real, n = M._completar, []

    def muere_en_la_tercera(*a, **k):
        n.append(1)
        if len(n) == 3:
            raise SystemExit("servidor parado")          # ni Exception ni KeyboardInterrupt: nadie lo recoge
        return real(*a, **k)

    monkeypatch.setattr(M, "_completar", muere_en_la_tercera)
    with pytest.raises(SystemExit):
        T.transcribir(_pdf(repo / "a.pdf", paginas=4), titulo="Tema 1")
    ts = T.listar()
    assert len(ts) == 1 and ts[0]["paginas"] == "1,2" and ts[0]["estado"] == "sin_revisar"
    assert [p for p, _ in T.paginas(ts[0]["cuerpo"])[1]] == [1, 2]
    assert T.leer(ts[0]["nombre"])["original"].endswith(".pdf")       # se puede revisar al lado


def test_si_no_sale_ninguna_pagina_no_queda_el_original_suelto(repo, monkeypatch):
    monkeypatch.setattr(E, "fase_actual", lambda: ("f1", E._marcas_vacias()))
    with pytest.raises(M.MotorApagado):
        T.transcribir(_pdf(repo / "a.pdf"))
    d_orig = repo / "transcripciones" / "originales"
    assert T.listar() == [] and (not d_orig.exists() or os.listdir(d_orig) == [])


def test_retranscribir_desde_originales_no_borra_la_entrada(repo):
    r = T.transcribir(_pdf(repo / "tema1.pdf", paginas=2), titulo="Tema 1")
    original = T.leer(r["nombre"])["original"]
    os.remove(r["ruta"])                                  # salio mal: se borra el .md y se repite desde el original
    r2 = T.transcribir(original, titulo="Tema 1")
    assert r2["nombre"] == r["nombre"] and not r2["sin_original"]
    assert os.path.exists(original) and T.leer(r2["nombre"])["original"] == original


def test_el_comando_para_seguir_conserva_titulo_y_calidad(repo, monkeypatch, capsys):
    real, n = M._completar, []

    def falla_a_la_segunda(*a, **k):
        n.append(1)
        if len(n) == 2:
            raise ConnectionError("sin red")
        return real(*a, **k)

    monkeypatch.setattr(M, "_completar", falla_a_la_segunda)
    K.cmd_transcribir(types.SimpleNamespace(fichero=_pdf(repo / "a.pdf"), tipo="curso", titulo="Tema 3: Carleman",
                                            paginas=None, motor="modelo", calidad="normal", lista=False, revisado=None))
    salida = capsys.readouterr().out
    assert '--paginas 2,3 --tipo curso --titulo "Tema 3: Carleman" --calidad normal' in salida      # alta es el defecto


def test_un_png_de_16_bits_no_llega_en_blanco(repo):
    from PIL import Image
    im = Image.new("I;16", (200, 120), 200 * 256)        # papel gris claro, como lo da un escaner a 16 bits
    for x in range(20, 180):
        for y in range(55, 65):
            im.putpixel((x, y), 30 * 256)                 # trazo oscuro
    im.save(str(repo / "escaner.png"))
    out = Image.open(io.BytesIO(T.pagina_png(str(repo / "escaner.png"), 1))).convert("L")
    ancho, alto = out.size                                # fitz la escala: se mira por proporcion
    assert out.getpixel((ancho // 2, alto // 2)) < 100 < out.getpixel((ancho // 20, alto // 20)) < 250


# ----------------------------------------------------------------------
# indice: cada pagina su fragmento; andamiaje de plantilla fuera; la fuente se actualiza
# ----------------------------------------------------------------------

def test_cada_pagina_de_una_transcripcion_tiene_su_fragmento():
    cuerpo = "# Apuntes\n\n" + "\n\n".join(
        f"<!-- pagina {n} -->\n\n" + " ".join(f"parrafo de la pagina {n} sobre sucesiones peso y clases de Carleman"
                                             for _ in range(4))
        for n in (1, 2, 3, 4))
    frags = I.fragmentar(T.unidades(cuerpo))
    assert [f["pagina"] for f in frags] == [1, 2, 3, 4]
    assert all(f"de la pagina {f['pagina']} " in f["texto"] and f"de la pagina {f['pagina'] % 4 + 1} " not in f["texto"]
               for f in frags)
    # los papers (sin corte_pagina) se siguen agrupando como antes
    us = [dict(pagina=n, seccion="1", tipo="parrafo", label=None, texto=f"texto corto {n}") for n in (1, 2, 3)]
    assert len(I.fragmentar(us)) == 1


def test_el_andamiaje_de_la_plantilla_no_se_indexa_y_lo_tuyo_si(tmp_path, monkeypatch):
    lecturas, sesiones = tmp_path / "lecturas", tmp_path / "sesiones"
    lecturas.mkdir(); sesiones.mkdir()
    (lecturas / "PLANTILLA-resultado.md").write_text(
        "## RN — TITULO\n\n### Enunciado\n(en tu notacion, con las hipotesis completas y la pagina: [ID:pNN])\n\n"
        "### Reconstruccion (fase 3, a ciegas)\n(con todo cerrado menos el enunciado; es lo que lee `nota check --resultado RN`)\n\n"
        "Intentos:\n", encoding="utf-8")
    (lecturas / "PLANTILLA.md").write_text(
        "## Sintesis\nQue hace el paper en tres frases y cual es el resultado que importa para la tesis.\n\n"
        "## Mapa\n<!-- un resultado por linea -->\n", encoding="utf-8")
    (sesiones / "PLANTILLA.md").write_text(
        "## Fase 2 - Lectura asistida\nLagunas de grado/master detectadas (una linea cada una, NO paro a resolverlas):\n",
        encoding="utf-8")
    monkeypatch.setattr(C, "DIR_LECTURAS", str(lecturas))
    monkeypatch.setattr(C, "DIR_SESIONES", str(sesiones))
    pl = I._lineas_plantilla()
    nota = ("## R3 — Lema 2.1.1\n\n### Enunciado\n(en tu notacion, con las hipotesis completas y la pagina: [thilliez-2003:pNN])\n\n"
            "### Hipotesis\n(mg) y (snq) implican (dc)\n\n"
            "### Reconstruccion (fase 3, a ciegas)\n(con todo cerrado menos el enunciado; es lo que lee `nota check --resultado R3`)\n\n"
            "Intentos:\n\n"
            "## Sintesis\nQue hace el paper en tres frases y cual es el resultado que importa para la tesis.\n\n"
            "## Mapa\n<!-- un resultado por linea -->\n- R3 — Lema 2.1.1 (p5): Poisson\n\n"
            "## Fase 2 - Lectura asistida\nLagunas de grado/master detectadas (una linea cada una, NO paro a resolverlas):\n"
            "- Definicion de limite inductivo\n")
    textos = [u["texto"] for u in I._unidades_markdown(nota, pl) if u["tipo"] == "parrafo"]
    assert textos == ["(mg) y (snq) implican (dc)", "- R3 — Lema 2.1.1 (p5): Poisson", "- Definicion de limite inductivo"]
    # sin plantilla (PROYECTO.md) no se quita nada
    assert len([u for u in I._unidades_markdown(nota) if u["tipo"] == "parrafo"]) > len(textos)


def test_indexar_de_punta_a_punta_solo_lo_revisado_y_la_fuente_se_corrige(repo, monkeypatch):
    monkeypatch.setattr(C, "DIR_INDICE", str(repo / "indice"))
    monkeypatch.setattr(I, "F_DB", str(repo / "indice" / "fragmentos.sqlite"))
    monkeypatch.setattr(I, "F_VEC", str(repo / "indice" / "vectores.npy"))
    monkeypatch.setattr(I, "F_VEC_IDS", str(repo / "indice" / "vectores_ids.json"))
    monkeypatch.setattr(C, "DIR_TEXT", str(repo / "text"))
    monkeypatch.setattr(C, "F_PROYECTO", str(repo / "PROYECTO.md"))
    monkeypatch.setattr(C, "DIR_LECTURAS", str(repo / "lecturas"))
    monkeypatch.setattr(C, "DIR_SESIONES", str(repo / "sesiones"))
    monkeypatch.setattr(Q, "leer_bib", lambda: {})
    largo = " ".join("Sea M una sucesion peso fuertemente regular y gamma(M) su indice de crecimiento." for _ in range(6))
    monkeypatch.setattr(M, "_completar", lambda *a, **k: (largo, 100, 200, 0, {}))
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=2), tipo="paper", titulo="Apuntes")
    assert I.indexar(verbose=False)[0] == 0                              # sin revisar: nada
    T.marcar_revisado(r["nombre"])
    total, nuevos = I.indexar(verbose=False)
    assert total == 2 and nuevos == 2
    doc = "transcripcion:" + r["nombre"]
    assert [f["pagina"] for f in I.por_pagina(doc, 2)] == [2] and I.por_pagina(doc, 1)[0]["fuente"] == "nota"
    assert I._cargar(fuente="curso") == [] and len(I._cargar(fuente="nota")) == 2      # el filtro de buscar --fuente
    # era un curso: se corrige `tipo:` a mano y se vuelve a indexar, sin re-embeber
    t = open(r["ruta"], encoding="utf-8").read().replace("tipo: paper", "tipo: curso")
    open(r["ruta"], "w", encoding="utf-8", newline="\n").write(t)
    total, nuevos = I.indexar(verbose=False)
    assert (total, nuevos) == (2, 0)
    assert {f["doc"] for f in I._cargar(fuente="curso")} == {doc} and I._cargar(fuente="nota") == []
    # y si se borra la transcripcion, sus fragmentos salen del indice
    os.remove(r["ruta"])
    assert I.indexar(verbose=False)[0] == 0


# ----------------------------------------------------------------------
# web: nombres con acentos, guardar varias paginas, lo tuyo rotulado en buscar
# ----------------------------------------------------------------------

def test_el_nombre_subido_conserva_los_acentos(cliente):
    _subir(cliente, nombre="Análisis armónico tema 3.pdf")
    t = T.listar()[0]
    assert t["origen"] == "Análisis armónico tema 3.pdf" and t["titulo"] == "Análisis armónico tema 3"
    assert t["nombre"].endswith("-analisis-armonico-tema-3")
    _subir(cliente, nombre="..\\..\\raro<>|.pdf")
    assert sorted(x["origen"] for x in T.listar())[-1] == "raro___.pdf"


def test_guardar_cambios_guarda_todas_las_paginas_corregidas_y_solo_esas(cliente):
    _subir(cliente, paginas="1-2", nombre="tres.pdf")
    nombre = T.listar()[0]["nombre"]
    html = cliente.get(f"/transcripciones/{nombre}").text
    # un solo formulario: el boton "La he revisado" tambien lo envia (form="paginas"), para no perder lo sin guardar
    assert 'name="texto_1"' in html and 'name="texto_2"' in html and html.count("<form") == 1
    assert 'form="paginas" name="accion" value="revisado"' in html and '<form id="paginas"' in html
    hojas = dict(T.paginas(T.leer(nombre)["cuerpo"])[1])
    h = {n: S._huella_texto(t) for n, t in hojas.items()}
    # entretanto, la pagina 2 se corrige en VS Code
    assert T.guardar_pagina(nombre, 2, "corregida en VS Code")
    # y en el navegador (con la pagina 2 vieja en su textarea) solo se toca la 1
    r = cliente.post(f"/transcripciones/{nombre}/paginas", follow_redirects=False, data={
        "h_1": h[1], "texto_1": hojas[1].replace("\n", "\r\n") + "\r\nlinea nueva",
        "h_2": h[2], "texto_2": hojas[2].replace("\n", "\r\n"), "ancla": "1"})
    assert r.status_code == 303 and r.headers["location"].endswith("aviso=guardada#p1")
    despues = dict(T.paginas(T.leer(nombre)["cuerpo"])[1])
    assert despues[1] == hojas[1] + "\nlinea nueva" and despues[2] == "corregida en VS Code"
    # corregir las dos a la vez: se guardan las dos
    h = {n: S._huella_texto(t) for n, t in despues.items()}
    cliente.post(f"/transcripciones/{nombre}/paginas", follow_redirects=False, data={
        "h_1": h[1], "texto_1": "uno", "h_2": h[2], "texto_2": "dos", "ancla": "2"})
    assert dict(T.paginas(T.leer(nombre)["cuerpo"])[1]) == {1: "uno", 2: "dos"}
    # sin cambios no se escribe nada
    antes = open(T.leer(nombre)["ruta"], encoding="utf-8").read()
    r = cliente.post(f"/transcripciones/{nombre}/paginas", follow_redirects=False, data={
        "h_1": S._huella_texto("uno"), "texto_1": "uno", "h_2": S._huella_texto("dos"), "texto_2": "dos"})
    assert r.headers["location"].endswith("aviso=sincambios")
    assert open(T.leer(nombre)["ruta"], encoding="utf-8").read() == antes
    assert cliente.post("/transcripciones/no-existe/paginas", data={"texto_1": "x"},
                        follow_redirects=False).status_code == 404


def test_buscar_en_la_web_rotula_lo_tuyo_y_no_lo_ofrece_como_paper(cliente, monkeypatch):
    frags = [dict(id="transcripcion:x#0000", fuente="curso", doc="transcripcion:x", pagina=2, seccion="Tema 1",
                  tipo="parrafo", label=None, numero=None, texto="Sea $M$ una sucesion peso.", bm25=3.2, coseno=None),
             dict(id="t#0000", fuente="paper", doc="t", pagina=3, seccion="1", tipo="lema", label=None,
                  numero="2.1", texto="Let M be a weight sequence.", bm25=2.0, coseno=None)]
    monkeypatch.setattr(I, "buscar", lambda *a, **k: [dict(f) for f in frags])
    html = cliente.get("/buscar?q=sucesion").text
    assert "tuyo: curso" in html and html.count("preguntar sobre") == 1
    assert "/preguntar?doc=t" in html and "/preguntar?doc=transcripcion" not in html
