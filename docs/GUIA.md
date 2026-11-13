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

## Pasar a limpio lo escrito a mano (transcribir)

Para lo que escribes en papel o en la tableta: apuntes de un curso, notas al leer un paper,
una duda. El sistema lo transcribe a markdown con LaTeX y tu lo revisas contra el original,
que es mas corto que escribirlo de cero. Nada sin revisar entra en el indice ni se cita.

1. Ten el fichero: PDF (escaneado o exportado de la tableta) o foto (`png`, `jpg`, `webp`).
   Las fotos HEIC del iPhone, exportalas antes como JPG o PDF. Una foto tumbada del movil se
   endereza sola. WebP y el enderezado usan Pillow (`instalar.py` lo pone; a mano,
   `python -m pip install pillow`).
2. Transcribe. En la consola:
   `python doc.py transcribir apuntes.pdf --tipo curso --titulo "Curso X, tema 1" --paginas 1-5`
   (`--tipo curso | paper | duda`; sin `--paginas`, todas). Desde el movil: web, pestana
   Transcripciones, subir el fichero; trabaja en segundo plano y la pagina se refresca sola.
3. Sale `transcripciones/AAAA-MM-DD-titulo.md` con `estado: sin_revisar` y una seccion por
   pagina. El original se copia a `transcripciones/originales/` (fuera de git: no viaja a la
   otra maquina).
4. Revisa con el original al lado: web, `/transcripciones/NOMBRE` (original a la izquierda,
   texto a la derecha, "corregir esta pagina" debajo de cada una; "Guardar cambios" guarda de
   una vez todas las paginas que hayas tocado), o el `.md` en VS Code. Lo
   resaltado son las marcas del modelo: `[ILEGIBLE]` (no pudo leerlo) y `[?]` (no esta
   seguro). Lo que NO lleva marca y hay que mirar igual: subindices (`M_p` frente a
   `M_{p+1}`), cuantificadores, `<` frente a `\le`, exponentes y signos. El modelo copia: no
   corrige ni completa, y un error tuyo en el papel sale tal cual.
5. Marca: `python doc.py transcribir --revisado NOMBRE` (o el boton de la web, que guarda antes
   lo que tengas corregido sin guardar) y despues
   `python doc.py indexar`. Un curso revisado entra como `fuente: curso`
   (`buscar --fuente curso`); las notas de paper y las dudas, como `fuente: nota`. `ask` no
   las usa salvo que se lo pidas (`--fuente curso` o `--con-propios`): no son literatura.
6. `python doc.py transcribir --lista` dice que hay y que sigue sin revisar; `ahora` lo
   recuerda en PENDIENTE.
7. El LaTeX: junto al `.md` queda `transcripciones/NOMBRE.tex`, exportado de el, por si con
   un par de cambios te sirve para un documento: `article` con `amsmath`, `amssymb`, `amsthm`
   y `babel` en espanol; titulos, listas (las numeradas conservan su numero) y formulas tal
   cual (la que va sola en su linea, en `\[ \]`); las marcas `[ILEGIBLE]` y `[?]` en rojo con
   `\duda{}`; un comentario `% ---------- pagina N ----------` donde empieza cada pagina. Un
   simbolo Unicode suelto pasa a su comando (`≤` a `\le`); el que no tenga comando conocido se
   declara en el preambulo y sale en rojo como `[U+XXXX]` para que lo sustituyas. Reglas:
   - La fuente es el `.md`. Corrige ahi (web o VS Code); el `.tex` se rehace solo al marcar
     `--revisado`, o cuando quieras con `python doc.py transcribir --tex NOMBRE`. En la web,
     "descargar .tex" da siempre el del texto de ese momento.
   - Si editas el `.tex` a mano, deja de rehacerse (no se pisa lo tuyo): `--tex NOMBRE --pisar`
     lo rehace desde el `.md` y pierde tus cambios. Lo que cambies en el `.tex` no vuelve al
     `.md` ni al indice.
   - No esta compilado: en la torre no hay `pdflatex`. Se comprueba que llaves y entornos
     casan y que el texto va escapado, y un revisor hizo de compilador leyendo el LaTeX
     generado (salieron seis fallos, corregidos). Aun asi, hasta que no lo compiles tu no esta
     probado de verdad: si algo no compila en tu LaTeX, dimelo con el error.

El formato del `.tex` es el de tu TFM (visto en su PDF): 12 pt, enunciados con la etiqueta en
negrita y numeracion corrida y comun (Teorema 1, Observacion 2...), cuerpo en redonda,
"Demostracion:" en negrita y cuadrado negro al final. Cada enunciado y cada demostracion van
en su entorno (`teorema`, `lema`, `proposicion`, `corolario`, `definicion`, `observacion`,
`ejemplo`, `notacion`, `nota`, `demostracion`), con su nombre: `**Teorema (Pringsheim):**`
sale como `\begin{teorema}[Pringsheim]`.

