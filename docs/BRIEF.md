# BRIEF — Sistema de apoyo al doctorado (handoff para Claude Code)

> **Instrucción de arranque:** lee este documento completo antes de tocar nada. Empieza por la Fase 0 (auditoría). No modifiques el repo hasta terminarla y presentar el plan. Responde y documenta en español.

---

## 1. Contexto

**Quién.** Mariano: matemático (grado en Matemáticas, másteres en Big Data y en Matemáticas), trabaja en el equipo de datos/growth de Fever (Python, SQL/Snowflake, agentes, MCP). Empieza el doctorado en Matemáticas en el IMUVa (Universidad de Valladolid), con directores Javier Sanz Gil y Alberto Rodríguez Arenas. Dedicación: ~15 h/semana, compaginando con el trabajo. Las primeras reuniones con los directores son inminentes. Objetivo a 6–12 meses: méritos visibles (preprint, charla en seminario o congreso de jóvenes investigadores, repo público).

**Tema de tesis.** Regularidad y sumabilidad de soluciones de ecuaciones algebraicas en clases ultraholomorfas (Carleman–Roumieu y Beurling) en regiones (poli)sectoriales.

**Contexto matemático mínimo para el agente.**

- *Clases ultraholomorfas:* funciones holomorfas en un sector con derivadas (o restos de la expansión asintótica) acotados por C·Aⁿ·Mₙ, donde M = (Mₙ) es una sucesión de pesos. Caso base: Gevrey, Mₙ = (n!)^α. Sucesiones "fuertemente regulares" (Thilliez): log-convexa (lc), crecimiento moderado (mg), fuertemente no cuasianalítica (snq). Las definiciones exactas se sacan del corpus, no de memoria.
- *Roumieu vs Beurling:* Roumieu = existe A > 0 con la cota; Beurling = la cota vale para todo A > 0 (con C dependiente de A). Es una diferencia de cuantificadores y se pierde fácil en las pruebas.
- *Aplicación de Borel* (función ↦ serie formal de coeficientes asintóticos): inyectividad (cuasianaliticidad, lema de Watson) y sobreyectividad (Borel–Ritt–Gevrey, teoremas de extensión).
- *Sumabilidad:* k-sumabilidad (Ramis, Balser) vía Borel–Laplace; M-sumabilidad con kernels asociados a órdenes aproximados (Lastra–Malek–Sanz). Direcciones singulares, aberturas de sector.
- *Ecuaciones algebraicas* P(z, y) = 0 con coeficientes series formales: raíz simple → lema de Hensel / iteración de Newton; raíz múltiple → polígono de Newton, ramificación z = tʳ, series de Puiseux.

---

## 2. Principios de diseño (innegociables)

1. **Generación y verificación separadas.** La instancia o contexto que redacta nunca es la que juzga.
2. **Cero bibliografía inventada.** Toda afirmación sobre la literatura lleva cita a un fragmento real del corpus `[id:página]`. Si no está en el corpus, se dice "no está en el corpus". Las entradas bibliográficas solo se dan por buenas con DOI/arXiv resueltos; si no, se marcan `pendiente_verificar`.
3. **El sistema devuelve horas de trabajo profundo; no sustituye la comprensión.** Las notas de lectura las redacta Mariano. El sistema pregunta, busca agujeros y cita; no rellena.
4. **Registro.** Toda afirmación que se dé por verificada queda en `log/verificaciones.md` con fecha, método y resultado.
5. **Reproducible.** Tests, aritmética exacta donde toque, semillas fijas, comandos documentados.

---

## 3. Fase 0 — Auditoría (primer paso; sin cambios en el repo)

Recorre la estructura (tree hasta 3 niveles), README, CLAUDE.md, dependencias, scripts, notebooks y tests. Escribe `ESTADO_SISTEMA.md` (máx. 2 páginas, sin claves ni rutas personales) con:

1. Objetivo del sistema en una línea.
2. Estructura del repo: una frase por carpeta.
3. Corpus: nº de PDFs, títulos/autores, método de extracción, dónde están texto y chunks, calidad de las fórmulas extraídas (muestra 3 fórmulas tal cual quedaron).
4. Índice/RAG: embeddings, almacén, forma de consulta, si exige citas, un ejemplo real de consulta y respuesta.
5. Notas de lectura: formato, cuántas hay, si están indexadas.
6. Cómputo: funciones existentes (series formales, solver algebraico, estimador de crecimiento, Borel/Padé), lenguaje, dependencias, tests que pasan.
7. Prompts y plantillas existentes, con su contenido.
8. Integraciones: MCPs, skills/comandos, hooks, modelos usados, dónde corre (portátil, servidor, nube).
9. Roto / a medias / pendiente, con horas estimadas por ítem.
10. Qué haría falta, en orden, para usarlo mañana.

