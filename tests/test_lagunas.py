"""Lagunas de base durante la lectura de papers: una linea en registro/lagunas.md, sin parar."""
from nucleo import comandos as K
from nucleo import config as C


def test_anadir_lagunas_escribe_bajo_pendientes_con_origen_y_fase(tmp_path, monkeypatch):
    f = tmp_path / "lagunas.md"
    f.write_text("# Lagunas\n\n## Pendientes\n\n- [ ] 2026-09-01 | diagnostico | - | vieja\n\n## Resueltas\n",
                 encoding="utf-8")
    monkeypatch.setattr(C, "F_LAGUNAS", str(f))
    n = K._anadir_lagunas(["Phragmen-Lindelof en un sector: no recuerdo el papel de la apertura"],
                          "thilliez-2003", "f2")
    t = f.read_text(encoding="utf-8")
    assert n == 1
    nuevas = [l for l in t.splitlines() if "Phragmen" in l]
    assert len(nuevas) == 1 and nuevas[0].startswith("- [ ] ") and "| thilliez-2003 | f2 |" in nuevas[0]
    assert t.index("Phragmen") < t.index("vieja") < t.index("## Resueltas")   # arriba de Pendientes
    assert K._anadir_lagunas([], "x") == 0
    pend, estr = K._cuenta_lagunas()
    assert (pend, estr) == (2, 0)


def test_anadir_lagunas_crea_la_seccion_si_no_existe(tmp_path, monkeypatch):
    f = tmp_path / "lagunas.md"
    f.write_text("# Lagunas\n", encoding="utf-8")
    monkeypatch.setattr(C, "F_LAGUNAS", str(f))
    K._anadir_lagunas(["a", "b"], "preguntar", "f2")
    t = f.read_text(encoding="utf-8")
    assert "## Pendientes" in t and t.count("- [ ] ") == 2
