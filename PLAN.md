# PLAN — del sistema de sesiones al sistema del BRIEF (2026-09-16)

Parte de `ESTADO_SISTEMA.md`. Las horas son de construccion del agente; las de
Mariano son solo revision y pruebas, y van aparte porque son las que escasean.
Cada fase termina con tests en verde, commit, push y una linea en el registro de
abajo.

## Decisiones de arquitectura (cerradas el 2026-09-16 con las respuestas de Mariano)

1. **Un solo punto de entrada.** Los comandos del BRIEF (`ingest`, `indexar`,
   `buscar`, `ask`, `nota`, `referee`, `lab demo`) son subcomandos de `doc.py`.
   Motivo: el README ya promete "un unico punto de acceso a la IA" y
   `motor.llamar()` es la unica puerta.
2. **Dos comandos, no uno.** `buscar "..."` es recuperacion pura (BM25 +
   embeddings): devuelve fragmentos con `[id:pagina]`, sin llamada al modelo, en
   todas las fases; equivale a abrir el PDF y buscar. `ask "..."` es sintesis con
   modelo sobre esos fragmentos, por `motor.llamar()`, sujeta a las fases igual
   que `preguntar`. La puerta conserva su sentido y el corpus no queda inutil en
   fases 1 y 3.
3. **Nombres en espanol y sobre lo que ya hay.** `corpus/raw|meta|text` bajo el
   `corpus/` existente; `indice/` para el almacen; `lecturas/{id}.md` para la nota
   por paper (la unidad `sesiones/` sigue siendo el dia); `registro/verificaciones.md`
   hace de `log/verificaciones.md`; `registro/consultas/` guarda cada `ask` con los
   fragmentos usados **y los recuperados no usados**, para auditar el indice y no
   solo la respuesta; los prompts nuevos van a `nucleo/prompts.py`. El BRIEF vive
   en `docs/BRIEF.md`.
4. **Extraccion en tres capas, por prioridad.** (1) Fuente `.tex` de arXiv cuando
   el paper tenga id (`arxiv.org/e-print/<id>`, descargada en el `ingest`):
   formulas exactas, cita `[id:seccion/teorema]`. (2) Si no, Marker en la GPU
   (RTX 4070): markdown con LaTeX, cita `[id:pagina]`. (3) PyMuPDF como fallback
   y para mapear paginas. Cada fichero de `corpus/text/` declara con que capa se
   extrajo. Nougat no.
5. **Indice sin dependencias pesadas.** BM25 con `rank_bm25` + embeddings por API
   (`text-embedding-3-small`, mismo `.env`) en sqlite + numpy. Local en la 4070
   solo si algun dia se quiere independencia del proveedor; no es prioridad.
   Fuentes: papers (`paper`), `corpus/PROYECTO.md` sin extraccion (`proyecto`),
   `lecturas/` y `sesiones/` (`nota`).
6. **Laboratorio en SymPy + `Fraction`/`QQ` + mpmath.** Sin Sage. Si Puiseux lo
   pide mas adelante, WSL + Sage; no antes.
7. **Presupuesto: 20 EUR/mes.** `metricas` muestra el coste acumulado del mes por
   comando; las llamadas de embeddings tambien se registran en `llamadas.jsonl`.
   Tabla de precios editable en `config.py`, con la fecha en que se verifico.
8. **Orden.** Los tests de `estado.py` y `pesos.py` (4a) van antes de `ask` (1c) y
   de `referee` (3b): `motor.llamar()` no se toca sin tests que la cubran.
9. **Antes de la fase 1:** `git tag pre-brief` en `master`.

## Fases

### Fase 0 — Auditoria y plan  · hecha (2026-09-16)
Entrega: `ESTADO_SISTEMA.md`, `PLAN.md`. Las 8 preguntas respondidas; decisiones
cerradas arriba.

### Fase 1 — Corpus + indice + `buscar` + `ask`  · en curso
Corpus: 19 PDFs en `corpus/raw/` (los 8 de `orden.md` primero; los demas, de
Sanz, Jimenez-Garrido, Lastra, Malek, Schindl, Rainer, la tesis de
Jimenez-Garrido 2018). Lista de lectura de los directores: pendiente de la primera
reunion; hasta entonces `orden.md` es la lista. **`corpus/PROYECTO.md` no esta en
el repo: pendiente de Mariano.**

