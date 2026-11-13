"""El .tex como unos apuntes: portada, indice, cada clase con su fecha como seccion y los comentarios
(lo dicho de palabra, las notas al margen, las reflexiones) en su propio bloque."""
import re
import pytest

from nucleo import transcribir as T
from nucleo import a_latex as L
from nucleo import comandos as K
from nucleo import config as C
from nucleo import estado as E
from nucleo import motor as M
from nucleo import prompts as P


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "RAIZ", str(tmp_path))
    monkeypatch.setattr(C, "F_LLAMADAS", str(tmp_path / "llamadas.jsonl"))
    monkeypatch.setattr(C, "SIMULAR", True)
    monkeypatch.setattr(E, "sesion_hoy", lambda: None)
    monkeypatch.setattr(E, "commits_todos", lambda: [])
    monkeypatch.setattr(E, "fase_actual", lambda: ("libre", E._marcas_vacias()))
    monkeypatch.setattr(K, "_abrir", lambda ruta: None)
    return tmp_path


def _pdf(ruta, paginas=2):
    import fitz
    doc = fitz.open()
    for n in range(paginas):
        doc.new_page().insert_text((72, 100), f"pagina {n + 1}")
    doc.save(str(ruta))
    doc.close()
    return str(ruta)


MD = """# Curso Javi, hasta 12/11

<!-- pagina 1 -->

<!-- clase -->
30 sep **clases de Javi:**
<!-- fin -->

## **Clases de funciones analíticas:**

<!-- teorema -->
**Teorema (Pringsheim):** Sea $f$ analítica.
<!-- fin -->

<!-- comentario -->
“Javi: voy a dar una idea”
<!-- fin -->

<!-- demostracion -->
Dem: Basta usar Taylor.

<!-- comentario -->
Al regularizar $CA_1$ no afectan
<!-- fin -->

Y se sigue con la demostración.
<!-- fin -->

<!-- pagina 2 -->

<!-- clase -->
## 21 Oct / **Clase Javi**:
<!-- fin -->

### Ejemplos

<!-- comentario -->
No lo demostramos, se usa la segunda desigualdad de Gorny-Cartan.
"""


def test_cada_clase_es_una_seccion_y_los_titulos_bajan_un_nivel():
    tex, _ = L.cuerpo_latex(MD)
    assert "\\section{30 sep clases de Javi}" in tex and "\\section{21 Oct / Clase Javi}" in tex
    assert "\\subsection{Clases de funciones analíticas}" in tex and "\\subsubsection{Ejemplos}" in tex
    assert "\\section*" not in tex and "\\textbf{clases de Javi" not in tex
    assert L.clases(MD) == ["30 sep clases de Javi", "21 Oct / Clase Javi"]
    # sin clases marcadas, los titulos manuscritos son las secciones; sin negrita ni dos puntos
    tex2, _ = L.cuerpo_latex("## **Clases de funciones analíticas:**\n\nTexto.\n\n### Otro\n")
    assert "\\section{Clases de funciones analíticas}" in tex2 and "\\subsection{Otro}" in tex2


def test_los_comentarios_van_aparte_y_pueden_ir_dentro_de_una_demostracion():
    tex, _ = L.cuerpo_latex(MD)
    assert "\\end{teorema}\n\n\\begin{comentario}\n``Javi: voy a dar una idea''\n\\end{comentario}" in tex
    assert ("\\begin{demostracion}\nBasta usar Taylor.\n\n\\begin{comentario}\nAl regularizar $CA_1$ no afectan\n"
            "\\end{comentario}\n\nY se sigue con la demostración.\n\\end{demostracion}") in tex
    assert tex.rstrip().endswith("\\begin{comentario}\nNo lo demostramos, se usa la segunda desigualdad de "
                                 "Gorny-Cartan.\n\\end{comentario}")
    for env in L.ENTORNOS:
        assert tex.count("\\begin{%s}" % env) == tex.count("\\end{%s}" % env)
    assert tex.count("\\begin{comentario}") == 3 and not re.search("[\ue000-\ue0ff]", tex)


def test_portada_e_indice_con_lo_que_dice_la_cabecera():
    tex = L.documento(MD, nombre="x", estado="sin_revisar", fecha="2026-11-13",
                      meta=dict(tipo="curso", autor="Mariano San José Gómez", profesor="Javier Sanz",
                                asignatura="Clases ultradiferenciables", fecha="2026-11-12"))
    pre, cuerpo = tex.split("\\begin{document}")
    assert "\\newenvironment{comentario}" in pre and "{hyperref}" in pre and "\\title{Curso Javi, hasta 12/11}" in pre
    portada = cuerpo[:cuerpo.index("\\tableofcontents")]
    assert portada.lstrip().startswith("\\begin{titlepage}") and "\\end{titlepage}" in portada
    for trozo in ("{\\Huge\\bfseries Curso Javi, hasta 12/11\\par}", "Clases ultradiferenciables", "Apuntes de clase",
                  "Profesor: Javier Sanz", "Clases del 30 sep al 21 Oct", "Mariano San José Gómez",
                  "Transcrito de los apuntes manuscritos el 2026-11-12", "Sin revisar contra el original"):
        assert trozo in portada, trozo
    assert cuerpo.index("\\tableofcontents") < cuerpo.index("\\clearpage") < cuerpo.index("\\section{30 sep")
    assert "\\maketitle" not in tex
    revisado = L.documento(MD, nombre="x", estado="revisado", meta=dict(tipo="paper"))
    assert "Revisado contra el original." in revisado and "Notas de lectura" in revisado and "Profesor" not in revisado
    # sin titulo no hay portada ni indice
    assert "\\begin{titlepage}" not in L.documento("<!-- pagina 1 -->\n\nTexto.\n", nombre="x")


