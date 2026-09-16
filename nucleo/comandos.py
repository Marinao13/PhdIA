"""Los comandos de doc.py. Cada uno es una funcion cmd_*(args)."""
import os, re, sys, glob, json, time, datetime, statistics as st
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
        t = E.minutos(marcas["inicio"], datetime.datetime.now().astimezone())
        M.aviso(f"\nfase 1 sellada tras {t} min. MOTOR ENCENDIDO.  python doc.py preguntar")
    if ok and n == 3:
        t = E.minutos(marcas["ataque"], datetime.datetime.now().astimezone())
        M.aviso(f"\nfase 3 sellada tras {t} min. MOTOR ENCENDIDO.  python doc.py cierre")


def cmd_ataque(args):
    fase, _ = E.fase_actual()
    if fase != "f2":
        print(f"el ataque empieza desde la fase 2 (fase actual: {fase})")
        return
    ok, msg = E.sellar("ataque ::")
    if not ok and "nada que sellar" in msg:
        # no hay cambios pero queremos el marcador igualmente
        E.git("commit", "-q", "--allow-empty", "-m",
              f"ataque :: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        ok = True
    que = ("EJERCICIOS del capitulo, libro abierto" if _es_base()
           else "extension, contraejemplo, caso Beurling")
    M.aviso(f"MOTOR APAGADO. Fase 3, 45 min: {que}.\n"
            "Al terminar:  python doc.py sellar 3")


def cmd_estado(args):
    fase, m = E.fase_actual()
    nombres = dict(libre="libre (sin sesion hoy)", f1="fase 1, motor OFF",
                   f2="fase 2, motor ON", f3="fase 3, motor OFF", f4="fase 4, motor ON")
    print(nombres[fase])
    for l in C.leer(C.F_ESTADO).splitlines():
        if l.startswith("- Fase:"):
            print(" ", l[2:])
    for k in ("inicio", "sello1", "ataque", "sello3"):
        if m[k]:
            print(f"  {k:<8} {m[k].strftime('%H:%M')}")
    if m["inicio"] and m["sello1"]:
        print(f"  fase 1: {E.minutos(m['inicio'], m['sello1'])} min")
    if m["ataque"] and m["sello3"]:
        print(f"  fase 3: {E.minutos(m['ataque'], m['sello3'])} min")
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


# Las cuatro fases de una sesion, con el motor de cada una.
CICLO = (("1 ciego", "OFF"), ("2 IA", "ON"), ("3 ataque", "OFF"), ("4 cierre", "ON"))
_COLUMNA = {"f1": 0, "f2": 1, "f3": 2, "f4": 3}


def _mapa(fase, en_sesion):
    """El ciclo dibujado, con corchetes donde estas."""
    if not en_sesion:
        return ["    sin sesion abierta hoy. El motor esta ENCENDIDO: puedes preguntar,",
                "    resolver lagunas o usar el laboratorio."]
    aqui = _COLUMNA[fase]
    arriba, abajo = "   ", "   "
    for i, (nombre, motor) in enumerate(CICLO):
        arriba += (f"[ {nombre} ]" if i == aqui else f"  {nombre}  ").center(16)
        abajo += (motor if i != aqui else f"AQUI, {motor}").center(16)
    return [arriba.rstrip(), abajo.rstrip()]


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
            porque + " ETIQUETA es el paper: p. ej. thilliez2003.",
            "detras: 10 min de carga en frio y 25 de intento a ciegas, motor OFF")


