"""lecturas/ID.md por resultado: bloques '## Rn — titulo', nota add, quiz/check sobre un bloque."""
import os
import shutil
import pytest

from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def lecturas(tmp_path, monkeypatch):
    d = tmp_path / "lecturas"
    d.mkdir()
    for f in ("PLANTILLA.md", "PLANTILLA-resultado.md", "thilliez-2003.md"):
        shutil.copy(os.path.join(RAIZ, "lecturas", f), d / f)
    monkeypatch.setattr(C, "DIR_LECTURAS", str(d))
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(K, "_abrir", lambda ruta: None)
    return d


def test_la_nota_migrada_conserva_la_duda_y_tiene_las_secciones_de_paper(lecturas):
    t = (lecturas / "thilliez-2003.md").read_text(encoding="utf-8")
    assert "¿Qué era un límite inductivo?" in K._seccion_md(t, "Dudas")
    for sec in ("Mapa", "Sintesis", "Transferencia", "Abierto", "Dudas", "Dependencias"):
        assert f"## {sec}" in t
    assert K._bloques_nota(t) == []
    import re
    assert not re.search(r"^## (Enunciado principal|Mi explicacion)", t, re.M)


def test_nota_add_inserta_el_bloque_antes_de_sintesis_y_lo_apunta_en_el_mapa(lecturas, capsys):
    K._nota_add("thilliez-2003", "R1 — Teorema 3.2")
    K._nota_add("thilliez-2003", "Lema 2.1.1 (division)")          # sin Rn: numera el siguiente
    t = (lecturas / "thilliez-2003.md").read_text(encoding="utf-8")
    bloques = K._bloques_nota(t)
    assert [(r, ti) for r, ti, _ in bloques] == [("R1", "Teorema 3.2"), ("R2", "Lema 2.1.1 (division)")]
    assert t.index("## R1") < t.index("## R2") < t.index("## Sintesis")
    mapa = K._seccion_md(t, "Mapa")
    assert "- R1 — Teorema 3.2" in mapa and "- R2 — Lema 2.1.1 (division)" in mapa
    for campo in ("Enunciado", "Hipotesis, y por que cada una", "Lema clave", "Que se rompe sin el",
                  "Idea de la prueba", "Donde se usa", "Mi explicacion"):
        assert f"### {campo}" in bloques[0][2]
    assert "[thilliez-2003:pNN]" in bloques[0][2]
    assert "¿Qué era un límite inductivo?" in K._seccion_md(t, "Dudas")   # nada se pierde
    K._nota_add("thilliez-2003", "R1 — otra vez")
    assert "ya existe" in capsys.readouterr().out


def test_numero_impreso_y_subseccion():
    assert K._numero_impreso("Teorema 2.3") == "2.3" and K._numero_impreso("Lemma 2.1.1 (x)") == "2.1.1"
    assert K._numero_impreso("Resultado principal") is None
    cuerpo = "### Enunciado\nA\n\n### Mi explicacion\nB B\n"
    assert K._subseccion_md(cuerpo, "Mi explicacion") == "B B" and K._subseccion_md(cuerpo, "Enunciado") == "A"


def _con_explicacion(lecturas, rid, texto):
    p = lecturas / "thilliez-2003.md"
    t = p.read_text(encoding="utf-8")
    t = t.replace(f"Tu reconstruccion del argumento, con tus palabras. Es lo que lee `nota check --resultado {rid}`.",
                  texto)
    p.write_text(t, encoding="utf-8")


def test_check_por_resultado_usa_la_explicacion_del_bloque(lecturas, monkeypatch, capsys, tmp_path):
    K._nota_add("thilliez-2003", "R1 — Teorema 3.2")
    K._nota_add("thilliez-2003", "R2 — Lema 2.1.1")
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", {}))
    monkeypatch.setattr(C, "F_VERIFICACIONES", str(tmp_path / "verificaciones.md"))
    from nucleo import indice as I
    frag = dict(id="thilliez-2003#0001", fuente="paper", doc="thilliez-2003", pagina=7, seccion="2",
                tipo="lema", label="l", texto="Lemma text", numero="2.1.1")
    monkeypatch.setattr(I, "por_numero", lambda doc, numero: [frag] if numero == "2.1.1" else [])
    monkeypatch.setattr(I, "buscar", lambda *a, **k: [dict(frag, id="thilliez-2003#0002")])
    monkeypatch.setattr(I, "seguir_refs", lambda frags, maximo=4: [])
    enviado = {}

    def llamar(comando, system, messages, max_tokens=None, forzar=False):
        enviado["contenido"] = messages[0]["content"]
        return "1. objecion X (alta): dice A, el texto dice B [thilliez-2003:p7]"
    monkeypatch.setattr(M, "llamar", llamar)
    K._nota_check("thilliez-2003", 12, "R2")
    out = capsys.readouterr().out
    assert "esta vacia" in out and "contenido" not in enviado          # R2 sin explicacion: no llama
    _con_explicacion(lecturas, "R2", "Mi explicacion del lema: " + "palabra " * 60)
    K._nota_check("thilliez-2003", 12, "R2")
    assert enviado["contenido"].startswith("RESULTADO: R2 — Lema 2.1.1")
    assert "Mi explicacion del lema" in enviado["contenido"] and "Lemma text" in enviado["contenido"]
    assert os.path.exists(str(lecturas / f"thilliez-2003-check-R2-{K.HOY}.md"))
    assert "thilliez-2003 R2 (Lema 2.1.1)" in (tmp_path / "verificaciones.md").read_text(encoding="utf-8")
    # sin --resultado y un solo bloque con explicacion: lo elige solo
    enviado.clear()
    K._nota_check("thilliez-2003", 12, None)
    assert enviado["contenido"].startswith("RESULTADO: R2")


def test_quiz_por_resultado_pone_el_foco_y_el_fragmento_del_numero(lecturas, monkeypatch, capsys):
    K._nota_add("thilliez-2003", "R1 — Teorema 3.2")
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", {}))
    from nucleo import indice as I
    frag = dict(id="thilliez-2003#0009", fuente="paper", doc="thilliez-2003", pagina=9, seccion="3",
                tipo="teorema", label="t", texto="Theorem text", numero="3.2")
    monkeypatch.setattr(I, "por_numero", lambda doc, numero: [frag] if numero == "3.2" else [])
    monkeypatch.setattr(I, "buscar", lambda *a, **k: [])
    monkeypatch.setattr(I, "seguir_refs", lambda frags, maximo=4: [])
    enviado = {}
    monkeypatch.setattr(M, "llamar", lambda comando, system, messages, max_tokens=None, forzar=False:
                        enviado.setdefault("c", messages[0]["content"]) and "1. pregunta? [thilliez-2003:p9]")
    K._nota_quiz("thilliez-2003", 12, "R1")
    assert enviado["c"].startswith("RESULTADO: R1 — Teorema 3.2") and "Theorem text" in enviado["c"]
    assert os.path.exists(str(lecturas / f"thilliez-2003-quiz-R1-{K.HOY}.md"))
    K._nota_quiz("thilliez-2003", 12, "R7")
    assert "no hay bloque R7" in capsys.readouterr().out
