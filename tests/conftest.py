import os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (RAIZ, os.path.join(RAIZ, "lab")):
    if p not in sys.path:
        sys.path.insert(0, p)

# los tests no tocan la red ni la API
os.environ.setdefault("DOC_SIMULAR", "1")
