# Uso en una pagina

(El "como" de cada tarea, paso a paso: `docs/GUIA.md`.)

Todo pasa por `doc.py`. El motor (la IA) se apaga solo en las fases 1 y 3; `buscar` no
usa motor y vale siempre. Si dudas: `python doc.py ahora`.

## Una sesion (3 h)

```
python doc.py sesion thilliez-2003      abre el fichero de hoy (id de bib.yaml; base-* = con libro). Motor OFF
    fase 0 (10 min) que se ya; fase 1 (25 min) enunciado solo, prediccion por escrito
python doc.py sellar 1                  commit. Motor ON
python doc.py preguntar                 fase 2 (60 min). REPL con el paper de la sesion en el corpus:
                                        /ver 2.1.3, /ver p8, /doc ID, /sigue, /notacion /lema /paso,
                                        /laguna, /queja; pega varias lineas y se localizan en el indice
python doc.py ataque                    commit. Motor OFF. Elige el resultado (el mas preguntado hoy, o azar)
                                        y lo escribe en la sesion; --resultado R2 lo cambia
    fase 3 (45 min): ejercicios (base) / comprension (paper, hasta leer el nucleo) /
    extension (nucleo leido). `ataque` imprime la guia del modo; --modo la fuerza
python doc.py sellar 3                  commit. Motor ON
python doc.py cierre                    diff de tu fase 1, errores, 5 tarjetas, lagunas, metricas,
                                        y el intento (nivel, minutos) en el bloque R de la nota
python doc.py pausar / reanudar         para y arranca el reloj sin cambiar de fase ni motor
```

Una sesion sin cerrar caduca a las 20 h de su ultima marca; pausada, no. `min_f1` y `min_f3`
descuentan las pausas. `estado` y `ahora` avisan si lleva mas de 72 h pausada: reanuda y
termina, o cierra y abre otra. Los sellados hacen `git pull --ff-only` antes y `git push`
despues cuando hay red (avisan si no; `DOC_SIN_RED=1` lo apaga): la fase viaja entre maquinas.

Fase base saltada (2026-09-22): las sesiones son de papers, en el orden de `corpus/orden.md`
(`ahora` dice cual toca y su id, y lista aparte los papers con sesiones que aun no has marcado en
`orden.md`: las casillas las cambias tu, con `python doc.py leido ID`). Un hueco de grado/master no para la sesion: una linea en
`registro/lagunas.md` con `/laguna ...` dentro de `preguntar` o en la linea `Lagunas` de la
sesion (la recoge `cierre`), y se estudia aparte: viernes `python doc.py lagunas`; si reaparece
tres veces, `[ESTRUCTURAL]` y una sesion de libro `python doc.py sesion base-ETIQUETA` con la
semana de `corpus/base.md` que la cubra.

## preguntar: como lee el paper contigo (desde 2026-10-13)

`preguntar` sabe que paper estas leyendo: el id de `bib.yaml` que es prefijo de la etiqueta
de la sesion (`thilliez-2003-section-2` -> `thilliez-2003`; `/doc ID` lo cambia,
`--sin-corpus` lo apaga). En cada pregunta manda al modelo los fragmentos del indice mas
afines (hasta ~2500 tokens, solo de ese paper, con su cita `[id:pNN, Lema 2.1.1 | texto:
arXiv v1]`) y las definiciones a las que remiten por `\ref`. No hace falta pegar: `/ver
2.1.3` trae el enunciado con ese numero impreso y `/ver p8` la pagina 8, con texto limpio
de la capa tex. Pegar sigue valiendo para fijar EXACTAMENTE el paso que miras (version de
revista, formulas): el pegado se localiza en el indice (palabras pegadas del PDF incluidas)
y la respuesta lo cita por pagina; si no se localiza, lo dice y lo envia tal cual.

La respuesta sale en texto plano para consola (`nucleo/consola.py`): formulas en `$...$` con
simbolos (≤ ∞ ℝ ∫), bloques sangrados, sin `##` ni `**`, lineas de 90 columnas. La cruda
queda en `registro/consultas/`. Cada afirmacion lleva su origen: cita del corpus, rotulo del
fragmento pegado, o `[!]` con el NOMBRE del resultado estandar (nunca un DOI, ano o titulo
de memoria); lo que no esta en ninguna parte va en una linea `FALTA:`; al final, `USADOS:`.
Debajo se imprimen las citas consultadas y `[segundos | entrada (cache) | salida
(razonamiento) | tope]`. Tope de salida de `preguntar`: 4000 tokens (incluye el razonamiento;
esfuerzo `low`, en `nucleo/config.py`). Si se corta, lo avisa; si para limpio en una linea `SIGUE:`
(tope de 40 lineas del prompt), lo dice; en los dos casos `/sigue` continua con los mismos fragmentos. El historial se reenvia entero, pero los fragmentos del corpus de turnos pasados no:
cuando la entrada crezca (lo ves en la linea de tokens), `/nuevo`.

