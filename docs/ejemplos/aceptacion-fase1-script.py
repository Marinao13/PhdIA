"""Lanza las preguntas de aceptacion de la Fase 1 con doc.py ask y escribe docs/aceptacion-fase1.md."""
import io, json, os, re, subprocess, sys, glob, datetime

RAIZ = os.getcwd()
PREGUNTAS = [
    ("0", "que condiciones sobre la sucesion M usa el teorema de extension de Thilliez"),
    ("a", "Segun Thilliez 2010, que hipotesis sobre M exige el resultado de estabilidad para ecuaciones algebraicas y en que clase quedan las soluciones?"),
    ("b", "Que relacion demuestran Jimenez-Garrido y Sanz (2016) entre gamma(M) y omega(M), y bajo que condicion?"),
    ("c", "Como se define la M-sumabilidad en una direccion en Lastra-Malek-Sanz 2015 y que papel juega el orden aproximado asociado a M?"),
    ("d", "En Jimenez-Garrido-Sanz-Schindl 2019, que indice separa las aberturas de sector con aplicacion de Borel inyectiva, y cual las de sobreyectiva?"),
    ("e", "Que prueba el corpus sobre la sumabilidad de soluciones de ecuaciones algebraicas con raices multiples, via poligono de Newton, en clases ultraholomorfas?"),
]

salida = ["# Aceptacion de la Fase 1: seis preguntas a `ask` (%s)\n" % datetime.date.today().isoformat(),
          "Modelo: gpt-5.6-terra, esfuerzo bajo, k=8. `ask` v2 tras el primer veredicto: cupo propio y sin tope para cada documento nombrado, segunda busqueda con las palabras clave que pide el modelo (BUSCAR) o forzada si la fuente primaria no se uso, citas con pagina y numero impreso, notacion atribuida, y lista de referencias citadas fuera del corpus. Cada respuesta va con los",
          "fragmentos que el modelo declaro usar. **La comprobacion contra el PDF es de Mariano**:",
          "marca cada fila como correcta / incompleta / incorrecta en la tabla del final.\n",
          "La (e) es control negativo: la respuesta buena es \"no esta en el corpus\" o una cita real;",
          "nunca una sintesis sin cita.\n"]
tabla = ["| # | Pregunta | Fragmentos usados | Veredicto de Mariano |", "|---|---|---|---|"]

for letra, pregunta in PREGUNTAS:
    antes = set(glob.glob(os.path.join("registro", "consultas", "*.json")))
    r = subprocess.run([sys.executable, "doc.py", "ask", pregunta], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    nuevos = set(glob.glob(os.path.join("registro", "consultas", "*.json"))) - antes
    if not nuevos:
        salida += [f"\n## ({letra}) {pregunta}\n", "FALLO al ejecutar ask:\n```\n" + (r.stderr or r.stdout)[-800:] + "\n```"]
        tabla.append(f"| {letra} | {pregunta[:60]}... | fallo | |")
        continue
    c = json.load(open(nuevos.pop(), encoding="utf-8"))
    usados = [f for f in c["fragmentos"] if f.get("usado")]
    citas = "; ".join(dict.fromkeys(f"[{f['doc']}:p{f['pagina']}]" for f in usados)) or "ninguno"   # sin duplicados
    salida += [f"\n## ({letra}) {pregunta}\n", c["respuesta"].strip(), "",
               f"*Recuperados {len(c['fragmentos'])}, usados {len(usados)}. Consulta completa en `registro/consultas/{c['ts']}.json`.*"]
    tabla.append(f"| {letra} | {pregunta[:60]}... | {citas} | |")
    print(f"({letra}) ok: {len(usados)}/{len(c['fragmentos'])} usados")

salida += ["\n## Tabla de veredictos\n"] + tabla
os.makedirs("docs", exist_ok=True)
io.open(os.path.join("docs", "aceptacion-fase1.md"), "w", encoding="utf-8", newline="\n").write("\n".join(salida) + "\n")
print("-> docs/aceptacion-fase1.md")
