# Uso en una pagina

Todo pasa por `doc.py`. El motor (la IA) se apaga solo en las fases 1 y 3; `buscar` no
usa motor y vale siempre. Si dudas: `python doc.py ahora`.

## Una sesion (3 h)

```
python doc.py sesion base-conway-iv     abre el fichero de hoy (base-* = con libro). Motor OFF
    fase 0 (10 min) que se ya; fase 1 (25 min) enunciado solo, prediccion por escrito
python doc.py sellar 1                  commit. Motor ON
python doc.py preguntar                 fase 2 (60 min). REPL: /notacion /lema /paso; pega varias
                                        lineas de golpe y quedan como fragmento
python doc.py ataque                    commit. Motor OFF
    fase 3 (45 min): ejercicios (base) / extension, contraejemplo, Beurling (paper)
python doc.py sellar 3                  commit. Motor ON
python doc.py cierre                    diff de tu fase 1, errores, 5 tarjetas, lagunas, metricas
```

## Corpus: PDFs con citas por pagina

```
python doc.py ingest                    ingiere lo nuevo de corpus/raw/: tex de arXiv > Marker > PyMuPDF
python doc.py ingest X.pdf --fuente proyecto    documento propio, sin metadatos de red
python doc.py ingest --arxiv ID [nombre.pdf] --id ID --etiquetas citado --factorial fuera
                                        baja el PDF de arXiv a corpus/raw/ y lo ingiere (tex incluido)
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
`dentro` si |f^(p)| <= C A^p M_p (JGSS 2019 sectorial, 2022, JGCSS 2023-2026), `no_aplica`
sin sucesion peso (Balser, BMT, Carrillo-Mozo), `pendiente` sin comprobar (los que definen la
clase solo por expansion asintotica: JGSS 2017, JGCSS 2026 stability). `ask` lo pone en la
cabecera DOCUMENTOS y en la linea "Notacion: la de [doc], factorial dentro/fuera"; no iguala
M_p entre documentos con convencion distinta. `etiquetas` y `factorial` sobreviven a
`--rehacer`. Toda cita de capa tex lleva `| texto: arXiv vN` (el texto es el de arXiv; la
pagina, la del PDF), sin excepcion. `corpus/meta/glosario.yaml`: ES -> EN para que preguntar en espanol alcance los
papers en ingles. `corpus/raw/` y `corpus/text/` son datos locales (fuera de git).

## Leer un paper con protocolo

```
python doc.py nota new ID               lecturas/ID.md desde plantilla. La escribes tu
python doc.py nota quiz ID              8-12 preguntas de examen con cita, sin respuestas
python doc.py nota check ID             agujeros en tu "## Mi explicacion", citando el texto
```

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
python doc.py lab "especificacion"      la IA escribe el script contra lab/pesos.py; mpmath juzga
python doc.py lab demo                  los 4 casos del BRIEF (Euler+Borel, Catalan, raiz simple, raiz multiple) con graficos en lab/salidas/
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
| `registro/llamadas.jsonl` | toda llamada a la API: comando, fase, modelo, tokens (tambien cacheados) |
| `contexto/estado.md`, `contexto/directores.md` | lo que la IA sabe de ti; lo mantienes tu |
| `nucleo/config.py` | precios en USD, tipo de cambio, modelo y esfuerzo por comando, presupuesto |

Coste: `metricas` lo muestra por comando; el tope es 20 EUR/mes. Copia de seguridad:
`git push` a mano; los sellados no empujan solos.
