"""Los comandos de doc.py. Cada uno es una funcion cmd_*(args)."""
import os, re, sys, glob, json, time, types, datetime, statistics as st
from collections import Counter, defaultdict

from . import config as C
from . import estado as E
from . import motor as M
from . import prompts as P

HOY = datetime.date.today().isoformat()


def _pon(texto, clave, valor):
    """Fija `clave: valor` en el frontmatter de una sesion."""
    patron = re.compile(rf"^{re.escape(clave)}:.*$", re.M)
    linea = f"{clave}: {valor}"
    return patron.sub(linea, texto, count=1) if patron.search(texto) else texto


def _seccion_pendientes(texto):
    """Lineas '- [ ] ...' bajo '## Pendientes' en lagunas.md."""
    m = re.search(r"^## Pendientes\s*$(.*?)(?=^## |\Z)", texto, re.M | re.S)
    if not m:
        return []
    return [l for l in m.group(1).splitlines() if l.strip().startswith("- [ ]")]


def _tema(linea):
    cuerpo = linea.split("]", 1)[-1]
    cuerpo = cuerpo.split("|")[-1]
    return cuerpo.split(":")[0].strip().lower()


def _anadir_tarjetas(tarjetas, origen):
    if not tarjetas:
        return 0
    lineas = [f"{t['p'].strip()} :: {t['r'].strip()}" for t in tarjetas
              if t.get("p") and t.get("r")]
    C.anadir(C.F_PENDIENTES, f"\n<!-- {HOY} {origen} -->\n" + "\n".join(lineas) + "\n")
    return len(lineas)


def _anadir_queja(texto, origen, turno):
    """Una linea en registro/quejas.md: fecha | sesion | turno | queja. Se revisan en lote (MEJORAS 6)."""
    ruta = os.path.join(C.DIR_REGISTRO, "quejas.md")
    if not os.path.exists(ruta):
        C.escribir(ruta, "# Quejas sobre las respuestas\n\nUna linea por queja, desde `preguntar` con `/queja texto`. "
                         "El turno localiza la respuesta en registro/consultas/FECHA-preguntar.jsonl. "
                         "Se revisan en lote cada mes o cada diez: cambio de regla con test y pasada de control.\n\n")
    C.anadir(ruta, f"- {HOY} | {origen} | turno {turno} | {texto.strip()}\n")


def _anadir_lagunas(lagunas, origen, fase="-"):
    if not lagunas:
        return 0
    texto = C.leer(C.F_LAGUNAS)
    nuevas = "".join(f"- [ ] {HOY} | {origen} | {fase} | {l.strip()}\n" for l in lagunas)
    if "## Pendientes" in texto:
        texto = texto.replace("## Pendientes\n", "## Pendientes\n\n" + nuevas, 1)
    else:
        texto += "\n## Pendientes\n\n" + nuevas
    C.escribir(C.F_LAGUNAS, texto)
    return len(lagunas)


def _es_base(etiqueta=None):
    """True si la sesion (o la etiqueta dada) es de fase base: 'base-...'."""
    if etiqueta is None:
        ruta = E.sesion_hoy()
        etiqueta = os.path.basename(ruta)[11:-3] if ruta else ""
    return etiqueta.startswith("base-")


def _sistema(prompt):
    """El system de una llamada: con la nota de base si la sesion es de base."""
    return prompt + P.NOTA_BASE if _es_base() else prompt


def _plantilla_para(etiqueta):
    """Plantilla de sesion segun la etiqueta: la de base para 'base-*'."""
    if _es_base(etiqueta) and os.path.exists(C.F_PLANTILLA_BASE):
        return C.F_PLANTILLA_BASE
    return C.F_PLANTILLA


def _hay_entrada_pendiente():
    """True si quedan lineas ya tecleadas (o pegadas) sin leer en stdin."""
    try:
        import msvcrt
        return bool(msvcrt.kbhit())
    except ImportError:
        import select
        return bool(select.select([sys.stdin], [], [], 0)[0])


def _leer_lineas(prompt, pendiente=_hay_entrada_pendiente):
    """
    Lee una linea. Si inmediatamente hay mas esperando -- un pegado de varias
    lineas -- las lee todas. Devuelve la lista, sin recortar.
    """
    lineas = [input(prompt)]
    try:
        while pendiente():
            lineas.append(input())
    except (EOFError, OSError):
        pass
    return lineas


# ======================================================================
# sesion / sellar / ataque / estado
# ======================================================================

def cmd_sesion(args):
    etiqueta = "-".join(args.etiqueta)
    E.sincronizar_antes()                      # otra maquina pudo sellar: la fase se lee tras traerlo
    if E.sesion_hoy():
        print("ya hay sesion hoy:", os.path.relpath(E.sesion_hoy(), C.RAIZ))
        return
    destino = os.path.join(C.DIR_SESIONES, f"{HOY}-{etiqueta}.md")
    texto = C.leer(_plantilla_para(etiqueta)).replace("AAAA-MM-DD", HOY).replace("ETIQUETA", etiqueta)
    C.escribir(destino, texto)
    ok, msg = E.sellar(f"inicio sesion {etiqueta} ::")
    print("creada", os.path.relpath(destino, C.RAIZ))
    print(msg if ok else f"aviso: {msg}")
    M.aviso("\nMOTOR APAGADO. Fase 0 (10 min) y fase 1 (25 min) por escrito.\n"
            "Cuando termines el intento a ciegas:  python doc.py sellar 1")
    _abrir(destino)


def cmd_sellar(args):
    E.sincronizar_antes()
    fase, marcas = E.fase_actual()
    n = args.fase
    if n == 1 and fase != "f1":
        print(f"la fase 1 ya esta sellada o no hay sesion hoy (fase actual: {fase})")
        return
    if n == 3 and fase != "f3":
        print("para sellar la fase 3 antes tienes que haberla empezado:  python doc.py ataque")
        return
    ok, msg = E.sellar(f"sellado :: fase {n} ::")
    print(msg if ok else msg)
    if ok and n == 1:
        t = E.minutos_netos(marcas["inicio"], E.ahora(), marcas["pausas"])
        M.aviso(f"\nfase 1 sellada tras {t} min (pausas descontadas). MOTOR ENCENDIDO.  python doc.py preguntar")
    if ok and n == 3:
        t = E.minutos_netos(marcas["ataque"], E.ahora(), marcas["pausas"])
        M.aviso(f"\nfase 3 sellada tras {t} min (pausas descontadas). MOTOR ENCENDIDO.  python doc.py cierre")


def _aviso_pausa(marcas):
    """Linea de aviso si la sesion esta pausada; None si no."""
    h = E.horas_pausada(marcas)
    if h is None:
        return None
    desde = marcas["pausas"][-1][0].strftime("%Y-%m-%d %H:%M")
    linea = f"SESION PAUSADA desde {desde} ({h} h). Reanuda con:  python doc.py reanudar"
    if h > E.PAUSA_AVISO_HORAS:
        linea += (f"\n  AVISO: mas de {E.PAUSA_AVISO_HORAS} h en pausa. Reanuda y termina el ciclo, "
                  "o cierra la sesion (python doc.py cierre) y abre otra: una sesion que no se "
                  "retoma pierde el intento a ciegas.")
    return linea


def cmd_pausar(args):
    """Para el reloj de la sesion sin cambiar de fase. El commit lleva la fase para que se lea en el log."""
    E.sincronizar_antes()
    fase, marcas = E.fase_actual()
    if fase == "libre":
        print("no hay sesion abierta que pausar")
        return
    if marcas["pausada"]:
        print(_aviso_pausa(marcas))
        return
    ok, msg = E.marcar(f"pausa :: fase {fase[1]} ::")
    print(msg)
    if ok:
        print(f"sesion pausada en fase {fase[1]}. La fase y el motor no cambian; el tiempo en pausa "
              "no cuenta en min_f1/min_f3 y la sesion no caduca.\n"
              "Para seguir:  python doc.py reanudar")


def cmd_reanudar(args):
    E.sincronizar_antes()
    fase, marcas = E.fase_actual()
    if fase == "libre":
        print("no hay sesion abierta")
        return
    if not marcas["pausada"]:
        print(f"la sesion no esta pausada (fase actual: {fase})")
        return
    h = E.horas_pausada(marcas)
    ok, msg = E.marcar(f"reanudacion :: fase {fase[1]} ::")
    print(msg)
    if ok:
        print(f"reanudada tras {h} h de pausa, en fase {fase[1]}.")
        hay_diagnostico = any(m.startswith("sellado :: diagnostico") for _, m in E.commits_todos())
        comando, porque, _ = _siguiente(fase, E.sesion_hoy() is not None, hay_diagnostico, _semana_base())
        print(f"te toca:  {comando}\n  {porque}")


def _citas_de_hoy():
    """Citas del corpus de los turnos de preguntar de la sesion en curso (la fecha del inicio,
    que es la del fichero de registro/consultas aunque la sesion cruce la medianoche)."""
    citas = []
    ruta = os.path.join(C.DIR_CONSULTAS, f"{E.fecha_sesion()}-preguntar.jsonl")
    if os.path.exists(ruta):
        for l in C.leer(ruta).splitlines():
            try:
                citas += json.loads(l).get("citas") or []
            except (ValueError, AttributeError):
                pass
    return citas


def _elegir_resultado(doc, forzado=None):
    """
    (etiqueta, titulo) del resultado que se ataca hoy: lo elige el sistema, no Mariano.
    Candidatos: los bloques R de la nota del paper; si no hay, los enunciados numerados del
    indice. Gana el mas citado en los turnos de preguntar de hoy; si ninguno, uno al azar con
    semilla = fecha (reproducible). `forzado` ('R2' o '2.3') manda.
    """
    from . import indice as I
    from .corpus import NOMBRE_ES
    cands = []
    if doc and os.path.exists(_ruta_nota(doc)):
        cands = [(rid, titulo) for rid, titulo, _ in _bloques_nota(C.leer(_ruta_nota(doc)))]
    if not cands and doc:
        vistos = set()
        for f in sorted(I._cargar(doc=doc), key=lambda f: f["id"]):
            if f.get("numero") and f.get("tipo") in ("teorema", "lema", "proposicion", "corolario") \
                    and (f["tipo"], f["numero"]) not in vistos:
                vistos.add((f["tipo"], f["numero"]))
                titulo = f"{NOMBRE_ES.get(f['tipo'], f['tipo'])} {f['numero']}"
                cands.append((titulo, titulo))        # sin nota: la etiqueta es el titulo ("Teorema 3")
    if forzado:
        f = forzado.strip()
        for rid, titulo in cands:
            if rid.upper() == f.upper() or titulo.lower() == f.lower() \
                    or (re.fullmatch(r"[\d.]+", f) and (_numero_impreso(titulo) or "") == f):
                return rid, titulo
        return f, f                                   # lo que diga Mariano, aunque no este en la lista
    if not cands:
        return None
    citas = [_tipo_numero(c) for c in _citas_de_hoy() if c.startswith(f"[{doc}:")]

    def menciones(titulo):
        tn = _tipo_numero(titulo)
        return sum(1 for c in citas if c and tn and c[1] == tn[1] and (c[0] == tn[0] or not tn[0])) if tn else 0
    mejor = max(cands, key=lambda x: menciones(x[1]))
    if menciones(mejor[1]) > 0:
        return mejor
    import random
    return random.Random(E.fecha_sesion()).choice(cands)


_TIPO_NORMAL = {"teorema": "teorema", "theorem": "teorema", "lema": "lema", "lemma": "lema",
                "proposicion": "proposicion", "proposition": "proposicion", "corolario": "corolario",
                "corollary": "corolario", "definicion": "definicion", "definition": "definicion"}


def _tipo_numero(texto):
    """('teorema', '2.3') de 'R2 — Teorema 2.3', '[doc:p4, Teorema 2.3 | ...]' o 'Lemma 2.1.1 (x)'; None sin numero."""
    import unicodedata as ud
    plano = ud.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    m = re.search(r"\b(teorema|theorem|lema|lemma|proposicion|proposition|corolario|corollary|definicion|definition)\s+(\d+(?:\.\d+)*)\b", plano)
    if m:
        return _TIPO_NORMAL[m.group(1)], m.group(2)
    num = _numero_impreso(texto)
    return ("", num) if num else None


def _resolver_ataque(doc, eleccion):
    """(rid, titulo) a partir de lo que `ataque` escribio en la sesion: 'R2 — Teorema 2.3' o 'Teorema 3'.
    Si no es un bloque R, busca el bloque de la nota con el mismo tipo y numero; rid None si no hay."""
    m = re.match(r"(R\d+)\s*[—–-]+\s*(.*)$", eleccion)
    if m:
        return m.group(1).upper(), m.group(2).strip()
    tn = _tipo_numero(eleccion)
    if tn and os.path.exists(_ruta_nota(doc)):
        for rid, titulo, _ in _bloques_nota(C.leer(_ruta_nota(doc))):
            t2 = _tipo_numero(titulo)
            if t2 and t2[1] == tn[1] and (t2[0] == tn[0] or not tn[0] or not t2[0]):
                return rid, titulo
    return None, eleccion


def _anotar_ataque(ruta_sesion, eleccion, modo):
    """Escribe 'Ataque: R2 — titulo (...)' bajo la cabecera de la fase 3 de la sesion, una sola vez.
    Devuelve la linea escrita, o la que ya habia."""
    texto = C.leer(ruta_sesion)
    m = re.search(r"^Ataque: .*$", texto, re.M)
    if m:
        return m.group(0)
    que = eleccion[1] if eleccion[0] == eleccion[1] else f"{eleccion[0]} — {eleccion[1]}"
    linea = f"Ataque: {que} (modo {modo}; lo eligio el sistema, --resultado para cambiarlo)"
    m = re.search(r"^## Fase 3[^\n]*\n", texto, re.M)
    if m:
        texto = texto[:m.end()] + linea + "\n" + texto[m.end():]
    else:
        texto = texto.rstrip("\n") + "\n\n## Fase 3 - Ataque\n" + linea + "\n"
    C.escribir(ruta_sesion, texto)
    return linea


def _ataque_elegido(args, modo):
    """Elige (o lee) el resultado del ataque de hoy y lo deja en la sesion. None si no hay sesion/paper."""
    ruta = E.sesion_hoy()
    if not ruta:
        return None
    doc = _doc_de_sesion()
    eleccion = _elegir_resultado(doc, getattr(args, "resultado", None))
    if eleccion is None:
        return None
    if getattr(args, "resultado", None):              # forzado: sustituye la linea que hubiera, en su sitio
        texto = C.leer(ruta)
        que = eleccion[1] if eleccion[0] == eleccion[1] else f"{eleccion[0]} — {eleccion[1]}"
        nueva = f"Ataque: {que} (modo {modo}; lo pediste con --resultado)"
        if re.search(r"^Ataque: .*$", texto, re.M):
            C.escribir(ruta, re.sub(r"^Ataque: .*$", lambda _m: nueva, texto, count=1, flags=re.M))
            return nueva
    return _anotar_ataque(ruta, eleccion, modo)


def cmd_ataque(args):
    E.sincronizar_antes()
    fase, _ = E.fase_actual()
    if fase == "f3":                                  # ya en ataque: recordar la guia y el resultado
        modo, guia = _modo_ataque(getattr(args, "modo", None))
        linea = _ataque_elegido(args, modo)
        print(f"ya estas en fase 3, ataque de {modo}:" + (f"\n{linea}" if linea else "")
              + "\n" + guia + "\nAl terminar:  python doc.py sellar 3")
        return
    if fase != "f2":
        print(f"el ataque empieza desde la fase 2 (fase actual: {fase})")
        return
    modo, guia = _modo_ataque(getattr(args, "modo", None))
    linea = _ataque_elegido(args, modo)               # antes del sello: el commit de ataque la lleva
    ok, msg = E.marcar("ataque ::")                   # marca aunque no haya cambios; con push
    print(msg)
    if not ok:
        M.aviso("el ataque NO quedo marcado en git; la fase sigue siendo la 2. Arregla git y repite.")
        return
    M.aviso(f"MOTOR APAGADO. Fase 3, 45 min, ataque de {modo}." + (f"\n{linea}" if linea else "")
            + "\n" + guia + "\nAl terminar:  python doc.py sellar 3")


