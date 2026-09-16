# ESTADO_SISTEMA — auditoria de Fase 0 (2026-09-16)

Sin cambios en el repo. Todo lo de abajo esta comprobado ejecutandolo, no leido
de memoria. Rutas relativas a la raiz del repo.

## 1. Objetivo en una linea

Disciplina de estudio por fases con la IA como motor que se apaga solo: intento a
ciegas sellado en git antes de cada consulta, registro de cada llamada, y drill,
lagunas y conjeturas que salen del propio trabajo. **No es** lo que describe el
BRIEF (corpus + indice + referee + laboratorio): de eso no hay nada construido.

## 2. Estructura

| Carpeta / fichero | Que es |
|---|---|
| `doc.py` | Unico punto de entrada; 16 subcomandos (`sesion`, `sellar`, `preguntar`, `ataque`, `cierre`, `lagunas`, `lab`, `diagnostico`, `reunion`, `metricas`, `anki`, `estado`, `ahora`...). |
| `nucleo/` | El sistema: `estado.py` (fase derivada de git), `motor.py` (puerta + log + API), `comandos.py`, `prompts.py`, `config.py`. ~1.500 lineas, Python puro. |
| `contexto/` | Contexto vivo que se pega a TODO system prompt: `estado.md` (donde esta) y `directores.md` (lo que dicen J y A; vacio aun). |
| `corpus/` | Tres `.md`: lista de 8 papers del nucleo con casillas (`orden.md`), plan de 8 semanas de base (`base.md`), items del diagnostico. **Cero PDFs.** |
| `sesiones/` | Un fichero por sesion (fases 0-4) mas dos plantillas (paper / libro). Hay 1 diagnostico y 1 sesion real en curso. |
| `registro/` | `errores.md` (taxonomia Q C S M A F E P), `lagunas.md` (8 pendientes), `conjeturas.md`, `llamadas.jsonl` (23 llamadas). |
| `drill/` | Tarjetas pendientes de exportar a Anki y registro de exportadas. Anki+FSRS hace el repaso. |
| `lab/` | `pesos.py`: sucesiones peso en escala log con mpmath. `conj/`: un script por conjetura (vacio). |
| `ia/reglas.md` | Las tres reglas del motor, para humanos. |
| `reuniones/`, `produccion/notas/` | Notas crudas de reuniones (solo plantilla) y salidas redactadas (1 pre-read para directores). |
| `instalar.py`, `.env.ejemplo`, `README.md` | Instalacion, clave de API fuera de git, manual de uso. |

Sin `CLAUDE.md`, sin `tests/`, sin notebooks, sin `requirements.txt`.

## 3. Corpus

- PDFs: **0**. Titulos previstos (en `corpus/orden.md`): Thilliez 2003 y 2010, Balser, Lastra-Malek-Sanz 2015, Jimenez-Garrido-Sanz-Schindl 2019, Rainer-Schindl 2014, Braun-Meise-Taylor 1990, Carrillo-Mozo 2018. Ninguno ingerido.
- Extraccion, texto por pagina, chunks: no existen. `pymupdf` esta instalado pero no se usa.
- Formulas: no hay extraccion que evaluar. El unico texto matematico del repo son las tarjetas y `pesos.py`, en texto plano/Unicode. Tres muestras tal cual:
  1. `|f^(n)(a)| ≤ n! M_R/R^n`
  2. `sum_{q>=p} M_q / ((q+1) M_{q+1})  <=  A * M_p / M_{p+1}` (forma de Thilliez 2003, en `pesos.py`)
  3. `L[t^n](s)=n!/s^(n+1), para Re(s)>0`

## 4. Indice y consulta

- Embeddings, almacen, BM25: **no hay.** Ninguna libreria de indexacion instalada (`chromadb`, `lancedb`, `sqlite_vec`, `rank_bm25`, `sentence_transformers`: ausentes).
- Consulta actual: `doc.py preguntar`, REPL sin recuperacion. El modelo solo ve lo que se le pega (`/pegar` o pegado de varias lineas) mas el contexto vivo.
- Citas: la regla 1 del prompt le prohibe afirmar nada del campo sin fragmento pegado y le obliga a marcar `[SIN VERIFICAR]`. No hay citas `[id:pagina]` porque no hay corpus. Para textos clasicos (sesiones `base-*`) rige la regla 2 y no exige fragmento.
- Ejemplo real: **no reproducible.** Las conversaciones de fase 2 no se guardan; `llamadas.jsonl` registra solo hora, comando, fase, modelo y tokens. Es un hueco frente al principio 4 del BRIEF (registro).

## 5. Notas de lectura

- Formato: un `.md` por sesion con frontmatter de metricas (`min_f1`, `min_f3`, `coincidencia_estructural`, `llamadas_f2`, `conjeturas`) que rellena `cierre`, y secciones Fase 0-4. Dos plantillas: paper y libro (base).
- Cuantas: 1 diagnostico sellado y calibrado (media 0,29/3); 1 sesion real (`base-conway-iv`, en fase 2). Un pre-read para directores, borrador.
- Indexadas: no. No existe la nota por paper del BRIEF (4.3); la unidad actual es el dia, no el paper.

## 6. Computo