| Paso | Que | Horas agente |
|---|---|---|
| 1a | `corpus/meta/bib.yaml` (id, autores, titulo, ano, venue, DOI, arXiv, etiquetas, `estado: pendiente_verificar`, capa de extraccion). `doc.py ingest <pdf>`: detecta id de arXiv en el PDF, descarga la fuente `.tex` (capa 1) o extrae con Marker (capa 2) / PyMuPDF (capa 3); texto a `corpus/text/{id}/` con paginas; resuelve DOI/arXiv por red para pasar a `verificado`; nunca completa metadatos de memoria. | 4 |
| 1b | Chunking por parrafo/seccion (300-800 tokens) con id, pagina o seccion, tipo si se detecta (definicion / teorema / prueba). BM25 + embeddings en `indice/`. `doc.py indexar` (incremental). `doc.py buscar "..."`: solo recuperacion, todas las fases. | 3 |
| 4a | `pytest`; tests de `estado.py` (7 escenarios de medianoche) y de `pesos.py`. Antes de tocar `motor.llamar()`. | 2,5 |
| 1c | `doc.py ask "pregunta"`: recupera k, responde con `[id:pagina]` tras cada afirmacion, separa "el corpus dice" de "conocimiento general", dice "no esta en el corpus" si no hay evidencia. Por `motor.llamar()`. Guarda en `registro/consultas/` pregunta, fragmentos usados, fragmentos recuperados y no usados, respuesta. | 3 |
| 1d | Registro de conversaciones de `preguntar` (hueco del ESTADO 9). Mismo formato. Coste del mes por comando en `metricas`. | 2 |

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
| 4e | Tests 1-3 del BRIEF, parte de crecimiento: Euler es Gevrey-1, algebraica convergente (alpha ~ 0), raiz simple con f Gevrey-1 (alpha ~ 1). | 2 |
| 4f | `borel.py`: Borel de orden k con normalizacion documentada y citada, Pade para singularidades, direcciones y radio, Laplace numerico de vuelta. Aqui va la parte de Borel del test 1: polo en -1, direccion pi. | 4-5 |
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

Orden temporal: 1a -> 1b -> 4a -> 1c -> 1d -> 2 -> 3 -> 4b-4e -> 5 -> 4f -> 4g.
Los PDFs ya existen: la fase 1 se entrega en dos dias. Las fases 4f y 4g esperan a que
haya una conjetura que las necesite: construirlas antes es el "no optimizar la
arquitectura antes de que `ask` funcione" del BRIEF 7.

## Lo que NO cambia

`doc.py sesion / sellar / preguntar / ataque / cierre`, la puerta por fases, el
sellado en git, `drill/` + Anki, `registro/lagunas.md`, el contexto vivo. Es lo
que ya devuelve horas; el BRIEF se construye alrededor, no encima.

## Registro de avance

| Fecha | Fase | Hecho | Queda |
|---|---|---|---|
| 2026-09-16 | 0 | Auditoria y plan; 8 respuestas; decisiones cerradas; BRIEF a `docs/`; 19 PDFs versionados; tag `pre-brief` | Fase 1: 1a ingest |
| 2026-09-16 | 1a, 1b, 4a | `ingest` en tres capas (12 por tex de arXiv, 7 por PyMuPDF a la espera de Marker/Docker); `bib.yaml` con 19 entradas, 16 verificadas; `indexar` (2.312 fragmentos) y `buscar` con glosario ES->EN; 33 tests en verde | 1c `ask`; 1d registro y coste; reextraer con Marker; `PROYECTO.md`; ids de los 3 pendientes |
| 2026-09-16 | 1c, 1d | `ask` con citas y registro de consultas (usados y no usados); conversaciones de `preguntar` registradas; coste del mes por comando en `metricas` (tabla `config.PRECIOS`, presupuesto 20 EUR) | De Mariano: Docker para Marker, `PROYECTO.md`, precios, 5 preguntas, ids de 3 pendientes, DOI de Thilliez 2003. Agente: Fase 2 |
