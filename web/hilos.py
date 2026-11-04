"""
Hilos de /preguntar: en memoria del proceso, uno por pestaña del navegador (se pierden al
reiniciar el servidor; cada turno queda igualmente en registro/consultas/ como en la consola).

Cada turno se construye EXACTAMENTE como el REPL de nucleo.comandos.cmd_preguntar, con sus
mismas funciones: _doc_de_sesion, indice.localizar, _recuperar, _bloque_corpus, _mensajes,
motor.llamar (la puerta de las fases) y _registrar_conversacion.
"""
import os, re, uuid, threading, datetime

from nucleo import comandos as K
from nucleo import estado as E
from nucleo import motor as M
from nucleo import prompts as P
from nucleo import indice as I

MAX_HILOS = 40
PLANTILLAS = {"notacion": "P_NOTACION", "lema": "P_LEMA", "paso": "P_PASO"}   # como _CMD_PLANTILLA del REPL
DESARROLLA = "Desarrolla este fragmento paso a paso, con todos los pasos intermedios (regla FUENTES)."

_hilos, _cerrojo = {}, threading.Lock()


def _ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def nuevo(doc=None):
    with _cerrojo:
        if len(_hilos) >= MAX_HILOS:
            viejo = min(_hilos.values(), key=lambda h: h["ultimo"])
            del _hilos[viejo["id"]]
        h = dict(id=uuid.uuid4().hex[:12], doc=doc, turnos=[], vista=[], avisos=[],
                 ultima_cortada=False, ultima_sigue=False, creado=_ahora(), ultimo=_ahora())
        _hilos[h["id"]] = h
    return h


def obtener(hid):
    return _hilos.get((hid or "").strip())


def o_nuevo(hid):
    """El hilo pedido, o uno nuevo con el paper de la sesion (como al abrir el REPL)."""
    h = obtener(hid)
    if h:
        return h
    h = nuevo(K._doc_de_sesion())
    if hid:
        h["avisos"].append("ese hilo ya no existe (el servidor se reinicio): hilo nuevo")
    return h


def fijar_doc(h, doc):
    """Como /doc ID en el REPL: solo un id con fragmentos en el indice. Vacio = sin corpus."""
    doc = (doc or "").strip()
    if doc == (h["doc"] or ""):
        return
    if not doc:
        h["doc"] = None
        h["avisos"].append("sin paper del corpus: el modelo solo vera lo que pegues")
        return
    try:
        hay = bool(I._cargar(doc=doc))
    except Exception:
        hay = False
    if hay:
        h["doc"] = doc
        h["avisos"].append(f"corpus fijado: {doc}")
    else:
        h["avisos"].append("ese id no esta en el indice (mira corpus/meta/bib.yaml, o python doc.py indexar)")


def fragmentos_en_indice(doc):
    if not doc:
        return 0
    try:
        return len(I._cargar(doc=doc))
    except Exception:
        return 0


def turno(h, pregunta, fragmento="", plantilla="", sigue=False):
    """Un turno. True si hubo respuesta (queda en h['vista']); si no, el motivo en h['avisos']."""
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO:
        h["avisos"].append("MOTOR APAGADO: " + E.EXPLICACION.get(fase, "motor apagado"))
        return False
    doc, turnos = h["doc"], h["turnos"]
    fragmento = (fragmento or "").replace("\r\n", "\n").strip()
    linea = (pregunta or "").strip()
    plantilla_txt = getattr(P, PLANTILLAS[plantilla]) if plantilla in PLANTILLAS else ""

    localizados, donde = [], None
    if fragmento and doc:                                  # como _localizar_pegado, sin print
        try:
            loc = I.localizar(doc, fragmento)
        except Exception as e:
            loc, donde = None, f"indice no disponible ({type(e).__name__}): se envia tal cual"
        if loc:
            localizados = loc["fragmentos"]
            donde = (f"localizado en el corpus (cobertura {loc['cobertura']}): "
                     + "; ".join(I.cita(f) for f in localizados))
        elif donde is None:
            donde = f"no localizado en {doc}: se envia tal cual, sin cita del corpus"

    if sigue:
        if not (h["ultima_cortada"] or h["ultima_sigue"]):
            h["avisos"].append("la ultima respuesta no quedo cortada ni termino en SIGUE:")
            return False
        linea = ("Continua exactamente desde la linea SIGUE:, sin repetir lo anterior." if h["ultima_sigue"]
                 else "Continua exactamente donde te cortaste, sin repetir lo anterior.")
        fragmento, plantilla_txt, localizados = "", "", []
    elif not linea:
        if not fragmento and not localizados:
            h["avisos"].append("escribe una pregunta, o pega un fragmento y deja la pregunta vacia "
                               "para que lo desarrolle paso a paso")
            return False
        linea = DESARROLLA

    if sigue and len(turnos) >= 2:                         # la continuacion reutiliza los fragmentos del turno cortado
        frags_turno, bloque = turnos[-2].get("frags", []), turnos[-2].get("bloque", "")
    else:
        frags_turno = K._recuperar(doc, linea, fragmento, localizados)
        bloque = K._bloque_corpus(frags_turno)
    contenido = plantilla_txt + (f"FRAGMENTO PEGADO (texto del PDF):\n{fragmento}\n\n" if fragmento else "") + linea
    turnos.append(dict(role="user", content=contenido, bloque=bloque, frags=frags_turno))
    try:
        respuesta = M.llamar("preguntar", K._sistema(P.FASE2), K._mensajes(turnos))
    except M.MotorApagado as e:
        turnos.pop()
        h["avisos"].append("MOTOR APAGADO: " + str(e))
        return False
    except (Exception, SystemExit) as e:                   # red, clave, paquete: la pregunta no entra al hilo
        turnos.pop()
        h["avisos"].append(f"la llamada fallo ({type(e).__name__}: {str(e)[:200]}); el hilo sigue como estaba")
        return False
    turnos.append(dict(role="assistant", content=respuesta))
    u = dict(M.ULTIMA)
    citas = [I.cita(f) for f in frags_turno]
    h["ultima_cortada"] = bool(u.get("cortada"))
    h["ultima_sigue"] = bool(re.search(r"^SIGUE:", respuesta, re.M))
    # el registro va ANTES de mostrar: una respuesta pagada no se pierde por un fallo de render
    K._registrar_conversacion(fase, linea, respuesta, plantilla_txt, fragmento, citas, len(turnos) // 2, u)
    h["vista"].append(dict(n=len(turnos) // 2, pregunta=linea, fragmento=fragmento, plantilla=plantilla,
                           donde=donde, respuesta=respuesta, citas=list(dict.fromkeys(citas)), u=u,
                           cortada=h["ultima_cortada"], sigue=h["ultima_sigue"], n_frags=len(frags_turno),
                           ts=_ahora()))
    h["ultimo"] = _ahora()
    return True


def origen_sesion(defecto):
    """Etiqueta de la sesion abierta (como /laguna en el REPL), o `defecto`."""
    ruta = E.sesion_hoy()
    return os.path.basename(ruta)[11:-3] if ruta else defecto
