# MEJORAS — analisis y plan (2026-10-27)

Seis preguntas de Mariano sobre el sistema, con lo que haria en cada una, y el plan en
cuatro bloques que sale de ellas. Nada de esto esta ejecutado salvo lo marcado. Las
decisiones ya tomadas en la conversacion: el detalle de la fase 2 va a la nota del paper,
no a la sesion; `corpus/raw/` se separa por tipo (papers, libros, cursos).

## 1. Que pasa si entra mas conocimiento al corpus

El mecanismo aguanta: `ingest` es incremental, `indexar` solo embebe lo nuevo y las citas
no dependen del tamano. Lo que se degrada es la velocidad y el cuidado manual:

- Con 100 papers (el tamano que daba el BRIEF) son unos 15.000 fragmentos; BM25 se
  reconstruye en cada busqueda (0,2 s hoy, un segundo largo entonces) y los vectores
  (26 MB) se recargan en cada llamada. Arreglo: cache por proceso en `preguntar` y `ask`.
- Cada paper nuevo entra con `factorial: pendiente` hasta comprobarlo en el texto; las
  etiquetas (`nucleo`, `citado`, `directores`) las pone Mariano; arXiv y revista del mismo
  trabajo deben ser un solo id.
- Propuesta: `ingest` termina con una lista "pendiente de ti" (factorial, etiquetas, linea
  en `orden.md`); `ask --etiqueta nucleo` para no diluir el nucleo entre papers citados.

## 2. Fase 3: saber si se aprende

Si el teorema lo elige uno, mide lo que ya sabe. Tres medidas, todas sin modelo:

- Que no elija Mariano: `ataque` propone el resultado (el mas preguntado en fase 2 ese dia,
  segun `registro/consultas`; si no, azar con semilla entre los numerados de la seccion).
- Registro por resultado en el bloque `R<n>` de la nota: una linea por intento, "fecha,
  0-3, minutos, hueco donde paro". Hoy `cierre` guarda una coincidencia por sesion.
- Repeticion espaciada de demostraciones: `ahora` propone reconstruir un `R` antiguo a los
  3 dias, 2 semanas o 1 mes segun el ultimo nivel. Aprender es que la segunda vez salga sin
  el hueco de la primera.

Honesto: con un paper no lo dice ninguna metrica; empieza a medir con tres o cuatro
resultados repetidos.

## 3. Referencias de lo que esta fuera del corpus

Dos casos. Lo elemental (componer funciones, un producto cartesiano) no se cita: la regla
FUENTES ya lo dice (hecho el 2026-10-21). Lo que merece referencia (derivacion bajo la
integral, Phragmen-Lindelof, anillos henselianos) debe citarse como un paper: a un texto
real del corpus. Propuesta: ingerir los libros que ya usa (Conway, Rudin, Hormander; Balser
esta) como `fuente: libro`, y que tras cada respuesta el sistema busque cada linea `[!]`
en los libros, sin modelo, y anada "en el corpus: [conway-1978:p145]" o "no esta en los
libros del corpus". La referencia nunca sale de la memoria del modelo (BRIEF, principio 2).
Lo mismo sirve a `lagunas`.

## 4. Las notas propias en un formato que el sistema lea

El metodo real de Mariano: fase 0 elige; fase 1 lee enunciados y texto sin demostraciones;
fase 2 lo hace todo con detalle y el motor solo donde no sale; fase 3 demuestra con todo
cerrado menos el enunciado. Van surgiendo expresiones deducidas y reformulaciones.

- La plantilla de sesion debe decir eso, no lo que dice hoy. La sesion es el diario del
  dia (que resultados, donde entro el motor, atascos, tiempos); `cierre` lee eso.
- El detalle de la fase 2 va al bloque `R<n>` de `lecturas/ID.md`, por resultado y
  persistente. Campos del bloque (ocho): Enunciado; Hipotesis y por que; Lema clave; Que se
  rompe sin el; Desarrollo (fase 2, con el paper); Reconstruccion (fase 3, a ciegas, con el
  registro de intentos debajo); Derivaciones y reformulaciones; Donde se usa. "Idea de la
  prueba" desaparece: la absorbe Desarrollo. `nota check --resultado` lee Reconstruccion;
  `--desarrollo` revisa el otro.
- Formato: markdown con `$...$`; VS Code lo renderiza en la vista previa. Todo lo de
  `lecturas/` y `sesiones/` se indexa como `fuente: nota`.
- `nota estado ID`: por bloque, campos escritos, intentos (fecha, nivel), objeciones del
  ultimo check.
- No: escanear notas a mano; la OCR de matematicas manuscritas no da para citar.

## 5. Apuntes de cursos con ejercicios corregidos

Lo mas valioso que puede entrar: detallado y contrastado por un profesor. `fuente: curso`
con etiquetas `curso` y `corregido`, distinta de los papers (no es literatura para la
tesis) pero fiable para fase 2, `lagunas` y `[!]`. Desde el `.tex` si lo hay (capa de
formulas exactas). Los ejercicios como unidades propias: las sesiones `base-*` de lagunas
estructurales y las tarjetas de Anki salen de ahi en vez del modelo. El prompt los presenta
como material propio corregido.

## 6. Mejorar el contexto y los prompts

Tiene sentido con disciplina. Lo que ha funcionado: medir en `registro/consultas` (62
marcas `[!]` y cero citas, el 2026-10-13) y cambiar una regla con test. Lo que no: dejar
que el modelo retoque sus instrucciones, o cambiar prompts por impresion.

