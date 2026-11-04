"""python -m web [--host 127.0.0.1] [--port 8765]"""
import os, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from web.servidor import main

if __name__ == "__main__":
    main()