ATAQUE_COMPRENSION = """Elige uno o dos, con el PDF cerrado; cada uno deja algo escrito en la sesion:
  - reconstruir una prueba de la seccion desde el enunciado; donde te atasques, apunta el hueco y sigue
  - probar el resultado con una sucesion concreta (Gevrey M_p = p!^a): constantes, casos triviales
    (python lab/pesos.py vale: es tu script, no el motor)
  - quitar una hipotesis y ver que se rompe (es el campo "Que se rompe sin el" de la nota)
  - mapa de dependencias de la seccion: que se apoya en que (## Mapa y ## Dependencias de la nota)
  - preguntas para los directores, una por linea; en un paper de base son las conjeturas
Lo que NO toca aun: caso Beurling y debilitar hipotesis; eso viene con el nucleo leido."""

ATAQUE_EXTENSION = """Extension de lo leido: caso Beurling, contraejemplo, debilitar una hipotesis.
Conjeturas, una por linea, aunque sean malas: cierre las registra."""

ATAQUE_BASE = "EJERCICIOS del capitulo, libro abierto. Son puzzles calibrados con solucion conocida."


def _modo_ataque(modo=None):
    """
    (modo, guia) de la fase 3. 'base' en sesiones de libro; si no, 'comprension' mientras el
    nucleo de corpus/orden.md no este leido entero, y 'extension' despues. `modo` lo fuerza.
    """
    if modo not in (None, "comprension", "extension"):
        modo = None
    if _es_base():
        return "base", ATAQUE_BASE
    if modo is None:
        _, hechos, total = _corpus_siguiente()
        modo = "extension" if total and hechos >= total else "comprension"
    if modo == "extension":
        return "extension", ATAQUE_EXTENSION
    _, hechos, total = _corpus_siguiente()
    return "comprension", (f"(nucleo del corpus leido: {hechos}/{total}; --modo extension lo fuerza)\n"
                           + ATAQUE_COMPRENSION)


def cmd_estado(args):
    fase, m = E.fase_actual()
    nombres = dict(libre="libre (sin sesion hoy)", f1="fase 1, motor OFF",
                   f2="fase 2, motor ON", f3="fase 3, motor OFF", f4="fase 4, motor ON")
    print(nombres[fase] + (" [PAUSADA]" if m.get("pausada") else ""))
    aviso = _aviso_pausa(m)
    if aviso:
        print("  " + aviso)
    for l in C.leer(C.F_ESTADO).splitlines():
        if l.startswith("- Fase:"):
            print(" ", l[2:])
    for k in ("inicio", "sello1", "ataque", "sello3"):
        if m[k]:
            print(f"  {k:<8} {m[k].strftime('%Y-%m-%d %H:%M')}")
    for p, rr in m.get("pausas", []):
        print(f"  pausa    {p.strftime('%Y-%m-%d %H:%M')} -> "
              + (rr.strftime('%Y-%m-%d %H:%M') if rr else "(en curso)"))
    if m["inicio"] and m["sello1"]:
        print(f"  fase 1: {E.minutos_netos(m['inicio'], m['sello1'], m['pausas'])} min netos")
    if m["ataque"] and m["sello3"]:
        print(f"  fase 3: {E.minutos_netos(m['ataque'], m['sello3'], m['pausas'])} min netos")
    print(f"  proveedor: {C.PROVEEDOR}   modelo: {C.MODELO}" + ("  [SIMULACION]" if C.SIMULAR else ""))


def _linea_estado(clave):
    """La linea '- clave: ...' de contexto/estado.md, sin el guion."""
    for l in C.leer(C.F_ESTADO).splitlines():
        if l.startswith(f"- {clave}:"):
            return l[2:].strip()
    return None


def _corpus_siguiente():
    """(primer titulo sin leer, leidos, total) del nucleo de corpus/orden.md."""
    m = re.search(r"^## Nucleo.*?$(.*?)(?=^## |\Z)", C.leer(C.F_ORDEN), re.M | re.S)
    if not m:
        return None, 0, 0
    items = re.findall(r"^- \[(.)\]\s*(.+)$", m.group(1), re.M)
    sin = [t for e, t in items if e == " "]
    return (sin[0] if sin else None), len(items) - len(sin), len(items)


def _lineas_orden():
    """[(estado, titulo, id de bib.yaml o None)] del nucleo de corpus/orden.md, en orden.
    El id se resuelve por apellido y ano; si casan varios (dos JGSS 2019), None."""
    m = re.search(r"^## Nucleo.*?$(.*?)(?=^## |\Z)", C.leer(C.F_ORDEN), re.M | re.S)
    if not m:
        return []
    out = []
    for e, t in re.findall(r"^- \[(.)\]\s*(.+)$", m.group(1), re.M):
        ids = _docs_mencionados(t)
        out.append((e, t, ids[0] if len(ids) == 1 else None))
    return out


def _sesiones_por_doc():
    """{id: [(fecha, etiqueta, cerrada)]} de las sesiones de papers (ni base ni diagnostico),
    por el prefijo de la etiqueta; cerrada = `cierre` escribio coincidencia_estructural."""
    out = {}
    for ruta in sorted(glob.glob(os.path.join(C.DIR_SESIONES, "2*.md"))):
        nombre = os.path.basename(ruta)
        if "diagnostico" in nombre or "EJEMPLO" in nombre:
            continue
        etiqueta = nombre[11:-3]
        doc = _doc_de_sesion(etiqueta)
        if not doc:
            continue
        cerrada = bool(re.search(r"^coincidencia_estructural:\s*\d", C.leer(ruta), re.M))
        out.setdefault(doc, []).append((nombre[:10], etiqueta, cerrada))
    return out


def _marcar_leido(id_, frio=False):
    """Casilla del paper en corpus/orden.md: [~] leido con protocolo, [x] reconstruido en frio.
    Devuelve la linea nueva, o None si el id no esta en el nucleo (o no casa solo)."""
    texto = C.leer(C.F_ORDEN)
    for e, t, d in _lineas_orden():
        if d == id_:
            vieja, nueva = f"- [{e}] {t}", f"- [{'x' if frio else '~'}] {t}"
            if vieja in texto:
                C.escribir(C.F_ORDEN, texto.replace(vieja, nueva, 1))
                return nueva
    return None


def cmd_leido(args):
    """python doc.py leido ID [--frio]: marca el paper en corpus/orden.md; `ahora` deja de proponerlo."""
    nueva = _marcar_leido(args.id, getattr(args, "frio", False))
    if nueva:
        print("corpus/orden.md:", nueva)
    else:
        print(f"{args.id} no esta en el nucleo de corpus/orden.md, o su linea casa con varios ids: "
              "cambia la casilla a mano ([~] leido con protocolo, [x] reconstruido en frio)")


def _cuenta_drill():
    """(tarjetas, cuantas esperan el paper delante)."""
    lineas = [l for l in C.leer(C.F_PENDIENTES).splitlines()
              if "::" in l and not l.startswith("#") and not l.startswith("<!--")
              and "`" not in l]
    return len(lineas), sum(1 for l in lineas if "VERIFICAR CON PAPER" in l)


def _cuenta_lagunas():
    """(pendientes, estructurales). Fuera los ejemplos de los bloques de codigo."""
    lag = re.sub(r"```.*?```", "", C.leer(C.F_LAGUNAS), flags=re.S)
    return (len(re.findall(r"^- \[ \]", lag, re.M)),
            len(re.findall(r"^- \[.*ESTRUCTURAL", lag, re.M)))


# repeticion espaciada de reconstrucciones: dias hasta volver a intentar un R segun el ultimo nivel
INTERVALO_RECONSTRUCCION = {0: 3, 1: 3, 2: 14, 3: 30}


def _reconstrucciones_pendientes(hoy=None):
    """[(doc, rid, titulo, fecha_ultimo, nivel, dias)] de los bloques R cuyo ultimo intento ya
    vence (INTERVALO_RECONSTRUCCION), de todas las notas de lecturas/. Sin modelo."""
    hoy = hoy or datetime.date.today()
    out = []
    for ruta in sorted(glob.glob(os.path.join(C.DIR_LECTURAS, "*.md"))):
        nombre = os.path.basename(ruta)
        if nombre.startswith("PLANTILLA") or "-quiz-" in nombre or "-check-" in nombre:
            continue
        doc = nombre[:-3]
        for rid, titulo, cuerpo in _bloques_nota(C.leer(ruta)):
            ints = _intentos(cuerpo)
            if not ints:
                continue
            fecha, nivel = ints[-1][0], ints[-1][1]
            try:
                dias = (hoy - datetime.date.fromisoformat(fecha)).days
            except ValueError:
                continue
            if nivel < 3 and dias >= INTERVALO_RECONSTRUCCION.get(nivel, 14) or nivel >= 3 and dias >= 30:
                out.append((doc, rid, titulo, fecha, nivel, dias))
    return out


# ======================================================================
# control de prompts, exportar / importar (MEJORAS 6 y 7)
# ======================================================================

def cmd_control(args):
    """Pasa las preguntas de docs/control/preguntas.txt por `ask` y guarda las respuestas con fecha."""
    import io as _io, contextlib
    ruta_p = os.path.join(C.RAIZ, "docs", "control", "preguntas.txt")
    preguntas = [l.strip() for l in C.leer(ruta_p).splitlines() if l.strip() and not l.strip().startswith("#")]
    if not preguntas:
        print("no hay preguntas en docs/control/preguntas.txt")
        return
    solo = getattr(args, "solo", None)
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        return
    salida = [f"# Control de ask ({HOY})\n", "Mismas preguntas que la ultima vez: compara a mano con el fichero anterior.\n"]
    for n, p in enumerate(preguntas, 1):
        if solo and n != solo:
            continue
        print(f"[{n}/{len(preguntas)}] {p[:70]}...")
        buf = _io.StringIO()
        ns = types.SimpleNamespace(pregunta=p.split(), k=8, fuente=None, doc=None, bm25=False, por_doc=2,
                                   con_propios=False, forzar=False)
        con_antes = M._con
        try:
            if con_antes is not None:                 # consola sin color ni ancho de terminal: markdown limpio
                from rich.console import Console
                M._con = Console(file=buf, force_terminal=False, color_system=None, width=100, no_color=True)
            with contextlib.redirect_stdout(buf):
                try:
                    cmd_ask(ns)
                except Exception as e:
                    print(f"ERROR {type(e).__name__}: {e}")
        finally:
            M._con = con_antes
        salida.append(f"\n## {n}. {p}\n\n{buf.getvalue().strip()}\n")
    destino = os.path.join(C.RAIZ, "docs", "control", f"{HOY}" + (f"-solo-{solo}" if solo else "") + ".md")
    C.escribir(destino, "\n".join(salida))
    print(f"-> {os.path.relpath(destino, C.RAIZ)}")


DATOS_LOCALES = ("corpus/text", "indice")


def cmd_exportar(args):
    """Zip con corpus/text e indice/ (lo que no va en git) para llevarlo a otra maquina."""
    import zipfile
    destino = getattr(args, "destino", None) or os.path.join(C.RAIZ, "exportado")
    if not destino.lower().endswith(".zip"):
        os.makedirs(destino, exist_ok=True)
        destino = os.path.join(destino, f"doctorado-datos-{HOY}.zip")
    n = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in DATOS_LOCALES:
            base = os.path.join(C.RAIZ, rel)
            for raiz, _, ficheros in os.walk(base):
                for f in ficheros:
                    ruta = os.path.join(raiz, f)
                    z.write(ruta, os.path.relpath(ruta, C.RAIZ))
                    n += 1
    print(f"{n} ficheros -> {destino} ({os.path.getsize(destino) // 1024} KB). En la otra maquina: "
          "python doc.py importar <zip>. El .env se copia a mano y nunca va en git.")


def cmd_importar(args):
    """Desempaqueta un zip de exportar en este repo: pisa corpus/text e indice/."""
    import zipfile, shutil
    if not os.path.exists(args.zip):
        print("no existe", args.zip)
        return
    temporal = os.path.join(C.RAIZ, ".importando")
    shutil.rmtree(temporal, ignore_errors=True)
    with zipfile.ZipFile(args.zip) as z:
        nombres = z.namelist()
        if not nombres or any(n.startswith("/") or ".." in n.replace("\\", "/").split("/") for n in nombres):
            print("zip vacio o con rutas raras; no se importa")
            return
        malo = z.testzip()
        if malo:
            print(f"zip corrupto en {malo}; no se toca nada (vuelve a copiarlo)")
            return
        z.extractall(temporal)                        # primero aparte: si algo falla, lo tuyo sigue intacto
    for rel in DATOS_LOCALES:
        nuevo = os.path.join(temporal, *rel.split("/"))
        if os.path.isdir(nuevo):
            destino = os.path.join(C.RAIZ, *rel.split("/"))
            shutil.rmtree(destino, ignore_errors=True)
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.move(nuevo, destino)
    shutil.rmtree(temporal, ignore_errors=True)
    print(f"{len(nombres)} ficheros importados en {C.RAIZ}. Luego:  python doc.py buscar \"...\" para comprobar el indice")


# Las cuatro fases de una sesion, con el motor de cada una.
CICLO = (("1 ciego", "OFF"), ("2 IA", "ON"), ("3 ataque", "OFF"), ("4 cierre", "ON"))
_COLUMNA = {"f1": 0, "f2": 1, "f3": 2, "f4": 3}


def _mapa(fase, en_sesion, pausada=False):
    """El ciclo dibujado, con corchetes donde estas."""
    if not en_sesion:
        return ["    sin sesion abierta hoy. El motor esta ENCENDIDO: puedes preguntar,",
                "    resolver lagunas o usar el laboratorio."]
    aqui = _COLUMNA[fase]
    arriba, abajo = "   ", "   "
    for i, (nombre, motor) in enumerate(CICLO):
        arriba += (f"[ {nombre} ]" if i == aqui else f"  {nombre}  ").center(16)
        abajo += (motor if i != aqui else f"AQUI, {motor}").center(16)
    lineas = [arriba.rstrip(), abajo.rstrip()]
    if pausada:
        lineas.append("    (en PAUSA: el reloj de la fase esta parado)")
    return lineas


def _parrafo(cuerpo, etiqueta):
    """El parrafo que empieza por `etiqueta`, en una sola linea. None si no esta."""
    m = re.search(rf"^{re.escape(etiqueta)}\s*(.*?)(?=\n\s*\n|\Z)", cuerpo, re.M | re.S)
    return " ".join(m.group(1).split()) if m else None


def _semana_base():
    """
    Si contexto/estado.md dice 'BASE ... semana N de T', devuelve la seccion
    de corpus/base.md que cubre esa semana: dict(n, total, titulo, texto, meta).
    Fuera de la fase base, None.
    """
    m = re.search(r"BASE.*?semana (\d+) de (\d+)", _linea_estado("Fase") or "")
    if not m:
        return None
    n, total = int(m.group(1)), int(m.group(2))
    sem = dict(n=n, total=total, titulo=None, texto=None, meta=None)
    patron = r"^## Semanas? (\d+)(?:-(\d+))?\.\s*(.+?)\s*$(.*?)(?=^## |\Z)"
    for sec in re.finditer(patron, C.leer(C.F_BASE), re.M | re.S):
        a, b = int(sec.group(1)), int(sec.group(2) or sec.group(1))
        if a <= n <= b:
            cuerpo = sec.group(4)
            sem.update(titulo=sec.group(3), texto=_parrafo(cuerpo, "Texto:"),
                       meta=_parrafo(cuerpo, "Meta al acabar:"))
            break
    return sem


