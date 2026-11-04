---
fecha: AAAA-MM-DD
paper: ETIQUETA
objetivo:
min_f1:
min_f3:
coincidencia_estructural:
llamadas_f2:
conjeturas:
---

# Sesion AAAA-MM-DD  ETIQUETA

Las cinco lineas de metricas de arriba las rellena `doc.py cierre`. No las toques.
Esta sesion es el DIARIO del dia. El detalle por resultado (desarrollo, reconstruccion,
derivaciones) va al bloque `## R<n>` de lecturas/ID.md (`python doc.py nota add ID "R2 — ..."`).

## Fase 0 - Carga en frio (10 min, MOTOR APAGADO)
Que voy a leer hoy (seccion, resultados), que se ya de esto, que espero encontrar.


## Fase 1 - Intento a ciegas (25 min, MOTOR APAGADO)
Leo enunciados y texto, NO las demostraciones. Para el resultado principal, mi prediccion:
- hipotesis que creo que entran, y donde:
- tecnica que espero:
- donde creo que esta el paso duro:

>>> python doc.py sellar 1 <<<


## Fase 2 - Lectura asistida (60 min, python doc.py preguntar)
Lo hago todo con detalle en el bloque R<n> de la nota (### Desarrollo); el motor solo
donde no sale. Aqui, el diario:
- resultados trabajados (R<n>) y donde me atasque:
- donde encendi el motor y para que:

Lagunas de grado/master detectadas (una linea cada una, NO paro a resolverlas):
-


## Fase 3 - Ataque (45 min, python doc.py ataque -> MOTOR APAGADO)
`ataque` elige el resultado (el mas preguntado en fase 2, o al azar) y lo escribe aqui
debajo como "Ataque: R<n> — ...". Con todo cerrado menos el enunciado: la demostracion va
a ### Reconstruccion del bloque R<n> de la nota; `cierre` anota el intento ahi.
Dos modos; `ataque` dice cual toca (comprension hasta leer el nucleo de corpus/orden.md).

Comprension (paper de base), uno o dos, PDF cerrado:
- reconstruir una prueba de la seccion desde el enunciado; huecos apuntados, no resueltos
- el resultado con una sucesion concreta (Gevrey M_p = p!^a): constantes, casos triviales
- quitar una hipotesis y ver que se rompe ("Que se rompe sin el" de la nota)
- mapa de dependencias de la seccion (## Mapa y ## Dependencias de la nota)
- preguntas para los directores, una por linea: son las conjeturas de hoy

Extension (nucleo leido): caso Beurling de lo leido, contraejemplo, debilitar la
regularidad fuerte. Conjeturas, una por linea, aunque sean malas:
-

>>> python doc.py sellar 3 <<<


## Fase 4 - Cierre (python doc.py cierre)
Lo hace el programa: diff de la fase 1 contra el paper, errores tipificados,
5 tarjetas, lagunas movidas, conjeturas registradas, intento anotado en la nota, metricas.
