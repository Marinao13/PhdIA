# CLAUDE.md — reglas para trabajar en este repo

Sistema de apoyo al doctorado de Mariano (IMUVa; clases ultraholomorfas, sucesiones
peso, sumabilidad). El BRIEF completo esta en `docs/BRIEF.md`; el uso, en `docs/USO.md`;
el estado y el plan, en `ESTADO_SISTEMA.md` y `PLAN.md`.

## Principios innegociables (BRIEF, seccion 2)

1. **Generacion y verificacion separadas.** Quien redacta no juzga. Ante cualquier
   afirmacion matematica no trivial, ofrece pasar `python doc.py referee`.
2. **Cero bibliografia inventada.** Toda afirmacion sobre la literatura lleva cita a un
   fragmento real del corpus `[id:pagina]`. Si no esta en el corpus, se dice "no esta en
   el corpus". Metadatos solo de arXiv o Crossref; lo demas, `pendiente_verificar`.
   Nunca completes un DOI, un ano o un titulo de memoria.
3. **El sistema devuelve horas; no sustituye la comprension.** No rellenes `sesiones/`
   ni `lecturas/`: son de Mariano. El sistema pregunta, busca agujeros y cita.
4. **Registro.** Lo que se da por verificado va a `registro/verificaciones.md` con fecha,
   metodo y resultado.
5. **Reproducible.** Tests antes de commit (`python -m pytest tests -q`), aritmetica exacta
   donde toque, semillas fijas, comandos documentados.

## Las tres reglas del motor (`ia/reglas.md`)

- Compromiso antes de consulta: 25 min escritos y sellados antes de encender el motor.
- Nada del campo entra en notas sin referencia abierta: el modelo inventa enunciados de
  Thilliez con aplomo y mezcla normalizaciones de (gamma_1), (mg), (dc) entre autores.
- El motor esta apagado en fase 1 y fase 3. `motor.llamar()` es la unica puerta; no la
  rodees. `buscar` no usa motor y por eso vale siempre.

## Como trabajar aqui

- Responde y documenta en espanol. El codigo y los ficheros del sistema van sin acentos
  (consola de Windows); el contenido matematico puede llevarlos.
- Commits pequenos y explicitos. Los sellados (`sellar`, `cierre`...) hacen `git add -A`
  y son intentos a ciegas: no deben arrastrar ficheros ajenos. Si vas a dejar ficheros
  nuevos en el arbol, commitealos tu.
- `corpus/raw/`, `corpus/text/` e `indice/` son datos locales fuera de git. Antes de
  sacar del repo algo rastreado, copialo: `git rm --cached` + merge borra el fichero en
  los demas checkouts (paso el 2026-09-16; se recupero del worktree).
- No edites `nucleo/estado.py` ni `nucleo/motor.py` sin correr los tests: son la puerta.
- `.env` nunca se versiona ni se muestra. Los precios y el presupuesto viven en
  `nucleo/config.py`.
- Trabaja en un worktree (`.claude/worktrees/`) y fusiona a `master` solo commits
  cerrados; Mariano puede tener una sesion abierta con ficheros sin commitear.
- No optimices la arquitectura antes de que `ask` funcione con citas (BRIEF, 7).
