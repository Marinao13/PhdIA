# PLAN — del sistema de sesiones al sistema del BRIEF (2026-09-16)

Parte de `ESTADO_SISTEMA.md`. Las horas son de construccion del agente; las de
Mariano son solo revision y pruebas, y van aparte porque son las que escasean.
Cada fase termina con tests en verde, commit, push y una linea en el registro de
abajo.

## Decisiones de arquitectura (propuestas; se cierran con las respuestas)

1. **Un solo punto de entrada.** Los comandos del BRIEF (`ingest`, `ask`, `nota`,
   `referee`, `lab demo`) se anaden como subcomandos de `doc.py`. Si se quiere
   `phd`, es un alias de una linea. Motivo: el README ya promete "un unico punto
   de acceso a la IA" y `motor.llamar()` es la unica puerta.
2. **`ask` respeta las fases.** Pasa por `motor.llamar()`: apagado en fases 1 y 3,
   `--forzar` registrado como violacion. **[PENDIENTE: pregunta 6]** Si se prefiere
   corpus consultable siempre, `ask` entra por `llamar(..., forzar=True)` con
   `comando="ask"` y se ve en `metricas`, pero no rompe la puerta de `preguntar`.
3. **Nombres en espanol y sobre lo que ya hay.** `corpus/raw|meta|text` bajo el
   `corpus/` existente; `indice/` para el almacen; `lecturas/{id}.md` para la nota
   por paper (la unidad `sesiones/` sigue siendo el dia); `registro/verificaciones.md`
   hace de `log/verificaciones.md`; los prompts nuevos van a `nucleo/prompts.py`
   como los demas.
4. **Extraccion: PyMuPDF con numero de pagina, siempre.** Marker/Nougat solo si hay
   GPU **[PENDIENTE: pregunta 4]**; sin ella tardan horas por paper en CPU y en
   Windows su instalacion es fragil. Las formulas de un PDF con capa de texto salen
   como texto plano deformado: se guarda tal cual, se marca la pagina, y la cita
   `[id:pagina]` remite al PDF. No se pretende LaTeX limpio en esta fase.
5. **Indice minimo sin dependencias pesadas.** BM25 con `rank_bm25` + embeddings
   por API (`text-embedding-3-small`, mismo `.env`) guardados en sqlite + numpy.
   10 papers son ~2.000 chunks: centimos de embedding, consulta en milisegundos.
   Local (`sentence_transformers`) solo si hay GPU y presupuesto cero
   **[PENDIENTE: preguntas 4 y 5]**.
6. **Laboratorio en SymPy + `Fraction`/`QQ` + mpmath.** Sage no se asume
   **[PENDIENTE: pregunta 3]**; si existe, `algebraic.py` lo usa para Puiseux en la
   fase 5c y ahorra 3-4 h.
7. **Antes de la fase 1:** `git tag pre-brief` en `master`.

## Fases

### Fase 0 — Auditoria y plan  · hecha
Entrega: `ESTADO_SISTEMA.md`, `PLAN.md`. Aceptacion: Mariano responde las 6
preguntas y aprueba las decisiones de arriba.

### Fase 1 — Corpus + indice + `ask`  · prioridad maxima
Bloqueada por: **PDFs y documento del proyecto [preguntas 1 y 2]**.

| Paso | Que | Horas agente |
|---|---|---|
| 1a | `corpus/meta/bib.yaml` (id, autores, titulo, ano, venue, DOI/arXiv, etiquetas, `estado: pendiente_verificar`). `doc.py ingest <pdf>`: copia a `corpus/raw/`, texto por pagina a `corpus/text/{id}/pNNN.txt`, entrada en `bib.yaml`. Resolucion de DOI/arXiv por red para pasar a `verificado`. | 3 |
| 1b | Chunking por parrafo (300-800 tokens) con id, pagina, seccion si se detecta, tipo si se detecta (definicion / teorema / prueba). Indice BM25 + embeddings en `indice/`. `doc.py indexar`. Tambien `lecturas/` y `sesiones/` como fuente `nota`. | 3 |
| 1c | `doc.py ask "pregunta"`: recupera k, responde con `[id:pagina]` tras cada afirmacion, separa "el corpus dice" de "conocimiento general", dice "no esta en el corpus" cuando no hay evidencia. Por `motor.llamar()`. Guarda pregunta, fragmentos usados y respuesta en `registro/consultas/`. | 3 |
| 1d | Registro de conversaciones de `preguntar` (hueco del ESTADO 9). Mismo formato. | 1 |

Aceptacion: `ingest` procesa un PDF nuevo de principio a fin y una formula de
muestra queda legible (o marcada como deformada con su pagina); 5 preguntas de
prueba con cita comprobada a mano contra el PDF, por ejemplo "que condiciones
sobre M usa el teorema de extension de Thilliez". Mariano: 1 h para comprobar
las 5 contra el PDF. Coste estimado: < 1 EUR de embeddings; consultas al precio
del modelo actual.

### Fase 2 — Notas de lectura por paper
| Paso | Que | Horas |
|---|---|---|
| 2a | `doc.py nota new <id>`: crea `lecturas/{id}.md` desde plantilla (enunciado principal, hipotesis y por que, lema clave, que se rompe sin el, que dejan abierto, pregunta de transferencia Roumieu/Beurling y sectores/polisectores, dudas para directores). La redaccion es de Mariano; el sistema no rellena. | 1 |
| 2b | `doc.py nota quiz <id>`: preguntas de interrogatorio a partir del texto indexado, sin respuestas, con cita de pagina. | 1 |
| 2c | `doc.py nota check <id>`: Mariano pega su explicacion; el modelo busca agujeros citando el texto. Motor sujeto a fases. | 1,5 |

