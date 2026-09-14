"""
El unico camino hacia la IA. Todo pasa por llamar(), que:
  1. comprueba la fase y se niega si el motor debe estar apagado,
  2. registra cada llamada en registro/llamadas.jsonl con hora y tokens,
  3. devuelve el texto.

Con DOC_SIMULAR=1 no toca la red: devuelve respuestas fijas para probar el
flujo sin gastar.
"""
import json, datetime, re, sys
from . import config as C
from . import estado as E

try:
    from rich.console import Console
    from rich.markdown import Markdown
    _con = Console()
except ImportError:            # rich es opcional
    _con = None


class MotorApagado(Exception):
    pass


# ----------------------------------------------------------------------
# salida
# ----------------------------------------------------------------------

def imprimir(texto, md=True):
    if _con and md:
        _con.print(Markdown(texto))
    else:
        print(texto)


def aviso(texto):
    if _con:
        _con.print(f"[bold yellow]{texto}[/bold yellow]")
    else:
        print(texto)


# ----------------------------------------------------------------------
# cliente
# ----------------------------------------------------------------------

_cliente = None


def _completar(system, messages, max_tokens):
    """Llamada cruda. Devuelve (texto, tokens_in, tokens_out)."""
    if C.SIMULAR:
        return _simulado(system, messages), 0, 0
    if C.PROVEEDOR == "openai":
        return _completar_openai(system, messages, max_tokens)
    return _completar_anthropic(system, messages, max_tokens)


def _completar_anthropic(system, messages, max_tokens):
    global _cliente
    if _cliente is None:
        try:
            from anthropic import Anthropic
        except ImportError:
            sys.exit("falta el paquete anthropic:  python -m pip install anthropic")
        _cliente = Anthropic()          # lee ANTHROPIC_API_KEY del entorno o del .env
    r = _cliente.messages.create(model=C.MODELO, max_tokens=max_tokens,
                                 system=system, messages=messages)
    texto = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    return texto, r.usage.input_tokens, r.usage.output_tokens


def _completar_openai(system, messages, max_tokens):
    global _cliente
    if _cliente is None:
        try:
            from openai import OpenAI
        except ImportError:
            sys.exit("falta el paquete openai:  python -m pip install openai")
        _cliente = OpenAI()             # lee OPENAI_API_KEY del entorno o del .env
    # Responses API: el system prompt va en instructions, el historial en input.
    r = _cliente.responses.create(model=C.MODELO, instructions=system,
                                  input=messages, max_output_tokens=max_tokens)
    u = getattr(r, "usage", None)
    return (r.output_text,
            getattr(u, "input_tokens", 0) or 0,
            getattr(u, "output_tokens", 0) or 0)


def contexto_vivo():
    """contexto/estado.md + contexto/directores.md, para pegar al system prompt."""
    estado = C.leer(C.F_ESTADO).strip()
    directores = C.leer(C.F_DIRECTORES).strip()
    if not estado and not directores:
        return ""
    bloque = ("\n\nCONTEXTO VIVO\n"
              "Lo siguiente lo mantiene el propio Mariano y MANDA sobre cualquier cosa que "
              "tu creas saber, incluidos los libros. Si te pide algo que contradiga una "
              "instruccion de sus directores, senalalo antes de responder. Las lineas "
              "marcadas (J), (A) o (ambos) son palabras de sus directores.\n")
    if estado:
        bloque += f"\n--- contexto/estado.md ---\n{estado}\n"
    if directores:
        bloque += f"\n--- contexto/directores.md ---\n{directores}\n"
    if len(bloque) > C.LIMITE_CONTEXTO:
        aviso(f"contexto vivo con {len(bloque)} caracteres: condensa contexto/*.md")
    return bloque


