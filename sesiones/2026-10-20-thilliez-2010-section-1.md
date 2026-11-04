---
fecha: 2026-10-20
paper: thilliez-2010-section-1
objetivo:
min_f1: 15.5
min_f3: 16.8
coincidencia_estructural: 2
llamadas_f2: 0
conjeturas: 0
---

# Sesion 2026-10-20  thilliez-2010-section-1

Las cinco lineas de metricas de arriba las rellena `doc.py cierre`. No las toques.

## Fase 0 - Carga en frio (10 min, MOTOR APAGADO)
He leído el paper de thilliez 2003, ya sé como construir funciones planas o que existen y cuando la aplicación de Borel es sobreyectiva. Aquí espero encontrar métodos o condiciones para resolver ecuaciones de tipo algebraico o diferenciales o similar. Es decir, dar soluciones a ecuaciones mediante funciones ultraholomorfas o cuasianalíticas de manera que la solución resulte también ultraholomorfa o cuasianalítica. El objetivo es leer la sección 1 donde imagino se harán los resultados técnicos necesarios para la sección 2 donde se darán los resultados.


## Fase 1 - Intento a ciegas (25 min, MOTOR APAGADO)
De la primera parte, la relativa a las propiedades de las sucesiones, no veo nada especialmente raro, desconocido o complicado. Lo único que me mosquea y me parece un pelín difícil es probar que: dada la condición de derivabilidad se tiene que para todo mu>0 existe C dependiendo de mu constante positiva, tal que t^-muh_M(t) <= c(mu)h_M(t) para todo t>0. Me falta un poco de contexto sobre los desarrollos asintóticos. Tampoco entiendo que significa que algo sea "henselian" o un anillo de valuación discreta. No tengo claro tampoco lo que esel teorema de Puiseux. El teorema 2, el primero de los que incluyen demostración, no tengo muy claro por donde va a tirar, estoy en blanco aquí. En cuanto al lema 1 diría que no tiene mucho misterio más allá de escribir lo que significa cada cosa.

>>> python doc.py sellar 1 <<<


## Fase 2 - Lectura asistida (60 min, python doc.py preguntar)
Lagunas de grado/master detectadas (una linea cada una, NO paro a resolverlas):
- Usar la fórmula de Cauchy
- Fórmula integral de Cauchy
- Desigualdades entre módulo y parte real e imaginaria
- En general recordar teoremas básicos (usarlos, una vez visto bien)

Notas:


## Fase 3 - Ataque (45 min, python doc.py ataque -> MOTOR APAGADO)
Dos modos; `ataque` dice cual toca (comprension hasta leer el nucleo de corpus/orden.md).

Comprension (paper de base), uno o dos, PDF cerrado:
- reconstruir una prueba de la seccion desde el enunciado; huecos apuntados, no resueltos
- el resultado con una sucesion concreta (Gevrey M_p = p!^a): constantes, casos triviales
- quitar una hipotesis y ver que se rompe ("Que se rompe sin el" de la nota)
- mapa de dependencias de la seccion (## Mapa y ## Dependencias de la nota)
- preguntas para los directores, una por linea: son las conjeturas de hoy

Vamos a probar que se verifica (7). Para ello probamos primero que se cumple si /mu es natural. Por definición de h_M(t) = inf_{j>=0} t^j M_j <= inf_{j>=1} t^j M_j = inf_{j>=0} t^{j+1}M_{j+1}. Que la sucesión verifique la condición (3) significa que existe A (que podemos suponer mayor que 1 sin pérdida de generalidad) tal que M_{j+1} <= A^{j+1}M_j para todo j natural. Así, en la desigualdad sobre h tenemos h_M(t) <= t A inf_{j>=0} (At)^j M_j = tA h_M(At) y, recurrentemente, h_M(t) <= t^n A^{n(n+1)/2} h_M(A^n t) probando la igualdad para todo n natural. Ahora si tomamos /mu real, sabemos que existe n natural tal que n <= /mu <= n+1. Si observamos que t^{/mu} >= t^{n} si t > 1 y t^{/mu} >= t^{n+1} si t < 1, entonces podemos usar la desigualdad para n y n+1 para concluir que basta tomar C_1(/mu) = A^{(/mu+1)(/mu+2)/2} y C_2(/mu) = A^{/mu+1}

Extension (nucleo leido): caso Beurling de lo leido, contraejemplo, debilitar la
regularidad fuerte. Conjeturas, una por linea, aunque sean malas:
-

>>> python doc.py sellar 3 <<<


## Fase 4 - Cierre (python doc.py cierre)
Lo hace el programa: diff de la fase 1 contra el paper, errores tipificados,
5 tarjetas, lagunas movidas, conjeturas registradas, metricas.