## Corpus: PDFs con citas por pagina

```
python doc.py ingest                    ingiere lo nuevo de corpus/raw/: tex de arXiv > Marker > PyMuPDF
python doc.py ingest X.pdf --fuente proyecto    documento propio, sin metadatos de red
python doc.py ingest --arxiv ID [nombre.pdf] --id ID --etiquetas citado --factorial fuera
                                        baja el PDF de arXiv a corpus/raw/ y lo ingiere (tex incluido)
python doc.py ingest --arxiv ID corpus/raw/revista.pdf --id ID
                                        PDF de revista ya en raw (sin sello): sus paginas + el tex de arXiv
python doc.py ingest --solo-meta [ids]  refresca metadatos (arXiv, Crossref) sin reextraer
python doc.py ingest --remapear [ids]   rehace unidades y paginas desde el tex guardado, sin red
python doc.py indexar                   fragmenta y embebe lo nuevo (incremental, centimos)
python doc.py buscar "..."              fragmentos con [id:pagina]. SIN modelo: vale en toda fase
python doc.py ask "..."                 sintesis con cita tras cada afirmacion. Motor ON.
                                        --doc ID  --con-propios (proyecto y notas)  -k N
```

`corpus/meta/bib.yaml`: metadatos. `verificado` solo si vienen de arXiv/Crossref y el
titulo esta en el PDF; si no, `pendiente_verificar`. Tu pones `etiquetas` y los DOI que
falten. `factorial` dice donde va p! en la clase del documento: `fuera` si
|f^(p)| <= C A^p p! M_p (Thilliez, Lastra-Malek-Sanz, Sanz, Rainer-Schindl, tesis, proyecto),
`dentro` si |f^(p)| <= C A^p M_p (JGSS 2019 sectorial, 2022, JGCSS 2023, 2024, 2026 stieltjes
y surjectivity), `no_aplica` sin sucesion peso (Balser, BMT, Carrillo-Mozo), `pendiente` sin
comprobar. Regla de Mariano para los que definen la clase solo por expansion asintotica:
analitica <=> M = 1 es `fuera`, analitica <=> M_p = p! es `dentro` (JGSS 2017 y JGCSS 2026
stability quedaron `fuera`). `ask` lo pone en la
cabecera DOCUMENTOS y en la linea "Notacion: la de [doc], factorial dentro/fuera"; no iguala
M_p entre documentos con convencion distinta. `etiquetas` y `factorial` sobreviven a
`--rehacer`. Toda cita de capa tex lleva `| texto: arXiv vN` (el texto es el de arXiv; la
pagina, la del PDF), sin excepcion. `corpus/meta/glosario.yaml`: ES -> EN para que preguntar en espanol alcance los
papers en ingles. `corpus/raw/` y `corpus/text/` son datos locales (fuera de git).

## Leer un paper con protocolo

```
python doc.py nota new ID               lecturas/ID.md desde plantilla, con el Mapa vacio. La escribes tu
python doc.py nota add ID "R2 — Teorema 2.3"   anade el bloque del resultado (ocho campos) y su linea en el Mapa
python doc.py nota quiz ID --resultado R2      8-12 preguntas de examen sobre ese resultado, con cita
python doc.py nota check ID --resultado R2     agujeros en la "### Reconstruccion" de ese bloque (--desarrollo: el Desarrollo)
python doc.py nota estado ID            por bloque: campos escritos, intentos de reconstruccion, ultimo check
```

`lecturas/ID.md` tiene un bloque `## Rn — titulo` por resultado, con los ocho campos de
`lecturas/PLANTILLA-resultado.md` (Enunciado, Hipotesis y por que, Lema clave, Que se rompe
sin el, Desarrollo (fase 2, con el paper), Reconstruccion (fase 3, a ciegas, con `Intentos:`),
Derivaciones y reformulaciones, Donde se usa; edita esa plantilla si quieres otros),
y una sola vez las secciones de paper: Mapa, Sintesis, Transferencia, Abierto, Dudas,
Dependencias. `quiz` y `check` con `--resultado` traen primero el fragmento del numero impreso
del titulo ("Teorema 2.3" -> el teorema 2.3 del indice) y luego los afines. Sin `--resultado`,
`check` elige el unico bloque con explicacion escrita; `quiz` interroga sobre todo el paper.

