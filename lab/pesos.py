"""
Laboratorio de sucesiones peso.

Motor de REFUTACION, no de demostracion. Sirve para matar conjeturas falsas
en segundos. Que una desigualdad sobreviva aqui no es evidencia de que sea
cierta, solo de que no la has roto todavia.

Todo se guarda en escala logaritmica: M_p = (p!)^2 con p = 300 desborda
cualquier float. Internamente solo existe logM[p].

AVISO DE NORMALIZACION
----------------------
Las condiciones (mg), (dc) y (gamma_1) aparecen en la literatura con varias
normalizaciones equivalentes pero distintas en las constantes. Las de aqui
estan escritas en la forma que usa Thilliez (Results Math 44, 2003), pero
ANTES de usar una constante en un argumento escrito, abre el paper y verifica
la normalizacion. Ver ia/reglas.md.
"""

from mpmath import mp, mpf, log, e, inf, loggamma

mp.dps = 40


# ----------------------------------------------------------------------
# Objeto principal
# ----------------------------------------------------------------------

class SucesionPeso:
    """Sucesion peso M = (M_p), p = 0..N, normalizada con M_0 = 1."""

    def __init__(self, logM, nombre="M"):
        self.logM = [mpf(x) for x in logM]
        self.nombre = nombre
        self.N = len(logM) - 1
        if abs(self.logM[0]) > mpf("1e-30"):
            raise ValueError("normaliza con M_0 = 1 (logM[0] = 0)")

    @classmethod
    def desde_log(cls, log_f, N=400, nombre="M"):
        """log_f(p) devuelve log(M_p). La via recomendada."""
        return cls([log_f(p) for p in range(N + 1)], nombre)

    @classmethod
    def desde_cocientes(cls, log_m, N=400, nombre="M"):
        """log_m(p) devuelve log(m_p) con m_p = M_{p+1}/M_p."""
        acc, out = mpf(0), [mpf(0)]
        for p in range(N):
            acc += mpf(log_m(p))
            out.append(acc)
        return cls(out, nombre)

    # --- accesores -----------------------------------------------------

    def log_m(self, p):
        """log del cociente m_p = M_{p+1}/M_p."""
        return self.logM[p + 1] - self.logM[p]

    def m(self, p):
        return e ** self.log_m(p)

    def M(self, p):
        return e ** self.logM[p]

    # --- condiciones ---------------------------------------------------

    def es_log_convexa(self, tol=mpf("1e-25")):
        """(lc): m_p no decreciente. Devuelve (bool, primer p que falla)."""
        for p in range(self.N - 1):
            if self.log_m(p + 1) < self.log_m(p) - tol:
                return False, p
        return True, None

    def constante_mg(self):
        """
        (mg) crecimiento moderado: exists A con M_{p+q} <= A^{p+q} M_p M_q.
        Devuelve el sup empirico de (logM[p+q] - logM[p] - logM[q])/(p+q),
        exponenciado. Si crece con N, (mg) falla.
        """
        peor, arg = mpf("-inf"), None
        for p in range(self.N + 1):
            for q in range(p, self.N + 1 - p):
                if p + q == 0 or p + q > self.N:
                    continue
                v = (self.logM[p + q] - self.logM[p] - self.logM[q]) / (p + q)
                if v > peor:
                    peor, arg = v, (p, q)
        return e ** peor, arg

    def constante_dc(self):
        """(dc) cierre por derivacion: exists A con M_{p+1} <= A^{p+1} M_p."""
        peor, arg = mpf("-inf"), None
        for p in range(self.N):
            v = self.log_m(p) / (p + 1)
            if v > peor:
                peor, arg = v, p
        return e ** peor, arg

    def constante_gamma1(self, margen=40):
        """
        (gamma_1) no cuasianaliticidad fuerte, forma de Thilliez 2003:

            sum_{q>=p} M_q / ((q+1) M_{q+1})  <=  A * M_p / M_{p+1}

        Devuelve (A_empirica, p_peor, fiable). La cola se trunca en N, asi que
        'fiable' avisa si los ultimos terminos aun pesan: en ese caso sube N.
        Si A crece sin freno al subir N, (gamma_1) falla.
        """
        tope = self.N - margen
        if tope < 10:
            raise ValueError("N demasiado pequeno para estimar la cola")

        colas = [mpf(0)] * (self.N + 1)
        for q in range(self.N - 1, -1, -1):
            colas[q] = colas[q + 1] + e ** (-self.log_m(q)) / (q + 1)

        peor, arg = mpf("-inf"), None
        for p in range(tope):
            v = colas[p] * self.m(p)
            if v > peor:
                peor, arg = v, p

        resto = colas[tope]
        fiable = bool(resto < colas[0] / 1000) if colas[0] > 0 else True
        return peor, arg, fiable

    # --- funciones asociadas -------------------------------------------

    def omega(self, t):
        """omega_M(t) = sup_p ( p*log(t) - logM[p] ), para t > 0."""
        lt = log(mpf(t))
        return max(p * lt - self.logM[p] for p in range(self.N + 1))

    def log_h(self, t):
        """log de h_M(t) = inf_p M_p t^p."""
        lt = log(mpf(t))
        return min(self.logM[p] + p * lt for p in range(self.N + 1))


# ----------------------------------------------------------------------
# Catalogo
# ----------------------------------------------------------------------
# Sin etiquetas: el panel calcula que cumple cada una. No te fies de lo que
# creas recordar sobre estos ejemplos, ejecutalo.

