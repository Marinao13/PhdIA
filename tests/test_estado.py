"""La puerta del motor: la fase se deriva de los commits de las ultimas 20 h."""
import datetime
import pytest
from nucleo import estado as E

TZ = datetime.datetime.now().astimezone().tzinfo


def t(dia, hm):
    h, m = map(int, hm.split(":"))
    return datetime.datetime(2026, 9, dia, h, m, tzinfo=TZ)


def ciclo(*pares):
    return [(t(d, hm), msg) for d, hm, msg in pares]


NOCHE = [(13, "22:00", "inicio sesion x ::"), (13, "22:35", "sellado :: fase 1 ::"),
         (13, "23:40", "ataque ::"), (14, "00:25", "sellado :: fase 3 ::"), (14, "00:50", "cierre ::")]

CASOS = [
    ("inicio", NOCHE[:1], "f1"),
    ("sello1", NOCHE[:2], "f2"),
    ("ataque cruzando medianoche", NOCHE[:3], "f3"),
    ("sello3 a las 00:25", NOCHE[:4], "f4"),
    ("cierre", NOCHE, "libre"),
    ("cerrado y despues inicio nuevo", [NOCHE[0], NOCHE[4], (14, "09:00", "inicio sesion y ::")], "f1"),
    ("ventana vacia", [], "libre"),
    ("diagnostico sellado equivale a fase 2", [(14, "21:58", "inicio diagnostico ::"),
                                                (14, "21:59", "sellado :: diagnostico ::")], "f2"),
]


@pytest.mark.parametrize("nombre,pares,esperada", CASOS, ids=[c[0] for c in CASOS])
def test_fase(monkeypatch, nombre, pares, esperada):
    monkeypatch.setattr(E, "commits_recientes", lambda: ciclo(*pares))
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)
    fase, _ = E.fase_actual()
    assert fase == esperada


def test_motor_apagado_en_1_y_3():
    assert "f1" not in E.MOTOR_PERMITIDO and "f3" not in E.MOTOR_PERMITIDO
    assert {"libre", "f2", "f4"} <= E.MOTOR_PERMITIDO


def test_fecha_sesion_es_la_del_inicio_del_ciclo_abierto(monkeypatch):
    monkeypatch.setattr(E, "commits_recientes", lambda: ciclo(*NOCHE[:3]))
    assert E.fecha_sesion() == "2026-09-13"


def test_fecha_sesion_es_hoy_si_el_ciclo_esta_cerrado(monkeypatch):
    monkeypatch.setattr(E, "commits_recientes", lambda: ciclo(*NOCHE))
    assert E.fecha_sesion() == datetime.date.today().isoformat()


def test_un_commit_ajeno_no_cambia_la_fase(monkeypatch):
    commits = ciclo(*NOCHE[:2]) + [(t(13, "23:00"), "Merge branch 'claude/x'"),
                                    (t(13, "23:05"), "comando ahora: que toca")]
    monkeypatch.setattr(E, "commits_recientes", lambda: commits)
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)
    assert E.fase_actual()[0] == "f2"


def test_minutos():
    assert E.minutos(t(13, "22:00"), t(13, "22:35")) == 35.0
    assert E.minutos(None, t(13, "22:35")) is None
