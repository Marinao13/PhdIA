"""Fase 3 en dos modos: comprension hasta leer el nucleo del corpus, extension despues; base en libros."""
import types
from nucleo import comandos as K
from nucleo import estado as E


def test_modo_comprension_mientras_el_nucleo_no_este_leido(monkeypatch):
    monkeypatch.setattr(K, "_es_base", lambda etiqueta=None: False)
    monkeypatch.setattr(K, "_corpus_siguiente", lambda: ("Thilliez 2003", 0, 8))
    modo, guia = K._modo_ataque()
    assert modo == "comprension" and "reconstruir una prueba" in guia and "0/8" in guia
    assert "Beurling" in guia and "NO toca aun" in guia


def test_modo_extension_con_el_nucleo_leido_o_forzado(monkeypatch):
    monkeypatch.setattr(K, "_es_base", lambda etiqueta=None: False)
    monkeypatch.setattr(K, "_corpus_siguiente", lambda: (None, 8, 8))
    assert K._modo_ataque()[0] == "extension"
    monkeypatch.setattr(K, "_corpus_siguiente", lambda: ("x", 1, 8))
    assert K._modo_ataque("extension")[0] == "extension"
    assert K._modo_ataque("comprension")[0] == "comprension"
    assert K._modo_ataque("cualquiera")[0] == "comprension"     # modo invalido: el automatico


def test_modo_base_en_sesiones_de_libro(monkeypatch):
    monkeypatch.setattr(K, "_es_base", lambda etiqueta=None: True)
    modo, guia = K._modo_ataque("extension")
    assert modo == "base" and "EJERCICIOS" in guia


def test_ataque_en_fase_3_solo_reimprime_la_guia_sin_commit(monkeypatch, capsys):
    monkeypatch.setattr(E, "fase_actual", lambda: ("f3", {}))
    monkeypatch.setattr(K, "_es_base", lambda etiqueta=None: False)
    monkeypatch.setattr(K, "_corpus_siguiente", lambda: ("x", 0, 8))
    monkeypatch.setattr(E, "sellar", lambda etiqueta: (_ for _ in ()).throw(AssertionError("no debe sellar")))
    K.cmd_ataque(types.SimpleNamespace(modo=None))
    out = capsys.readouterr().out
    assert "ya estas en fase 3, ataque de comprension" in out and "sellar 3" in out


def test_siguiente_en_fase_3_nombra_el_modo(monkeypatch):
    monkeypatch.setattr(K, "_es_base", lambda etiqueta=None: False)
    monkeypatch.setattr(K, "_corpus_siguiente", lambda: ("x", 0, 8))
    comando, porque, _ = K._siguiente("f3", True, True, None)
    assert comando == "python doc.py sellar 3" and "ataque de comprension" in porque