def _sugerir_sesion(base, porque):
    """Como abrir la sesion de hoy: con libro durante la base, con paper despues."""
    if base:
        return ("python doc.py sesion base-ETIQUETA",
                porque,
                "ETIQUETA = libro y capitulo, p. ej. base-conway-iv. Fase 1 con el libro cerrado.")
    return ("python doc.py sesion ETIQUETA",
            porque + " ETIQUETA es el id del paper en bib.yaml: p. ej. thilliez-2003.",
            "detras: 10 min de carga en frio y 25 de intento a ciegas, motor OFF")


def _siguiente(fase, en_sesion, hay_diagnostico, base, marcas=None):
    """(comando, por que, lo que viene detras) desde donde estas ahora."""
    if marcas and marcas.get("pausada"):
        h = E.horas_pausada(marcas)
        return ("python doc.py reanudar",
                f"la sesion esta PAUSADA en fase {fase[1]} desde hace {h} h. La fase y el motor no han cambiado."
                + (f" Lleva mas de {E.PAUSA_AVISO_HORAS} h: reanuda y termina, o cierra con python doc.py cierre."
                   if h > E.PAUSA_AVISO_HORAS else ""),
                "detras: lo que tocaba en esa fase")
    if fase == "f1" and not en_sesion:
        return ("(sigue en la ventana del diagnostico)",
                "el diagnostico esta a medias: se sella solo al terminar los items.",
                "si lo cortaste: python doc.py diagnostico --repetir")
    if fase == "f1":
        return ("python doc.py sellar 1",
                "estas en el intento a ciegas, por escrito y sin ayuda. Motor APAGADO.",
                "detras: python doc.py preguntar")
    if fase == "f3":
        modo, _ = _modo_ataque()
        que = {"base": "ejercicios del capitulo", "comprension": "reconstruir, ejemplo concreto, quitar una "
               "hipotesis, mapa (python doc.py ataque --modo comprension imprime la guia)",
               "extension": "extension, contraejemplo, caso Beurling"}[modo]
        return ("python doc.py sellar 3",
                f"45 min de ataque de {modo}: {que}. Motor APAGADO.",
                "detras: python doc.py cierre")
    if fase == "f4":
        return ("python doc.py cierre",
                "fase 4: diff contra el texto, errores, tarjetas y lagunas.",
                "cierra el dia. Manana, sesion nueva.")
    if fase == "f2" and en_sesion:
        return ("python doc.py preguntar",
                "fase 2, 60 min. El motor esta encendido.",
                "detras: python doc.py ataque")
    if fase == "libre" and E.sesion_hoy():
        return ("(nada: la sesion de hoy esta cerrada)",
                "ya hiciste el ciclo completo hoy. Manana, otra.",
                "si te sobra hora: python doc.py anki, o una laguna del registro")
    if not hay_diagnostico:
        return ("python doc.py diagnostico",
                "la primera toma de contacto, 3 horas, una sola vez. Reserva el hueco.",
                "ensena antes corpus/diagnostico.md a tus directores.")
    if fase == "f2" and not en_sesion:
        return _sugerir_sesion(base, "el diagnostico ya esta sellado y calibrado. "
                                     "No estas dentro de una sesion.")
    if datetime.date.today().weekday() == 4:
        return ("python doc.py lagunas",
                "es viernes: toca el lote de lagunas, 45 min.",
                "detras: python doc.py metricas, para ver como va el trimestre")
    return _sugerir_sesion(base, "abre la sesion de hoy.")


AYUDA_CICLO = """
  UNA SESION ENTERA, DE PRINCIPIO A FIN
    python doc.py sesion ETIQUETA   fase 0 y 1, 35 min.  motor OFF
    python doc.py sellar 1          cierra el intento a ciegas -> motor ON
    python doc.py preguntar         fase 2, 60 min.  /notacion /lema /paso /pegar /laguna
    python doc.py ataque            fase 3, 45 min.  motor OFF
    python doc.py sellar 3          cierra el ataque -> motor ON
    python doc.py cierre            fase 4: diff, errores, tarjetas, lagunas
    python doc.py pausar / reanudar para el reloj sin cambiar de fase (la sesion no caduca)

  FUERA DE SESION
    python doc.py nota add ID "R2 — Teorema 2.3"   bloque del resultado en lecturas/ID.md; nota estado ID
    python doc.py leido ID          marca el paper en corpus/orden.md ([x] con --frio)
    python doc.py lagunas           viernes, 45 min, el lote de huecos
    python doc.py lab "..."         la IA escribe el script, mpmath juzga
    python doc.py reunion           notas de la reunion de hoy
    python doc.py anki              exporta las tarjetas nuevas
    python doc.py metricas          los numeros, sin autodeclaracion
    python doc.py exportar          zip de corpus/text e indice/ para otra maquina (importar <zip> alli)
    python doc.py control           pasada fija de preguntas a ask tras cambiar prompts (30 centimos)
    python -m web                   la mini web en http://127.0.0.1:8765 (docs/WEB.md)

  (esta chuleta se calla con:  python doc.py ahora --breve)"""


def cmd_ahora(args):
    fase, marcas = E.fase_actual()
    en_sesion = fase != "libre" and E.sesion_hoy() is not None
    hay_diagnostico = any(m.startswith("sellado :: diagnostico")
                          for _, m in E.commits_todos())
    base = _semana_base()

    cabecera = _linea_estado("Fase") or "sin fase declarada en contexto/estado.md"
    if cabecera.startswith("Fase: "):
        cabecera = cabecera[len("Fase: "):]
    print()
    print("  " + cabecera)
    print()
    for l in _mapa(fase, en_sesion, marcas.get("pausada", False)):
        print(l)

    comando, porque, detras = _siguiente(fase, en_sesion, hay_diagnostico, base, marcas)
    print("\n  TE TOCA AHORA\n")
    print("    " + comando)
    print("    " + porque)
    if detras:
        print("    " + detras)

    print("\n  MATERIAL")
    if base:
        print(f"    semana {base['n']} de {base['total']} de base"
              + (f": {base['titulo']}" if base["titulo"] else ""))
        texto = base["texto"] or _linea_estado("Texto de la semana")
        if texto:
            print("    " + (texto.split(":", 1)[1].strip() if texto.startswith("Texto") else texto))
        if base["meta"]:
            print("    meta: " + base["meta"])
        print("    el corpus de papers espera a que acabe la base (corpus/base.md)")
    else:
        texto = _linea_estado("Texto de la semana")
        siguiente, hechos, total = _corpus_siguiente()
        if texto:
            print("    " + (texto.split(":", 1)[1].strip() if ":" in texto else texto))
        marcados = {d for e, _, d in _lineas_orden() if e != " " and d}
        for d, v in _sesiones_por_doc().items():          # lo que dicen las sesiones, no las casillas
            if d in marcados:
                continue
            cerradas = sum(1 for _, _, c in v if c)
            ruta_n = _ruta_nota(d)
            bloques = len(_bloques_nota(C.leer(ruta_n))) if os.path.exists(ruta_n) else 0
            print(f"    en curso segun tus sesiones: {d} ({len(v)} sesiones, {cerradas} cerradas, ultima "
                  f"{v[-1][0]} {v[-1][1]}; nota: {bloques} bloques R). Si lo das por leido: python doc.py leido {d}")
        if siguiente:
            print(f"    corpus {hechos}/{total}, siguiente sin leer segun orden.md: {siguiente}")
            ids = _docs_mencionados(siguiente)
            if len(ids) == 1:
                print(f"    en bib.yaml: {ids[0]}.  Antes de la sesion: python doc.py nota new {ids[0]}"
                      f"  (y nota quiz {ids[0]} tras leerlo)")
        elif total:
            print(f"    corpus {hechos}/{total}: nucleo terminado")
        print("    hueco de grado/master al leer: UNA linea en registro/lagunas.md (/laguna en preguntar,")
        print("    o la linea 'Lagunas' de la sesion) y sigues. Se resuelve aparte: viernes, python doc.py lagunas.")

    tarjetas, verificar = _cuenta_drill()
    lagunas, estructurales = _cuenta_lagunas()
    print("\n  PENDIENTE")
    if tarjetas:
        print(f"    drill      {tarjetas} sin exportar a Anki"
              + (f", {verificar} esperan que pegues el paper" if verificar else ""))
    else:
        print("    drill      nada sin exportar. El repaso lo lleva Anki, no esto.")
    print(f"    lagunas    {lagunas}"
          + (f", {estructurales} ESTRUCTURALES: esas piden libro, no chat" if estructurales else ""))
    for doc, rid, titulo, fecha, nivel, dias in _reconstrucciones_pendientes():
        print(f"    reconstruir {rid} de {doc} ({titulo}): nivel {nivel} hace {dias} d. "
              "Sesion corta con el enunciado abierto; cierre anota el intento")
    if not _reuniones():
        reunion = _linea_estado("Primera reunion con directores")
        if reunion and ":" in reunion:
            reunion = reunion.split(":", 1)[1].strip()
        print("    reunion    " + (reunion or "sin ninguna registrada todavia"))
    problema = _linea_estado("Problema de arranque")
    if problema and "sin delimitar" in problema:
        print("    problema   " + problema.split(":", 1)[1].strip())

    if not getattr(args, "breve", False):
        print(AYUDA_CICLO)
    print()


def _abrir(ruta):
    import shutil, subprocess
    try:
        if shutil.which("code"):
            subprocess.Popen(["code", ruta], shell=(os.name == "nt"))
        elif os.name == "nt":
            os.startfile(ruta)      # noqa
    except Exception:
        pass


# ======================================================================
# fase 2: preguntar
# ======================================================================

AYUDA_REPL = """Fase 2. Tres usos y nada mas.
  /notacion [texto]  la siguiente pregunta (o ese texto) va con la plantilla de notacion
  /lema [texto]      ... con la de lema estandar
  /paso [texto]      ... con la de paso comprimido
  Pega varias lineas de golpe y quedan como fragmento; si el paper esta en el corpus se
  localiza y la respuesta lo cita por pagina. Luego la pregunta, o Enter para que lo
  desarrolle paso a paso.
  /pegar      lo mismo a mano: pega y termina con una linea que sea solo un punto
  /ver 2.1.3  trae del corpus el enunciado con ese numero impreso; /ver p8, la pagina 8
  /doc ID     fija el paper del corpus contra el que se busca (por defecto, el de la sesion)
  /sigue      que continue una respuesta cortada por el tope de salida
  /laguna X   anota el hueco de grado/master X en registro/lagunas.md y sigues (90 s max)
  /queja X    anota que ha fallado en la ultima respuesta (registro/quejas.md); se revisan en lote
  /nuevo      olvida la conversacion (nuevo fragmento, nuevo hilo)
  /salir
Sin plantilla la pregunta va tal cual, con las reglas de fase 2 igualmente."""

_CMD_PLANTILLA = {"/notacion": "P_NOTACION", "/lema": "P_LEMA", "/paso": "P_PASO"}
TOPE_TOKENS_CORPUS = 2500      # fragmentos del corpus por turno, como mucho


def _registrar_conversacion(fase, pregunta, respuesta, plantilla, fragmento, citas=(), turno=None, u=None):
    """Cada turno de preguntar queda en registro/consultas/AAAA-MM-DD-preguntar.jsonl."""
    os.makedirs(C.DIR_CONSULTAS, exist_ok=True)
    ruta = os.path.join(C.DIR_CONSULTAS, f"{HOY}-preguntar.jsonl")
    u = u or {}
    C.anadir(ruta, json.dumps(dict(
        ts=datetime.datetime.now().isoformat(timespec="seconds"), fase=fase,
        modelo=u.get("modelo") or C.modelo_para("preguntar"), esfuerzo=u.get("esfuerzo"), turno=turno,
        plantilla=(plantilla[:40].split("]")[0].lstrip("[") if plantilla else None),
        fragmento=fragmento or None, pregunta=pregunta, respuesta=respuesta, citas=list(citas),
        tokens_in=u.get("tokens_in"), tokens_out=u.get("tokens_out"), tokens_cache=u.get("tokens_cache"),
        segundos=u.get("segundos"), cortada=u.get("cortada"),
    ), ensure_ascii=False) + "\n")


def _doc_de_sesion(etiqueta=None):
    """
    Id de bib.yaml del paper de la sesion: el prefijo mas largo de la etiqueta de
    sesiones/AAAA-MM-DD-ETIQUETA.md que sea un id ('thilliez-2003-section-2' -> 'thilliez-2003').
    None en sesiones base-*, sin sesion, o si la etiqueta no casa con ningun id.
    """
    from . import corpus as Q
    if etiqueta is None:
        ruta = E.sesion_hoy()
        etiqueta = os.path.basename(ruta)[11:-3] if ruta else ""
    if not etiqueta or etiqueta.startswith("base-"):
        return None
    cands = [k for k, e in Q.leer_bib().items() if e.get("fuente") != "proyecto"
             and (etiqueta == k or etiqueta.startswith(k + "-"))]
    return max(cands, key=len) if cands else None


def _fragmento_de_pegado(lineas):
    """
    (fragmento, comando) de un pegado de varias lineas. Si la primera linea empieza por
    /pegar, /paso, /lema o /notacion (tecleado justo antes de pegar), se quita del
    fragmento y se devuelve el comando.
    """
    comando = None
    lineas = list(lineas)
    if lineas:
        m = re.match(r"(/pegar|/paso|/lema|/notacion)\b\s*(.*)", lineas[0].strip(), re.S)
        if m:
            comando = m.group(1)
            lineas = ([m.group(2)] if m.group(2) else []) + lineas[1:]
    if lineas and lineas[-1].strip() == ".":          # el terminador de /pegar, pegado con el texto
        lineas = lineas[:-1]
    return "\n".join(lineas).strip(), comando


def _localizar_pegado(doc, fragmento):
    """Fragmentos del indice que contienen lo pegado (con su cita), o [] avisando."""
    from . import indice as I
    if not doc or not fragmento:
        return []
    loc = I.localizar(doc, fragmento)
    if not loc:
        print(f"no localizado en {doc}: se envia tal cual, sin cita del corpus")
        return []
    print(f"localizado en el corpus (cobertura {loc['cobertura']}): "
          + "; ".join(I.cita(f) for f in loc["fragmentos"]))
    return loc["fragmentos"]


def _recuperar(doc, pregunta, fragmento, localizados, tope=TOPE_TOKENS_CORPUS):
    """
    Fragmentos del corpus para este turno: los localizados del pegado, los mas afines a la
    pregunta (buscar, solo ese documento) y las \\ref que citen. Sin modelo de chat.
    """
    from . import indice as I
    frags = list(localizados)
    if doc:
        por_pegado = not pregunta or pregunta.startswith("Desarrolla este fragmento")
        if por_pegado:
            # Enter tras un pegado o un /ver: la consulta es ese texto, por BM25 (sin embeddings)
            consulta = fragmento or " ".join(f["texto"] for f in localizados)[:2000]
        else:
            consulta = pregunta
        if consulta.strip():
            try:
                nuevos = I.buscar(consulta, k=4, doc=doc, por_doc=0, solo_bm25=por_pegado)
            except Exception as e:
                M.aviso(f"corpus: {type(e).__name__}: {str(e)[:80]}")
                nuevos = []
            frags = _fusionar(frags, nuevos)
            frags = _fusionar(frags, I.seguir_refs(frags, maximo=2))
    out, total = [], 0
    for f in frags:
        n = I._tokens(f["texto"])
        if out and total + n > tope:
            break
        out.append(f)
        total += n
    return out