Después, **decisión por componente** con esta regla:

- **Conservar:** funciona y tiene tests (o son fáciles de añadir).
- **Adaptar:** la arquitectura sirve pero faltan piezas.
- **Reconstruir:** la extracción destroza fórmulas, el índice no da citas por página, o el código no es reproducible.

Antes de cualquier reconstrucción: rama o tag `pre-rebuild`. Nada se borra sin copia.

**Entrega de la fase:** `ESTADO_SISTEMA.md` + `PLAN.md` (fases, horas reales, criterios de aceptación). Pregunta a Mariano **solo lo que bloquee:** dónde están los PDFs, licencias disponibles (Mathematica/Maple/Sage), máquina donde corre, presupuesto de API, si ya tiene el documento del proyecto y la lista de lectura de los directores.

---

## 4. Componentes objetivo

### 4.1 Corpus (`corpus/`)

- `corpus/raw/*.pdf` · `corpus/meta/bib.yaml` (id, autores, título, año, venue, DOI/arXiv, etiquetas, estado de verificación) · `corpus/text/{id}/` con texto por página conservando LaTeX cuando sea posible.
- Extracción con una herramienta que respete fórmulas (tipo Marker/Nougat); fallback PyMuPDF. Guardar siempre el número de página.
- Lista inicial (Mariano la completará): papers de Sanz, Lastra, Jiménez-Garrido, Schindl, Thilliez, Rainer, Malek y Rodríguez Arenas; Balser (libro de sumabilidad); Ramis; clásicos de Denjoy–Carleman; tesis del grupo del IMUVa; el documento del proyecto de tesis.
- **Aceptación:** `phd ingest <pdf>` procesa un PDF nuevo de principio a fin y una fórmula de muestra queda legible en el texto extraído.

### 4.2 Índice y consulta (`index/`, comando `phd ask`)

- Chunking por sección/párrafo (300–800 tokens) con metadatos: id, página, sección, tipo (definición / teorema / prueba / observación) cuando sea detectable.
- Búsqueda híbrida: BM25 + embeddings (modelo local o API; documentar cuál y su coste). Almacén local (sqlite-vec, LanceDB o Chroma; lo que ya exista si funciona).
- `phd ask "pregunta"`: recupera k fragmentos y responde con estas reglas: cita `[id:página]` tras cada afirmación; separa "el corpus dice" de "conocimiento general del modelo"; si no hay evidencia, lo dice.
- Las notas de Mariano (`notes/`) también se indexan, etiquetadas como fuente `nota`.
- **Aceptación:** 5 preguntas de prueba con respuesta citada y comprobada a mano contra el PDF (ejemplo: "¿qué condiciones sobre M usa el teorema de extensión de Thilliez?").

### 4.3 Protocolo de lectura (`notes/`, comando `phd note`)

- `phd note new <id>` crea `notes/{id}.md` desde plantilla: enunciado principal · hipótesis y por qué cada una · lema clave · qué se rompe sin él · qué dejan abierto los autores · pregunta de transferencia (¿análogo en clases ultradiferenciables? ¿pasa a sectores/polisectores? ¿Roumieu ↔ Beurling?) · dudas para los directores.
- `phd note quiz <id>`: el modelo genera preguntas de interrogatorio sobre el paper a partir del texto (sin respuestas).
- `phd note check <id>`: Mariano escribe su explicación del argumento; el modelo busca agujeros citando el texto.
- La redacción de la nota es de Mariano; el modelo no rellena la plantilla.

### 4.4 Laboratorio de cómputo (`lab/`)

Python + SymPy con aritmética exacta (Fraction / QQ), mpmath para numérico de alta precisión; Sage opcional si está disponible.

**Módulos:**

- `series.py` — series formales truncadas a orden N y operaciones básicas. Generadores con crecimiento prescrito: Gevrey α (aₙ = εₙ·(n!)^α con εₙ acotado y semilla fija); fuertemente regular no Gevrey (p. ej. Mₙ = (n!)^α · (log(n+e))^{βn}); q-Gevrey (Mₙ = q^{n²}) como caso frontera donde falla mg. Opción: construir la serie a partir de una transformada de Borel dada con singularidades en direcciones elegidas.
- `weights.py` — sucesiones de pesos y comprobación numérica de propiedades (lc, mg, snq y las que aparezcan en el corpus), con la definición explícita de cada una y su cita.
- `algebraic.py` — solución formal de P(z, y) = 0 con coeficientes series formales. Raíz simple: Hensel/Newton. Raíz múltiple: polígono de Newton, ramificación z = tʳ, Puiseux. Devuelve la serie y la traza del polígono.
- `growth.py` — estimador de clase: ajuste por mínimos cuadrados en la cola de log|aₙ| ≈ α·n·log n + n·log A + c; test de cocientes; cálculo de (|aₙ|/Mₙ)^{1/n} para un M dado (Roumieu: acotado; Beurling: tiende a 0, se ve peor numéricamente). Informe con intervalos.
- `borel.py` — transformada de Borel de orden k (normalización documentada), aproximantes de Padé para localizar singularidades en el plano de Borel, estimación de direcciones singulares y radio; Laplace numérico de vuelta en una dirección; comparación con la función cuando se conoce.
- `viz.py` — coeficientes, plano de Borel, sectores.

