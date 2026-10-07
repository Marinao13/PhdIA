"""La puerta del motor: la fase se deriva del ultimo ciclo del git log; las pausas paran el reloj."""
import datetime
import pytest
from nucleo import estado as E

TZ = datetime.datetime.now().astimezone().tzinfo


def t(dia, hm, mes=9):
    h, m = map(int, hm.split(":"))
    return datetime.datetime(2026, mes, dia, h, m, tzinfo=TZ)


def ciclo(*pares):
    return [(t(d, hm), msg) for d, hm, msg in pares]


NOCHE = [(13, "22:00", "inicio sesion x ::"), (13, "22:35", "sellado :: fase 1 ::"),
         (13, "23:40", "ataque ::"), (14, "00:25", "sellado :: fase 3 ::"), (14, "00:50", "cierre ::")]

EN = t(14, "01:00")      # "ahora" para los casos de la noche del 13

CASOS = [
    ("inicio", NOCHE[:1], "f1"),
    ("sello1", NOCHE[:2], "f2"),
    ("ataque cruzando medianoche", NOCHE[:3], "f3"),
    ("sello3 a las 00:25", NOCHE[:4], "f4"),
    ("cierre", NOCHE, "libre"),
    ("cerrado y despues inicio nuevo", [NOCHE[0], NOCHE[4], (14, "00:55", "inicio sesion y ::")], "f1"),
    ("historial vacio", [], "libre"),
    ("diagnostico sellado equivale a fase 2", [(13, "21:58", "inicio diagnostico ::"),
                                                (13, "21:59", "sellado :: diagnostico ::")], "f2"),
]


def _fija(monkeypatch, commits, en=EN):
    monkeypatch.setattr(E, "commits_todos", lambda: commits)
    monkeypatch.setattr(E, "ahora", lambda: en)
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)


@pytest.mark.parametrize("nombre,pares,esperada", CASOS, ids=[c[0] for c in CASOS])
def test_fase(monkeypatch, nombre, pares, esperada):
    _fija(monkeypatch, ciclo(*pares))
    fase, _ = E.fase_actual()
    assert fase == esperada


def test_motor_apagado_en_1_y_3():
    assert "f1" not in E.MOTOR_PERMITIDO and "f3" not in E.MOTOR_PERMITIDO
    assert {"libre", "f2", "f4"} <= E.MOTOR_PERMITIDO


def test_fecha_sesion_es_la_del_inicio_del_ciclo_abierto(monkeypatch):
    monkeypatch.setattr(E, "commits_todos", lambda: ciclo(*NOCHE[:3]))
    monkeypatch.setattr(E, "ahora", lambda: EN)
    assert E.fecha_sesion() == "2026-09-13"


def test_fecha_sesion_es_hoy_si_el_ciclo_esta_cerrado(monkeypatch):
    monkeypatch.setattr(E, "commits_todos", lambda: ciclo(*NOCHE))
    monkeypatch.setattr(E, "ahora", lambda: EN)
    assert E.fecha_sesion() == datetime.date.today().isoformat()


def test_un_commit_ajeno_no_cambia_la_fase_ni_la_mantiene_viva(monkeypatch):
    commits = ciclo(*NOCHE[:2]) + [(t(13, "23:00"), "Merge branch 'claude/x'"),
                                    (t(13, "23:05"), "comando ahora: que toca")]
    _fija(monkeypatch, commits)
    fase, m = E.fase_actual()
    assert fase == "f2" and m["ultimo"] == t(13, "22:35")


def test_sesion_sin_cerrar_caduca_a_las_20_h_de_su_ultima_marca(monkeypatch):
    _fija(monkeypatch, ciclo(*NOCHE[:2]), en=t(14, "19:00"))     # 20 h 25 min tras el sello 1
    fase, m = E.fase_actual()
    assert fase == "libre" and m["caducado"]
    _fija(monkeypatch, ciclo(*NOCHE[:2]), en=t(14, "18:00"))     # 19 h 25 min: sigue viva
    assert E.fase_actual()[0] == "f2"


