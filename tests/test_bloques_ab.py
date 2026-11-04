"""Bloques A, B, C y E de MEJORAS.md: intentos por resultado, eleccion del ataque, repeticion espaciada,
quejas, sincronizacion de los sellados y exportar/importar."""
import datetime
import os
import shutil
import types
import pytest

from nucleo import comandos as K
from nucleo import config as C
from nucleo import corpus as Q
from nucleo import estado as E

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    d = tmp_path / "lecturas"
    d.mkdir()
    for f in ("PLANTILLA.md", "PLANTILLA-resultado.md", "thilliez-2003.md"):
        shutil.copy(os.path.join(RAIZ, "lecturas", f), d / f)
    (tmp_path / "sesiones").mkdir()
    (tmp_path / "registro").mkdir()
    monkeypatch.setattr(C, "DIR_LECTURAS", str(d))
    monkeypatch.setattr(C, "DIR_SESIONES", str(tmp_path / "sesiones"))
    monkeypatch.setattr(C, "DIR_REGISTRO", str(tmp_path / "registro"))
    monkeypatch.setattr(C, "DIR_CONSULTAS", str(tmp_path / "registro" / "consultas"))
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(K, "_abrir", lambda ruta: None)
    monkeypatch.setattr(Q, "leer_bib", lambda: {"thilliez-2003": {"fuente": "paper", "autores": ["Thilliez, Vincent"], "ano": 2003}})
    K._nota_add("thilliez-2003", "R1 — Teorema 3.2")
    K._nota_add("thilliez-2003", "R2 — Lema 2.1.1")
    return tmp_path


def test_registrar_intento_y_leerlos(entorno):
    assert K._registrar_intento("thilliez-2003", "R2", "2026-11-04", 2, 30.5, "thilliez-2003-section-2") == "lecturas/thilliez-2003.md R2"
    K._registrar_intento("thilliez-2003", "R2", "2026-11-20", 3, 25.0, "thilliez-2003-section-3")
    t = (entorno / "lecturas" / "thilliez-2003.md").read_text(encoding="utf-8")
    bloques = {r: c for r, _, c in K._bloques_nota(t)}
    ints = K._intentos(bloques["R2"])
    assert ints == [("2026-11-04", 2, 30.5, "sesion thilliez-2003-section-2"), ("2026-11-20", 3, 25.0, "sesion thilliez-2003-section-3")]
    assert K._intentos(bloques["R1"]) == []
    assert t.count("Intentos:") == 2                                   # una por bloque, no se duplica
    assert K._registrar_intento("thilliez-2003", "R9", "2026-11-04", 1, 1, "x") is None
    # el registro no cuenta como explicacion escrita
    assert not K._explicacion_valida(K._subseccion_flexible(bloques["R2"], "Reconstruccion"))


def test_reconstrucciones_pendientes_por_nivel(entorno):
    K._registrar_intento("thilliez-2003", "R1", "2026-11-01", 1, 20, "s")     # nivel 1: a los 3 dias
    K._registrar_intento("thilliez-2003", "R2", "2026-11-01", 2, 20, "s")     # nivel 2: a los 14 dias
    hoy = datetime.date(2026, 11, 5)
    pend = K._reconstrucciones_pendientes(hoy)
    assert [(p[1], p[4], p[5]) for p in pend] == [("R1", 1, 4)]
    pend = K._reconstrucciones_pendientes(datetime.date(2026, 11, 16))
    assert sorted(p[1] for p in pend) == ["R1", "R2"]


def test_elegir_resultado_el_mas_citado_hoy_o_azar_reproducible(entorno, monkeypatch):
    monkeypatch.setattr(K, "_citas_de_hoy", lambda: ["[thilliez-2003:p7, Lema 2.1.1 | texto: arXiv v1]"] * 2)
    assert K._elegir_resultado("thilliez-2003") == ("R2", "Lema 2.1.1")
    monkeypatch.setattr(K, "_citas_de_hoy", lambda: [])
    a = K._elegir_resultado("thilliez-2003")
    assert a == K._elegir_resultado("thilliez-2003") and a[0] in ("R1", "R2")   # azar con semilla fija
    assert K._elegir_resultado("thilliez-2003", "r1") == ("R1", "Teorema 3.2")
    assert K._elegir_resultado("thilliez-2003", "2.1.1") == ("R2", "Lema 2.1.1")
    assert K._elegir_resultado("thilliez-2003", "4.4") == ("4.4", "4.4")


def test_anotar_ataque_una_vez_bajo_la_cabecera_de_fase_3(entorno):
    s = entorno / "sesiones" / "2026-11-04-thilliez-2003-section-3.md"
    s.write_text("# Sesion\n\n## Fase 2 - Lectura\nnotas\n\n## Fase 3 - Ataque (45 min)\nguia\n\n>>> sellar 3 <<<\n", encoding="utf-8")
    linea = K._anotar_ataque(str(s), ("R2", "Lema 2.1.1"), "comprension")
    assert linea.startswith("Ataque: R2 — Lema 2.1.1")
    t = s.read_text(encoding="utf-8")
    assert t.index("## Fase 3") < t.index("Ataque: R2") < t.index("guia")
    assert K._anotar_ataque(str(s), ("R1", "otro"), "comprension") == linea       # no se repite
    assert t.count("Ataque:") == 1


def test_queja_se_anota_con_fecha_sesion_y_turno(entorno):
    K._anadir_queja("ha inventado una referencia", "thilliez-2003-section-3", 4)
    t = (entorno / "registro" / "quejas.md").read_text(encoding="utf-8")
    assert t.startswith("# Quejas") and f"- {K.HOY} | thilliez-2003-section-3 | turno 4 | ha inventado una referencia" in t


