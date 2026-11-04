"""
Mini web local del sistema de doctorado (docs/WEB.md).

    python -m web                  escucha en http://127.0.0.1:8765
    python web/servidor.py --port 9000

No tiene autenticacion propia: delante va Cloudflare Tunnel + Cloudflare Access. Todo lo
que hace pasa por las funciones de nucleo/ (la puerta del motor es nucleo.motor.llamar).
"""
