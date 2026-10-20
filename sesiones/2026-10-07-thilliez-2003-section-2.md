---
fecha: 2026-10-07
paper: thilliez-2003-section-2
objetivo:
min_f1: 195.1
min_f3: 29.7
coincidencia_estructural: 2
llamadas_f2: 0
conjeturas: 0
---

# Sesion 2026-10-07  thilliez-2003-section-2

Las cinco lineas de metricas de arriba las rellena `doc.py cierre`. No las toques.

## Fase 0 - Carga en frio (10 min, MOTOR APAGADO)
Conozco varias propiedades sobre las sucesiones, que es una sucesion fuertemente regular, como afecta eso a su sucesión de cocientes y a otras relacionadas, que es una clase de Denjoy-Carleman y el marco general de trabajo.


## Fase 1 - Intento a ciegas (25 min, MOTOR APAGADO)
He leido los enunciados de la sección 2.1, lemas y pruebas 2.1.1, 2.1.2 y 2.1.3. La parte dura está para mi en probar cotas suficientemente buenas y en saber como se construyen las funciones exteriores en otros contextos. Después, mayormente es manejo de desigualdades y echar las cuentas.

>>> python doc.py sellar 1 <<<


## Fase 2 - Lectura asistida (60 min, python doc.py preguntar)
Lagunas de grado/master detectadas (una linea cada una, NO paro a resolverlas):
-

Notas:


## Fase 3 - Ataque (45 min, python doc.py ataque -> MOTOR APAGADO)
Modo: comprensión.

Reconstrucción del Lema 2.1.2 con el PDF cerrado:
Dado que gamma(M)>1, podemos tomar gamma tal que gamma(M)>gamma>1. Así, como gamma(M) es el supremo de los números para los que se cumple P_gamma, entonces existe a mayor que 0 tal que (m'_0/a)^j j!^gamma es más pequeño o igual que M_j para todo j natural. Teniendo en cuenta que a_1^j |t|^j j!^gamma = (j!/(a_1|t|)^(-j/gamma))^gamma con a_1 = m'_0/a, y que, e^x = sum_k=0^infinito x^k/k! es mayor que un término x^j/j!, entonces a_1^j|t|^j j!^gamma es mayor o igual que e^(-gamma a_1^(-1/gamma)|t|^(-1/gamma)). Así, si multiplicamos la desigualdad sobre la sucesión M y el factorial por |t|^j y tomamos ínfimos en j, tenemos que h_M(|t|) >= exp(-gamma a_1^(-1/gamma) |t|^(-1/gamma)). Por tanto, tomando logaritmos, Log h_N(|t|) >= -b_4|t|^(-1/gamma) con b_4 = gamma a_1^(-1/gamma) y lo mismo pasa si dividimos por 1+t^2 que se mantiene siempre mayor que 1. Estudiando la integral entre menos infinito e infinito del segundo sumando, tenemos que, entre 0 y 1 vale 1-1/gamma; entre 1 e infinito vale 1/gamma+1 y entre menos infinito y 0 es por simetría, finita al igual que entre 0 e infinito. Por tanto, es una integral finita en todo R y se tiene lo que buscábamos. 

Conjeturas / preguntas para los directores, una por línea:

>>> python doc.py sellar 3 <<<


## Fase 4 - Cierre (python doc.py cierre)
Lo hace el programa: diff de la fase 1 contra el paper, errores tipificados,
5 tarjetas, lagunas movidas, conjeturas registradas, metricas.