- `/queja texto` en `preguntar`: guarda la queja junto al turno en `registro/quejas.md`.
- Cada mes, o cada diez quejas: revision de quejas y consultas, cambios con test y una
  pasada fija de cinco preguntas de control (unos 30 centimos) para que no se rompa lo
  que iba bien.
- Contexto vivo como hasta ahora: `directores.md` tras cada reunion (`reunion
  --destilar`), `estado.md` cuando cambie algo. Los prompts estan en git: el historial es
  el registro de cambios.

## 7. Usarlo desde otro sitio: portatil en la uni y movil

Lo que hace falta en otra maquina: Python con los paquetes, el repo, `.env` (nunca en git)
y los datos locales fuera de git, `corpus/text` e `indice/` (unos 40 MB; los PDFs de
`corpus/raw` solo para ingerir y leer). Las fases, pausas y reloj viven en el log de git:
viajan con push y pull. Marker y la GPU solo se usan al ingerir: se quedan en la torre.

Portatil (caso resuelto):
- `sellar`, `pausar`, `reanudar` y `cierre` hacen `git pull --ff-only` antes y `git push`
  despues cuando hay red; sin red avisan. Hoy los sellados no empujan solos, y con dos
  maquinas eso es lo que rompe las fases (dos historiales).
- Regla: una maquina abierta cada vez; antes de cambiar, `pausar` (commitea todo) y push.
- `python doc.py exportar` empaqueta `corpus/text` e `indice/` en un zip; `importar` lo
  desempaqueta (USB u OneDrive como transporte, no como carpeta de trabajo). Se repite
  tras cada `ingest` en la torre. `.env` se copia a mano una vez.

Movil (lo honesto: ni fase 2 con formulas ni el REPL; si `ahora`, `estado`, `ask`,
`buscar`, una laguna, Anki):
1. SSH a la torre con Tailscale (torre encendida): todo identico. Una hora de Mariano,
   cero codigo. Primero esto.
2. Mini web servida desde la torre por Tailscale (`ask`, `buscar`, `laguna`, `estado`) con
   KaTeX, que en el movil se ve mejor que la consola. Un par de dias. Solo si 1 se queda
   corto.
3. Nube (VPS o Codespace con repo, datos y `.env`): la torre solo para ingerir. Mas caro y
   mas piezas; para cuando portatil y SSH no basten.

## Plan en cuatro bloques

Cada bloque es un commit cerrado que deja el sistema usable.

### Bloque A. Notas y sesiones al metodo real (ya; sin coste)
1. Plantilla de sesion con las fases reales (fase 2 como diario).
2. Bloque `R<n>` con los ocho campos; `nota check --resultado` sobre Reconstruccion,
   `--desarrollo` sobre Desarrollo.
3. `nota estado ID`.
4. `cierre` anade la linea del intento al `R` atacado y guarda la coincidencia por resultado.

### Bloque B. Fase 3 que mide (ya, junto con A)
5. `ataque` elige el resultado (mas preguntado en fase 2, o azar con semilla); `--resultado
   R2` lo fuerza; queda escrito en la sesion.
6. Repeticion espaciada en `ahora`: "reconstruir R2 de thilliez-2003" a 3 dias / 2 semanas
   / 1 mes segun nivel, como sesion corta.

### Bloque C. Quejas y prompts (ya; pequeno)
7. `/queja texto` en `preguntar` -> `registro/quejas.md`.
8. Revision mensual con pasada de control fija.

### Bloque D. Corpus por tipo, libros, cursos y cache (cuando entre el primer libro o curso)
9. `corpus/raw/papers/`, `libros/`, `cursos/`; la carpeta fija la `fuente`; los 27 PDFs
   actuales pasan a `papers/` con un comando que actualiza `bib.yaml`; `ingest` recorre las
   tres y termina con "pendiente de ti".
10. Libros por Marker; cada `[!]` se busca en los libros tras la respuesta, sin modelo.
11. Cursos como `fuente: curso`; ejercicios como unidades; `lagunas` y tarjetas desde ahi.
12. Cache por proceso de BM25 y vectores; `ask --etiqueta`.

### Bloque E. Llevarselo (cuando empiece a estudiar fuera)
13. Pull y push automaticos en `sellar`, `pausar`, `reanudar` y `cierre`, con aviso sin red.
14. `exportar` / `importar` de `corpus/text` e `indice/`.
15. SSH + Tailscale a la torre desde el movil (instalacion de Mariano, sin codigo); mini web
    con KaTeX solo si hace falta.

### Lo que necesita de Mariano
- Para A: conformidad con los ocho campos del bloque `R<n>` (o sus nombres).
- Para D: que libros y cursos, en PDF o `.tex`, cuando los tenga.

### Coste
A, B y C: trabajo del agente sin gasto de API; media hora de Mariano leyendo plantillas.
D: el tiempo de Marker con los libros (sin coste) y centimos de embeddings; la pasada de
control de C, 30 centimos cada vez.

## Fallos visuales de `preguntar` vistos en las sesiones del 21 al 27 (corregidos el 2026-10-27)
- `$f inE_p(M)$`: un comando pegado a `\mathcal{...}` (corregido el 21).
- `mathfrak m`, `bmod`: comandos sin tabla (corregido el 21).
- Formulas sin convertir cuando el modelo parte `$...$` en dos lineas (corregido el 27).
- `widehat` sin tabla; citas repetidas en "corpus consultado" (corregido el 27).