def test_pausa_en_fase_2_no_cambia_la_fase_y_la_sesion_no_caduca(monkeypatch):
    commits = ciclo(*NOCHE[:2]) + [(t(13, "23:00"), "pausa :: fase 2 :: 2026-09-13 23:00")]
    _fija(monkeypatch, commits, en=t(17, "10:00"))               # tres dias y medio despues
    fase, m = E.fase_actual()
    assert fase == "f2" and m["pausada"] and not m["caducado"]
    assert E.horas_pausada(m, t(17, "10:00")) == 83.0
    assert E.horas_pausada(m, t(17, "10:00")) > E.PAUSA_AVISO_HORAS
    assert E.fecha_sesion() == "2026-09-13"


def test_pausa_en_fase_1_mantiene_el_motor_apagado(monkeypatch):
    commits = ciclo(NOCHE[0]) + [(t(13, "22:10"), "pausa :: fase 1 ::")]
    _fija(monkeypatch, commits, en=t(15, "09:00"))
    fase, m = E.fase_actual()
    assert fase == "f1" and fase not in E.MOTOR_PERMITIDO and m["pausada"]


def test_reanudar_vuelve_a_poner_el_reloj_y_la_ventana_cuenta_desde_ahi(monkeypatch):
    commits = ciclo(*NOCHE[:2]) + [(t(13, "23:00"), "pausa :: fase 2 ::"),
                                    (t(16, "09:00"), "reanudacion :: fase 2 ::")]
    _fija(monkeypatch, commits, en=t(16, "12:00"))
    fase, m = E.fase_actual()
    assert fase == "f2" and not m["pausada"] and m["pausas"] == [[t(13, "23:00"), t(16, "09:00")]]
    _fija(monkeypatch, commits, en=t(17, "06:00"))               # 21 h tras reanudar, sin marcas: caduca
    assert E.fase_actual()[0] == "libre"


def test_min_f1_y_min_f3_suman_los_tramos_y_descuentan_las_pausas():
    pausas = [[t(13, "22:10"), t(13, "22:30")], [t(13, "23:50"), t(14, "00:05")]]
    # fase 1: 22:00 -> 22:35 son 35 min, menos 20 de pausa = 15
    assert E.minutos_netos(t(13, "22:00"), t(13, "22:35"), pausas) == 15.0
    # fase 3: 23:40 -> 00:25 son 45 min, menos 15 de pausa = 30
    assert E.minutos_netos(t(13, "23:40"), t(14, "00:25"), pausas) == 30.0
    # una pausa fuera del tramo no resta nada; sin pausas, igual que minutos()
    assert E.minutos_netos(t(13, "22:00"), t(13, "22:35"), [[t(13, "23:00"), t(13, "23:30")]]) == 35.0
    assert E.minutos_netos(t(13, "22:00"), t(13, "22:35")) == E.minutos(t(13, "22:00"), t(13, "22:35"))
    # pausa sin reanudar: cuenta hasta `en`
    assert E.minutos_netos(t(13, "22:00"), t(13, "22:35"), [[t(13, "22:20"), None]], en=t(13, "22:35")) == 20.0
    assert E.minutos_netos(None, t(13, "22:35"), pausas) is None


def test_pausa_doble_y_reanudacion_sin_pausa_se_ignoran(monkeypatch):
    commits = ciclo(*NOCHE[:2]) + [(t(13, "22:40"), "reanudacion :: fase 2 ::"),
                                    (t(13, "23:00"), "pausa :: fase 2 ::"),
                                    (t(13, "23:10"), "pausa fase 2 (a mano)")]
    _fija(monkeypatch, commits, en=t(14, "01:00"))
    fase, m = E.fase_actual()
    assert fase == "f2" and m["pausas"] == [[t(13, "23:00"), None]] and m["pausada"]


def test_minutos():
    assert E.minutos(t(13, "22:00"), t(13, "22:35")) == 35.0
    assert E.minutos(None, t(13, "22:35")) is None
