# Fase base (semanas 1-8)

Resultado de la calibracion del diagnostico del 2026-09-14 (media 0,29/3).
Objetivo: llegar a poder leer Thilliez 2003 y 2010 de verdad. Hasta entonces el
corpus de orden.md espera.

## Como es una sesion de base

Identica al protocolo normal, con libro en vez de paper:

    python doc.py sesion base-conway-vi
    fase 0   que se ya del capitulo, que espero
    fase 1   leo SOLO el enunciado del teorema del dia, cierro el libro,
             predigo la estructura de la prueba
    sellar 1
    fase 2   leo el capitulo con `preguntar`. Aqui el modelo SI es fiable:
             es material clasico. Usalo sin miedo para desatascar pasos
    ataque
    fase 3   EJERCICIOS del capitulo, motor apagado. Son puzzles calibrados
             con solucion conocida: la pieza del ajedrez que faltaba
    sellar 3
    cierre   las tarjetas de Anki salen de aqui, y solo de aqui

Dos sesiones por semana. La tercera hora y media semanal de "laboratorio" se
convierte durante la base en una tercera sesion corta de ejercicios, salvo en
la semana 6, que es cuando el laboratorio empieza de verdad.

## Semanas 1-2. Crecimiento de funciones holomorfas

Es lo que sostiene todo el campo: acotar derivadas y controlar crecimiento en
sectores.

- Estimaciones de Cauchy para las derivadas. Liouville como corolario.
- Principio del modulo maximo. Lema de Schwarz.
- Phragmen-Lindelof en una banda y en un sector. Por que la apertura del
  sector fija el orden de crecimiento admisible (la funcion exp(z^alpha) es el
  ejemplo que hay que tener en la cabeza).

Texto: Conway, Functions of One Complex Variable I. Capitulo IV para las
estimaciones de Cauchy, capitulo VI (maximum modulus theorem) completo, con la
seccion de Phragmen-Lindelof y sus ejercicios. Alternativa: Rudin, Real and
Complex Analysis, capitulo 12.

Meta al acabar: enunciar Phragmen-Lindelof en un sector sin mirar y explicar
en una linea el papel de la apertura.

Corte en sesiones (dos por semana, un teorema del dia cada una):

    1. estimaciones de Cauchy, con Liouville como corolario     Conway IV
    2. principio del modulo maximo                               Conway VI
    3. lema de Schwarz                                           Conway VI
    4. Phragmen-Lindelof en un sector                            Conway VI

La cuarta es la que cuenta; las tres primeras la sostienen. La sesion corta de
la semana va de ejercicios del capitulo que toque.

## Semana 3. C-infinito frente a holomorfo

- Teorema de Borel: toda serie formal es la de Taylor de una funcion
  C-infinito. La construccion con funciones de corte y radios decrecientes.
- Por que es imposible con holomorfia (principio de identidad).
- El puente hacia el campo: Borel-Ritt, la version en sectores.

Texto: la demostracion clasica de Borel esta en Hormander, The Analysis of
Linear Partial Differential Operators I, seccion 1.2. Borel-Ritt esta en Balser
(abajo). Esta semana enlaza con la anterior: el teorema de Borel es lo que
falla cuando pides demasiado, y las clases de Carleman son justo el terreno
intermedio entre C-infinito y holomorfo.

## Semanas 4-5. Asintotica, Gevrey y sumabilidad

El nucleo del area. Todo lo que puntuaste a 0 en el item 6 vive aqui.

- Desarrollo asintotico en un sector. Desarrollo asintotico Gevrey.
- Transformada de Borel formal y transformada de Laplace. Como una deshace la
  otra y por que eso convierte una serie divergente en una funcion.
- k-sumabilidad en una direccion. Borel-Ritt-Gevrey. Lema de Watson.

Texto: Balser, From Divergent Power Series to Analytic Functions (Lecture
Notes in Mathematics 1582). Es corto y va exactamente a esto: las secciones
sobre desarrollos asintoticos, asintotica Gevrey, transformadas de Laplace y
Borel, y k-sumabilidad. Aqui el modelo es razonablemente fiable pero menos que
en Conway: mantén la costumbre de verificar contra el libro cualquier enunciado
que te de.

Meta al acabar: repetir el item 6 del diagnostico y sacar al menos un 2.

## Semana 6. Sucesiones peso y clases de Carleman

Ya con las herramientas, el vocabulario del proyecto.

- Sucesion peso. Log-convexidad, (mg), (dc), (gamma_1). Que implica que.
- Funcion asociada. Gevrey como caso modelo.
- Clases de Carleman-Roumieu y Carleman-Beurling. El cuantificador.

Texto: Thilliez 2003, secciones 1 y 2, leidas despacio. Para el origen
clasico de las condiciones, Komatsu, Ultradistributions I (1973), seccion 3.
Para las clases Gevrey como introduccion, Rodino, Linear Partial Differential
Operators in Gevrey Spaces, capitulo 1.

Esta es la semana en que el laboratorio empieza en serio: rellenar la tabla
de normalizaciones de orden.md con Thilliez 2003 delante, ejecutar el panel de
pesos.py y comprobar que entiendes por que q-Gevrey rompe (mg) y por que
Gevrey(0) rompe (gamma_1). Y el TODO del indice gamma(M).

## Semanas 7-8. El primer paper de verdad

- Thilliez 2003 completo con protocolo.
- Thilliez 2010 como primera sesion "real" del corpus.

## Control de salida

Al terminar la semana 8:

    python doc.py diagnostico --repetir

Los items 1 a 6 deberian estar en 2 o mas. Si la media queda por debajo de
1,5, no es un fracaso, es un dato: se lo dices a tus directores y la base se
alarga. Lo que no se hace es pasar al corpus con la base a medias.

## Lo que se pide a los directores en la primera reunion

1. Que revisen esta lista: si sobra o falta algo, ellos lo saben y yo no.
2. Si en la UVa hay algun curso de master o de doctorado este cuatrimestre que
   cubra parte de esto, y si conviene asistir.
3. Si un problema de arranque a 6 meses sigue siendo realista con esta base
   por delante, o conviene pensarlo a 9.
