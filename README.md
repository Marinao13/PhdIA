# Sistema de doctorado

Quince horas semanales. Un unico punto de acceso a la IA, `doc.py`, que sabe en
que fase estas porque lo lee de git, se niega a responder cuando el motor tiene
que estar apagado, y registra cada llamada. Nada se autodeclara.

## Instalacion (una vez)

```
python instalar.py
```

Te crea `.env`. Abrelo y pega tu clave de la API (se crea en
https://platform.claude.com, apartado API Keys). Es un fichero ignorado por git;
no lo compartas.

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

## Coste

Cada llamada queda en `registro/llamadas.jsonl` con sus tokens, asi que el
coste exacto lo calculas tu contra la tabla de precios del modelo
(https://platform.claude.com). Con este volumen, del orden de una veintena de
llamadas cortas por semana, es marginal. `DOC_MODELO` en `.env` cambia el modelo.
`DOC_SIMULAR=1` prueba el flujo sin gastar nada.

## Estructura

```
doc.py                 unico punto de entrada
instalar.py            una vez
nucleo/                config, estado (git), motor (API + puerta + log), prompts, comandos
sesiones/              una por sesion, metricas en la cabecera (las rellena cierre)
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