- De donde sale: en el `.md`, cada bloque va entre una linea `<!-- teorema -->` y una linea
  `<!-- fin -->`. En la web no se ven; en el texto de "corregir esta pagina", si. Si un bloque
  acaba donde no es, mueve su `<!-- fin -->`; si falta uno, ponlo tu.
- En una transcripcion nueva las pone el modelo al transcribir.
- En una ya hecha: `python doc.py transcribir --estructura NOMBRE`. Pregunta al modelo que
  parrafos forman cada enunciado y cada demostracion (una llamada de texto por pagina, unos
  2 centimos) y solo anade esas lineas: no cambia ni una palabra. Probado con tu curso el
  2026-11-13: 57 bloques en 17 hojas, 63 s y 27 centimos.
- Otro preambulo: si dejas un `transcripciones/preambulo.tex` (desde `\documentclass` hasta
  antes de `\begin{document}`), se usa el tuyo. Tiene que definir esos entornos y `\duda`.
- Lo que no se: como son tus macros y tus paquetes, porque solo tengo los PDF. Con los `.tex`
  del TFM podria copiar el preambulo tal cual.

Las figuras: cada dibujo (una grafica, unos ejes, un esquema) se recorta del original y entra
como imagen, con la descripcion del modelo debajo como pie. Los recortes quedan en
`transcripciones/figuras/` y los usan el `.md`, la web y el `.tex` (`\includegraphics`). No se
redibujan: es tu dibujo tal cual, no una version del modelo.

- En una transcripcion nueva salen solas.
- En una ya hecha, que solo tiene `[FIGURA: descripcion]`:
  `python doc.py transcribir --figuras NOMBRE`. Pregunta al modelo donde esta cada dibujo (una
  llamada por pagina con figuras, unos 3 centimos), los recorta y cambia solo esas lineas; lo
  que hayas corregido no se toca. Necesita el original en `transcripciones/originales/`.
- Mira cada recorte al revisar. Si la caja corta el dibujo o coge texto de mas: deshaz esa
  figura a `[FIGURA: descripcion | x0,y0,x1,y1]` con la caja buena (tantos por ciento del ancho
  y del alto de la hoja) y lanza `--figuras` otra vez, o sustituye el `.jpg` por tu recorte.
- Probado el 2026-11-13 con tu curso (17 hojas, 9 figuras): las 9 localizadas y bien
  recortadas, alguna con un poco de texto vecino en el borde; 29 s y 23 centimos.

Reglas y limites:

- Con el modelo (por defecto) es una llamada al motor: en fase 1 y 3 se niega. Escribe a mano
  y transcribe despues de sellar.
- Probado con tu letra el 2026-11-12 (tres hojas dobles de CamScanner, apuntes del curso, con
  tachones, notas en azul y el reverso transparentandose):
  - `--calidad alta`, que es el defecto: lee bien las formulas (`\delta A_1 \ge A`, el `n!` del
    teorema, `\mathcal{E}_{\{M^{lc}\}}`, "Gorny-Cartan", la nota en azul) y marca sus dudas
    donde las tiene. Quedan deslices sueltos sin marca (un subindice perdido, una palabra):
    por eso se revisa. 18 s y unos 9 centimos por hoja doble.
  - `--calidad normal` (el modelo barato, 3 centimos por hoja): cambia `\delta` por 8, pierde
    subindices y el `n!`, y no avisa. Con letra manuscrita no sirve; partir la hoja en dos
    mejora algo y no basta.
  - `--motor marker` (OCR local, gratis): texto sin sentido. Vale para texto impreso, no
    para tu letra.
- Coste: un cuaderno de 60 paginas son 30 hojas dobles, unos 3 EUR de los 20 del mes. Por
  temas, no de golpe. `metricas` lo cuenta en el comando `transcribir`.
- Escanea a doble pagina sin miedo: el modelo lee primero la izquierda y despues la derecha, y
  no copia lo que se transparenta del reverso. Lo que quede cortado por el borde sale como
  `[ILEGIBLE]`.
- Si se para a media pasada (red, cuota, Ctrl+C, o cambias de fase mientras transcribe) se
  guarda lo hecho y dice que paginas faltan y el comando para seguir. El fichero se escribe
  tras cada pagina: aunque cierres la ventana o se reinicie la torre, lo ya transcrito esta en
  `transcripciones/`.
- Puedes ir corrigiendo las paginas que ya han salido mientras la pasada sigue: cada pagina
  nueva se anade al fichero, no lo reescribe. Si la marcas revisada antes de que acabe, vuelve
  a sin revisar en cuanto entra la pagina siguiente (nadie la ha mirado).
- Las notas de un paper transcritas no se copian solas a `lecturas/ID.md`: lo que quieras en
  el bloque `R<n>` (Desarrollo, Derivaciones) lo pegas tu desde la transcripcion revisada.
- Con el modelo, las paginas viajan a la API del proveedor, como cualquier `preguntar`.

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
