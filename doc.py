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
  python doc.py reunion                notas de la reunion de hoy con directores
  python doc.py reunion --destilar     de las notas crudas a contexto/directores.md
  python doc.py reunion --preparar     pre-read para la proxima reunion
  python doc.py metricas               los numeros, sin autodeclaracion
  python doc.py anki                   exporta tarjetas nuevas
  python doc.py estado                 en que fase estas
  python doc.py ingest [pdf...]        ingiere PDFs al corpus (tex de arXiv / Marker / PyMuPDF)
  python doc.py indexar                fragmenta y embebe lo ingerido (incremental)
  python doc.py buscar "..."           fragmentos con [id:pagina], sin modelo, en cualquier fase
  python doc.py ask "..."              sintesis con citas [id:pagina] sobre esos fragmentos; motor ON
  python doc.py nota new ID            nota de lectura por paper (la escribes tu)
  python doc.py nota quiz ID           preguntas de examen sobre el paper, sin respuestas
  python doc.py nota check ID          agujeros en tu explicacion, citando el texto
  python doc.py referee ARCHIVO        objeciones numeradas con gravedad; sin valoracion global
  python doc.py redactar ARCHIVO       pule forma sin inventar; marca [VERIFICAR]
  python doc.py ahora                  que te toca ahora, y el comando exacto
"""
import sys, argparse

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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

    s = sub.add_parser("ahora", help="que te toca ahora mismo")
    s.add_argument("--breve", action="store_true", help="sin la chuleta de comandos")
    s.set_defaults(fn=K.cmd_ahora)

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
    s.add_argument("--calibrar", action="store_true",
                   help="solo la calibracion con IA, sobre el diagnostico ya sellado")
    s.set_defaults(fn=K.cmd_diagnostico)

    s = sub.add_parser("reunion", help="notas de reunion con directores")
    s.add_argument("--destilar", action="store_true", help="propone lineas para contexto/directores.md")
    s.add_argument("--preparar", action="store_true", help="redacta el pre-read de la proxima reunion")
    s.set_defaults(fn=K.cmd_reunion)

    s = sub.add_parser("ingest", help="ingiere PDFs al corpus: tex de arXiv, Marker o PyMuPDF")
    s.add_argument("pdf", nargs="*", help="rutas; vacio = todos los de corpus/raw aun no ingeridos")
    s.add_argument("--id", help="id del paper (por defecto, el nombre del fichero)")
    s.add_argument("--capa", choices=["tex", "marker", "pymupdf"], help="forzar una capa")
    s.add_argument("--rehacer", action="store_true")
    s.add_argument("--sin-red", dest="sin_red", action="store_true", help="sin arXiv ni Crossref")
    s.set_defaults(fn=K.cmd_ingest)

    s = sub.add_parser("indexar", help="fragmenta y embebe el corpus (incremental)")
    s.add_argument("--rehacer", action="store_true")
    s.set_defaults(fn=K.cmd_indexar)

    s = sub.add_parser("buscar", help="recuperacion pura, sin modelo, en todas las fases")
    s.add_argument("pregunta", nargs="*")
    s.add_argument("-k", type=int, default=8)
    s.add_argument("--fuente", choices=["paper", "proyecto", "nota"])
    s.add_argument("--doc", help="limitar a un id de bib.yaml")
    s.add_argument("--bm25", action="store_true", help="sin embeddings")
    s.add_argument("--por-doc", dest="por_doc", type=int, default=2, help="maximo por documento (0 = sin tope)")
    s.set_defaults(fn=K.cmd_buscar)

    s = sub.add_parser("ask", help="sintesis con modelo sobre el corpus, con citas; respeta las fases")
    s.add_argument("pregunta", nargs="*")
    s.add_argument("-k", type=int, default=8)
    s.add_argument("--fuente", choices=["paper", "proyecto", "nota"])
    s.add_argument("--doc", help="limitar a un id de bib.yaml")
    s.add_argument("--por-doc", dest="por_doc", type=int, default=2)
    s.add_argument("--forzar", action="store_true", help="saltar la puerta (queda registrado)")
    s.set_defaults(fn=K.cmd_ask)

    s = sub.add_parser("nota", help="nota de lectura por paper: new | quiz | check")
    s.add_argument("accion", choices=["new", "quiz", "check"])
    s.add_argument("id", help="id de bib.yaml, p. ej. thilliez-2003")
    s.add_argument("-k", type=int, default=12, help="fragmentos del paper que ve el modelo")
    s.set_defaults(fn=K.cmd_nota)

    s = sub.add_parser("referee", help="referee hostil: encuentra el error. Contexto limpio")
    s.add_argument("archivo")
    s.add_argument("--seccion", help="solo esa seccion ## del markdown, p. ej. \"Fase 3\"")
    s.add_argument("--proveedor", choices=["anthropic", "openai"], help="juzgar con el otro modelo")
    s.add_argument("--contexto", action="store_true", help="pegar fragmentos del corpus para contrastar citas")
    s.set_defaults(fn=K.cmd_referee)

    s = sub.add_parser("redactar", help="pulir forma sin inventar: marca [VERIFICAR]")
    s.add_argument("archivo")
    s.add_argument("--seccion")
    s.set_defaults(fn=K.cmd_redactar)

    sub.add_parser("metricas", help="los numeros").set_defaults(fn=K.cmd_metricas)
    sub.add_parser("anki", help="exporta tarjetas").set_defaults(fn=K.cmd_anki)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
