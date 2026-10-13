"""nucleo/motor.py: tope por comando, deteccion de respuesta cortada, registro con segundos."""
import json
import types
import pytest

from nucleo import motor as M
from nucleo import config as C
from nucleo import estado as E


class _Uso:
    def __init__(self, tin, tout, cache=0, razonamiento=0):
        self.input_tokens, self.output_tokens = tin, tout
        self.input_tokens_details = types.SimpleNamespace(cached_tokens=cache)
        self.output_tokens_details = types.SimpleNamespace(reasoning_tokens=razonamiento)


class _Respuesta:
    def __init__(self, texto, status="completed", razon=None, **kw):
        self.output_text, self.status = texto, status
        self.incomplete_details = types.SimpleNamespace(reason=razon) if razon else None
        self.usage = _Uso(**kw)


class _ClienteFalso:
    def __init__(self, respuesta):
        self.kw = None
        self.responses = types.SimpleNamespace(create=self._create)
        self._r = respuesta

    def _create(self, **kw):
        self.kw = kw
        return self._r


def test_openai_detecta_el_corte_por_max_output_tokens(monkeypatch):
    cli = _ClienteFalso(_Respuesta("a mitad de \\(2^m", status="incomplete", razon="max_output_tokens",
                                   tin=1600, tout=1500, cache=1200, razonamiento=900))
    monkeypatch.setattr(M, "_cliente", cli)
    texto, tin, tout, cache, extra = M._completar_openai("sys", [{"role": "user", "content": "q"}],
                                                         1500, "gpt-6-astra", "low")
    assert texto.startswith("a mitad") and (tin, tout, cache) == (1600, 1500, 1200)
    assert extra == dict(cortada=True, razonamiento=900)
    assert cli.kw["max_output_tokens"] == 1500 and cli.kw["reasoning"] == {"effort": "low"}


def test_openai_respuesta_completa_no_es_cortada(monkeypatch):
    monkeypatch.setattr(M, "_cliente", _ClienteFalso(_Respuesta("ok", tin=10, tout=5)))
    _, _, _, _, extra = M._completar_openai("s", [], 100, "m", None)
    assert extra == dict(cortada=False, razonamiento=0)


def test_tope_por_comando():
    assert C.max_tokens_para("preguntar") == C.MAX_TOKENS_POR_COMANDO["preguntar"] >= 4000
    assert C.max_tokens_para("otro") == C.MAX_TOKENS_CHAT
    assert C.esfuerzo_para("preguntar") == "low"


def test_llamar_registra_segundos_cortada_y_tope(tmp_path, monkeypatch):
    log = tmp_path / "llamadas.jsonl"
    monkeypatch.setattr(C, "F_LLAMADAS", str(log))
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", {}))
    monkeypatch.setattr(M, "contexto_vivo", lambda: "")
    texto = M.llamar("preguntar", "SYS", [{"role": "user", "content": "hola"}])     # DOC_SIMULAR=1
    assert texto.startswith("[SIMULADO]")
    fila = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    for k in ("segundos", "cortada", "tokens_razonamiento", "max_tokens", "esfuerzo"):
        assert k in fila
    assert fila["max_tokens"] == C.max_tokens_para("preguntar") and fila["cortada"] is False
    assert M.ULTIMA["comando"] == "preguntar" and M.ULTIMA["max_tokens"] == fila["max_tokens"]


def test_imprimir_consola_convierte_el_latex(capsys):
    M.imprimir(r"Sea \(x\le y\).", consola=True)
    out = capsys.readouterr().out
    assert "\\(" not in out and ("≤" in out or "<=" in out)


def test_esperando_no_rompe_sin_terminal(capsys):
    with M.esperando("pensando..."):
        pass
    assert "pensando" in capsys.readouterr().out
