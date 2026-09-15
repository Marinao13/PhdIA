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

# Sesion AAAA-MM-DD  ETIQUETA   (fase base: libro, no paper)

Las cinco lineas de metricas de arriba las rellena `doc.py cierre`. No las toques.
Teorema del dia (UNO, no un capitulo):

## Fase 0 - Carga en frio (10 min, MOTOR APAGADO)
Libro cerrado. Que se ya de esto y que espero encontrar. Tres lineas.


## Fase 1 - Intento a ciegas (25 min, MOTOR APAGADO)
Abro el libro SOLO para leer el enunciado del teorema del dia, y lo cierro.
Predigo la demostracion por escrito:
- hipotesis que creo que entran, y donde:
- tecnica que espero:
- donde creo que esta el paso duro:
Va a salir incompleto. Lo escribo igualmente: eso es la medida.

>>> python doc.py sellar 1 <<<


## Fase 2 - Lectura asistida (60 min, python doc.py preguntar)
Leo el capitulo con el REPL al lado. Es material clasico y el modelo es fiable:
usalo sin miedo para desatascar pasos. Le nombro libro y teorema; no hace falta
pegar. Si pego varias lineas de golpe, se toman como un solo fragmento.
Lagunas de grado/master detectadas (una linea cada una, NO paro a resolverlas):
-

Notas (solo lo que difiere de mi fase 1):


## Fase 3 - Ataque (45 min, python doc.py ataque -> MOTOR APAGADO)
En la base el ataque son los EJERCICIOS del capitulo: libro abierto, motor
apagado. Numero del ejercicio y mi intento, aunque quede a medias:
-

Conjeturas, si alguna (en la base, normalmente ninguna):
-

>>> python doc.py sellar 3 <<<


## Fase 4 - Cierre (python doc.py cierre)
Lo hace el programa: diff de la fase 1 contra la demostracion del libro, errores
tipificados, 5 tarjetas, lagunas movidas, metricas.
