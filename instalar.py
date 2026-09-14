#!/usr/bin/env python3
"""
Instalacion, una sola vez, desde la carpeta doctorado:

    python instalar.py

Igual en Windows, Mac y Linux. Solo Python y git.
"""
import os, sys, subprocess, shutil

RAIZ = os.path.dirname(os.path.abspath(__file__))


def paso(n, t):
    print(f"{n}/5  {t}")


def git(*a):
    return subprocess.run(["git", *a], cwd=RAIZ, capture_output=True, text=True)


def instalar(paquete):
    try:
        __import__(paquete)
        return "ya estaba"
    except ImportError:
        pass
    for extra in ([], ["--break-system-packages"], ["--user"]):
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *extra, paquete])
        if r.returncode == 0:
            return "instalado"
    return "FALLO: instala a mano con  python -m pip install " + paquete


paso(1, "dependencias")
for p in ("mpmath", "anthropic", "rich"):
    print(f"  {p:<10} {instalar(p)}")

paso(2, "quitar la marca de internet (solo Windows)")
if os.name == "nt":
    n = 0
    for base, _, fs in os.walk(RAIZ):
        if ".git" in base:
            continue
        for f in fs:
            try:
                os.remove(os.path.join(base, f) + ":Zone.Identifier")
                n += 1
            except OSError:
                pass
    print(f"  desbloqueados {n} ficheros")
else:
    print("  no aplica")

paso(3, "clave de la API")
env = os.path.join(RAIZ, ".env")
if not os.path.exists(env):
    shutil.copy(os.path.join(RAIZ, ".env.ejemplo"), env)
    print("  creado .env. ABRELO y pega tu clave donde dice pega-aqui-tu-clave.")
    print("  La clave se crea en https://platform.claude.com (API Keys). No la compartas ni la subas a git.")
else:
    tiene = any(l.startswith("ANTHROPIC_API_KEY=") and "pega-aqui" not in l
                for l in open(env, encoding="utf-8-sig"))
    print("  .env con clave" if tiene else "  .env existe pero FALTA la clave dentro")

paso(4, "git")
if not shutil.which("git"):
    sys.exit("  falta git: https://git-scm.com/download/win")
nuevo = git("rev-parse", "--git-dir").returncode != 0
if nuevo:
    git("init", "-q")
    git("config", "user.name", "Mariano San Jose")
    git("config", "user.email", "mariano.sanjose@feverup.com")
git("config", "core.autocrlf", "false")
git("config", "core.safecrlf", "false")
git("add", "-A")
git("commit", "-q", "-m", "inicio" if nuevo else "configuracion")
print("  repositorio creado" if nuevo else "  repositorio ya existente")

paso(5, "laboratorio")
subprocess.run([sys.executable, os.path.join(RAIZ, "lab", "pesos.py")])

print("""
Listo. Comprueba la conexion sin gastar apenas:
    python doc.py estado
    python doc.py preguntar        (escribe 'hola' y luego /salir)

Y cuando tengas 3 horas y tus directores hayan visto corpus/diagnostico.md:
    python doc.py diagnostico
""")