def llamar(comando, system, messages, max_tokens=C.MAX_TOKENS_CHAT, forzar=False):
    """Puerta + log + llamada. El contexto vivo se anade al system en toda llamada."""
    fase, _ = E.fase_actual()
    if fase not in E.MOTOR_PERMITIDO and not forzar:
        raise MotorApagado(E.EXPLICACION.get(fase, "motor apagado"))

    texto, tin, tout = _completar(system + contexto_vivo(), messages, max_tokens)

    C.anadir(C.F_LLAMADAS, json.dumps({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "comando": comando, "fase": fase, "proveedor": C.PROVEEDOR, "modelo": C.MODELO,
        "tokens_in": tin, "tokens_out": tout,
        "forzado": bool(forzar and fase not in E.MOTOR_PERMITIDO),
        "simulado": C.SIMULAR,
    }, ensure_ascii=False) + "\n")
    return texto


def llamadas():
    """Lista de dicts del log."""
    out = []
    for l in C.leer(C.F_LLAMADAS).splitlines():
        l = l.strip()
        if l:
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                pass
    return out


# ----------------------------------------------------------------------
# json
# ----------------------------------------------------------------------

def parse_json(texto):
    """Tolera vallas ``` y texto alrededor. Lanza ValueError si no hay JSON."""
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip(), flags=re.M)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        return json.loads(t[i:j + 1])
    raise ValueError("la respuesta no contenia JSON:\n" + texto[:400])


# ----------------------------------------------------------------------
# simulacion
# ----------------------------------------------------------------------

def _simulado(system, messages):
    ultimo = messages[-1]["content"] if messages else ""
    if "MODO_CIERRE" in system:
        return json.dumps({
            "diff_estructural": "Simulacion: acertaste la tecnica general, fallaste el factor (q+1).",
            "coincidencia_propuesta": 1,
            "errores": [{"cod": "M", "contexto": "sim", "creia": "sum 1/m_q",
                         "es": "factor (q+1) en el denominador", "posicion": "sec. 1"}],
            "tarjetas": [{"p": "Forma de (gamma_1) en Thilliez 2003",
                          "r": "sum_{q>=p} M_q/((q+1)M_{q+1}) <= A M_p/M_{p+1}"}],
            "lagunas": ["Phragmen-Lindelof en sectores: hipotesis de crecimiento"],
            "conjeturas": []}, ensure_ascii=False)
    if "MODO_LAGUNA" in system:
        return json.dumps({
            "enunciado": "Simulacion de enunciado minimo.",
            "referencia": "Libro X, cap. 3, sec. 2",
            "intuicion": "Una linea de intuicion.",
            "trampa": "El error tipico.",
            "tarjetas": [{"p": "pregunta sim 1", "r": "respuesta 1"},
                         {"p": "pregunta sim 2", "r": "respuesta 2"}],
            "ejercicio": "Ejercicio de 5 minutos sin solucion."}, ensure_ascii=False)
    if "MODO_DIAGNOSTICO" in system:
        return json.dumps({
            "resumen": "Simulacion: base de grado solida, sumabilidad floja.",
            "tarjetas": [{"p": "Que es k-sumable en direccion d", "r": "..."}],
            "lagunas": ["Transformada de Borel formal: definicion exacta"],
            "orden_corpus": "Adelantar Balser antes de Thilliez 2010.",
            "preread_directores": "Borrador de pre-read en primera persona."},
            ensure_ascii=False)
    if "MODO_DESTILAR" in system:
        return json.dumps({
            "directores": [{"seccion": "Lecturas: que si, que no, en que orden",
                            "linea": "(J) Balser LNM 1582 solo los capitulos 1-4; el resto no hace falta ahora"},
                           {"seccion": "Notacion y convenciones del grupo",
                            "linea": "(ambos) escribimos (gamma_1) en la forma de Thilliez 2003, no en la de Komatsu"}],
            "estado": ["Problema de arranque: caso Beurling del teorema de Thilliez 2010, horizonte 9 meses"],
            "dudas": ["No quedo claro si hay que leer Rainer-Schindl antes del verano (?)"]},
            ensure_ascii=False)
    if "MODO_PREPARAR" in system:
        return "# Pre-read simulado\n\nDonde estoy, que he hecho, que pregunto.\n"
    if "MODO_LAB" in system:
        return "# codigo simulado\nprint('ok')\n"
    return f"[SIMULADO] Recibido: {ultimo[:120]}"