def test_nota_estado_cuenta_campos_e_intentos(entorno, capsys):
    K._registrar_intento("thilliez-2003", "R1", "2026-11-04", 2, 30, "s")
    K._nota_estado("thilliez-2003")
    out = capsys.readouterr().out
    assert "2 bloques" in out and "R1 — Teorema 3.2" in out and "intentos: 1; ultimo 2026-11-04 nivel 2" in out
    assert "campos escritos: 0/8" in out and "Dudas          escrita" in out


class _Git:
    """git falso: registra las llamadas y responde segun un guion."""
    def __init__(self, fallos=()):
        self.llamadas, self.fallos = [], set(fallos)

    def __call__(self, *args, check=False, timeout=None):
        self.llamadas.append(args)
        rc = 1 if args[0] in self.fallos else 0
        out = "origin/master\n" if args[0] == "rev-parse" else ""
        return types.SimpleNamespace(returncode=rc, stdout=out, stderr="")


def _git_falso(monkeypatch, fallos=(), sin_red=False):
    g = _Git(fallos)
    monkeypatch.setattr(E, "git", g)
    monkeypatch.setattr(E, "hay_repo", lambda: True)
    monkeypatch.setattr(E, "SIN_RED", sin_red)
    monkeypatch.setattr(E, "_SINCRONIZADO", None)          # la sincronizacion se cachea por proceso
    return g


def test_sellar_sincroniza_antes_y_empuja_despues(monkeypatch):
    g = _git_falso(monkeypatch)
    ok, msg = E.sellar("sellado :: fase 1 ::")
    assert ok and "AVISO" not in msg
    ordenes = [a[0] for a in g.llamadas]
    assert ordenes.index("fetch") < ordenes.index("merge") < ordenes.index("add") < ordenes.index("commit") < ordenes.index("push")
    # segunda llamada en el mismo proceso: no vuelve a hacer fetch
    n = len(g.llamadas)
    E.sellar("otro ::")
    assert "fetch" not in [a[0] for a in g.llamadas[n:]]


def test_sellar_avisa_sin_red_divergencia_y_arbol_sucio_pero_sella(monkeypatch):
    g = _git_falso(monkeypatch, fallos={"fetch", "push"})
    ok, msg = E.sellar("pausa :: fase 2 ::", vacio_ok=True)
    assert ok and "sin red" in msg and "sin push" in msg
    g = _git_falso(monkeypatch, fallos={"merge", "merge-base"})      # HEAD no es ancestro: divergen
    ok, msg = E.sellar("x ::")
    assert ok and "divergen" in msg
    g = _git_falso(monkeypatch, fallos={"merge"})                    # HEAD es ancestro: arbol sucio
    ok, msg = E.sellar("x ::")
    assert ok and "sellados nuevos" in msg and "esta maquina divergen" not in msg
    g = _git_falso(monkeypatch, sin_red=True)
    E.sellar("y ::")
    assert [a[0] for a in g.llamadas] == ["add", "commit"]


def test_marcar_conserva_el_aviso_del_pull_cuando_no_hay_cambios(monkeypatch):
    class _GitVacio(_Git):
        def __call__(self, *args, check=False, timeout=None):
            r = super().__call__(*args, check=check, timeout=timeout)
            if args[0] == "commit" and "--allow-empty" not in args:
                return types.SimpleNamespace(returncode=1, stdout="nothing to commit", stderr="")
            return r
    g = _GitVacio(fallos={"fetch"})
    monkeypatch.setattr(E, "git", g)
    monkeypatch.setattr(E, "hay_repo", lambda: True)
    monkeypatch.setattr(E, "SIN_RED", False)
    monkeypatch.setattr(E, "_SINCRONIZADO", None)
    ok, msg = E.marcar("pausa :: fase 2 ::")
    assert ok and "sin red" in msg and any("--allow-empty" in a for a in g.llamadas) and "push" in [a[0] for a in g.llamadas]
    ok, msg = E.sellar("sellado :: fase 1 ::")                  # sin vacio_ok: nada que sellar, con el aviso
    assert not ok and "nada que sellar" in msg and "sin red" in msg


def test_exportar_e_importar_mueven_text_e_indice(tmp_path, monkeypatch, capsys):
    origen = tmp_path / "a"
    (origen / "corpus" / "text" / "doc1").mkdir(parents=True)
    (origen / "indice").mkdir()
    (origen / "corpus" / "text" / "doc1" / "unidades.jsonl").write_text('{"n":1}\n', encoding="utf-8")
    (origen / "indice" / "fragmentos.sqlite").write_bytes(b"sqlite")
    monkeypatch.setattr(C, "RAIZ", str(origen))
    K.cmd_exportar(types.SimpleNamespace(destino=str(tmp_path / "z")))
    zips = list((tmp_path / "z").glob("*.zip"))
    assert len(zips) == 1 and "2 ficheros" in capsys.readouterr().out
    destino = tmp_path / "b"
    (destino / "indice").mkdir(parents=True)
    (destino / "indice" / "viejo.npy").write_bytes(b"x")
    monkeypatch.setattr(C, "RAIZ", str(destino))
    K.cmd_importar(types.SimpleNamespace(zip=str(zips[0])))
    assert (destino / "corpus" / "text" / "doc1" / "unidades.jsonl").exists()
    assert (destino / "indice" / "fragmentos.sqlite").exists() and not (destino / "indice" / "viejo.npy").exists()