def gevrey(alpha, N=400):
    """M_p = (p!)^alpha."""
    return SucesionPeso.desde_log(
        lambda p: mpf(alpha) * loggamma(p + 1), N, f"Gevrey({float(alpha):.3g})")


def gevrey_log(alpha, beta, N=400):
    """M_p = (p!)^alpha * (log(p+e))^(beta*p)."""
    return SucesionPeso.desde_log(
        lambda p: mpf(alpha) * loggamma(p + 1) + mpf(beta) * p * log(log(p + e)),
        N, f"Gevrey-log({float(alpha):.3g},{float(beta):.3g})")


def q_gevrey(q, N=400):
    """M_p = q^(p^2), con q > 1."""
    return SucesionPeso.desde_log(
        lambda p: mpf(p) ** 2 * log(mpf(q)), N, f"q-Gevrey({q})")


def cocientes_lentos(N=400):
    """m_p = log(p + e). Cocientes de crecimiento muy lento."""
    return SucesionPeso.desde_cocientes(
        lambda p: log(log(p + e)), N, "m_p = log(p+e)")


def cocientes_potencia(s, N=400):
    """m_p = (p+1)^s. Reparametrizacion util de Gevrey."""
    return SucesionPeso.desde_cocientes(
        lambda p: mpf(s) * log(p + 1), N, f"m_p=(p+1)^{float(s):.3g}")


CATALOGO = [gevrey(0), gevrey(mpf(1) / 2), gevrey(1), gevrey(2),
            gevrey_log(1, 1), q_gevrey(2), cocientes_lentos(),
            cocientes_potencia(mpf(1) / 3)]


# ----------------------------------------------------------------------
# Panel: la pantalla de evaluacion del motor
# ----------------------------------------------------------------------

def panel(*sucesiones, N_test=(150, 300)):
    """
    Diagnostico de cada sucesion en dos valores de N. Si una constante crece
    mucho de la columna izquierda a la derecha, la condicion FALLA y lo que
    ves es divergencia lenta, no una constante.
    """
    fila = "{:<22} {:>4} {:>12} {:>12} {:>12}"
    print(fila.format("sucesion", "N", "A_mg", "A_dc", "A_gamma1"))
    print("-" * 66)
    for S in sucesiones:
        for N in N_test:
            if N > S.N:
                continue
            T = SucesionPeso(S.logM[:N + 1], S.nombre)
            lc, _ = T.es_log_convexa()
            amg, _ = T.constante_mg()
            adc, _ = T.constante_dc()
            try:
                ag, _, fiable = T.constante_gamma1()
                sg = f"{float(ag):.3g}" + ("" if fiable else "?")
            except ValueError:
                sg = "n/d"
            nom = (T.nombre + ("" if lc else " [NO lc]"))[:22]
            print(fila.format(nom, N, f"{float(amg):.4g}",
                              f"{float(adc):.4g}", sg))
        print()


# ----------------------------------------------------------------------
# Motor de refutacion
# ----------------------------------------------------------------------

def refutar(predicado, barrido, nombre="conjetura", max_contra=5, verbose=True):
    """
    Busca contraejemplos de una conjetura.

    predicado(**kwargs) -> bool. Devuelve True si la conjetura SE CUMPLE
    en ese punto. barrido es un dict {nombre_param: iterable}.

    Ejemplo:
        refutar(lambda M, p, q: M.logM[p+q] <= M.logM[p] + M.logM[q] + (p+q)*log(3),
                {"M": [gevrey(1), q_gevrey(2)],
                 "p": range(1, 60), "q": range(1, 60)},
                nombre="mg con A=3")
    """
    import itertools
    claves = list(barrido)
    contras = []
    n = 0
    for combo in itertools.product(*(barrido[k] for k in claves)):
        kw = dict(zip(claves, combo))
        n += 1
        try:
            ok = predicado(**kw)
        except Exception as exc:
            contras.append((kw, f"error: {exc}"))
            if len(contras) >= max_contra:
                break
            continue
        if not ok:
            contras.append((kw, "falla"))
            if len(contras) >= max_contra:
                break

    if verbose:
        if contras:
            print(f"[REFUTADA] {nombre}  ({n} puntos probados)")
            for kw, motivo in contras:
                desc = {k: (v.nombre if isinstance(v, SucesionPeso) else v)
                        for k, v in kw.items()}
                print(f"   {motivo}: {desc}")
        else:
            print(f"[sobrevive] {nombre}  ({n} puntos probados) "
                  "-- no es evidencia de que sea cierta")
    return contras


def casi_creciente(valores, tol=mpf("1e-25")):
    """
    (a_p) es casi creciente si existe C con a_p <= C*a_q para todo p <= q.
    Devuelve la C empirica. Util para los indices de crecimiento.
    """
    peor, minimo_desde_la_derecha = mpf(0), mpf("inf")
    for a in reversed([mpf(v) for v in valores]):
        minimo_desde_la_derecha = min(minimo_desde_la_derecha, a)
        if minimo_desde_la_derecha > tol:
            peor = max(peor, a / minimo_desde_la_derecha)
    return peor


# TODO (primera sesion de laboratorio): implementar el indice gamma(M).
# NO lo implementes de memoria ni preguntandoselo a un LLM. Abre
# Thilliez 2003 y Jimenez-Garrido & Sanz, copia la definicion exacta, y
# usa casi_creciente() como primitiva. Anota en corpus/orden.md la pagina.


if __name__ == "__main__":
    panel(*CATALOGO)
