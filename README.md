# Sistema de doctorado

Quince horas semanales. Un unico punto de acceso a la IA, `doc.py`, que sabe en
que fase estas porque lo lee de git, se niega a responder cuando el motor tiene
que estar apagado, y registra cada llamada. Nada se autodeclara.

## Instalacion (una vez)

```
python instalar.py
```

Te crea `.env`. Abrelo y pega UNA clave de API: `ANTHROPIC_API_KEY` o
`OPENAI_API_KEY` (se crean en platform.claude.com o platform.openai.com,
apartado API Keys). El proveedor se deduce de la clave que haya; con las dos,
manda `DOC_PROVEEDOR`. Es un fichero ignorado por git; no lo compartas.

Luego instala Anki, crea un mazo "doctorado" y activa FSRS en sus opciones. No
construyas tu propio repetidor espaciado.

**Saca la carpeta de OneDrive.** El sellado depende de que el repositorio git no
se corrompa, y OneDrive sincroniza `.git` mientras git escribe dentro:

```
Move-Item "$env:USERPROFILE\OneDrive\Escritorio\doctorado" "$env:USERPROFILE\doctorado"
```

Copia de seguridad: un repositorio privado en GitHub y `git push`. Te deja
ademas las fechas de los sellados fuera de tu maquina.

## Primera toma de contacto

Antes de cualquier sesion:

1. Ensena `corpus/diagnostico.md` a tus directores y ajusta la lista si te dicen.
2. Reserva 3 horas. Papel o un fichero de texto, nada mas abierto.
3. `python doc.py diagnostico`

Te guia item a item, cronometra, te pide puntuacion 0-3 y que anotes que no
recordabas. Se sella en git. Y solo entonces entra la IA, una vez, para
calibrar el sistema: baraja inicial de drill sobre lo que fallaste, lagunas
sembradas, orden del corpus ajustado, y un borrador de pre-read de una pagina
para tu primera reunion con los directores (reescribelo con tu voz).

Ese pre-read acaba con la peticion mas importante del trimestre: un problema de
arranque acotado a 6 meses. Tu proyecto ya senala el caso Beurling y la
transferencia de Thilliez a clases de matriz peso como primeros pasos. Que te lo
delimiten ellos.

## Una sesion (3 h)

```
python doc.py sesion thilliez2003    crea el fichero. Motor OFF.
    fase 0 (10 min) carga en frio, fase 1 (25 min) intento a ciegas, por escrito
python doc.py sellar 1               commit. Motor ON.
python doc.py preguntar              fase 2 (60 min). REPL con tres usos:
                                       /notacion  /lema  /paso  y /pegar para fragmentos
python doc.py ataque                 commit. Motor OFF.
    fase 3 (45 min): extension, contraejemplo, caso Beurling. Conjeturas en el fichero.
python doc.py sellar 3               commit. Motor ON.
python doc.py cierre                 fase 4 (20 min): diff de tu fase 1 contra el paper,
                                     errores tipificados, 5 tarjetas, lagunas, conjeturas,
                                     metricas al frontmatter. Tu confirmas la puntuacion.
```

Si intentas `preguntar` en fase 1 o 3, se niega. Existe `--forzar` porque la
vida pasa, pero queda registrado como violacion y sale en `metricas`.

## Fuera de sesion

```
python doc.py lagunas                viernes, 45 min. Resuelve el lote de huecos de
                                     grado/master con el formato: enunciado minimo,
                                     referencia con capitulo, intuicion, trampa, 2
                                     tarjetas, ejercicio SIN solucion. Detecta las que
                                     van por la tercera vez: eso es un capitulo que
                                     falta, y va con un libro, no con la IA.
python doc.py lab "especificacion"   la IA escribe el script contra lab/pesos.py,
                                     mpmath dicta la verdad. Tu no escribes Python.
python doc.py metricas               duracion de fase 1 y 3 (de git), coincidencia
                                     estructural, violaciones, tokens, errores por tipo,
                                     conjeturas, lagunas.
python doc.py anki                   exporta las tarjetas nuevas.
python doc.py estado                 en que fase estas.
```

## Contexto vivo: lo que la IA sabe de ti

`nucleo/prompts.py` le dice a la IA tu tema y las reglas, pero eso es fijo. Lo
que cambia vive en dos ficheros que TU mantienes y que se pegan al final del
system prompt en TODAS las llamadas:

