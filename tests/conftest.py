import os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (RAIZ, os.path.join(RAIZ, "lab")):
    if p not in sys.path:
        sys.path.insert(0, p)

# los tests no tocan la red ni la API
os.environ.setdefault("DOC_SIMULAR", "1")


# Guarda: ningun test escribe en lo que es de Mariano ni en los registros o datos reales. El
# 2026-11-11 un test de `ataque` dejaba una linea "Ataque:" en la sesion abierta de verdad.
import hashlib
import pytest

_VIGILADO = ("sesiones", "lecturas", "contexto", "registro", "reuniones", "transcripciones", "produccion",
             "drill", "indice", os.path.join("corpus", "meta"),
             os.path.join("corpus", "orden.md"), os.path.join("corpus", "base.md"),
             os.path.join("corpus", "diagnostico.md"), os.path.join("corpus", "PROYECTO.md"))
_GRANDE = 4 * 1024 * 1024


def _huella(f):
    """Contenido si es pequeno; tamano y fecha si no (el indice, un PDF original)."""
    s = os.stat(f)
    if s.st_size > _GRANDE:
        return (s.st_size, s.st_mtime_ns)
    with open(f, "rb") as h:
        return hashlib.sha1(h.read()).hexdigest()


def _huellas():
    out = {}
    for rel in _VIGILADO:
        ruta = os.path.join(RAIZ, rel)
        if os.path.isfile(ruta):
            out[rel] = _huella(ruta)
        for carpeta, _, ficheros in os.walk(ruta):     # os.walk ve tambien los ficheros con punto
            for nombre in ficheros:
                f = os.path.join(carpeta, nombre)
                try:
                    out[os.path.relpath(f, RAIZ)] = _huella(f)
                except OSError:
                    pass
    return out


_ANTES = _huellas()          # al importar conftest: antes de recoger los tests y de importar sus modulos


@pytest.fixture(scope="session", autouse=True)
def _arbol_intacto():
    yield
    despues = _huellas()
    tocados = sorted(k for k in set(_ANTES) | set(despues) if _ANTES.get(k) != despues.get(k))
    assert not tocados, ("los tests han escrito en el arbol real (aisla con tmp_path / monkeypatch), o lo has "
                         "editado tu durante la pasada: " + ", ".join(tocados))
