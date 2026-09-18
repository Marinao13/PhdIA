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

## Tarea obligatoria antes de publicar el repo

Los commits `fb81fa2` (19 PDFs) y `4315e8c` (texto extraido) llevan datos locales
que ya no se versionan (`corpus/raw/`, `corpus/text/`). Antes de hacer publico el
repositorio hay que reescribir la historia para sacarlos (`git filter-repo` sobre
esas rutas), forzar el push y avisar a cualquier clon. No se hace ahora: la
historia sellada es la prueba fechada del trabajo y solo se toca una vez, con
copia (`git bundle`) previa. Decision de Mariano, 2026-09-16.

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
| 2026-09-16 | 2 | `lecturas/PLANTILLA.md`; `nota new` (solo metadatos verificados), `nota quiz` (12 preguntas con cita sobre Thilliez 2003), `nota check` (objeciones tipificadas + fila en `registro/verificaciones.md`) | De Mariano: escribir `## Mi explicacion` y lanzar el check. Agente: Fase 3 referee |
| 2026-09-16 | 3 | `REFEREE` y `REDACTOR`; `doc.py referee` (contexto limpio, `--seccion`, `--proveedor`, `--contexto`) y `redactar`; `registro/verificaciones.md`. Probado con 4 errores plantados: los pesca y gradua bien (`docs/ejemplos/`) | Agente: 5a CLAUDE.md y README, 5c metricas por ciclos, luego laboratorio 4b-4e |
| 2026-09-16 | 1 (afinado), 5a | Precios USD + cacheada y EUR fijo; modelo y esfuerzo por comando; `proyecto.pdf` como fuente `proyecto`; Crossref por titulo (Thilliez 2003 y 3 JMAA resueltos); mapa de paginas monotono y `--remapear`; `ask` por papers con `
ef` seguidas y cupo al paper nombrado; tres pasadas de aceptacion en `docs/aceptacion-fase1.md`; `docs/USO.md`, `CLAUDE.md`, `.claude/commands/`. Incidente: el `rm --cached` + merge borro `corpus/raw` y `corpus/text` en `master`; restaurados del worktree, hashes verificados | De Mariano: veredictos de aceptacion, modelo barato, tipo de cambio, ids de 3 pendientes, JGSS 2019, renombrado de ids, README. Agente: Marker 1.x reextrayendo 7 docs; luego 5c y laboratorio 4b-4e |
| 2026-09-16 | 1 (cierre) | Terra en `ask` y el resto, Astra en `referee`/`preguntar`; 0,87 EUR/USD; 20/20 verificados (Balser, BMT y tesis por DOI/handle con titulo coincidente; Thilliez 2003 por Crossref); ano de volumen impreso; 11 ids renombrados por la regla de Mariano (`corpus/meta/renombrados.yaml`); README enlaza `docs/USO.md`; cuarta pasada de aceptacion con Terra | De Mariano: veredictos de `docs/aceptacion-fase1.md`; PDF de JGSS 2019. Agente: Marker termina tesis y Balser -> copiar a master y reindexar; 5c; laboratorio |
| 2026-09-16 | 1 (corpus) | Dos JGSS 2019 ingeridos por tex y verificados (JMAA 469; Results Math 74); (d) regenerada; `metricas` por ciclos; `instalar.py` con OpenAI; residuo de renombrado en master corregido | De Mariano: veredictos de las seis. Agente: Balser (Marker), bib restaurada e identificadores, sincronizar master; laboratorio 4b-4e |
| 2026-09-16 | 1 (corpus, cierre) | Marker termino los 7 (Balser 2.361 unidades). Incidente: una ingesta larga escribio una foto vieja de `bib.yaml` y el commit `08088ea` perdio renombrados, identificadores y anos impresos; reparado (refresco, 3 identificadores, renombrado en bib, claves == directorios), `ingerir` relee antes de escribir e `indexar` avisa de directorios sin entrada. 22 docs: 15 tex, 7 marker; 21 verificados | De Mariano: veredictos. Agente: laboratorio 4b-4e |
| 2026-09-17 | 1 (ask v2) | Cuatro correcciones del primer veredicto: (1) 'no esta en el corpus' solo tras segunda busqueda (BUSCAR) restringida al documento nombrado, sin tope para el; (2) fuente primaria obligatoria (apellido solo activa todos sus papers), segunda pasada forzada si no se uso, notacion atribuida; (3) citas con pagina + entorno y numero impreso (61% resuelto) o etiqueta LaTeX marcada; (4) referencias \cite de los fragmentos usados resueltas con el .bbl y listadas si no estan en el corpus. Hoja regenerada | De Mariano: segunda ronda de veredictos. Agente: laboratorio 4b-4e |
| 2026-09-17 | 1 (ask v2) | Ronda 1 de Mariano conservada en `docs/aceptacion-fase1-veredicto-1.md`; sin macros privadas del paper; referencias tambien del parrafo de atribucion (la Prop. 4.18 de JGS 2016 se apoya en Thilliez 2003 [en corpus] y Lastra-Sanz 2010 Ann. Inst. Fourier [fuera]: primera candidata a bib.yaml) | De Mariano: ronda 2 de veredictos; PDF o arXiv de Lastra-Sanz 2010. Agente: laboratorio 4b-4e |
| 2026-09-17 | 4b-4e | `lab/series.py` (series truncadas exactas o mpf; Gevrey, fuertemente regular no Gevrey, q-Gevrey con semilla; Euler y Catalan exactas; construccion desde la Borel con normalizacion de Balser [balser-2000:p97]); `lab/growth.py` (ajuste de cola, cocientes, Roumieu/Beurling con pendiente); `lab/algebraic.py` (Hensel/Newton exacto, raiz simple, traza); tests 1-3 del BRIEF en su parte de crecimiento: 47 tests en verde | De Mariano: ronda 2; Lastra-Sanz 2010. Agente: 4h `lab demo`; 4f y 4g esperan una conjetura viva |
| 2026-09-17 | 4h (parcial) | `doc.py lab demo`: casos 1-3 con informe de crecimiento y grafico en `lab/salidas/`; el 4 solo comprueba que Hensel lo rechaza. Borel del caso 1 y raices multiples esperan a 4f/4g | De Mariano: ronda 2 de veredictos; Lastra-Sanz 2010. Agente: nada hasta la ronda 2 (BRIEF 7: no construir de mas) |
| 2026-09-18 | 1 (ACEPTADA) | Ronda 2 de Mariano: 5 correctas, 1 incorrecta en un detalle; conservada en `docs/aceptacion-fase1-veredicto-2.md`. Flecos -> `ask` v2.1: (1) la formula de LMS 2015 dice m_{p+1}/m_p en arXiv v1 y en la revista (sin discrepancia); toda cita de capa tex indica `texto: arXiv vN`; (2) `\ref`/`\eqref` resueltos a lo impreso (items de enumerate, `\tag`, entornos numerados) y regla 9 para los que quedan; mapa de paginas con bolsa de palabras: paginas estimadas 15% -> 1%, numeros resueltos 61% -> 86%; (3) tabla sin duplicados | Agente: laboratorio 4f (borel.py) y 4g (poligono de Newton) |
| 2026-09-18 | 4f | `lab/borel.py`: Borel de orden k [balser-2000:p97], Pade minimo que detecta racionalidad exacta (comparacion relativa), votacion de estabilidad entre ordenes para el caso generico, dobletes filtrados, direcciones singulares y radio, Laplace numerica de vuelta [balser-2000:p95]. Test 1 completo: polo en -1, direccion pi, suma de Borel = funcion de Euler a 1e-10. `lab demo` incluye la parte de Borel. 54 tests | Agente: 4g poligono de Newton, ramificacion, test 4 |
| 2026-09-18 | 4g, 4h | `lab/newton.py`: poligono de Newton (envolvente inferior), ecuacion caracteristica por arista, ramificacion z = t^r, y = t^a (c + y_1) y Hensel sobre la rama; ramas de Puiseux como Series en t con traza; `comprobar()` verifica P(t^r, y(t)) = 0. Test 4 del BRIEF: y^2 = z(1 + z Euler) ramifica con r = 2, dos ramas exactas al orden 24; y^3 = z con r = 3. `lab demo` reproduce los cuatro casos. 57 tests. **Laboratorio 4.4 entregado (polisectores: extension posterior).** | De Mariano: direccion (polisectores / usar el sistema / otra cosa), `## Mi explicacion` + `nota check` (Fase 2), Lastra-Sanz 2010 opcional. Agente: nada hasta entonces (BRIEF 7) |