## Verificar lo que escribes

```
python doc.py referee ARCHIVO [--seccion "Fase 3"] [--contexto] [--proveedor anthropic]
                                        objeciones numeradas: donde, que falla, codigo, gravedad.
                                        Sin valoracion global. Fila en registro/verificaciones.md
python doc.py redactar ARCHIVO          pule forma sin inventar; marca [VERIFICAR]
```

## Fuera de sesion

```
python doc.py lagunas                   viernes, 45 min: el lote de huecos de grado/master
python doc.py leido ID [--frio]         marca el paper en corpus/orden.md ([~] leido; [x] reconstruido en frio)
python doc.py control                   pasada fija de preguntas por ask (docs/control/), tras cambiar prompts
python doc.py exportar / importar ZIP   corpus/text e indice/ a otra maquina (el .env, a mano)
python -m web                           la mini web (docs/WEB.md): panel, buscar, ask, preguntar, notas, transcripciones, guia
python doc.py transcribir FICHERO       lo manuscrito (PDF o foto) a markdown con LaTeX; queda sin_revisar (docs/GUIA.md)
        [--tipo curso|paper|duda] [--titulo T] [--paginas 1-3,5] [--motor modelo|marker] [--calidad normal]
        (calidad alta por defecto: con letra manuscrita el modelo barato falla en las formulas; ~9 cent por hoja doble)
python doc.py transcribir --lista       que hay transcrito y que sigue sin revisar
python doc.py transcribir --revisado NOMBRE   la has comparado con el original: entra en el indice (tras indexar)
python doc.py transcribir --tex NOMBRE  rehace transcripciones/NOMBRE.tex desde el .md de ahora (--pisar si lo editaste a mano)
python doc.py transcribir --figuras NOMBRE   en una transcripcion ya hecha: localiza sus [FIGURA: ...] y las recorta del original
python doc.py lab "especificacion"      la IA escribe el script contra lab/pesos.py; mpmath juzga
python doc.py lab demo                  los 4 casos del BRIEF (Euler+Borel, Catalan, raiz simple, raiz multiple) con graficos en lab/salidas/
```

`lab/pesos.py` lleva la convencion del factorial como parametro: `SucesionPeso(logM, factorial="fuera"|"dentro")`,
`gevrey(alpha, factorial=...)`, y `M.en("fuera")` convierte (`M_dentro[p] = p! M_fuera[p]`). Todo indice
(`indice_omega`, y `gamma(M)` cuando lo escribas) se calcula siempre sobre la version fuera, la de Thilliez;
la misma clase Gevrey escrita en las dos convenciones da el mismo omega (test). Mira `factorial` en
`bib.yaml` antes de meter la M de un paper.

```
python doc.py anki                      exporta tarjetas (las [VERIFICAR CON PAPER] se quedan)
python doc.py metricas                  fases, violaciones, y coste del mes por comando en EUR
python doc.py reunion [--destilar|--preparar]   notas de reunion, directores.md, pre-read
```

## Donde queda cada cosa

| Ruta | Que |
|---|---|
| `sesiones/`, `lecturas/` | tu trabajo: sesiones por dia, notas por paper |
| `registro/consultas/` | cada `ask` y cada turno de `preguntar`, con fragmentos usados y no usados |
| `registro/verificaciones.md`, `registro/referee/` | lo que se dio por verificado, con metodo |
| `registro/quejas.md` | tus `/queja` de preguntar, con fecha y turno; se revisan en lote |
| `transcripciones/` | lo manuscrito pasado a limpio; `estado: sin_revisar` hasta que lo marcas. Cada `.md` lleva al lado su `.tex` exportado (la fuente es el `.md`); las figuras recortadas, en `transcripciones/figuras/`. Los originales, en `transcripciones/originales/` (fuera de git) |
| `registro/llamadas.jsonl` | toda llamada a la API: comando, fase, modelo, tokens (tambien cacheados) |
| `contexto/estado.md`, `contexto/directores.md` | lo que la IA sabe de ti; lo mantienes tu |
| `nucleo/config.py` | precios en USD, tipo de cambio, modelo y esfuerzo por comando, presupuesto |

Coste: `metricas` lo muestra por comando; el tope es 20 EUR/mes. Copia de seguridad: los
sellados hacen push cuando hay red (`DOC_SIN_RED=1` lo apaga); entre sellados, `git push` a mano.