def _siguiente(fase, en_sesion, hay_diagnostico, base):
    """(comando, por que, lo que viene detras) desde donde estas ahora."""
    if fase == "f1" and not en_sesion:
        return ("(sigue en la ventana del diagnostico)",
                "el diagnostico esta a medias: se sella solo al terminar los items.",
                "si lo cortaste: python doc.py diagnostico --repetir")
    if fase == "f1":
        return ("python doc.py sellar 1",
                "estas en el intento a ciegas, por escrito y sin ayuda. Motor APAGADO.",
                "detras: python doc.py preguntar")
    if fase == "f3":
        return ("python doc.py sellar 3",
                "45 min de ataque" + (": ejercicios del capitulo" if base else
                                      ": extension, contraejemplo, caso Beurling") + ". Motor APAGADO.",
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
    python doc.py preguntar         fase 2, 60 min.  /notacion /lema /paso /pegar
    python doc.py ataque            fase 3, 45 min.  motor OFF
    python doc.py sellar 3          cierra el ataque -> motor ON
    python doc.py cierre            fase 4: diff, errores, tarjetas, lagunas

  FUERA DE SESION
    python doc.py lagunas           viernes, 45 min, el lote de huecos
    python doc.py lab "..."         la IA escribe el script, mpmath juzga
    python doc.py reunion           notas de la reunion de hoy
    python doc.py anki              exporta las tarjetas nuevas
    python doc.py metricas          los numeros, sin autodeclaracion

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
    for l in _mapa(fase, en_sesion):
        print(l)

    comando, porque, detras = _siguiente(fase, en_sesion, hay_diagnostico, base)
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
        if siguiente:
            print(f"    corpus {hechos}/{total}, siguiente sin leer: {siguiente}")
        elif total:
            print(f"    corpus {hechos}/{total}: nucleo terminado")

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
  /notacion   la siguiente pregunta va con la plantilla de notacion
  /lema       ... con la de lema estandar
  /paso       ... con la de paso comprimido
  Pega varias lineas de golpe y quedan guardadas como fragmento; luego escribe la
  pregunta, o Enter para que lo desarrolle paso a paso.
  /pegar      lo mismo a mano: pega y termina con una linea que sea solo un punto
  /nuevo      olvida la conversacion (nuevo fragmento, nuevo hilo)
  /salir
Sin plantilla la pregunta va tal cual, con las reglas de fase 2 igualmente."""


def _registrar_conversacion(fase, pregunta, respuesta, plantilla, fragmento):
    """Cada turno de preguntar queda en registro/consultas/AAAA-MM-DD-preguntar.jsonl."""
    os.makedirs(C.DIR_CONSULTAS, exist_ok=True)
    ruta = os.path.join(C.DIR_CONSULTAS, f"{HOY}-preguntar.jsonl")
    C.anadir(ruta, json.dumps(dict(
        ts=datetime.datetime.now().isoformat(timespec="seconds"), fase=fase, modelo=C.MODELO,
        plantilla=(plantilla[:40].split("]")[0].lstrip("[") if plantilla else None),
        fragmento=fragmento or None, pregunta=pregunta, respuesta=respuesta,
    ), ensure_ascii=False) + "\n")


def cmd_preguntar(args):
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO and not args.forzar:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        print("(si de verdad hace falta: --forzar. Queda registrado como violacion.)")
        return
    if args.forzar and fase not in E.MOTOR_PERMITIDO:
        M.aviso("FORZADO. Esto cuenta como violacion en las metricas.")

    print(AYUDA_REPL)
    historia, plantilla, fragmento = [], "", ""
    while True:
        try:
            lineas = _leer_lineas("\n> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if len(lineas) > 1:
            # varias lineas de golpe: es un pegado, no varias preguntas
            fragmento = "\n".join(lineas).strip()
            print(f"fragmento de {len(lineas)} lineas guardado. Ahora la pregunta "
                  "(Enter = que lo desarrolle paso a paso)")
            continue
        linea = lineas[0].strip()
        if not linea:
            if not fragmento:
                continue
            linea = "Desarrolla este fragmento paso a paso, marcando con [!] lo que uses y no este en el."
        if linea == "/salir":
            break
        if linea == "/ayuda":
            print(AYUDA_REPL)
            continue
        if linea == "/nuevo":
            historia, plantilla, fragmento = [], "", ""
            print("hilo nuevo")
            continue
        if linea in ("/notacion", "/lema", "/paso"):
            plantilla = {"/notacion": P.P_NOTACION, "/lema": P.P_LEMA, "/paso": P.P_PASO}[linea]
            print("plantilla cargada para la siguiente pregunta")
            continue
        if linea == "/pegar":
            print("pega el fragmento; termina con una linea que sea solo un punto")
            buf = []
            while True:
                l = input()
                if l.strip() == ".":
                    break
                buf.append(l)
            fragmento = "\n".join(buf)
            print(f"fragmento guardado ({len(fragmento)} caracteres)")
            continue

        contenido = plantilla + (f"FRAGMENTO DEL TEXTO:\n{fragmento}\n\n" if fragmento else "") + linea
        historia.append({"role": "user", "content": contenido})
        try:
            respuesta = M.llamar("preguntar", _sistema(P.FASE2), historia, forzar=args.forzar)
        except M.MotorApagado as e:
            M.aviso("MOTOR APAGADO: " + str(e))
            historia.pop()
            break
        historia.append({"role": "assistant", "content": respuesta})
        print()
        M.imprimir(respuesta)
        _registrar_conversacion(fase, contenido, respuesta, plantilla, fragmento)
        plantilla, fragmento = "", ""


# ======================================================================
# fase 4: cierre
# ======================================================================

def cmd_cierre(args):
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
        coincidencia = int(c) if c in "0123" and c else prop
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
    texto = _pon(texto, "min_f1", E.minutos(m["inicio"], m["sello1"]))
    texto = _pon(texto, "min_f3", E.minutos(m["ataque"], m["sello3"]))
    texto = _pon(texto, "coincidencia_estructural", coincidencia)
    texto = _pon(texto, "llamadas_f2", f2)
    texto = _pon(texto, "conjeturas", len(conj))
    C.escribir(ruta, texto)

    E.sellar("cierre ::")
    print(f"\nerrores {len(errs)} | tarjetas {nt} | lagunas {nl} | conjeturas {len(conj)}")
    print(f"fase 1: {E.minutos(m['inicio'], m['sello1'])} min | "
          f"fase 3: {E.minutos(m['ataque'], m['sello3'])} min | llamadas f2: {f2}")


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
    E.git("commit", "-q", "--allow-empty", "-m",
          f"inicio diagnostico :: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

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
    # por dia: inicio / sello1 / ataque / sello3
    dias = defaultdict(lambda: dict(inicio=None, sello1=None, ataque=None, sello3=None))
    for ts, msg in E.commits_todos():
        d = dias[ts.date().isoformat()]
        for clave, pref in (("inicio", "inicio sesion"), ("sello1", "sellado :: fase 1"),
                            ("ataque", "ataque"), ("sello3", "sellado :: fase 3")):
            if msg.startswith(pref) and d[clave] is None:
                d[clave] = ts

    filas = []
    for ruta in sorted(glob.glob(os.path.join(C.DIR_SESIONES, "2*.md"))):
        if "diagnostico" in ruta or "EJEMPLO" in ruta:
            continue
        dia = os.path.basename(ruta)[:10]
        t = C.leer(ruta)
        m = re.search(r"^coincidencia_estructural:\s*(\d)", t, re.M)
        d = dias.get(dia, {})
        filas.append(dict(dia=dia,
                          f1=E.minutos(d.get("inicio"), d.get("sello1")),
                          f3=E.minutos(d.get("ataque"), d.get("sello3")),
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
    kw = dict(capa=args.capa, sin_red=args.sin_red, rehacer=args.rehacer, fuente=args.fuente)
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
    """Ids de bib.yaml cuyo primer apellido y ano (revista, arXiv o el del id) aparecen en la pregunta."""
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
        anos_doc = {str(e.get("ano") or ""), str(e.get("ano_arxiv") or ""), id_.rsplit("-", 1)[-1]}
        if apellidos and apellidos[0] and apellidos[0] in q and (anos & anos_doc):
            out.append(id_)
    return out


def _cabeceras_bib(frags):
    """Una linea por documento citado: id, titulo, autores, revista y ano verificados."""
    from . import corpus as Q
    bib = Q.leer_bib()
    lineas = []
    for doc in sorted({f["doc"] for f in frags}):
        e = bib.get(doc, {})
        if e.get("estado") == "verificado":
            partes = [e.get("titulo"), "; ".join(e.get("autores", [])[:3]), e.get("venue"),
                      str(e.get("ano") or e.get("ano_arxiv") or "")]
            lineas.append(f"  {doc}: " + " | ".join(p for p in partes if p))
        elif e:
            lineas.append(f"  {doc}: metadatos {e.get('estado', 'sin verificar')}")
        else:
            lineas.append(f"  {doc}: nota propia")
    return "\n".join(lineas)


def cmd_ask(args):
    """Sintesis con modelo sobre fragmentos de `buscar`. Sujeta a las fases."""
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
    frags = I.buscar(pregunta, k=args.k, fuente=fuente, doc=args.doc, por_doc=args.por_doc)
    nombrados = [] if args.doc else _docs_mencionados(pregunta)
    if len(nombrados) == 1:
        # la pregunta va sobre ese paper: la mitad del cupo, solo de el, sin tope por documento
        propios = I.buscar(pregunta, k=max(4, args.k // 2), doc=nombrados[0], por_doc=0)
        vistos = {f["id"] for f in frags}
        frags = [f for f in propios if f["id"] not in vistos] + frags
        frags = frags[:args.k + 2]
    if not frags:
        print("nada en el indice para esa pregunta (o indice vacio: python doc.py indexar)")
        return
    frags += I.seguir_refs(frags)          # las \ref{} del .tex traen su definicion o lema
    bloque = "\n\n".join(f"{I.cita(f)}" + (" (traido por referencia)" if f.get("via_ref") else "")
                          + f"\n{f['texto']}" for f in frags)
    contenido = f"PREGUNTA: {pregunta}\n\nDOCUMENTOS:\n{_cabeceras_bib(frags)}\n\nFRAGMENTOS:\n\n{bloque}"
    try:
        respuesta = M.llamar("ask", P.ASK, [{"role": "user", "content": contenido}],
                             max_tokens=C.MAX_TOKENS_ASK, forzar=args.forzar)
    except M.MotorApagado as e:
        M.aviso("MOTOR APAGADO: " + str(e))
        return
    print()
    M.imprimir(respuesta)

    # registro: pregunta, respuesta y TODOS los fragmentos recuperados, marcando los usados
    m = re.search(r"^USADOS:\s*(.*)$", respuesta, re.M)
    usadas = {c.strip() for c in m.group(1).split(";")} if m else set()
    for f in frags:
        f["usado"] = I.cita(f) in usadas
    os.makedirs(C.DIR_CONSULTAS, exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    ruta = os.path.join(C.DIR_CONSULTAS, f"{marca}.json")
    C.escribir(ruta, json.dumps(dict(
        ts=marca, fase=fase, pregunta=pregunta, k=args.k, fuente=args.fuente, doc=args.doc,
        respuesta=respuesta, modelo=C.MODELO,
        fragmentos=[{k_: f.get(k_) for k_ in ("id", "doc", "pagina", "seccion", "tipo", "label",
                                              "bm25", "coseno", "rrf", "usado", "via_ref", "texto")} for f in frags],
    ), ensure_ascii=False, indent=1))
    print(f"\n[{sum(f['usado'] for f in frags)}/{len(frags)} fragmentos usados; "
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
    texto = (C.leer(os.path.join(C.DIR_LECTURAS, "PLANTILLA.md"))
             .replace("TITULO", titulo).replace("AUTORES", autores).replace("CITA", cita.strip())
             .replace("ESTADO", e.get("estado", "?")).replace("AAAA-MM-DD", HOY).replace("ID", id_))
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


def _nota_quiz(id_, k):
    from . import indice as I
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        return
    frags = _fragmentos_doc(id_, "main theorem hypotheses definitions lemma proof conditions on M", k)
    if not frags:
        return
    bloque = "\n\n".join(f"{I.cita(f)}\n{f['texto']}" for f in frags)
    try:
        r = M.llamar("nota-quiz", P.NOTA_QUIZ, [{"role": "user", "content": bloque}],
                     max_tokens=C.MAX_TOKENS_JSON)
    except M.MotorApagado as e:
        M.aviso(str(e))
        return
    ruta = os.path.join(C.DIR_LECTURAS, f"{id_}-quiz-{HOY}.md")
    C.escribir(ruta, f"# Quiz {id_} ({HOY})\n\nSin respuestas. Contesta por escrito antes de abrir el paper.\n\n{r}\n")
    print()
    M.imprimir(r)
    print(f"\n-> {os.path.relpath(ruta, C.RAIZ)}")


def _nota_check(id_, k):
    from . import indice as I
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO:
        M.aviso("MOTOR APAGADO: " + E.EXPLICACION.get(fase, ""))
        return
    ruta = _ruta_nota(id_)
    if not os.path.exists(ruta):
        print(f"no hay nota. Primero:  python doc.py nota new {id_}")
        return
    expl = _seccion_md(C.leer(ruta), "Mi explicacion")
    if len(expl) < 200 or expl.startswith("Tu reconstruccion"):
        print("la seccion '## Mi explicacion' de la nota esta vacia o es la plantilla. Escribela primero.")
        return
    frags = _fragmentos_doc(id_, expl[:2000], k)
    if not frags:
        return
    bloque = "\n\n".join(f"{I.cita(f)}\n{f['texto']}" for f in frags)
    contenido = f"SU EXPLICACION:\n{expl}\n\nFRAGMENTOS DEL PAPER:\n\n{bloque}"
    try:
        r = M.llamar("nota-check", P.NOTA_CHECK, [{"role": "user", "content": contenido}],
                     max_tokens=C.MAX_TOKENS_JSON)
    except M.MotorApagado as e:
        M.aviso(str(e))
        return
    salida = os.path.join(C.DIR_LECTURAS, f"{id_}-check-{HOY}.md")
    C.escribir(salida, f"# Check {id_} ({HOY})\n\n{r}\n")
    print()
    M.imprimir(r)
    n_obj = len(re.findall(r"^\s*\d+[.)]", r, re.M))
    _verificacion(f"explicacion propia de {id_} (lecturas/{id_}.md)", "check contra el texto",
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
    if args.accion == "new":
        _nota_new(args.id)
    elif args.accion == "quiz":
        _nota_quiz(args.id, args.k)
    elif args.accion == "check":
        _nota_check(args.id, args.k)


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