def _bloque_corpus(frags):
    from . import indice as I
    if not frags:
        return ""
    return ("FRAGMENTOS DEL CORPUS (cita delante de cada uno; texto de la capa tex, pagina del PDF):\n\n"
            + "\n\n".join(I.cita(f) + (" (traido con /ver)" if f.get("via_ver") else
                                       " (contiene lo que pegaste)" if f.get("localizado") else "")
                          + (" (traido por referencia)" if f.get("via_ref") else "") + f"\n{f['texto']}"
                          for f in frags))


def _mensajes(turnos):
    """Historial para el modelo: el bloque del corpus solo viaja en el ultimo turno del usuario,
    para que los fragmentos de turnos pasados no se reenvien (ni se paguen) cada vez."""
    ultimo = max((i for i, t in enumerate(turnos) if t["role"] == "user"), default=-1)
    out = []
    for i, t in enumerate(turnos):
        c = t["content"] + (("\n\n" + t["bloque"]) if t.get("bloque") and i == ultimo else "")
        out.append({"role": t["role"], "content": c})
    return out


def cmd_preguntar(args):
    from . import indice as I
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO and not args.forzar:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        print("(si de verdad hace falta: --forzar. Queda registrado como violacion.)")
        return
    if args.forzar and fase not in E.MOTOR_PERMITIDO:
        M.aviso("FORZADO. Esto cuenta como violacion en las metricas.")

    print(AYUDA_REPL)
    sin_corpus = bool(getattr(args, "sin_corpus", False))
    doc = None if sin_corpus else _doc_de_sesion()
    if doc:
        print(f"\npaper de la sesion: {doc} ({len(I._cargar(doc=doc))} fragmentos en el indice). "
              "Cada pregunta lleva los fragmentos mas afines, con su cita por pagina.")
    elif not sin_corpus:
        print("\nsin paper del corpus asociado a esta sesion: el modelo solo vera lo que pegues (/doc ID para fijar uno)")
    turnos, plantilla, fragmento, localizados = [], "", "", []
    ultima_cortada = ultima_sigue = False
    while True:
        try:
            lineas = _leer_lineas("\n> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if len(lineas) > 1:
            # varias lineas de golpe: es un pegado, no varias preguntas
            fragmento, cmd = _fragmento_de_pegado(lineas)
            if cmd in _CMD_PLANTILLA:
                plantilla = getattr(P, _CMD_PLANTILLA[cmd])
            localizados = [f for f in localizados if f.get("via_ver")] + _localizar_pegado(doc, fragmento)
            print(f"fragmento de {len(lineas)} lineas guardado. Ahora la pregunta "
                  "(Enter = que lo desarrolle paso a paso)")
            continue
        linea = lineas[0].strip()
        if linea == "." and (fragmento or localizados):     # el punto de /pegar tecleado aparte
            print("fragmento ya guardado; ahora la pregunta (Enter = que lo desarrolle paso a paso)")
            continue
        if not linea:
            if not fragmento and not localizados:
                continue
            linea = "Desarrolla este fragmento paso a paso, con todos los pasos intermedios (regla FUENTES)."
        if linea == "/salir":
            break
        if linea == "/ayuda":
            print(AYUDA_REPL)
            continue
        if linea == "/nuevo":
            turnos, plantilla, fragmento, localizados = [], "", "", []
            ultima_cortada = ultima_sigue = False
            print("hilo nuevo")
            continue
        sigue = linea == "/sigue"
        m = re.match(r"(/notacion|/lema|/paso)\b\s*(.*)", linea, re.S)
        if m:
            plantilla = getattr(P, _CMD_PLANTILLA[m.group(1)])
            if not m.group(2).strip():
                print("plantilla cargada para la siguiente pregunta")
                continue
            linea = m.group(2).strip()
        elif linea.split(" ", 1)[0] == "/queja":
            queja = linea[len("/queja"):].strip()
            if not queja:
                print("uso: /queja <que ha fallado en la ultima respuesta>. Se revisan en lote.")
                continue
            ruta = E.sesion_hoy()
            _anadir_queja(queja, os.path.basename(ruta)[11:-3] if ruta else "preguntar", len(turnos) // 2)
            print("queja anotada en registro/quejas.md (con la fecha y el turno, para localizar la respuesta en registro/consultas)")
            continue
        elif linea.split(" ", 1)[0] == "/laguna":
            hueco = linea[len("/laguna"):].strip()
            if not hueco:
                print("uso: /laguna <una linea con el hueco de grado/master>. No se resuelve ahora.")
                continue
            ruta = E.sesion_hoy()
            origen = os.path.basename(ruta)[11:-3] if ruta else "preguntar"
            _anadir_lagunas([hueco], origen, fase)
            print("laguna anotada en registro/lagunas.md. Sigue con el paper; el viernes, python doc.py lagunas")
            continue
        elif linea.split(" ", 1)[0] == "/doc":
            nuevo = linea[len("/doc"):].strip()
            if nuevo and I._cargar(doc=nuevo):
                doc = nuevo
                print(f"corpus fijado: {doc}")
            else:
                print("ese id no esta en el indice (mira corpus/meta/bib.yaml, o python doc.py indexar)")
            continue
        elif linea.split(" ", 1)[0] == "/ver":
            que = linea[len("/ver"):].strip()
            if not doc:
                print("sin paper fijado: /doc ID")
                continue
            frags = I.por_pagina(doc, que[1:]) if re.fullmatch(r"p\d+", que) else I.por_numero(doc, que)
            if not frags:
                print(f"nada con '{que}' en {doc}. Prueba: python doc.py buscar \"...\" --doc {doc}")
                continue
            vistos = [dict(f, via_ver=True) for f in frags[:3]]
            localizados = _fusionar(localizados, vistos)        # se suma a lo pegado, no lo pisa
            for f in vistos:
                print("  " + I.cita(f))
            M.imprimir("\n\n".join(f["texto"] for f in vistos), consola=True)
            print("ahora la pregunta (Enter = que lo desarrolle paso a paso)")
            continue
        elif linea == "/pegar":
            print("pega el fragmento; termina con una linea que sea solo un punto")
            buf = []
            while True:
                l = input()
                if l.strip() == ".":
                    break
                buf.append(l)
            fragmento, _ = _fragmento_de_pegado(buf)
            localizados = [f for f in localizados if f.get("via_ver")] + _localizar_pegado(doc, fragmento)
            print(f"fragmento guardado ({len(fragmento)} caracteres)")
            continue
        elif sigue:
            if not (ultima_cortada or ultima_sigue):
                print("la ultima respuesta no quedo cortada ni termino en SIGUE:")
                continue
            linea = ("Continua exactamente desde la linea SIGUE:, sin repetir lo anterior." if ultima_sigue
                     else "Continua exactamente donde te cortaste, sin repetir lo anterior.")

        if sigue and len(turnos) >= 2:              # la continuacion reutiliza los fragmentos del turno cortado
            frags_turno, bloque = turnos[-2].get("frags", []), turnos[-2].get("bloque", "")
        else:
            frags_turno = _recuperar(doc, linea, fragmento, localizados)
            bloque = _bloque_corpus(frags_turno)
        contenido = plantilla + (f"FRAGMENTO PEGADO (texto del PDF):\n{fragmento}\n\n" if fragmento else "") + linea
        turnos.append(dict(role="user", content=contenido, bloque=bloque, frags=frags_turno))
        espera = (f"{C.modelo_para('preguntar')} (esfuerzo {C.esfuerzo_para('preguntar')}), turno "
                  f"{len(turnos) // 2 + 1}, {len(frags_turno)} fragmentos del corpus...")
        try:
            with M.esperando(espera):
                respuesta = M.llamar("preguntar", _sistema(P.FASE2), _mensajes(turnos), forzar=args.forzar)
        except M.MotorApagado as e:
            M.aviso("MOTOR APAGADO: " + str(e))
            turnos.pop()
            break
        turnos.append(dict(role="assistant", content=respuesta))
        u = dict(M.ULTIMA)
        citas = [I.cita(f) for f in frags_turno]
        ultima_cortada = bool(u.get("cortada"))
        ultima_sigue = bool(re.search(r"^SIGUE:", respuesta, re.M))
        # el registro va ANTES de imprimir: una respuesta pagada no se pierde por un fallo de render
        _registrar_conversacion(fase, linea, respuesta, plantilla, fragmento, citas, len(turnos) // 2, u)
        print()
        M.imprimir(respuesta, consola=True)
        if citas:
            print("\ncorpus consultado: " + "; ".join(dict.fromkeys(citas)))     # sin repetir la misma cita
        print(f"[{u.get('segundos')} s | entrada {u.get('tokens_in')} (cache {u.get('tokens_cache')}) | "
              f"salida {u.get('tokens_out')} (razonamiento {u.get('tokens_razonamiento')}) | tope {u.get('max_tokens')}]")
        if ultima_cortada:
            M.aviso("RESPUESTA CORTADA por el tope de salida. Escribe /sigue para que continue donde se quedo.")
        elif ultima_sigue:
            print("la respuesta para en SIGUE: (tope de 40 lineas). Escribe /sigue para que continue con los mismos fragmentos.")
        plantilla, fragmento, localizados = "", "", []


# ======================================================================
# fase 4: cierre
# ======================================================================

def cmd_cierre(args):
    E.sincronizar_antes()
    fase, m = E.fase_actual()
    ruta = E.sesion_hoy()
    if not ruta:
        print("no hay sesion hoy")
        return
    if fase != "f4":
        M.aviso(f"el cierre requiere la fase 3 sellada (fase actual: {fase})")
        return

    texto = C.leer(ruta)
    etiqueta = os.path.basename(ruta)[11:-3]
    print("comparando tu fase 1 con el texto...")
    bruto = M.llamar("cierre", _sistema(P.CIERRE),
                     [{"role": "user", "content": texto}], max_tokens=C.MAX_TOKENS_JSON)
    try:
        r = M.parse_json(bruto)
    except ValueError as e:
        print(e)
        return

    print()
    M.imprimir("**Diff estructural**\n\n" + r.get("diff_estructural", ""))
    prop = int(r.get("coincidencia_propuesta", 0))
    print(f"\ncoincidencia propuesta: {prop}  (0 nada / 1 enunciado / 2 con lagunas / 3 limpio)")
    try:
        c = input("tu valoracion [Enter = aceptar]: ").strip()
        coincidencia = int(c) if c in ("0", "1", "2", "3") else prop
    except (EOFError, ValueError):
        coincidencia = prop

    # errores
    errs = r.get("errores", []) or []
    if errs:
        bloque = ""
        for e in errs:
            bloque += (f"\n### {HOY}  [{e.get('cod','?')}]  {e.get('contexto','')}\n"
                       f"Creia: {e.get('creia','')}\nEs: {e.get('es','')}\n"
                       f"Posicion a repasar: {e.get('posicion','')}\n")
        C.anadir(C.F_ERRORES, bloque)

    nt = _anadir_tarjetas(r.get("tarjetas", []), etiqueta)
    nl = _anadir_lagunas(r.get("lagunas", []), etiqueta, "f2")

    conj = r.get("conjeturas", []) or []
    if conj:
        existentes = len(re.findall(r"^### C-\d+", C.leer(C.F_CONJETURAS), re.M))
        bloque = ""
        for i, cj in enumerate(conj, existentes + 1):
            bloque += (f"\n### C-{i:03d}  {HOY}  {cj.strip()}\nOrigen: sesion {etiqueta}\n"
                       f"Estado: viva\nScript: lab/conj/C-{i:03d}.py\nNota:\n")
        C.anadir(C.F_CONJETURAS, bloque)

    # metricas en el frontmatter, todas calculadas
    f2 = sum(1 for l in M.llamadas()
             if l["ts"].startswith(HOY) and l["comando"] == "preguntar")
    texto = _pon(texto, "min_f1", E.minutos_netos(m["inicio"], m["sello1"], m["pausas"]))
    texto = _pon(texto, "min_f3", E.minutos_netos(m["ataque"], m["sello3"], m["pausas"]))
    texto = _pon(texto, "coincidencia_estructural", coincidencia)
    texto = _pon(texto, "llamadas_f2", f2)
    texto = _pon(texto, "conjeturas", len(conj))
    C.escribir(ruta, texto)

    # el intento de reconstruccion, en el bloque R de la nota que se ataco (si lo hay)
    m_at = re.search(r"^Ataque: (.+?)\s*\(", texto, re.M)
    doc_sesion = _doc_de_sesion(etiqueta)
    if m_at and doc_sesion:
        rid_at, titulo_at = _resolver_ataque(doc_sesion, m_at.group(1).strip())
        donde = _registrar_intento(doc_sesion, rid_at, HOY, coincidencia,
                                   E.minutos_netos(m["ataque"], m["sello3"], m["pausas"]), etiqueta) if rid_at else None
        if donde:
            print("intento anotado en " + donde)
        elif os.path.exists(_ruta_nota(doc_sesion)):
            print(f"(el ataque fue a {titulo_at}, que no es un bloque de lecturas/{doc_sesion}.md: "
                  f"python doc.py nota add {doc_sesion} \"R? — {titulo_at}\" y anota el intento a mano)")
        else:
            print(f"(sin nota para {doc_sesion}: python doc.py nota new {doc_sesion} y nota add {doc_sesion} "
                  f"\"R1 — {titulo_at}\"; luego anota el intento a mano)")

    ok_s, msg_s = E.sellar("cierre ::")
    print(msg_s if ok_s else "AVISO: el cierre NO quedo sellado en git: " + msg_s)
    print(f"\nerrores {len(errs)} | tarjetas {nt} | lagunas {nl} | conjeturas {len(conj)}")
    print(f"fase 1: {E.minutos_netos(m['inicio'], m['sello1'], m['pausas'])} min | "
          f"fase 3: {E.minutos_netos(m['ataque'], m['sello3'], m['pausas'])} min | llamadas f2: {f2}")


# ======================================================================
# lagunas (viernes)
# ======================================================================

def cmd_lagunas(args):
    texto = C.leer(C.F_LAGUNAS)
    pendientes = _seccion_pendientes(texto)
    if not pendientes:
        print("no hay lagunas pendientes")
        return

    # recurrencia: cuantas veces aparece cada tema en TODO el fichero
    sin_ejemplos = re.sub(r"```.*?```", "", texto, flags=re.S)
    todas = [l for l in sin_ejemplos.splitlines() if l.strip().startswith("- [")]
    cuenta = Counter(_tema(l) for l in todas)

    print(f"{len(pendientes)} lagunas pendientes\n")
    salida = f"# Lote de lagunas {HOY}\n"
    resueltas = 0
    for linea in pendientes:
        if args.max and resueltas >= args.max:
            break
        tema = _tema(linea)
        detalle = linea.split("]", 1)[-1].split("|")[-1].strip()
        estructural = cuenta[tema] >= 3
        print("=" * 70)
        print(detalle)
        if estructural:
            M.aviso(f"  [ESTRUCTURAL] '{tema}' aparece {cuenta[tema]} veces. Esto ya no es una "
                    "laguna: es un capitulo que falta. Sesion de 3 h con un libro.")
        try:
            r = M.parse_json(M.llamar("lagunas", P.LAGUNA,
                                      [{"role": "user", "content": f"Hueco: {detalle}"}],
                                      max_tokens=C.MAX_TOKENS_JSON))
        except (M.MotorApagado, ValueError) as e:
            print("  ", e)
            break
        bloque = (f"\n## {detalle}\n\n**Enunciado.** {r.get('enunciado','')}\n\n"
                  f"**Referencia.** {r.get('referencia','')}\n\n"
                  f"**Intuicion.** {r.get('intuicion','')}\n\n"
                  f"**Trampa.** {r.get('trampa','')}\n\n"
                  f"**Ejercicio (5 min, sin solucion).** {r.get('ejercicio','')}\n")
        M.imprimir(bloque)
        salida += bloque
        _anadir_tarjetas(r.get("tarjetas", []), f"laguna: {tema}")

        marca = "- [ ] [ESTRUCTURAL]" if estructural else "- [~]"
        texto = texto.replace(linea, marca + linea[5:], 1)
        resueltas += 1

    C.escribir(C.F_LAGUNAS, texto)
    ruta = os.path.join(C.DIR_REGISTRO, "lagunas_resueltas", f"{HOY}.md")
    C.escribir(ruta, salida)
    E.sellar("lagunas ::")
    print("\n" + "=" * 70)
    print(f"{resueltas} respondidas -> {os.path.relpath(ruta, C.RAIZ)}")
    print("[~] = respondida. Pasa a [x] a mano cuando hayas hecho el ejercicio.")


# ======================================================================
# laboratorio
# ======================================================================

def cmd_lab(args):
    spec = " ".join(args.especificacion).strip()
    if spec == "demo":
        import sys as _sys
        _sys.path.insert(0, C.DIR_LAB)
        import demo as D
        D.demo()
        return
    if not spec:
        print('uso: python doc.py lab "comprueba si m_p = log(p+e) cumple (gamma_1) para N=200,400,800"')
        return
    nombre = re.sub(r"[^a-z0-9]+", "_", spec.lower())[:40].strip("_") or "script"
    ruta = os.path.join(C.DIR_LAB, "conj", f"{HOY}-{nombre}.py")
    mensaje = f"ESPECIFICACION:\n{spec}\n\nLIBRERIA lab/pesos.py:\n```python\n{C.leer(C.F_PESOS)}\n```"
    try:
        codigo = M.llamar("lab", P.LAB, [{"role": "user", "content": mensaje}],
                          max_tokens=C.MAX_TOKENS_JSON, forzar=args.forzar)
    except M.MotorApagado as e:
        M.aviso("MOTOR APAGADO: " + str(e))
        return
    codigo = re.sub(r"^```(?:python)?\s*|\s*```$", "", codigo.strip(), flags=re.M)
    cab = f'"""\nEspecificacion: {spec}\nGenerado: {HOY}. Revisalo antes de creerte nada.\n"""\n'
    cab += "import sys, os\nsys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))\n"
    C.escribir(ruta, cab + codigo)
    print("escrito", os.path.relpath(ruta, C.RAIZ))
    print(f"ejecuta:  python {os.path.relpath(ruta, C.RAIZ)}")


# ======================================================================
# diagnostico: primera toma de contacto
# ======================================================================

def _items_diagnostico():
    items, actual = [], None
    for l in C.leer(C.F_DIAGNOSTICO).splitlines():
        if l.startswith("## "):
            actual = dict(titulo=l[3:].strip(), tiempo=20, texto="")
            items.append(actual)
        elif actual is not None:
            m = re.match(r"tiempo:\s*(\d+)", l.strip())
            if m:
                actual["tiempo"] = int(m.group(1))
            else:
                actual["texto"] += l + "\n"
    return items


def cmd_diagnostico(args):
    if getattr(args, "calibrar", False):
        ya = sorted(glob.glob(os.path.join(C.DIR_SESIONES, "*-diagnostico.md")))
        if not ya:
            print("no hay ningun diagnostico sellado")
            return
        ruta = ya[-1]
        texto = C.leer(ruta)
        m = re.search(r"(\| # \| Item.*?)(?=\n## |\Z)", texto, re.S)
        if not m:
            print("no encuentro la tabla en", os.path.relpath(ruta, C.RAIZ))
            return
        if "## Calibracion" in texto and not args.repetir:
            print("ese diagnostico ya esta calibrado (usa --repetir para rehacerla)")
            return
        _calibrar(ruta, m.group(1).strip())
        return

    items = _items_diagnostico()
    if not items:
        print("no hay items en corpus/diagnostico.md")
        return
    ya = glob.glob(os.path.join(C.DIR_SESIONES, "*-diagnostico.md"))
    if ya and not args.repetir:
        print("ya hay un diagnostico:", os.path.relpath(ya[0], C.RAIZ), " (usa --repetir)")
        return

    total = sum(i["tiempo"] for i in items)
    M.aviso(f"DIAGNOSTICO DE CALIBRACION. {len(items)} items, unos {total} min.")
    print("A ciegas: nada abierto salvo papel o un fichero de texto. Motor apagado.\n"
          "En cada item: trabaja, pulsa Enter al terminar, puntua 0-3, anota que te faltaba.\n"
          "  0 nada / 1 recuerdo el enunciado / 2 lo reconstruyo con lagunas / 3 limpio\n"
          "Escribe 's' para saltar un item.\n")
    input("Enter para empezar...")
    ok, msg = E.marcar("inicio diagnostico ::")
    print(msg)

    resultados = []
    for k, it in enumerate(items, 1):
        print("\n" + "=" * 70)
        print(f"[{k}/{len(items)}]  {it['titulo']}     (orientativo: {it['tiempo']} min)")
        print(it["texto"].strip())
        t0 = time.time()
        r = input("\nEnter al terminar (s = saltar): ").strip().lower()
        mins = round((time.time() - t0) / 60, 1)
        if r == "s":
            resultados.append(dict(titulo=it["titulo"], min=mins, punt=0, nota="saltado"))
            continue
        while True:
            p = input("puntuacion 0-3: ").strip()
            if p in ("0", "1", "2", "3"):
                break
        nota = input("que no recordabas (una linea, o vacio): ").strip()
        resultados.append(dict(titulo=it["titulo"], min=mins, punt=int(p), nota=nota))

    # fichero + sello
    ruta = os.path.join(C.DIR_SESIONES, f"{HOY}-diagnostico.md")
    tabla = "| # | Item | min | 0-3 | Que faltaba |\n|---|---|---|---|---|\n"
    for k, r in enumerate(resultados, 1):
        tabla += f"| {k} | {r['titulo']} | {r['min']} | {r['punt']} | {r['nota']} |\n"
    media = st.mean(r["punt"] for r in resultados)
    C.escribir(ruta, f"---\nfecha: {HOY}\ntipo: diagnostico\nmedia: {media:.2f}\n---\n\n"
                     f"# Diagnostico de calibracion {HOY}\n\n{tabla}\n")
    E.sellar("sellado :: diagnostico ::")
    print(f"\nsellado. media {media:.2f}/3. Ahora, y solo ahora, entra la IA a calibrar.\n")

    _calibrar(ruta, tabla)


def _calibrar(ruta, tabla):
    """Solo la parte con IA. Se puede relanzar con --calibrar si la API fallo."""
    try:
        r = M.parse_json(M.llamar("diagnostico", P.DIAGNOSTICO,
                                  [{"role": "user", "content": tabla}],
                                  max_tokens=C.MAX_TOKENS_DIAGNOSTICO))
    except (M.MotorApagado, ValueError) as e:
        print(e)
        print("\nEl diagnostico esta sellado y a salvo. Cuando la API funcione:\n"
              "    python doc.py diagnostico --calibrar")
        return
    except Exception as e:
        print(f"fallo la llamada a la API: {e}")
        print("\nEl diagnostico esta sellado y a salvo. Revisa la clave en .env y luego:\n"
              "    python doc.py diagnostico --calibrar")
        return

    M.imprimir("**Donde estas**\n\n" + r.get("resumen", ""))
    M.imprimir("\n**Orden del corpus**\n\n" + r.get("orden_corpus", ""))
    nt = _anadir_tarjetas(r.get("tarjetas", []), "diagnostico")
    nl = _anadir_lagunas(r.get("lagunas", []), "diagnostico")
    C.anadir(C.F_ORDEN, f"\n## Ajuste tras el diagnostico ({HOY})\n\n{r.get('orden_corpus','')}\n")
    preread = os.path.join(C.DIR_NOTAS, f"{HOY}-preread-directores.md")
    C.escribir(preread, r.get("preread_directores", ""))
    C.anadir(ruta, f"\n## Calibracion\n\n{r.get('resumen','')}\n")
    E.sellar("diagnostico procesado ::")

    print(f"\ntarjetas {nt} -> drill/pendientes.md   (python doc.py anki)")
    print(f"lagunas  {nl} -> registro/lagunas.md    (python doc.py lagunas, el viernes)")
    print(f"pre-read para directores -> {os.path.relpath(preread, C.RAIZ)}")
    M.aviso("\nEl pre-read es un borrador en primera persona. Reescribelo con tu voz antes "
            "de mandarlo, y pideles que revisen la lista del diagnostico.")




# ======================================================================
# reuniones con directores
# ======================================================================

def _reuniones():
    """Ficheros de reunion (no pre-reads ni plantilla), ordenados por fecha."""
    return sorted(f for f in glob.glob(os.path.join(C.DIR_REUNIONES, "2*.md"))
                  if "preread" not in os.path.basename(f))


def cmd_reunion(args):
    if args.destilar:
        return _reunion_destilar(args)
    if args.preparar:
        return _reunion_preparar(args)

    destino = os.path.join(C.DIR_REUNIONES, f"{HOY}.md")
    if os.path.exists(destino):
        print("ya existe", os.path.relpath(destino, C.RAIZ))
    else:
        C.escribir(destino, C.leer(C.F_PLANTILLA_REUNION).replace("AAAA-MM-DD", HOY))
        print("creada", os.path.relpath(destino, C.RAIZ))
    print("Escribe las notas crudas. Despues:  python doc.py reunion --destilar")
    _abrir(destino)


def _reunion_destilar(args):
    reuniones = _reuniones()
    if not reuniones:
        print("no hay notas de reunion. Primero:  python doc.py reunion")
        return
    ruta = reuniones[-1]
    notas = C.leer(ruta)
    if "## Notas crudas\n" in notas and len(notas.split("## Notas crudas", 1)[1].strip()) < 40:
        print("las notas crudas estan vacias en", os.path.relpath(ruta, C.RAIZ))
        return

    print("destilando", os.path.relpath(ruta, C.RAIZ), "...")
    try:
        r = M.parse_json(M.llamar("reunion", P.DESTILAR,
                                  [{"role": "user", "content": notas}],
                                  max_tokens=C.MAX_TOKENS_JSON))
    except (M.MotorApagado, ValueError) as e:
        print(e)
        return

    fecha = os.path.basename(ruta)[:10]
    texto = C.leer(C.F_DIRECTORES)
    aceptadas = 0
    print("\nPropuestas para contexto/directores.md. Enter acepta, n rechaza, e edita.\n")
    for it in r.get("directores", []) or []:
        sec, linea = it.get("seccion", "Otros"), it.get("linea", "").strip()
        if not linea:
            continue
        print(f"[{sec}]\n  - {fecha} {linea}")
        try:
            resp = input("  > ").strip().lower()
        except EOFError:
            resp = ""
        if resp == "n":
            continue
        if resp == "e":
            linea = input("  linea corregida: ").strip() or linea
        cabecera = f"## {sec}\n"
        entrada = f"- {fecha} {linea}\n"
        if cabecera in texto:
            texto = texto.replace(cabecera, cabecera + entrada, 1)
        else:
            texto += f"\n{cabecera}{entrada}"
        aceptadas += 1
    C.escribir(C.F_DIRECTORES, texto)

    if r.get("estado"):
        print("\nCambios de estado que se deducen. Pegalos tu en contexto/estado.md:")
        for e in r["estado"]:
            print("  -", e)
    if r.get("dudas"):
        print("\nQuedo ambiguo, aclaralo con ellos:")
        for d in r["dudas"]:
            print("  -", d)

    E.sellar("reunion destilada ::")
    print(f"\n{aceptadas} lineas anadidas a contexto/directores.md")
    if len(C.leer(C.F_DIRECTORES)) + len(C.leer(C.F_ESTADO)) > C.LIMITE_CONTEXTO:
        M.aviso("El contexto vivo se esta haciendo largo. Condensa: fusiona lineas, quita lo caducado.")


def _reunion_preparar(args):
    reuniones = _reuniones()
    desde = os.path.basename(reuniones[-1])[:10] if reuniones else \
        (datetime.date.today() - datetime.timedelta(days=14)).isoformat()

    sesiones = [f for f in sorted(glob.glob(os.path.join(C.DIR_SESIONES, "2*.md")))
                if os.path.basename(f)[:10] > desde and "EJEMPLO" not in f]
    if not sesiones:
        print(f"no hay sesiones desde {desde}")
        return

    material = f"ESTADO:\n{C.leer(C.F_ESTADO)}\n\n"
    for f in sesiones:
        material += f"=== SESION {os.path.basename(f)} ===\n{C.leer(f)}\n\n"
    errores = C.leer(C.F_ERRORES)
    nuevos = [b for b in errores.split("\n### ")[1:] if b[:10] > desde]
    if nuevos:
        material += "ERRORES NUEVOS:\n### " + "\n### ".join(nuevos) + "\n\n"
    conj = C.leer(C.F_CONJETURAS)
    vivas = [b for b in conj.split("\n### ")[1:] if "Estado: viva" in b]
    if vivas:
        material += "CONJETURAS VIVAS:\n### " + "\n### ".join(vivas) + "\n"

    print(f"preparando el pre-read con {len(sesiones)} sesiones desde {desde}...")
    try:
        texto = M.llamar("reunion", P.PREPARAR, [{"role": "user", "content": material}],
                         max_tokens=C.MAX_TOKENS_JSON)
    except M.MotorApagado as e:
        print(e)
        return
    destino = os.path.join(C.DIR_REUNIONES, f"{HOY}-preread.md")
    C.escribir(destino, texto)
    print("escrito", os.path.relpath(destino, C.RAIZ))
    M.aviso("Borrador. Reescribelo con tu voz antes de mandarlo.")


# ======================================================================
# metricas
# ======================================================================

def _coste_eur(l):
    """EUR de una llamada segun config.PRECIOS (USD) y EUR_POR_USD, o None sin precio.
    La entrada cacheada se cobra a su tarifa; el resto de la entrada, a la normal."""
    p = C.PRECIOS.get(l.get("modelo") or "", {})
    if p.get("entrada") is None or p.get("salida") is None:
        return None
    cache = min(l.get("tokens_cache", 0) or 0, l.get("tokens_in", 0))
    usd = ((l.get("tokens_in", 0) - cache) * p["entrada"]
           + cache * (p.get("cacheada") if p.get("cacheada") is not None else p["entrada"])
           + l.get("tokens_out", 0) * p["salida"]) / 1e6
    return usd * C.EUR_POR_USD


def _coste_del_mes(ll):
    """Imprime tokens y euros del mes en curso por comando."""
    mes = datetime.date.today().strftime("%Y-%m")
    del_mes = [l for l in ll if l.get("ts", "").startswith(mes) and not l.get("simulado")]
    if not del_mes:
        return
    por = defaultdict(lambda: dict(n=0, tin=0, tout=0, eur=0.0, sin_precio=False))
    for l in del_mes:
        d = por[l.get("comando", "?")]
        d["n"] += 1
        d["tin"] += l.get("tokens_in", 0)
        d["tout"] += l.get("tokens_out", 0)
        c = _coste_eur(l)
        if c is None:
            d["sin_precio"] = True
        else:
            d["eur"] += c
    print(f"\n  coste de {mes} por comando          llamadas    tokens in / out       EUR"
          f"   (1 USD = {C.EUR_POR_USD} EUR, fijo en config)")
    total, incompleto = 0.0, False
    for cmd, d in sorted(por.items(), key=lambda kv: -kv[1]["tin"]):
        eur = f"{d['eur']:8.3f}" + ("+?" if d["sin_precio"] else "  ")
        print(f"    {cmd:<28} {d['n']:>8}    {d['tin']:>9,} / {d['tout']:<9,} {eur}")
        total += d["eur"]
        incompleto = incompleto or d["sin_precio"]
    aviso = ""
    if incompleto:
        aviso = "   (+? = modelos sin precio en config.PRECIOS: solo tokens)"
    elif total > C.PRESUPUESTO_MES:
        aviso = f"   <-- por encima del presupuesto de {C.PRESUPUESTO_MES:.0f} EUR"
    elif total > 0.8 * C.PRESUPUESTO_MES:
        aviso = f"   <-- al {100 * total / C.PRESUPUESTO_MES:.0f}% del presupuesto"
    print(f"    {'total':<28} {len(del_mes):>8}    {'':>21} {total:8.3f}{aviso}")


def cmd_metricas(args):
    # por ciclo: cada "inicio sesion" abre uno (con la fecha del inicio, que es la del
    # fichero de sesion) y los sellos se cuelgan de el aunque crucen la medianoche
    dias = {}
    actual = None
    for ts, msg in E.commits_todos():
        if msg.startswith("inicio sesion"):
            actual = dias.setdefault(ts.date().isoformat(),
                                     dict(inicio=None, sello1=None, ataque=None, sello3=None, pausas=[]))
            actual["inicio"] = actual["inicio"] or ts
            continue
        if actual is None:
            continue
        for clave, pref in (("sello1", "sellado :: fase 1"), ("ataque", "ataque"),
                            ("sello3", "sellado :: fase 3")):
            if msg.startswith(pref) and actual[clave] is None:
                actual[clave] = ts
        if msg.startswith("pausa") and not (actual["pausas"] and actual["pausas"][-1][1] is None):
            actual["pausas"].append([ts, None])
        if msg.startswith("reanud") and actual["pausas"] and actual["pausas"][-1][1] is None:
            actual["pausas"][-1][1] = ts
        if msg.startswith("cierre"):
            actual = None

    filas = []
    for ruta in sorted(glob.glob(os.path.join(C.DIR_SESIONES, "2*.md"))):
        if "diagnostico" in ruta or "EJEMPLO" in ruta:
            continue
        dia = os.path.basename(ruta)[:10]
        t = C.leer(ruta)
        m = re.search(r"^coincidencia_estructural:\s*(\d)", t, re.M)
        d = dias.get(dia, {})
        filas.append(dict(dia=dia,
                          f1=E.minutos_netos(d.get("inicio"), d.get("sello1"), d.get("pausas", [])),
                          f3=E.minutos_netos(d.get("ataque"), d.get("sello3"), d.get("pausas", [])),
                          coin=int(m.group(1)) if m else None))

    ll = M.llamadas()
    viol = sum(1 for l in ll if l.get("forzado"))

    if not filas:
        print("todavia no hay sesiones. Empieza por:  python doc.py diagnostico")
    else:
        ult, ant = filas[-4:], filas[-8:-4]

        def med(rs, k):
            v = [r[k] for r in rs if r[k] is not None]
            return st.mean(v) if v else None

        def f(x):
            return "   -" if x is None else f"{x:5.1f}"

        print(f"sesiones: {len(filas)}     ultimas 4 frente a las 4 anteriores\n")
        for k, nombre, minimo in (("f1", "min fase 1 (objetivo >= 35)", 35),
                                  ("f3", "min fase 3 (objetivo >= 45)", 45),
                                  ("coin", "coincidencia estructural 0-3", None)):
            a, b = med(ant, k), med(ult, k)
            marca = ""
            if b is not None and minimo and b < minimo:
                marca = "  <-- por debajo del objetivo"
            elif a is not None and b is not None and b < a:
                marca = "  <-- baja"
            print(f"  {nombre:<32} {f(a)} -> {f(b)}{marca}")

    print(f"\n  llamadas a la IA: {len(ll)}   violaciones (forzadas en fase 1/3): {viol}"
          + ("   <-- revisa por que" if viol else ""))
    tin = sum(l.get("tokens_in", 0) for l in ll)
    tout = sum(l.get("tokens_out", 0) for l in ll)
    print(f"  tokens: {tin:,} entrada / {tout:,} salida")
    _coste_del_mes(ll)

    conj = re.sub(r"```.*?```", "", C.leer(C.F_CONJETURAS), flags=re.S)
    estados = Counter(re.findall(r"^Estado:\s*(\w+)", conj, re.M))
    if estados:
        print("  conjeturas:", ", ".join(f"{k} {v}" for k, v in estados.items()))

    c = Counter(re.findall(r"^###\s+\d{4}-\d\d-\d\d\s+\[(\w)\]", C.leer(C.F_ERRORES), re.M))
    if c:
        print("  errores por tipo:", ", ".join(f"{k}={v}" for k, v in c.most_common()))
        print(f"  -> el drill de esta semana va sobre el tipo {c.most_common(1)[0][0]}")

    lag = re.sub(r"```.*?```", "", C.leer(C.F_LAGUNAS), flags=re.S)
    pend = len(re.findall(r"^- \[ \]", lag, re.M))
    estr = len(re.findall(r"^- \[.*ESTRUCTURAL", lag, re.M))
    print(f"  lagunas pendientes: {pend}   estructurales: {estr}")


# ======================================================================
# corpus: ingesta (BRIEF 4.1)
# ======================================================================

def cmd_ingest(args):
    from . import corpus as Q
    kw = dict(capa=args.capa, sin_red=args.sin_red, rehacer=args.rehacer, fuente=args.fuente,
              etiquetas=[e.strip() for e in (args.etiquetas or "").split(",") if e.strip()],
              factorial=args.factorial)
    if args.arxiv:
        if len(args.pdf) > 1:
            print("uso: python doc.py ingest --arxiv ID [nombre.pdf | ruta/existente.pdf] [--id ID] [--etiquetas a,b]")
            return
        if args.pdf and os.path.exists(args.pdf[0]):
            # PDF ya presente (p. ej. el de revista, sin sello): paginas de ese PDF, texto del e-print
            Q.ingerir(args.pdf[0], id_=args.id, arxiv=args.arxiv, **kw)
            return
        try:
            pdf = Q.descargar_pdf(args.arxiv, args.pdf[0] if args.pdf else None)
        except FileExistsError as e:
            print(e)
            return
        print(f"descargado {os.path.relpath(pdf)}")
        Q.ingerir(pdf, id_=args.id, arxiv=args.arxiv, **kw)
        return
    if args.identificar:
        if len(args.pdf) != 2:
            print("uso: python doc.py ingest --identificar ID DOI|URL")
            return
        Q.identificar(args.pdf[0], args.pdf[1])
        return
    if args.renombrar:
        if len(args.pdf) != 2:
            print("uso: python doc.py ingest --renombrar VIEJO NUEVO")
            return
        Q.renombrar(args.pdf[0], args.pdf[1])
        print("recuerda:  python doc.py indexar")
        return
    if args.remapear:
        ids = args.pdf or [k for k, e in Q.leer_bib().items() if e.get("capa") == "tex"]
        for id_ in ids:
            id_ = Q.id_desde_fichero(id_) if id_.lower().endswith(".pdf") else id_
            try:
                Q.remapear(id_)
            except Exception as e:
                print(f"{id_}: {type(e).__name__}: {e}")
        return
    if args.solo_meta:
        ids = args.pdf or sorted(Q.leer_bib())
        for id_ in ids:
            id_ = Q.id_desde_fichero(id_) if id_.lower().endswith(".pdf") else id_
            try:
                Q.refrescar_metadatos(id_)
            except Exception as e:
                print(f"{id_}: {type(e).__name__}: {e}")
        return
    if not args.pdf:
        Q.ingerir_todo(**kw)
        return
    if args.id and len(args.pdf) > 1:
        print("--id solo vale con un unico PDF")
        return
    for pdf in args.pdf:
        Q.ingerir(pdf, id_=args.id, **kw)


def _docs_mencionados(pregunta):
    """
    Ids de bib.yaml que la pregunta nombra. Casa el primer apellido; si la pregunta
    lleva un ano, exige ademas que coincida (revista, arXiv o el del id). Un apellido
    solo activa todos sus documentos: la fuente primaria tiene que estar entre los
    fragmentos aunque no sepamos cual de los papers del autor se quiere.
    """
    from . import corpus as Q
    import unicodedata as ud
    q = ud.normalize("NFKD", pregunta.lower()).encode("ascii", "ignore").decode()
    anos = set(re.findall(r"\b(19\d\d|20\d\d)\b", q))
    out = []
    for id_, e in Q.leer_bib().items():
        if e.get("fuente") == "proyecto":
            continue
        apellidos = [ud.normalize("NFKD", a.split(",")[0].lower()).encode("ascii", "ignore").decode()
                     for a in e.get("autores", [])] or [id_.split("-")[0]]
        if not (apellidos and apellidos[0] and re.search(r"\b" + re.escape(apellidos[0]) + r"\b", q)):
            continue
        anos_doc = {str(e.get("ano") or ""), str(e.get("ano_arxiv") or ""), str(e.get("ano_online") or ""),
                    re.sub(r"\D", "", id_.rsplit("-", 1)[-1])[:4]}
        if anos and not (anos & anos_doc):
            continue
        out.append(id_)
    return out[:3]


def _factorial_texto(e):
    """Convencion del documento para p!: 'factorial fuera: |f^(p)| <= C A^p p! M_p', etc."""
    f = e.get("factorial") or "pendiente"
    return {"dentro": "factorial dentro: |f^(p)| <= C A^p M_p",
            "fuera": "factorial fuera: |f^(p)| <= C A^p p! M_p",
            "no_aplica": "sin sucesion peso (no aplica el factorial)"}.get(f, "factorial: sin comprobar en el texto")


def _cabeceras_bib(frags):
    """Una linea por documento citado: id, titulo, autores, revista y ano verificados."""
    from . import corpus as Q
    bib = Q.leer_bib()
    lineas = []
    for doc in sorted({f["doc"] for f in frags}):
        e = bib.get(doc, {})
        if e.get("estado") == "verificado":
            partes = [e.get("titulo"), "; ".join(e.get("autores", [])[:3]), e.get("venue"),
                      str(e.get("ano") or e.get("ano_arxiv") or ""), _factorial_texto(e)]
            lineas.append(f"  {doc}: " + " | ".join(p for p in partes if p))
        elif e:
            lineas.append(f"  {doc}: metadatos {e.get('estado', 'sin verificar')}")
        else:
            lineas.append(f"  {doc}: nota propia")
    return "\n".join(lineas)


def _referencias_fuera_del_corpus(frags_usados):
    """Referencias que citan los fragmentos usados (\\cite resueltos con el .bbl) y no estan en bib.yaml."""
    from . import corpus as Q
    from . import indice as I
    bib = Q.leer_bib()
    vistas, fuera, dentro = set(), [], []
    for f in frags_usados:
        refs = Q.leer_referencias(f["doc"])
        textos = [f["texto"]]
        if f.get("tipo") in ("teorema", "proposicion", "lema", "corolario", "definicion"):
            # la atribucion ("proved by Thilliez \cite{...}") suele ir en el parrafo anterior
            textos += I.vecinos_anteriores(f["id"], 4)
        for clave in Q.claves_cite("\n".join(textos)):
            texto = refs.get(clave)
            if not texto or (f["doc"], clave) in vistas:
                continue
            vistas.add((f["doc"], clave))
            id_ = Q.referencia_en_corpus(texto, bib)
            (dentro if id_ else fuera).append(dict(doc=f["doc"], clave=clave, texto=texto, en_corpus=id_))
    return fuera, dentro


def _fusionar(*listas):
    vistos, out = set(), []
    for lista in listas:
        for f in lista:
            if f["id"] not in vistos:
                vistos.add(f["id"])
                out.append(f)
    return out


def _contexto_ask(pregunta, frags, segunda=None):
    from . import indice as I
    bloque = "\n\n".join(f"{I.cita(f)}" + (" (traido por referencia)" if f.get("via_ref") else "")
                         + (" (segunda busqueda)" if f.get("segunda") else "") + f"\n{f['texto']}" for f in frags)
    cab = f"PREGUNTA: {pregunta}\n\nDOCUMENTOS:\n{_cabeceras_bib(frags)}\n\n"
    if segunda:
        cab += ("SEGUNDA BUSQUEDA HECHA: " + segunda + "\nSi lo pedido sigue sin aparecer, ahora si puedes "
                "escribir: 'No esta en el corpus (segunda busqueda en <documentos> con: <palabras>)'.\n\n")
    return cab + "FRAGMENTOS:\n\n" + bloque


def cmd_ask(args):
    """Sintesis con modelo sobre fragmentos de `buscar`. Sujeta a las fases. Dos pasadas como maximo."""
    from . import indice as I
    pregunta = " ".join(args.pregunta).strip()
    if not pregunta:
        print('uso: python doc.py ask "que condiciones sobre M usa el teorema de extension de Thilliez"')
        return
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO and not args.forzar:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        print("(el corpus sigue disponible sin modelo:  python doc.py buscar \"...\")")
        return

    # evidencia: papers. El proyecto y las notas propias solo con --con-propios, y marcados.
    fuente = args.fuente or (None if args.con_propios else "paper")
    nombrados = [args.doc] if args.doc else _docs_mencionados(pregunta)
    generales = I.buscar(pregunta, k=args.k, fuente=fuente, doc=args.doc, por_doc=args.por_doc)
    # cada documento nombrado tiene cupo propio y sin tope: la fuente primaria entra siempre
    propios = []
    for d in nombrados:
        propios += I.buscar(pregunta, k=max(6, args.k // max(1, len(nombrados))), doc=d, por_doc=0)
    frags = _fusionar(propios, generales)
    if not frags:
        print("nada en el indice para esa pregunta (o indice vacio: python doc.py indexar)")
        return
    frags = _fusionar(frags, I.seguir_refs(frags))     # las \ref{} del .tex traen su definicion o lema

    def llamar(contenido):
        return M.llamar("ask", P.ASK, [{"role": "user", "content": contenido}],
                        max_tokens=C.MAX_TOKENS_ASK, forzar=args.forzar)

    def usados_de(respuesta):
        m = re.search(r"^USADOS:\s*(.*)$", respuesta, re.M | re.S)
        citas = {c.strip() for c in re.split(r";\s*", m.group(1).split("\n")[0])} if m else set()
        return [f for f in frags if I.cita(f) in citas]

    try:
        respuesta = llamar(_contexto_ask(pregunta, frags))
    except M.MotorApagado as e:
        M.aviso("MOTOR APAGADO: " + str(e))
        return
    pasadas = [dict(respuesta=respuesta, fragmentos=[f["id"] for f in frags])]

    # segunda pasada: si el modelo pide BUSCAR, o si la fuente primaria nombrada no se uso
    m = re.search(r"^BUSCAR:\s*(.+)$", respuesta, re.M)
    claves = m.group(1).strip() if m else None
    usados = usados_de(respuesta)
    primaria_ausente = bool(nombrados) and not any(f["doc"] in nombrados for f in usados)
    segunda = None
    if claves or primaria_ausente:
        consulta = claves or pregunta
        extra = []
        for d in (nombrados or [None]):
            extra += I.buscar(consulta, k=10, fuente=fuente if d is None else None, doc=d, por_doc=0)
        nuevos = [f for f in extra if f["id"] not in {g["id"] for g in frags}]
        for f in nuevos:
            f["segunda"] = True
        frags = _fusionar(frags, nuevos, I.seguir_refs(nuevos))
        donde = ", ".join(nombrados) if nombrados else "todo el corpus"
        segunda = f"restringida a {donde}, con las palabras: {consulta}" + \
            (" (la fuente primaria nombrada no aparecia entre los fragmentos usados)" if primaria_ausente and not claves else "")
        try:
            respuesta = llamar(_contexto_ask(pregunta, frags, segunda))
        except M.MotorApagado as e:
            M.aviso("MOTOR APAGADO: " + str(e))
            return
        pasadas.append(dict(respuesta=respuesta, fragmentos=[f["id"] for f in frags], busqueda=segunda))
        usados = usados_de(respuesta)

    # una BUSCAR sin segunda pasada posible no se ensena como conclusion
    respuesta_mostrar = re.sub(r"^BUSCAR:.*$", "", respuesta, flags=re.M).rstrip()
    print()
    M.imprimir(respuesta_mostrar)

    # referencias que citan los fragmentos usados y no estan en el corpus: candidatas a bib.yaml
    fuera, dentro = _referencias_fuera_del_corpus(usados)
    if fuera:
        print("\nREFERENCIAS CITADAS EN LOS FRAGMENTOS USADOS QUE NO ESTAN EN EL CORPUS (candidatas a bib.yaml):")
        for r_ in fuera:
            print(f"  - [{r_['doc']} -> {r_['clave']}] {r_['texto'][:170]}")
    if primaria_ausente and not any(f["doc"] in nombrados for f in usados):
        M.aviso(f"AVISO: la respuesta no usa ningun fragmento de {', '.join(nombrados)}, que es lo que la pregunta nombra.")

    for f in frags:
        f["usado"] = f in usados
    os.makedirs(C.DIR_CONSULTAS, exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    ruta = os.path.join(C.DIR_CONSULTAS, f"{marca}.json")
    C.escribir(ruta, json.dumps(dict(
        ts=marca, fase=fase, pregunta=pregunta, k=args.k, fuente=fuente, doc=args.doc,
        nombrados=nombrados, pasadas=pasadas, respuesta=respuesta, modelo=C.modelo_para("ask"),
        referencias_fuera=fuera, referencias_dentro=dentro,
        fragmentos=[{k_: f.get(k_) for k_ in ("id", "doc", "pagina", "tipo", "numero", "label", "seccion",
                                              "bm25", "coseno", "rrf", "usado", "via_ref", "segunda", "texto")}
                    for f in frags],
    ), ensure_ascii=False, indent=1))
    print(f"\n[{len(usados)}/{len(frags)} fragmentos usados; {len(pasadas)} pasada(s); "
          f"consulta guardada en {os.path.relpath(ruta, C.RAIZ)}]")


def cmd_indexar(args):
    from . import indice as I
    I.indexar(rehacer=args.rehacer)


def cmd_buscar(args):
    from . import indice as I
    pregunta = " ".join(args.pregunta).strip()
    if not pregunta:
        print('uso: python doc.py buscar "que condiciones sobre M usa el teorema de extension"')
        return
    res = I.buscar(pregunta, k=args.k, fuente=args.fuente, doc=args.doc, solo_bm25=args.bm25,
                   por_doc=args.por_doc)
    if not res:
        print("nada en el indice para esa pregunta (o indice vacio: python doc.py indexar)")
        return
    I.imprimir(res)


# ======================================================================
# notas de lectura por paper (BRIEF 4.3)
# ======================================================================

def _ruta_nota(id_):
    return os.path.join(C.DIR_LECTURAS, f"{id_}.md")


def _seccion_md(texto, titulo):
    """Contenido bajo '## titulo' hasta el siguiente '## '."""
    m = re.search(rf"^## {re.escape(titulo)}\s*$(.*?)(?=^## |\Z)", texto, re.M | re.S)
    return m.group(1).strip() if m else ""


def _nota_new(id_):
    from . import corpus as Q
    bib = Q.leer_bib()
    if id_ not in bib:
        print(f"{id_} no esta en corpus/meta/bib.yaml. Primero:  python doc.py ingest corpus/raw/{id_}.pdf")
        return
    ruta = _ruta_nota(id_)
    if os.path.exists(ruta):
        print("ya existe", os.path.relpath(ruta, C.RAIZ))
        _abrir(ruta)
        return
    e = bib[id_]
    # solo metadatos verificados; lo demas queda como "sin verificar"
    ok = e.get("estado") == "verificado"
    titulo = e.get("titulo") if ok else (e.get("titulo_pdf_sin_verificar") or "sin verificar")
    autores = "; ".join(e.get("autores", [])) if ok else "sin verificar"
    partes = (e.get("venue"), e.get("volumen"), f"({e['ano']})" if e.get("ano") else None,
              e.get("paginas_revista"))
    cita = " ".join(str(x) for x in partes if x) if ok else "sin verificar"
    if e.get("doi"):
        cita += f"  doi:{e['doi']}"
    if e.get("arxiv"):
        cita += f"  arXiv:{e['arxiv']}"
    valores = {"TITULO": titulo, "AUTORES": autores, "CITA": cita.strip(), "ESTADO": e.get("estado", "?"),
               "AAAA-MM-DD": HOY, "ID": id_}
    # una sola pasada sobre la plantilla: un titulo con 'IDEALS' o 'EXPLICITA' no se corrompe
    texto = re.sub(r"\b(TITULO|AUTORES|CITA|ESTADO|AAAA-MM-DD|ID)\b", lambda m: valores[m.group(1)],
                   C.leer(os.path.join(C.DIR_LECTURAS, "PLANTILLA.md")))
    C.escribir(ruta, texto)
    print("creada", os.path.relpath(ruta, C.RAIZ))
    if not ok:
        M.aviso("metadatos sin verificar: completa el DOI/handle en bib.yaml antes de citar este paper")
    _abrir(ruta)


def _fragmentos_doc(id_, consulta, k):
    from . import indice as I
    frags = I.buscar(consulta, k=k, doc=id_, por_doc=0)
    if not frags:
        print(f"{id_} no esta en el indice. Ejecuta:  python doc.py indexar")
    return frags


# --- bloques por resultado: '## R2 — Teorema 2.3' con los siete campos como '### ...' ---

RE_BLOQUE = re.compile(r"^## (R\d+)\s*[—–-]+\s*(.+?)\s*$", re.M)
SECCIONES_PAPER = ("## Sintesis", "## Transferencia", "## Abierto", "## Dudas", "## Dependencias")


def _bloques_nota(texto):
    """[(id 'R2', titulo, cuerpo)] de los bloques '## Rn — titulo' de una nota, en orden."""
    out = []
    for m in RE_BLOQUE.finditer(texto):
        fin = re.search(r"^## ", texto[m.end():], re.M)
        cuerpo = texto[m.end():m.end() + fin.start()] if fin else texto[m.end():]
        out.append((m.group(1).upper(), m.group(2).strip(), cuerpo.strip()))
    return out


def _bloque_nota(texto, resultado):
    for rid, titulo, cuerpo in _bloques_nota(texto):
        if rid == resultado.strip().upper():
            return rid, titulo, cuerpo
    return None


def _subseccion_md(cuerpo, titulo):
    """Contenido bajo '### titulo' hasta la siguiente '### ' (dentro de un bloque)."""
    m = re.search(rf"^### {re.escape(titulo)}\s*$(.*?)(?=^### |\Z)", cuerpo, re.M | re.S)
    return m.group(1).strip() if m else ""


def _numero_impreso(titulo):
    """'Teorema 2.3' / 'Lemma 2.1.1 (division)' / 'Teorema 2' -> '2.3' / '2.1.1' / '2'; None si no hay.
    Primero el numero que sigue a la palabra de tipo; si no, el primero con punto; si no, un entero."""
    m = re.search(r"(?i)\b(?:teorema|theorem|lema|lemma|proposicion|proposition|corolario|corollary|"
                  r"definicion|definition|observacion|remark|ejemplo|example)\s+(\d+(?:\.\d+)*)\b", titulo)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d+(?:\.\d+)+)\b", titulo) or re.search(r"\b(\d+)\b", titulo)
    return m.group(1) if m else None


def _pistas_plantilla():
    """Las lineas '(...)' de PLANTILLA-resultado.md, con RN/ID neutralizados: son la plantilla, no texto propio."""
    pistas = set()
    for l in C.leer(os.path.join(C.DIR_LECTURAS, "PLANTILLA-resultado.md")).splitlines():
        l = l.strip()
        if l.startswith("(") and l.endswith(")"):
            pistas.add(re.sub(r"\bR\d+\b|\bRN\b", "RN", re.sub(r"\[[^\]]*:pNN\]", "[ID:pNN]", l)))
    return pistas


RE_INTENTO = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \| nivel (\d+) \| ([\d.]+) min \| (.*)$", re.M)


def _texto_propio(sub):
    """Lo que escribio Mariano en una subseccion: sin la pista '(...)' de la plantilla y sin el
    registro 'Intentos:' con sus lineas (que escribe el sistema)."""
    s = re.sub(r"^Intentos:\s*$", "", sub, flags=re.M)
    s = RE_INTENTO.sub("", s).strip()
    m = re.match(r"\([^)]*\)", s, re.S)
    if m:
        pista = re.sub(r"\bR\d+\b", "RN", re.sub(r"\[[^\]]*:pNN\]", "[ID:pNN]", " ".join(m.group(0).split())))
        if pista in _pistas_plantilla() or any(" ".join(p.split())[:40] == pista[:40] for p in _pistas_plantilla()):
            s = s[m.end():].strip()
    return s


def _explicacion_valida(expl):
    """Texto propio de verdad (ni la pista de la plantilla ni el registro de intentos), y con cuerpo."""
    cuerpo = _texto_propio(expl)
    return len(cuerpo) >= 200 and not cuerpo.startswith("Tu reconstruccion")


CAMPOS_R = ("Enunciado", "Hipotesis, y por que cada una", "Lema clave", "Que se rompe sin el",
            "Desarrollo (fase 2, con el paper)", "Reconstruccion (fase 3, a ciegas)",
            "Derivaciones y reformulaciones", "Donde se usa")


def _subseccion_flexible(cuerpo, nombre):
    """'### Reconstruccion (fase 3, a ciegas)' tambien casa con 'Reconstruccion' a secas;
    'Reconstruccion' admite el nombre antiguo 'Mi explicacion'."""
    m = re.search(rf"^### {re.escape(nombre)}\b[^\n]*$(.*?)(?=^### |\Z)", cuerpo, re.M | re.S)
    if not m and nombre == "Reconstruccion":
        m = re.search(r"^### Mi explicacion\b[^\n]*$(.*?)(?=^### |\Z)", cuerpo, re.M | re.S)
    return m.group(1).strip() if m else ""


def _intentos(cuerpo):
    """[(fecha, nivel, minutos, sesion)] de las lineas '- fecha | nivel N | ...' bajo 'Intentos:'."""
    rec = _subseccion_flexible(cuerpo, "Reconstruccion")
    m = re.search(r"^Intentos:\s*$(.*)", rec, re.M | re.S)
    out = []
    if m:
        for l in RE_INTENTO.findall(m.group(1)):
            out.append((l[0], max(0, min(3, int(l[1]))), float(l[2]), l[3].strip()))
    return out


def _registrar_intento(doc, rid, fecha, nivel, minutos, sesion):
    """Anade '- fecha | nivel N | M min | sesion X' bajo 'Intentos:' de ### Reconstruccion del bloque.
    Devuelve 'lecturas/ID.md R2' o None si el bloque no existe."""
    ruta = _ruta_nota(doc)
    if not os.path.exists(ruta):
        return None
    texto = C.leer(ruta)
    b = _bloque_nota(texto, rid)
    if not b:
        return None
    rid, titulo, cuerpo = b
    nivel = max(0, min(3, int(nivel)))
    linea = f"- {fecha} | nivel {nivel} | {minutos if minutos is not None else 0} min | sesion {sesion}"
    if any(i[0] == fecha and i[3] == f"sesion {sesion}" for i in _intentos(cuerpo)):
        return f"lecturas/{doc}.md {rid} (ya anotado)"            # un cierre repetido no duplica
    m_bloque = re.search(rf"^## {rid}\b[^\n]*$", texto, re.M)
    fin = re.search(r"^## ", texto[m_bloque.end():], re.M)
    ini, fin = m_bloque.end(), (m_bloque.end() + fin.start() if fin else len(texto))
    bloque = texto[ini:fin]
    m_rec = (re.search(r"^### Reconstruccion\b[^\n]*$", bloque, re.M)          # misma prioridad que _intentos
             or re.search(r"^### Mi explicacion\b[^\n]*$", bloque, re.M))
    if m_rec:
        resto = re.search(r"^### ", bloque[m_rec.end():], re.M)
        r_fin = m_rec.end() + resto.start() if resto else len(bloque)
        seccion = bloque[m_rec.end():r_fin]
        if re.search(r"^Intentos:", seccion, re.M):
            seccion = seccion.rstrip("\n") + "\n" + linea + "\n\n"
        else:
            seccion = seccion.rstrip("\n") + "\n\nIntentos:\n" + linea + "\n\n"
        bloque = bloque[:m_rec.end()] + seccion + bloque[r_fin:]
    else:
        bloque = bloque.rstrip("\n") + "\n\n### Reconstruccion (fase 3, a ciegas)\n\nIntentos:\n" + linea + "\n\n"
    C.escribir(ruta, texto[:ini] + bloque + texto[fin:])
    return f"lecturas/{doc}.md {rid}"


def _nota_estado(id_):
    """Por bloque: campos escritos, intentos y ultimo check. Sin modelo."""
    ruta = _ruta_nota(id_)
    if not os.path.exists(ruta):
        print(f"no hay nota. Primero:  python doc.py nota new {id_}")
        return
    texto = C.leer(ruta)
    bloques = _bloques_nota(texto)
    print(f"lecturas/{id_}.md: {len(bloques)} bloques")
    plantilla = C.leer(os.path.join(C.DIR_LECTURAS, "PLANTILLA.md")).replace("ID", id_)
    for sec in ("Mapa", "Sintesis", "Transferencia", "Abierto", "Dudas", "Dependencias"):
        cuerpo = _seccion_md(texto, sec)
        escrita = bool(cuerpo.strip()) and cuerpo.strip() != _seccion_md(plantilla, sec).strip()
        print(f"  {sec:<14} {'escrita' if escrita else 'plantilla'}")
    for rid, titulo, cuerpo in bloques:
        escritos = [c.split(" (")[0] for c in CAMPOS_R
                    if len(_texto_propio(_subseccion_flexible(cuerpo, c.split(" (")[0]))) > 40]
        ints = _intentos(cuerpo)
        checks = sorted(glob.glob(os.path.join(C.DIR_LECTURAS, f"{id_}-check-{rid}-*.md")))
        print(f"\n  {rid} — {titulo}")
        print(f"    campos escritos: {len(escritos)}/{len(CAMPOS_R)}" + (": " + ", ".join(escritos) if escritos else ""))
        if ints:
            u = ints[-1]
            print(f"    intentos: {len(ints)}; ultimo {u[0]} nivel {u[1]} ({u[2]} min)")
        else:
            print("    intentos: ninguno")
        print("    ultimo check: " + (os.path.basename(checks[-1]) if checks else "ninguno"))


def _nota_add(id_, titulo):
    """
    Anade a lecturas/ID.md un bloque '## Rn — titulo' con los campos de PLANTILLA-resultado.md,
    antes de las secciones de paper, y su linea en ## Mapa. Sin 'Rn' en el titulo, numera el
    siguiente libre.
    """
    ruta = _ruta_nota(id_)
    if not os.path.exists(ruta):
        print(f"no hay nota. Primero:  python doc.py nota new {id_}")
        return
    if not titulo or not titulo.strip():
        print('uso:  python doc.py nota add ID "R2 — Teorema 2.3"')
        return
    texto = C.leer(ruta)
    bloques = _bloques_nota(texto)
    usados = {int(b[0][1:]) for b in bloques}
    libre = next(n for n in range(1, len(usados) + 2) if n not in usados)
    m = re.match(r"\s*(R\d+)\s*[—–-]*\s*(.*)$", titulo.strip(), re.S)
    if m:
        rid, resto = m.group(1).upper(), m.group(2).strip()
    else:
        rid, resto = f"R{libre}", titulo.strip()
    if any(b[0] == rid for b in bloques):
        print(f"{rid} ya existe en la nota; el siguiente libre es R{libre}")
        return
    if not resto:
        print('falta el titulo del resultado: p. ej. "R2 — Teorema 2.3"')
        return
    plantilla = C.leer(os.path.join(C.DIR_LECTURAS, "PLANTILLA-resultado.md"))
    if not plantilla.strip():
        plantilla = "## RN — TITULO\n\n### Enunciado\n\n### Mi explicacion\n"
    bloque = plantilla.replace("RN", rid).replace("ID", id_).replace("TITULO", resto).strip() + "\n"
    pos = None
    for sec in SECCIONES_PAPER:                  # el bloque va antes de la primera seccion de paper
        i = texto.find("\n" + sec)
        if i >= 0:
            pos = i + 1
            break
    if pos is None:
        texto = texto.rstrip("\n") + "\n\n" + bloque
    else:
        texto = texto[:pos] + bloque + "\n" + texto[pos:]
    mapa = re.search(r"^## Mapa\s*$", texto, re.M)
    if mapa:                                       # y una linea en el Mapa
        fin = re.search(r"^## ", texto[mapa.end():], re.M)
        corte = mapa.end() + fin.start() if fin else len(texto)
        cuerpo = texto[mapa.end():corte].rstrip("\n")
        texto = texto[:mapa.end()] + cuerpo + f"\n- {rid} — {resto}\n\n" + texto[corte:].lstrip("\n")
    C.escribir(ruta, texto)
    print(f"anadido {rid} — {resto} en {os.path.relpath(ruta, C.RAIZ)}")
    _abrir(ruta)


def _frags_resultado(id_, rid, titulo, consulta, k):
    """Fragmentos para un bloque: primero el del numero impreso del titulo, luego los afines."""
    from . import indice as I
    num = _numero_impreso(titulo)
    exactos = I.por_numero(id_, num) if num else []
    if num and not exactos:
        print(f"  (el numero {num} del titulo de {rid} no esta resuelto en el indice; se busca por texto)")
    frags = _fusionar(exactos, _fragmentos_doc(id_, consulta, k))
    return _fusionar(frags, I.seguir_refs(frags, maximo=3))


def _nota_quiz(id_, k, resultado=None):
    from . import indice as I
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        return
    foco, sufijo = "", ""
    if resultado:
        if not os.path.exists(_ruta_nota(id_)):
            print(f"no hay nota. Primero:  python doc.py nota new {id_}")
            return
        b = _bloque_nota(C.leer(_ruta_nota(id_)), resultado)
        if not b:
            print(f"no hay bloque {resultado} en lecturas/{id_}.md:  python doc.py nota add {id_} \"{resultado} — ...\"")
            return
        rid, titulo, cuerpo = b
        enunciado = _subseccion_md(cuerpo, "Enunciado")
        propio = _texto_propio(enunciado)
        consulta = titulo + (" " + propio[:600] if propio else "")
        frags = _frags_resultado(id_, rid, titulo, consulta, k)
        foco, sufijo = f"RESULTADO: {rid} — {titulo}\n\n", f"-{rid}"
    else:
        frags = _fragmentos_doc(id_, "main theorem hypotheses definitions lemma proof conditions on M", k)
    if not frags:
        return
    bloque = foco + "\n\n".join(f"{I.cita(f)}\n{f['texto']}" for f in frags)
    try:
        r = M.llamar("nota-quiz", P.NOTA_QUIZ, [{"role": "user", "content": bloque}],
                     max_tokens=C.MAX_TOKENS_JSON)
    except M.MotorApagado as e:
        M.aviso(str(e))
        return
    ruta = os.path.join(C.DIR_LECTURAS, f"{id_}-quiz{sufijo}-{HOY}.md")
    C.escribir(ruta, f"# Quiz {id_}{' ' + sufijo[1:] if sufijo else ''} ({HOY})\n\n"
                     "Sin respuestas. Contesta por escrito antes de abrir el paper.\n\n" + r + "\n")
    print()
    M.imprimir(r, consola=True)
    print(f"\n-> {os.path.relpath(ruta, C.RAIZ)}")


def _nota_check(id_, k, resultado=None, desarrollo=False):
    from . import indice as I
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        return
    ruta = _ruta_nota(id_)
    if not os.path.exists(ruta):
        print(f"no hay nota. Primero:  python doc.py nota new {id_}")
        return
    texto = C.leer(ruta)
    bloques = _bloques_nota(texto)
    campo = "Desarrollo" if desarrollo else "Reconstruccion"
    rid, titulo = None, None
    if resultado:
        b = _bloque_nota(texto, resultado)
        if not b:
            print(f"no hay bloque {resultado} en lecturas/{id_}.md:  python doc.py nota add {id_} \"{resultado} — ...\"")
            return
        rid, titulo, cuerpo = b
        expl = _subseccion_flexible(cuerpo, campo)
        if not _explicacion_valida(expl):
            print(f"la '### {campo}' de {rid} esta vacia o es la plantilla. Escribela primero.")
            return
    elif bloques:
        con = [(r_, t_, _subseccion_flexible(c_, campo)) for r_, t_, c_ in bloques]
        con = [x for x in con if _explicacion_valida(x[2])]
        if len(con) == 1:
            rid, titulo, expl = con[0]
        elif not con:
            print(f"ningun bloque tiene '### {campo}' escrita. Escribela y lanza:  "
                  f"python doc.py nota check {id_} --resultado R1")
            return
        else:
            print("varios bloques con explicacion; di cual:  --resultado " + " | ".join(x[0] for x in con))
            return
    else:                                           # nota sin bloques (formato antiguo)
        expl = _seccion_md(texto, "Mi explicacion")
        if not _explicacion_valida(expl):
            print("la nota no tiene bloques ni '## Mi explicacion' escrita. Anade un resultado:  "
                  f"python doc.py nota add {id_} \"R1 — Teorema ...\"")
            return
    if rid:
        frags = _frags_resultado(id_, rid, titulo, expl[:2000], k)
    else:
        frags = _fragmentos_doc(id_, expl[:2000], k)
    if not frags:
        return
    expl = re.sub(r"^Intentos:.*", "", expl, flags=re.M | re.S).strip()      # el registro de intentos no se juzga
    bloque = "\n\n".join(f"{I.cita(f)}\n{f['texto']}" for f in frags)
    contenido = ((f"RESULTADO: {rid} — {titulo}\n\n" if rid else "")
                 + f"SU EXPLICACION:\n{expl}\n\nFRAGMENTOS DEL PAPER:\n\n{bloque}")
    try:
        r = M.llamar("nota-check", P.NOTA_CHECK, [{"role": "user", "content": contenido}],
                     max_tokens=C.MAX_TOKENS_JSON)
    except M.MotorApagado as e:
        M.aviso(str(e))
        return
    sufijo = f"-{rid}" if rid else ""
    salida = os.path.join(C.DIR_LECTURAS, f"{id_}-check{sufijo}-{HOY}.md")
    C.escribir(salida, f"# Check {id_}{' ' + rid if rid else ''} ({HOY})\n\n{r}\n")
    print()
    M.imprimir(r, consola=True)
    n_obj = len(re.findall(r"^\s*\d+[.)]", r, re.M))
    que = f"{id_} {rid} ({titulo})" if rid else id_
    _verificacion(f"explicacion propia de {que} (lecturas/{id_}.md)", "check contra el texto",
                  f"{n_obj} objeciones -> lecturas/{os.path.basename(salida)}")
    print(f"\n-> {os.path.relpath(salida, C.RAIZ)}  |  fila en registro/verificaciones.md")


def _verificacion(afirmacion, metodo, resultado):
    """Fila en registro/verificaciones.md: fecha | afirmacion | metodo | resultado."""
    if not os.path.exists(C.F_VERIFICACIONES):
        C.escribir(C.F_VERIFICACIONES,
                   "# Verificaciones\n\nToda afirmacion que se de por verificada, con fecha, metodo y "
                   "resultado. Metodos: cita, computo, prueba propia, referee, check.\n\n"
                   "| Fecha | Afirmacion | Metodo | Resultado |\n|---|---|---|---|\n")
    C.anadir(C.F_VERIFICACIONES, f"| {HOY} | {afirmacion} | {metodo} | {resultado} |\n")


def cmd_nota(args):
    resultado = getattr(args, "resultado", None)
    titulo = getattr(args, "titulo", None)
    if args.accion in ("quiz", "check") and titulo:
        if not resultado and re.fullmatch(r"[Rr]\d+", titulo.strip()):
            resultado = titulo.strip().upper()          # 'nota quiz ID R2' vale como --resultado R2
        else:
            print(f"uso:  python doc.py nota {args.accion} {args.id} --resultado R2")
            return
    if args.accion == "new":
        _nota_new(args.id)
    elif args.accion == "add":
        _nota_add(args.id, getattr(args, "titulo", None))
    elif args.accion == "quiz":
        _nota_quiz(args.id, args.k, resultado)
    elif args.accion == "check":
        _nota_check(args.id, args.k, resultado, getattr(args, "desarrollo", False))
    elif args.accion == "estado":
        _nota_estado(args.id)


# ======================================================================
# referee y redactor (BRIEF 4.5)
# ======================================================================

def _texto_o_seccion(ruta, seccion):
    texto = C.leer(ruta)
    if not texto.strip():
        return None
    if seccion:
        parte = _seccion_md(texto, seccion)
        if not parte:
            # tolerante: '## Fase 3 - Ataque (...)' encaja con --seccion "Fase 3"
            m = re.search(rf"^## [^\n]*{re.escape(seccion)}[^\n]*$(.*?)(?=^## |\Z)", texto, re.M | re.S)
            parte = m.group(1).strip() if m else ""
        return parte or None
    return texto


def _llamar_con_proveedor(comando, system, messages, proveedor, max_tokens):
    """motor.llamar con otro proveedor solo durante esta llamada: el juez no es el redactor."""
    if not proveedor or proveedor == C.PROVEEDOR:
        return M.llamar(comando, system, messages, max_tokens=max_tokens)
    clave = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}[proveedor]
    if not os.environ.get(clave):
        raise RuntimeError(f"falta {clave} en .env para --proveedor {proveedor}")
    guardado = (C.PROVEEDOR, C.MODELO, M._cliente)
    try:
        C.PROVEEDOR = proveedor
        C.MODELO = C._MODELOS[proveedor]
        M._cliente = None
        return M.llamar(comando, system, messages, max_tokens=max_tokens)
    finally:
        C.PROVEEDOR, C.MODELO, M._cliente = guardado


def cmd_referee(args):
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        return
    if not os.path.exists(args.archivo):
        print("no existe", args.archivo)
        return
    texto = _texto_o_seccion(args.archivo, args.seccion)
    if not texto:
        print("nada que juzgar" + (f" en la seccion '{args.seccion}'" if args.seccion else ""))
        return
    contenido = "TEXTO A JUZGAR:\n\n" + texto
    if args.contexto:
        from . import indice as I
        frags = I.buscar(texto[:2000], k=6, fuente="paper")
        if frags:
            contenido += "\n\nFRAGMENTOS DEL CORPUS (solo para contrastar citas):\n\n" + \
                "\n\n".join(f"{I.cita(f)}\n{f['texto']}" for f in frags)
    # contexto nuevo: sin historial, un solo mensaje
    try:
        r = _llamar_con_proveedor("referee", P.REFEREE, [{"role": "user", "content": contenido}],
                                  args.proveedor, C.MAX_TOKENS_JSON)
    except (M.MotorApagado, RuntimeError) as e:
        M.aviso(str(e))
        return
    print()
    M.imprimir(r)
    rel = os.path.relpath(args.archivo, C.RAIZ).replace("\\", "/")
    os.makedirs(os.path.join(C.DIR_REGISTRO, "referee"), exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    salida = os.path.join(C.DIR_REGISTRO, "referee", f"{marca}.md")
    juez = args.proveedor or C.PROVEEDOR
    C.escribir(salida, f"# Referee {marca}\n\nArchivo: {rel}" + (f"  seccion: {args.seccion}" if args.seccion else "")
               + f"\nJuez: {juez}\n\n## Texto juzgado\n\n{texto}\n\n## Objeciones\n\n{r}\n")
    n_obj = len(re.findall(r"^\s*\d+[.)]", r, re.M))
    bloquea = len(re.findall(r"BLOQUEA", r))
    _verificacion(f"{rel}" + (f" [{args.seccion}]" if args.seccion else ""), f"referee ({juez})",
                  f"{n_obj} objeciones, {bloquea} bloquean -> registro/referee/{os.path.basename(salida)}")
    print(f"\n-> {os.path.relpath(salida, C.RAIZ)}  |  fila en registro/verificaciones.md")


def cmd_redactar(args):
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        return
    texto = _texto_o_seccion(args.archivo, args.seccion) if os.path.exists(args.archivo) else None
    if not texto:
        print("nada que redactar")
        return
    try:
        r = M.llamar("redactar", P.REDACTOR, [{"role": "user", "content": texto}], max_tokens=C.MAX_TOKENS_JSON)
    except M.MotorApagado as e:
        M.aviso(str(e))
        return
    print()
    M.imprimir(r)
    salida = os.path.splitext(args.archivo)[0] + f"-redactado-{HOY}.md"
    C.escribir(salida, r)
    print(f"\n-> {os.path.relpath(salida, C.RAIZ)}   (borrador: las marcas [VERIFICAR] son tuyas de resolver)")


# ======================================================================
# anki
# ======================================================================

def cmd_anki(args):
    import csv
    todas = [l.strip() for l in C.leer(C.F_PENDIENTES).splitlines()
             if "::" in l and not l.startswith("#") and not l.startswith("<!--")
             and "`" not in l]
    # Una tarjeta cuya respuesta es "pendiente de pegar la definicion" no se
    # repasa: se queda aqui hasta que exista la definicion.
    retenidas = [l for l in todas if "VERIFICAR CON PAPER" in l]
    lineas = [l for l in todas if "VERIFICAR CON PAPER" not in l]
    if not lineas:
        print("nada exportable" + (f": las {len(retenidas)} que hay esperan el paper" if retenidas else ""))
        return
    salida = os.path.join(C.DIR_DRILL, f"anki-{HOY}.csv")
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        for l in lineas:
            p, _, r = l.partition("::")
            w.writerow([p.strip().lstrip("- "), r.strip()])
    C.anadir(os.path.join(C.DIR_DRILL, "exportadas.md"),
             f"\n## exportadas {HOY}\n" + "\n".join(lineas) + "\n")
    cabecera = ("# Pendientes\n\nUna tarjeta por linea con el separador de dos puntos dobles.\n"
                "Las generan cierre, lagunas y diagnostico. No fabriques tarjetas a mano.\n")
    if retenidas:
        cabecera += "\n<!-- esperan el paper: completa la respuesta y vuelve a exportar -->\n" \
                    + "\n".join(retenidas) + "\n"
    C.escribir(C.F_PENDIENTES, cabecera)
    print(f"{len(lineas)} tarjetas -> {os.path.relpath(salida, C.RAIZ)}")
    if retenidas:
        print(f"{len(retenidas)} se quedan en drill/pendientes.md: su respuesta es 'pendiente de pegar'.")
    print("Anki: Archivo > Importar, separador punto y coma, mazo 'doctorado'.")
