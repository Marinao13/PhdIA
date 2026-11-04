# Guia: como se hace cada cosa

Instrucciones paso a paso, una seccion por tarea. `docs/USO.md` es la chuleta de comandos;
esto es el "como". Si dudas en medio de algo: `python doc.py ahora`. Esta guia se ve tambien
en la web (`python -m web`, pestana Guia).

## Una sesion de lectura de un paper (3 h)

1. Antes de la primera sesion de un paper: `python doc.py nota new ID` crea `lecturas/ID.md`
   (ID es el de `corpus/meta/bib.yaml`, p. ej. `thilliez-2010`). Luego, un bloque por
   resultado que vayas a trabajar: `python doc.py nota add ID "R1 — Teorema 2"`.
2. `python doc.py sesion ID-seccion-2` abre `sesiones/AAAA-MM-DD-ID-seccion-2.md` (la etiqueta
   empieza por el ID del paper: asi `preguntar` y `ataque` saben cual es). Motor apagado.
3. Fase 0 (10 min) y fase 1 (25 min) en ese fichero: que vas a leer, que sabes, y la
   prediccion del resultado principal leyendo solo enunciados y texto, no demostraciones.
4. `python doc.py sellar 1`. Motor encendido.
5. Fase 2 (60 min): `python doc.py preguntar`. El detalle de cada resultado lo escribes en
   `### Desarrollo` de su bloque `R<n>` en `lecturas/ID.md`; en la sesion, solo el diario
   (que trabajaste, donde encendiste el motor). Huecos de grado/master: `/laguna texto` y
   sigues. Si una respuesta falla: `/queja texto`.
6. `python doc.py ataque`: elige el resultado (el que mas preguntaste, o al azar) y lo escribe
   en la sesion como `Ataque: R2 — ...`. 45 min con todo cerrado menos el enunciado; la
   demostracion va a `### Reconstruccion` del bloque R2. `--resultado R1` lo cambia; `--modo`
   fuerza comprension o extension.
7. `python doc.py sellar 3`, y `python doc.py cierre`: diff de tu fase 1, errores, tarjetas,
   lagunas, y el intento anotado en el bloque R (fecha, nivel 0-3, minutos).
8. Si tienes que parar: `python doc.py pausar`; para seguir, `reanudar`. La fase no cambia y
   el tiempo en pausa no cuenta.

## Pasar notas a la nota de un paper

- `python doc.py nota add ID "R3 — Lema 2.1.1"` crea el bloque con ocho campos: Enunciado,
  Hipotesis y por que, Lema clave, Que se rompe sin el, Desarrollo (fase 2), Reconstruccion
  (fase 3, con `Intentos:` debajo), Derivaciones y reformulaciones, Donde se usa. Rellena los
  que tengas; los demas se quedan como plantilla (entre parentesis).
- Las secciones de paper van una vez: Mapa, Sintesis, Transferencia, Abierto, Dudas,
  Dependencias.
- Formulas entre `$...$`; VS Code las renderiza en la vista previa (Ctrl+Mayus+V) y la web
  con KaTeX. Cita con pagina: `[ID:pNN]`.
- `python doc.py nota estado ID` dice que campos tiene escritos cada bloque, los intentos y
  el ultimo check. `nota quiz ID --resultado R2` te interroga; `nota check ID --resultado R2`
  busca agujeros en tu Reconstruccion (`--desarrollo` para el Desarrollo).
- Cuando des el paper por leido: `python doc.py leido ID` (casilla `[~]` en `corpus/orden.md`;
  `--frio` para `[x]`). `ahora` deja de proponerlo y lista aparte los que tienen sesiones sin
  marcar.

## Reconstruir en frio (repeticion espaciada)

`ahora` propone "reconstruir R2 de ID" cuando vence el intervalo del ultimo intento (nivel 0 o
1: 3 dias; 2: dos semanas; 3: un mes). Es una sesion corta: `sesion ID-R2`, enunciado abierto,
todo lo demas cerrado, y `ataque --resultado R2` para que `cierre` anote el intento.

## Reuniones con los directores

1. `python doc.py reunion` crea las notas crudas de hoy en `reuniones/`; escribes lo que se dijo.
2. `python doc.py reunion --destilar` pasa lo que dijeron a `contexto/directores.md` (lo lee
   la IA en cada llamada) y las dudas a `contexto/estado.md`.
3. Antes de la siguiente: `python doc.py reunion --preparar` escribe el pre-read.

## Lagunas de grado y master

- Durante la lectura, UNA linea: `/laguna texto` en `preguntar`, o la linea "Lagunas" de la
  sesion (`cierre` la recoge). No se resuelven en el momento.
- Viernes, 45 min: `python doc.py lagunas` resuelve el lote (motor encendido) y deja tarjetas.
- Una laguna que vuelve tres veces se marca `[ESTRUCTURAL]` en `registro/lagunas.md` y pide
  una sesion de libro: `python doc.py sesion base-conway-vi` con la semana de `corpus/base.md`
  que la cubra.

## Meter un paper nuevo en el corpus

1. Con id de arXiv: `python doc.py ingest --arxiv ID nombre.pdf --id apellido-ano --etiquetas
   citado --factorial fuera` (baja PDF y fuente). Con el PDF de revista ya en `corpus/raw/`:
   `python doc.py ingest --arxiv ID corpus/raw/fichero.pdf --id apellido-ano`.
2. `python doc.py indexar`.
3. Comprueba en `corpus/meta/bib.yaml`: `estado: verificado`, `factorial` (dentro, fuera,
   no_aplica) mirando la definicion de la clase en el texto, `etiquetas`. Nunca completes un
   DOI, un ano o un titulo de memoria.
4. Si es del nucleo, su linea en `corpus/orden.md`.

## Preguntar al corpus fuera de sesion

- `python doc.py buscar "..."`: fragmentos con cita, sin modelo, en cualquier fase.
- `python doc.py ask "..."`: sintesis con una cita detras de cada afirmacion; motor encendido.
  `--doc ID` lo limita a un paper.

## Verificar lo que escribes

`python doc.py referee ARCHIVO [--seccion "Fase 3"]`: objeciones numeradas con gravedad, sin
valoracion global; deja una fila en `registro/verificaciones.md`. `redactar ARCHIVO` pule la
forma y marca `[VERIFICAR]`.

## Quejas y mejora de los prompts

`/queja texto` en `preguntar` guarda la queja con fecha y turno en `registro/quejas.md`. Cada
mes, o cada diez quejas: revision, cambio de reglas con test, y `python doc.py control`
(pasada fija de preguntas por `ask`, unos 30 centimos) para comparar con la anterior.

## Trabajar en otra maquina

- Los sellados (`sellar`, `pausar`, `reanudar`, `cierre`) hacen pull antes y push despues
  cuando hay red; si no, avisan. Regla: una maquina abierta cada vez; antes de cambiar,
  `pausar`.
- Datos locales (fuera de git): `python doc.py exportar` deja un zip en `exportado/`; en la
  otra maquina, `python doc.py importar ruta.zip`. El `.env` se copia a mano. Repetir tras
  cada `ingest`.
- Desde el movil o el portatil sin instalar nada: la web, `python -m web` en la torre y
  Cloudflare Tunnel + Access delante (`docs/WEB.md`).

## Laboratorio

`python doc.py lab "especificacion"`: la IA escribe el script contra `lab/pesos.py`, mpmath
juzga. `lab demo` reproduce los cuatro casos del BRIEF. La convencion del factorial va como
parametro (`factorial="fuera"|"dentro"`); los indices siempre sobre la fuera.
