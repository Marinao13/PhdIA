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


# ======================================================================
# sesion / sellar / ataque / estado
# ======================================================================

def cmd_sesion(args):
    etiqueta = "-".join(args.etiqueta)
    if E.sesion_hoy():
        print("ya hay sesion hoy:", os.path.relpath(E.sesion_hoy(), C.RAIZ))
        return
    destino = os.path.join(C.DIR_SESIONES, f"{HOY}-{etiqueta}.md")
    texto = C.leer(C.F_PLANTILLA).replace("AAAA-MM-DD", HOY).replace("ETIQUETA", etiqueta)
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
    M.aviso("MOTOR APAGADO. Fase 3, 45 min: extension, contraejemplo, caso Beurling.\n"
            "Al terminar:  python doc.py sellar 3")


def cmd_estado(args):
    fase, m = E.fase_actual()
    nombres = dict(libre="libre (sin sesion hoy)", f1="fase 1, motor OFF",
                   f2="fase 2, motor ON", f3="fase 3, motor OFF", f4="fase 4, motor ON")
    print(nombres[fase])
    for k in ("inicio", "sello1", "ataque", "sello3"):
        if m[k]:
            print(f"  {k:<8} {m[k].strftime('%H:%M')}")
    if m["inicio"] and m["sello1"]:
        print(f"  fase 1: {E.minutos(m['inicio'], m['sello1'])} min")
    if m["ataque"] and m["sello3"]:
        print(f"  fase 3: {E.minutos(m['ataque'], m['sello3'])} min")
    print(f"  modelo: {C.MODELO}" + ("  [SIMULACION]" if C.SIMULAR else ""))


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
  /pegar      pegar un fragmento del paper (varias lineas, termina con una linea con solo .)
  /nuevo      olvida la conversacion (nuevo fragmento, nuevo hilo)
  /salir
Sin plantilla la pregunta va tal cual, con las reglas de fase 2 igualmente."""


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
            linea = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not linea:
            continue
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

        contenido = plantilla + (f"FRAGMENTO DEL PAPER:\n{fragmento}\n\n" if fragmento else "") + linea
        historia.append({"role": "user", "content": contenido})
        try:
            respuesta = M.llamar("preguntar", P.FASE2, historia, forzar=args.forzar)
        except M.MotorApagado as e:
            M.aviso("MOTOR APAGADO: " + str(e))
            historia.pop()
            break
        historia.append({"role": "assistant", "content": respuesta})
        print()
        M.imprimir(respuesta)
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
    print("comparando tu fase 1 con el paper...")
    bruto = M.llamar("cierre", P.CIERRE,
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

    # calibracion
    try:
        r = M.parse_json(M.llamar("diagnostico", P.DIAGNOSTICO,
                                  [{"role": "user", "content": tabla}],
                                  max_tokens=C.MAX_TOKENS_DIAGNOSTICO))
    except (M.MotorApagado, ValueError) as e:
        print(e)
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
# metricas
# ======================================================================

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
# anki
# ======================================================================

def cmd_anki(args):
    import csv
    lineas = [l.strip() for l in C.leer(C.F_PENDIENTES).splitlines()
              if "::" in l and not l.startswith("#") and not l.startswith("<!--")
              and "`" not in l]
    if not lineas:
        print("nada pendiente")
        return
    salida = os.path.join(C.DIR_DRILL, f"anki-{HOY}.csv")
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        for l in lineas:
            p, _, r = l.partition("::")
            w.writerow([p.strip().lstrip("- "), r.strip()])
    C.anadir(os.path.join(C.DIR_DRILL, "exportadas.md"),
             f"\n## exportadas {HOY}\n" + "\n".join(lineas) + "\n")
    C.escribir(C.F_PENDIENTES, "# Pendientes\n\nUna tarjeta por linea con el separador de dos "
               "puntos dobles.\nLas generan cierre, lagunas y diagnostico. No fabriques tarjetas "
               "a mano.\n")
    print(f"{len(lineas)} tarjetas -> {os.path.relpath(salida, C.RAIZ)}")
    print("Anki: Archivo > Importar, separador punto y coma, mazo 'doctorado'.")
