#!/usr/bin/env python3
"""
Unico punto de entrada del sistema. Toda llamada a la IA pasa por aqui.

  python doc.py diagnostico            primera toma de contacto (3 h, una vez)
  python doc.py sesion thilliez2003    abre la sesion de hoy, motor OFF
  python doc.py sellar 1               sella el intento a ciegas, motor ON
  python doc.py preguntar              REPL de fase 2
  python doc.py ataque                 empieza la fase 3, motor OFF
  python doc.py sellar 3               sella el ataque, motor ON
  python doc.py cierre                 fase 4: diff, errores, tarjetas, lagunas
  python doc.py lagunas                viernes: lote de huecos de grado/master
  python doc.py lab "especificacion"   la IA escribe el script, mpmath juzga
  python doc.py metricas               los numeros, sin autodeclaracion
  python doc.py anki                   exporta tarjetas nuevas
  python doc.py estado                 en que fase estas
"""
import sys, argparse

try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

from nucleo import comandos as K


def main():
    ap = argparse.ArgumentParser(prog="doc.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("sesion", help="abre la sesion de hoy")
    s.add_argument("etiqueta", nargs="+")
    s.set_defaults(fn=K.cmd_sesion)

    s = sub.add_parser("sellar", help="sella la fase 1 o la 3")
    s.add_argument("fase", type=int, choices=[1, 3])
    s.set_defaults(fn=K.cmd_sellar)

    sub.add_parser("ataque", help="empieza la fase 3").set_defaults(fn=K.cmd_ataque)
    sub.add_parser("estado", help="fase actual").set_defaults(fn=K.cmd_estado)

    s = sub.add_parser("preguntar", help="REPL de fase 2")
    s.add_argument("--forzar", action="store_true", help="saltar la puerta (queda registrado)")
    s.set_defaults(fn=K.cmd_preguntar)

    sub.add_parser("cierre", help="fase 4").set_defaults(fn=K.cmd_cierre)

    s = sub.add_parser("lagunas", help="lote semanal")
    s.add_argument("--max", type=int, default=0, help="maximo de lagunas a resolver")
    s.set_defaults(fn=K.cmd_lagunas)

    s = sub.add_parser("lab", help="la IA escribe un script de laboratorio")
    s.add_argument("especificacion", nargs="*")
    s.add_argument("--forzar", action="store_true")
    s.set_defaults(fn=K.cmd_lab)

    s = sub.add_parser("diagnostico", help="primera toma de contacto")
    s.add_argument("--repetir", action="store_true")
    s.set_defaults(fn=K.cmd_diagnostico)

    sub.add_parser("metricas", help="los numeros").set_defaults(fn=K.cmd_metricas)
    sub.add_parser("anki", help="exporta tarjetas").set_defaults(fn=K.cmd_anki)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