- `lab/pesos.py` (mpmath, `dps=40`, todo en `logM[p]`): clase `SucesionPeso` con (lc), constantes empiricas de (mg), (dc) y (gamma_1) forma Thilliez, `omega_M`, `h_M`; catalogo de 8 sucesiones (Gevrey, Gevrey-log, q-Gevrey, cocientes lentos/potencia); `panel()` en dos N para ver divergencia lenta; `refutar()` (barrido de contraejemplos); `casi_creciente()`. Ejecuta: el panel del catalogo sale en segundos. El indice `gamma(M)` es un TODO deliberado: se implementa con el paper delante, no de memoria.
- `doc.py lab "spec"`: la IA escribe un script contra `pesos.py`; el usuario lo ejecuta.
- Frente al BRIEF 4.4: `weights.py` existe de facto (`pesos.py`); `series.py`, `algebraic.py`, `growth.py`, `borel.py`, `viz.py`: **no existen**.
- Dependencias instaladas: Python 3.10, mpmath, sympy, numpy, scipy, matplotlib, pymupdf, requests, openai, anthropic, yaml. Falta `pytest`.
- Tests que pasan: **ninguno, porque no hay tests.** Ni de `pesos.py` ni del nucleo.

## 7. Prompts y plantillas

Todos en `nucleo/prompts.py`, en espanol sin acentos, con un `BASE` comun (quien es, tema, 4 reglas: no sabes del campo / clasico si / las matematicas las escribe el / brevedad) y modos:

- `FASE2` + `P_NOTACION` / `P_LEMA` / `P_PASO`: tres usos permitidos, `[!]` en todo lo que no este en el fragmento. `NOTA_BASE` se anade en sesiones de libro.
- `CIERRE`: devuelve JSON con diff estructural, coincidencia 0-3, errores tipificados, 5 tarjetas, lagunas y conjeturas. Compara estructuras, no valida matematicas.
- `LAGUNA`: enunciado minimo, referencia, intuicion, trampa, 2 tarjetas, ejercicio sin solucion.
- `DIAGNOSTICO`: resumen, 15-25 tarjetas, lagunas, orden del corpus, pre-read de una pagina.
- `LAB`: solo codigo Python contra `pesos.py`, con caso cerrado; prohibido implementar `gamma(M)`.
- `DESTILAR` / `PREPARAR`: notas de reunion a lineas de `directores.md`; pre-read con sesiones, errores y conjeturas.
- Plantillas: `sesiones/PLANTILLA.md`, `sesiones/PLANTILLA-base.md`, `reuniones/PLANTILLA.md`.

No existen `prompts/referee.md` ni `prompts/redactor.md` (BRIEF 4.5).

## 8. Integraciones

- Proveedor: OpenAI Responses API (`gpt-6-astra` por defecto) o Anthropic (`claude-sonnet-5`); se elige por la clave presente en `.env`. `DOC_SIMULAR=1` para probar sin red.
- Puerta: `motor.llamar()` es el unico camino a la API; se niega en fases 1 y 3; `--forzar` queda registrado como violacion.
- MCPs, skills, hooks, `CLAUDE.md`: ninguno.
- Donde corre: portatil Windows 11, Python 3.10, git. Repo privado en GitHub como copia (`git push` manual; los sellados no empujan solos).
- Coste hasta hoy: 23 llamadas, 43.362 tokens de entrada, 5.022 de salida.

## 9. Roto, a medias, pendiente

| Item | Estado | Horas |
|---|---|---|
| Conversaciones de fase 2 no se registran (solo tokens) | hueco | 1 |
| Sin tests: ni `pesos.py` ni `estado.py` | pendiente | 2-3 |
| `metricas` agrupa por dia natural; `estado.py` ya usa ventana de 20 h. Una sesion que cruce medianoche se parte en dos dias en las metricas | inconsistencia | 1 |
| `instalar.py` solo instala `anthropic` y apunta a platform.claude.com; la via OpenAI funciona pero a mano | a medias | 0,5 |
| `README.md` conserva la instruccion de sacar la carpeta de OneDrive (ya hecho) | desactualizado | 0,2 |
| `gamma(M)` en `pesos.py` | TODO deliberado: lo hace el usuario con Thilliez 2003 delante | 0 (agente) |
| `contexto/directores.md` vacio | esperado: sin reunion aun | 0 |
| Corpus: 0 PDFs | **bloqueado** por el usuario | — |

## 10. Para usarlo manana

Como sistema de sesiones **ya se usa hoy** (hay una sesion en fase 2). Para lo que pide el BRIEF, en este orden:

1. PDFs en una carpeta y el documento del proyecto de tesis. Sin esto no hay nada que indexar.
2. `ingest` con PyMuPDF (ya instalado) + `bib.yaml` con `pendiente_verificar` por defecto.
3. Indice hibrido minimo y `ask` con cita `[id:pagina]`, pasando por `motor.llamar()` para respetar las fases.
4. Registro de conversaciones (hueco del punto 9).
5. Tests de `pesos.py`, y despues el resto del laboratorio.

## Decision por componente

| Componente | Decision | Por que |
|---|---|---|
| `doc.py` + `nucleo/` (fases, puerta, sellado, contexto vivo) | **Conservar** | Funciona, es la pieza que el BRIEF no tiene y que da valor. Faltan tests: faciles de anadir a `estado.py` (logica pura sobre listas de commits). |
| `prompts.py`, plantillas, `registro/`, `drill/` | **Conservar** | Cumplen los principios 2 y 3 del BRIEF tal cual. `registro/` hace de `log/`. |
| `motor.llamar()` | **Adaptar** | Debe ser tambien la puerta de `ask` y `referee`, y guardar la conversacion. |
| `lab/pesos.py` | **Adaptar** | Es el `weights.py` del BRIEF con otro nombre; le faltan tests y las condiciones que aparezcan en el corpus con su cita. |
| Corpus / indice / `ask` / notas por paper / referee / `series`, `growth`, `algebraic`, `borel`, `viz` | **Construir** | No hay nada que reconstruir: no existe. |
| Nada | Reconstruir | La extraccion no destroza formulas porque no hay extraccion; el codigo es reproducible. |

Antes de construir: `git tag pre-brief` en `master`. Es gratis y cumple la regla del BRIEF aunque no se reconstruya nada.
