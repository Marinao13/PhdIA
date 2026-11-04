"""`leido`: la casilla de corpus/orden.md por id; `ahora` ve lo que esta en curso por las sesiones."""
import types
from nucleo import comandos as K
from nucleo import config as C
from nucleo import corpus as Q

ORDEN = """# Corpus

## Nucleo, en este orden

- [ ] Thilliez, Results Math 44 (2003) 169-188 -- sucesiones fuertemente regulares
- [ ] Thilliez, Monatsh. Math. 160 (2010) 4, 443-453 -- EL teorema
- [ ] Jimenez-Garrido, Sanz, Schindl, Results Math 74:27 (2019)

## Registro de normalizaciones
"""
BIB = {"thilliez-2003": dict(fuente="paper", autores=["Thilliez, Vincent"], ano=2003),
       "thilliez-2010": dict(fuente="paper", autores=["Thilliez, Vincent"], ano=2010),
       "jimenez-garrido-sanz-schindl-2019-injectivity": dict(fuente="paper", autores=["Jimenez-Garrido, Javier"], ano=2019),
       "jimenez-garrido-sanz-schindl-2019-sectorial": dict(fuente="paper", autores=["Jimenez-Garrido, Javier"], ano=2019)}


def test_marcar_leido_cambia_solo_la_casilla_del_paper(tmp_path, monkeypatch):
    f = tmp_path / "orden.md"
    f.write_text(ORDEN, encoding="utf-8")
    monkeypatch.setattr(C, "F_ORDEN", str(f))
    monkeypatch.setattr(Q, "leer_bib", lambda: BIB)
    assert K._marcar_leido("thilliez-2003") == "- [~] Thilliez, Results Math 44 (2003) 169-188 -- sucesiones fuertemente regulares"
    t = f.read_text(encoding="utf-8")
    assert "- [~] Thilliez, Results Math 44" in t and "- [ ] Thilliez, Monatsh" in t
    assert K._marcar_leido("thilliez-2010", frio=True).startswith("- [x] Thilliez, Monatsh")
    assert K._marcar_leido("jimenez-garrido-sanz-schindl-2019-sectorial") is None      # la linea casa con dos ids
    assert K._marcar_leido("balser-2000") is None
    sig, hechos, total = K._corpus_siguiente()
    assert (hechos, total) == (2, 3) and sig.startswith("Jimenez-Garrido")


def test_sesiones_por_doc_ve_las_cerradas_y_las_abiertas(tmp_path, monkeypatch):
    d = tmp_path / "sesiones"
    d.mkdir()
    (d / "2026-10-07-thilliez-2003-section-2.md").write_text("---\ncoincidencia_estructural: 2\n---\n", encoding="utf-8")
    (d / "2026-10-20-thilliez-2010-section-1.md").write_text("---\ncoincidencia_estructural:\n---\n", encoding="utf-8")
    (d / "2026-09-14-diagnostico.md").write_text("x", encoding="utf-8")
    (d / "2026-09-15-base-conway-iv.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(C, "DIR_SESIONES", str(d))
    monkeypatch.setattr(Q, "leer_bib", lambda: BIB)
    ses = K._sesiones_por_doc()
    assert ses == {"thilliez-2003": [("2026-10-07", "thilliez-2003-section-2", True)],
                   "thilliez-2010": [("2026-10-20", "thilliez-2010-section-1", False)]}


def test_cmd_leido_avisa_si_no_casa(tmp_path, monkeypatch, capsys):
    f = tmp_path / "orden.md"
    f.write_text(ORDEN, encoding="utf-8")
    monkeypatch.setattr(C, "F_ORDEN", str(f))
    monkeypatch.setattr(Q, "leer_bib", lambda: BIB)
    K.cmd_leido(types.SimpleNamespace(id="thilliez-2003", frio=False))
    K.cmd_leido(types.SimpleNamespace(id="otro-2000", frio=False))
    out = capsys.readouterr().out
    assert "corpus/orden.md: - [~] Thilliez" in out and "cambia la casilla a mano" in out