def test_el_autor_sale_de_la_cabecera_o_de_la_configuracion(repo):
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=1), tipo="curso", titulo="Tema 1")
    assert "{\\Large " + C.AUTOR + "\\par}" in open(r["tex"], encoding="utf-8").read()
    t = open(r["ruta"], encoding="utf-8").read().replace("estado: sin_revisar", "autor: Otra Persona\nprofesor: J. Sanz\nestado: sin_revisar")
    open(r["ruta"], "w", encoding="utf-8", newline="\n").write(t)
    assert T.exportar_tex(r["nombre"])[1] == "escrito"
    tex = open(r["tex"], encoding="utf-8").read()
    assert "{\\Large Otra Persona\\par}" in tex and "Profesor: J. Sanz" in tex and C.AUTOR not in tex


def test_estructura_completa_lo_ya_marcado_con_comentarios_y_clases(repo, monkeypatch):
    pagina = ("30 sep **clases de Javi:**\n\n<!-- teorema -->\n**Teorema:** Sea $M$.\n<!-- fin -->\n\n"
              "“Javi: voy a dar una idea”\n\n<!-- demostracion -->\nDem: Es claro.\n\nNota al margen.\n\nFin.\n<!-- fin -->")
    monkeypatch.setattr(M, "_completar", lambda *a, **k: (pagina, 100, 50, 0, {}))
    r = T.transcribir(_pdf(repo / "a.pdf", paginas=1), tipo="curso", titulo="Tema 1")
    # como si fuera de antes de que hubiera comentarios y clases
    t = open(r["ruta"], encoding="utf-8").read().replace("estructura: 2\n", "")
    open(r["ruta"], "w", encoding="utf-8", newline="\n").write(t)
    vistos = []

    def modelo(system, messages, *a, **k):
        vistos.append(messages[-1]["content"])
        return "1: clase\n2: teorema\n3: comentario\n5: comentario\n4-6: lema", 300, 20, 0, {}

    monkeypatch.setattr(M, "_completar", modelo)
    res = T.estructura(r["nombre"])
    assert "(ya marcado: teorema)" in vistos[0] and "(ya marcado: demostracion)" in vistos[0] and "SOLO" in vistos[0]
    assert res["bloques"] == 3 and res["paginas"] == [1]                  # la clase y dos comentarios; nada mas
    hoja = dict(T.paginas(T.leer(r["nombre"])["cuerpo"])[1])[1]
    assert hoja == ("<!-- clase -->\n30 sep **clases de Javi:**\n<!-- fin -->\n\n"
                    "<!-- teorema -->\n**Teorema:** Sea $M$.\n<!-- fin -->\n\n"
                    "<!-- comentario -->\n“Javi: voy a dar una idea”\n<!-- fin -->\n\n"
                    "<!-- demostracion -->\nDem: Es claro.\n\n"
                    "<!-- comentario -->\nNota al margen.\n<!-- fin -->\n\nFin.\n<!-- fin -->")
    assert T.leer(r["nombre"])["estructura"] == "2"
    tex = open(r["tex"], encoding="utf-8").read()
    assert "\\section{30 sep clases de Javi}" in tex and tex.count("\\begin{comentario}") == 2
    assert "\\begin{demostracion}\nEs claro.\n\n\\begin{comentario}\nNota al margen.\n\\end{comentario}\n\nFin.\n\\end{demostracion}" in tex
    # ya esta al dia: no se vuelve a preguntar
    n = len(vistos)
    assert T.estructura(r["nombre"])["bloques"] == 0 and len(vistos) == n
    # --rehacer quita todo y empieza de cero
    monkeypatch.setattr(M, "_completar", lambda *a, **k: ("1: clase\n2: teorema", 300, 20, 0, {}))
    res = T.estructura(r["nombre"], rehacer=True)
    hoja = dict(T.paginas(T.leer(r["nombre"])["cuerpo"])[1])[1]
    assert res["bloques"] == 2 and hoja.count("<!-- fin -->") == 2 and "<!-- demostracion -->" not in hoja
    assert "Dem: Es claro." in hoja and "Nota al margen." in hoja


def test_el_prompt_conoce_las_clases_y_los_comentarios():
    for p in (P.TRANSCRIBIR, P.ESTRUCTURA):
        assert "comentario" in p and "clase" in p
    assert "<!-- clase -->" in P.TRANSCRIBIR and "<!-- comentario -->" in P.TRANSCRIBIR