Aceptacion: una nota real de Thilliez 2003 con quiz y check ejecutados.
Mariano: la redaccion de la nota es su trabajo de lectura, no coste extra.

### Fase 3 — Referee y registro de verificaciones
| Paso | Que | Horas |
|---|---|---|
| 3a | `REFEREE` en `prompts.py`: una orden, "encuentra el error"; lista de comprobacion del BRIEF 4.5 (constantes dependientes de n, uniformidad en el sector, cuantificadores Roumieu/Beurling, propiedades de M usadas, formal vs analitico, direccion y abertura, casos degenerados). Salida: objeciones numeradas con gravedad, sin valoracion global. `REDACTOR`: marca `[VERIFICAR]`. | 1,5 |
| 3b | `doc.py referee <archivo>`: contexto nuevo, sin historial; opcion `--proveedor` para juzgar con el otro modelo. Puerta de fases. Anade fila a `registro/verificaciones.md` (fecha, afirmacion, metodo, resultado). | 1,5 |

Aceptacion: `referee` sobre la seccion Fase 3 de una sesion devuelve objeciones numeradas; la fila queda en el registro.

### Fase 4 — Laboratorio
| Paso | Que | Horas |
|---|---|---|
| 4a | `pytest` + tests de `pesos.py` (panel del catalogo con valores fijados, `refutar` con contraejemplo conocido) y de `estado.py` (los 7 escenarios de medianoche ya probados a mano). | 2,5 |
| 4b | `series.py`: series truncadas a orden N, operaciones, generadores Gevrey alpha (semilla fija), fuertemente regular no Gevrey, q-Gevrey; construccion desde una Borel con singularidades dadas. | 4 |
| 4c | `growth.py`: ajuste en la cola de log abs(a_n), test de cocientes, (abs(a_n)/M_n)^(1/n) para M dado (Roumieu acotado / Beurling a 0), informe con intervalos. | 3 |
| 4d | `algebraic.py`, raiz simple: Hensel/Newton sobre series formales con coeficientes exactos. | 3 |
| 4e | Tests 1-3 del BRIEF: Euler (Gevrey-1, polo en -1, direccion pi), algebraica convergente (alpha ~ 0), raiz simple con f Gevrey-1 (alpha ~ 1). | 2 |
| 4f | `borel.py`: Borel de orden k con normalizacion documentada y citada, Pade para singularidades, direcciones y radio, Laplace numerico de vuelta. | 4-5 |
| 4g | Raices multiples: poligono de Newton, ramificacion z = t^r, Puiseux; test 4. | 4-6 (3 con Sage) |
| 4h | `viz.py` y `doc.py lab demo` con los cuatro casos. | 2 |

Aceptacion: `pytest` en verde; `lab demo` reproduce los cuatro casos con graficos.
`weights.py` del BRIEF = `pesos.py` adaptado: cada condicion con su definicion y
cita `[id:pagina]` cuando el corpus exista. `gamma(M)` sigue siendo de Mariano.

### Fase 5 — Documentacion y configuracion
| Paso | Que | Horas |
|---|---|---|
| 5a | `CLAUDE.md`: reglas de la seccion 2 del BRIEF, responder en espanol, no editar `lecturas/` ni `sesiones/`, tests antes de commit, commits pequenos, ofrecer `referee` ante afirmaciones matematicas, y las tres reglas de `ia/reglas.md`. | 1 |
| 5b | `README.md` de uso en una pagina; `instalar.py` con OpenAI; coste aproximado por consulta documentado; quitar lo caducado. | 1,5 |
| 5c | `metricas` sobre ciclos de 20 h, no dias naturales. | 1 |

## Totales

| | Horas agente | Horas Mariano |
|---|---|---|
| Fase 1 | 10 | 1 (comprobar 5 citas) + reunir PDFs |
| Fase 2 | 3,5 | 0 extra (es su lectura) |
| Fase 3 | 3 | 0,5 |
| Fase 4 | 25-28 | 1 (revisar normalizaciones de Borel y de M con el paper) |
| Fase 5 | 3,5 | 0,5 |
| **Total** | **45-48** | **~3 + los PDFs** |

Orden temporal: 1 -> 2 -> 3 -> 4a-4e -> 5 -> 4f -> 4g. La fase 1 se puede
entregar en dos dias desde que existan los PDFs. Las fases 4f y 4g esperan a que
haya una conjetura que las necesite: construirlas antes es el "no optimizar la
arquitectura antes de que `ask` funcione" del BRIEF 7.

## Lo que NO cambia

`doc.py sesion / sellar / preguntar / ataque / cierre`, la puerta por fases, el
sellado en git, `drill/` + Anki, `registro/lagunas.md`, el contexto vivo. Es lo
que ya devuelve horas; el BRIEF se construye alrededor, no encima.

## Registro de avance

| Fecha | Fase | Hecho | Queda |
|---|---|---|---|
| 2026-09-16 | 0 | Auditoria y plan | Respuestas a las 6 preguntas; aprobacion |
