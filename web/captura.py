"""
Ejecutar un cmd_* de nucleo.comandos desde la web y quedarse con lo que imprime.

Los comandos escriben por print() y por nucleo.motor.imprimir / nucleo.motor.aviso. Con rich
instalado, motor.imprimir reformatea la respuesta (markdown a 80 columnas), asi que aqui se
interceptan esas dos funciones durante la llamada: la respuesta cruda queda en `cuerpos`, los
avisos en `avisos`, y el resto del stdout en `texto`. stdout es global al proceso: un cerrojo
serializa las capturas.
"""
import io, contextlib, threading

from nucleo import motor as M

_cerrojo = threading.Lock()


class Salida:
    def __init__(self):
        self.texto = ""        # lo que fue a stdout
        self.cuerpos = []      # textos pasados a motor.imprimir (respuestas crudas del modelo)
        self.avisos = []       # textos pasados a motor.aviso
        self.error = None      # excepcion capturada por ejecutar(), si la hubo


@contextlib.contextmanager
def capturar():
    s = Salida()
    buf = io.StringIO()
    imprimir0, aviso0 = M.imprimir, M.aviso

    def imprimir(texto, md=True, consola=False, ancho=90):
        s.cuerpos.append(texto)

    def aviso(texto):
        s.avisos.append(str(texto))

    with _cerrojo:
        M.imprimir, M.aviso = imprimir, aviso
        try:
            with contextlib.redirect_stdout(buf):
                yield s
        finally:
            M.imprimir, M.aviso = imprimir0, aviso0
            s.texto = buf.getvalue()


def ejecutar(fn, args):
    """fn(args) capturado. Ninguna excepcion sale: queda en s.error y como aviso."""
    with capturar() as s:
        try:
            fn(args)
        except M.MotorApagado as e:
            s.error = e
            s.avisos.append("MOTOR APAGADO: " + str(e))
        except (Exception, SystemExit) as e:          # sys.exit por un paquete que falta, red...
            s.error = e
            s.avisos.append(f"error en {getattr(fn, '__name__', 'comando')}: {type(e).__name__}: {str(e)[:300]}")
    return s
