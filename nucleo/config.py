"""Rutas, modelo y carga del .env. Nada mas."""
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cargar_env():
    """Lee RAIZ/.env con formato CLAVE=valor. Sin dependencias."""
    ruta = os.path.join(RAIZ, ".env")
    if not os.path.exists(ruta):
        return
    for linea in open(ruta, encoding="utf-8-sig"):
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, _, v = linea.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_cargar_env()

MODELO = os.environ.get("DOC_MODELO", "claude-sonnet-5")
SIMULAR = os.environ.get("DOC_SIMULAR", "") not in ("", "0", "false")

MAX_TOKENS_CHAT = 1500
MAX_TOKENS_JSON = 4000
MAX_TOKENS_DIAGNOSTICO = 6000

DIR_SESIONES = os.path.join(RAIZ, "sesiones")
DIR_REGISTRO = os.path.join(RAIZ, "registro")
DIR_DRILL = os.path.join(RAIZ, "drill")
DIR_LAB = os.path.join(RAIZ, "lab")
DIR_CORPUS = os.path.join(RAIZ, "corpus")
DIR_NOTAS = os.path.join(RAIZ, "produccion", "notas")

F_PLANTILLA = os.path.join(DIR_SESIONES, "PLANTILLA.md")
F_ERRORES = os.path.join(DIR_REGISTRO, "errores.md")
F_LAGUNAS = os.path.join(DIR_REGISTRO, "lagunas.md")
F_CONJETURAS = os.path.join(DIR_REGISTRO, "conjeturas.md")
F_LLAMADAS = os.path.join(DIR_REGISTRO, "llamadas.jsonl")
F_PENDIENTES = os.path.join(DIR_DRILL, "pendientes.md")
F_DIAGNOSTICO = os.path.join(DIR_CORPUS, "diagnostico.md")
F_ORDEN = os.path.join(DIR_CORPUS, "orden.md")
F_PESOS = os.path.join(DIR_LAB, "pesos.py")


def leer(ruta, defecto=""):
    if not os.path.exists(ruta):
        return defecto
    return open(ruta, encoding="utf-8-sig").read()


def escribir(ruta, texto):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


def anadir(ruta, texto):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "a", encoding="utf-8", newline="\n") as f:
        f.write(texto)