```
contexto/estado.md       donde estas: fase, semana, texto, problema de arranque.
                         Diez lineas maximo. Se actualiza al cambiar de semana.
contexto/directores.md   lo que dicen Javier y Alberto, una linea por instruccion,
                         fechada y con quien la dijo. MANDA sobre el criterio del
                         modelo y sobre los libros: si le pides algo que lo
                         contradiga, te avisa antes de responder.
```

Curado, no transcrito. Las notas crudas de cada reunion son el archivo y van a
`reuniones/`; a `directores.md` pasa solo lo que deba gobernar el trabajo.

```
python doc.py reunion              crea reuniones/HOY.md y lo abre. Escribe TODO,
                                   durante o justo despues, textual entre comillas
python doc.py reunion --destilar   lee esas notas y te propone, una a una, las
                                   lineas para directores.md. Enter acepta, n
                                   rechaza, e edita. Te lista aparte los cambios
                                   de estado (los pegas tu en estado.md) y lo
                                   que quedo ambiguo para que lo aclares
python doc.py reunion --preparar   redacta el pre-read de la proxima reunion con
                                   tus sesiones, errores y conjeturas desde la
                                   anterior. Borrador: reescribelo con tu voz
```

Si el contexto vivo pasa de unos 7000 caracteres, el sistema te avisa. Entonces
se condensa: fusionar lineas, quitar lo caducado. Un system prompt que crece
sin limite acaba siendo ruido.

## Reparto semanal

| Bloque | Horas | Comandos |
|---|---|---|
| 2 sesiones profundas | 6 | sesion, sellar, preguntar, ataque, cierre |
| Laboratorio | 3 | lab, y ejecutar lo que genere |
| Produccion | 3 | LaTeX a mano, en espanol, primero. Sin IA hasta el pulido |
| Drill | 1,5 (5 x 20 min) | Anki |
| Metasistema | 1,5 | lagunas, metricas, pre-read para la reunion |

## Las tres reglas (ia/reglas.md)

1. Compromiso antes de consulta. El programa lo impone.
2. Nada sobre tu campo entra en tus notas sin referencia abierta. El prompt del
   sistema obliga a la IA a marcar [SIN VERIFICAR] lo que arriesgue sobre clases
   ultraholomorfas, y le permite responder con normalidad sobre material clasico
   de grado y master. Esa asimetria es el diseno entero.
3. Las matematicas las escribes tu. La IA no toca produccion/ hasta que exista
   el borrador.

## Proveedor y coste

El proveedor solo se toca en `_completar` dentro de `nucleo/motor.py`; todo lo
demas es independiente del modelo. Se elige en `.env`:

```
DOC_PROVEEDOR=anthropic | openai     (si falta, se deduce de la clave presente)
DOC_MODELO=...                       (por defecto claude-sonnet-5 / gpt-6-astra)
DOC_SIMULAR=1                        (prueba el flujo sin gastar nada)
```

Comprueba nombres y precios en la pagina de modelos del proveedor antes de
fiarte del modelo por defecto: cambian cada pocos meses. Cada llamada queda en
`registro/llamadas.jsonl` con proveedor, modelo y tokens, asi que el coste
exacto lo calculas tu. Con este volumen, del orden de una veintena de llamadas
cortas por semana, es marginal.

Si con OpenAI las respuestas llegan cortadas (los modelos con razonamiento
consumen parte del limite de salida en pensar), sube `MAX_TOKENS_*` en
`nucleo/config.py`.

## Estructura

```
doc.py                 unico punto de entrada
instalar.py            una vez
nucleo/                config, estado (git), motor (API + puerta + log), prompts, comandos
sesiones/              una por sesion, metricas en la cabecera (las rellena cierre)
contexto/              estado.md y directores.md: se inyectan en toda llamada
reuniones/             notas crudas de cada reunion y pre-reads
corpus/base.md         plan de la fase base (semanas 1-8)
corpus/diagnostico.md  items de la primera toma de contacto. Editable
corpus/orden.md        los 8 papers nucleo + tabla de normalizaciones
registro/errores.md    cuaderno de errores con taxonomia
registro/lagunas.md    huecos de grado y master
registro/conjeturas.md
registro/llamadas.jsonl  cada llamada a la IA
lab/pesos.py           motor de refutacion numerica
lab/conj/              scripts generados por lab
drill/                 tarjetas -> Anki
produccion/notas/      LaTeX y el pre-read para directores
ia/reglas.md           las tres reglas, en prosa
```