**Tests (pytest) con verdad conocida:**

1. Serie de Euler Σ (−1)ⁿ n! zⁿ: Gevrey-1; con normalización aₙ/n! la transformada de Borel es 1/(1+ζ), polo en ζ = −1, dirección singular arg z = π.
2. Función algebraica convergente (p. ej. raíz de y² − y + z = 0): exponente de crecimiento α ≈ 0.
3. Raíz simple de y² − y + z·f(z) = 0 con f Gevrey-1: la solución debe dar α ≈ 1 (calibración de regularidad).
4. Raíz múltiple, p. ej. y² = z·(1 + z·f(z)): ramificación r = 2 detectada por el polígono.

**Aceptación:** tests en verde y `phd lab demo` reproduce los cuatro casos con gráficos.

### 4.5 Verificación (`prompts/`, comando `phd referee`, `log/`)

- `prompts/referee.md` — rol de referee hostil con una sola orden: "encuentra el error". Lista de comprobación: ¿las constantes dependen de n? · ¿las estimaciones son uniformes en el sector/abertura? · ¿Roumieu y Beurling tratados con los cuantificadores correctos? · ¿qué propiedades de M se usan, dónde, y hacen falta todas? · ¿se confunde el nivel formal con el analítico? · ¿dirección y abertura del sector justificadas? · ¿casos degenerados (raíces múltiples, discriminante nulo) cubiertos? Salida: lista numerada de objeciones con gravedad; sin valoración global.
- `prompts/redactor.md` — ayuda a redactar sin inventar lemas; marca `[VERIFICAR]` toda afirmación no trivial.
- `phd referee <archivo>` — ejecuta el referee en un contexto separado del que redactó.
- `log/verificaciones.md` — fecha · afirmación · método (cita / cómputo / prueba propia / referee) · resultado.

### 4.6 Configuración del repo para Claude Code

- `CLAUDE.md` con las reglas de la sección 2 más: responder en español; no editar `notes/` (son de Mariano); tests antes de commit; commits pequeños; ante una afirmación matemática, ofrecer pasar el referee.
- Comandos o skills del repo para `ingest`, `ask`, `note`, `referee` y `lab`, con el mecanismo que Claude Code soporte actualmente (referencia: https://docs.claude.com/en/docs/claude-code/overview).
- `.env` fuera de git; documentar coste aproximado por consulta.

---

## 5. Orden de ejecución

Las reuniones con los directores son inminentes: la prioridad es poder **leer con el protocolo esta misma semana**.

1. **Fase 0** (auditoría + plan): 1 sesión.
2. **Corpus + índice + `phd ask`:** prioridad máxima. Meta: el documento del proyecto y 5–10 papers clave ingeridos y consultables con citas.
3. **Plantilla de notas + `quiz` + `check`.**
4. **Referee + log.**
5. **Laboratorio:** primero `series.py` + `growth.py` + `algebraic.py` (raíz simple) + tests 1–3; después `borel.py`; después raíces múltiples (test 4); polisectores como extensión posterior.
6. **Documentación** (`README.md` de uso en 1 página) + `phd lab demo`.

Cada fase termina con: tests en verde, commit, y una línea en `PLAN.md` con lo hecho y lo que queda.

---

## 6. Cómo reparte Mariano las 15 h (para calibrar qué automatizar)

6 h de trabajo profundo sin IA · 4 h de lectura interrogada · 3 h de cómputo · 2 h de escritura y registro. Todo lo que ahorre tiempo en las tres últimas sin tocar la primera es prioritario.

---

## 7. Qué NO hacer

- No generar pruebas "completas" para que Mariano las copie: pistas, objeciones y citas.
- No rellenar notas ni plantillas de lectura.
- No inventar bibliografía ni completar metadatos de memoria.
- No borrar ni reescribir trabajo previo sin auditoría y sin copia.
- No optimizar la arquitectura antes de que `phd ask` funcione con citas.

---

## 8. Definición de "hecho"

`phd ingest` procesa un PDF · `phd ask` responde con citas verificables · `phd note` genera plantilla y quiz · `phd referee` produce objeciones numeradas · tests del lab en verde · `CLAUDE.md`, `README.md`, `PLAN.md` y `log/verificaciones.md` existen y están al día.
