---
fecha: 2026-09-15
paper: base-conway-iv
objetivo:
min_f1:
min_f3:
coincidencia_estructural:
llamadas_f2:
conjeturas:
---

# Sesion 2026-09-15  base-conway-iv

Las cinco lineas de metricas de arriba las rellena `doc.py cierre`. No las toques.

## Fase 0 - Carga en frio (10 min, MOTOR APAGADO)
Las estimaciones de Cauchy acotan en cierto modo las derivadas de una función que asumo tendrá que tener unos ciertos criterios de regularidad. Supongo que se deduce de resultados clásicos como la fórmula integral de Cauchy.


## Fase 1 - Intento a ciegas (25 min, MOTOR APAGADO)
Solo he leido el enunciado. Mi reconstruccion: Dada f una función analítica en una bola de centro a y radio R, y, siendo f acotada por una constante M en dicho disco. Se tiene que la derivada n-ésima de f está acotada en módulo por M multiplicado por n factorial y dividido por R a la n.
- hipotesis que creo que entran, y donde: Aquí entrará seguramente la fórmula integral de Cauchy para las derivadas de una función analítica (de ahí que se pida dicha propiedad). Además, dado que f está acotada por M en la bola que es justo la curva donde se está integrando f en la expresión de su derivada n-ésima en la fórmula integral se usará la monotonía de la integral para usar la cota. Por último, el hecho de que sea en una bola concreta es relevante para que aparezca el R a la n, ya que estamos integrando en esa bola y el término w-z a la n que aparece en la fórmula integral de Cauchy lo sustituiremos por R que es de hecho el módulo de esa resta.
- tecnica que espero: en realidad no creo que sea un resultado muy técnico (una vez que tienes la fórmula integral de Cauchy claro), se trata más de ir teniendo en cuenta las distintas cotas e ir introduciendolas con cuidado. Quizá lo más técnico será eliminar el 1 partido por 2 pi de la fórmula de Cauchy simplemente teniendo en cuenta que es una fracción más pequeña que 1.
- donde creo que esta el paso duro: No creo que haya ningún paso más duro que otro una vez que se tienen la fórmula integral de Cauchy para las derivadas de una función analítica.

>>> python doc.py sellar 1 <<<


## Fase 2 - Lectura asistida (60 min, python doc.py preguntar)
Lagunas de grado/master detectadas (una linea cada una, NO paro a resolverlas):
-

Notas:


## Fase 3 - Ataque (45 min, python doc.py ataque -> MOTOR APAGADO)
Extension: caso Beurling de lo que acabo de leer, contraejemplo, debilitar la
regularidad fuerte. Conjeturas, una por linea, aunque sean malas:
-

>>> python doc.py sellar 3 <<<


## Fase 4 - Cierre (python doc.py cierre)
Lo hace el programa: diff de la fase 1 contra el paper, errores tipificados,
5 tarjetas, lagunas movidas, conjeturas registradas, metricas.
