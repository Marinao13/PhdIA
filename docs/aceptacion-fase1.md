# Aceptacion de la Fase 1: seis preguntas a `ask` (2026-09-17)

Modelo: gpt-5.6-terra, esfuerzo bajo, k=8. `ask` v2 tras el primer veredicto: cupo propio y sin tope para cada documento nombrado, segunda busqueda con las palabras clave que pide el modelo (BUSCAR) o forzada si la fuente primaria no se uso, citas con pagina y numero impreso, notacion atribuida, y lista de referencias citadas fuera del corpus. Cada respuesta va con los
fragmentos que el modelo declaro usar. **La comprobacion contra el PDF es de Mariano**:
marca cada fila como correcta / incompleta / incorrecta en la tabla del final.

La (e) es control negativo: la respuesta buena es "no esta en el corpus" o una cita real;
nunca una sintesis sin cita.


## (0) que condiciones sobre la sucesion M usa el teorema de extension de Thilliez

EL CORPUS DICE

Notacion: la de [thilliez-2003:p5, Definicion 1.3.1]. El teorema de extensión sectorial de Thilliez requiere que $M$ sea una sucesión fuertemente regular y que la apertura satisfaga $0<\gamma<\gamma(M)$. [thilliez-2003:p10, teorema, etiqueta LaTeX: sectflat]

La condición sobre $M$ que aparece explícitamente para controlar $\gamma$ es la propiedad $(\mathsf P_\gamma)$: existe una sucesión $m'$ equivalente, hasta constantes multiplicativas, a la sucesión de cocientes $m$, tal que $((j+1)^{-\gamma}m'_j)_j$ es creciente. [thilliez-2003:p5, Definicion 1.3.1]

Como confirmación secundaria, se atribuye a Thilliez el resultado de operadores de extensión lineales y continuos para toda $\delta<\gamma(M)$ cuando $M$ es fuertemente regular. [jimenez-garrido-cantero-sanz-schindl-2023:p16, Observacion 3.13]

USADOS: [thilliez-2003:p10, teorema, etiqueta LaTeX: sectflat]; [thilliez-2003:p5, Definicion 1.3.1]; [jimenez-garrido-cantero-sanz-schindl-2023:p16, Observacion 3.13]

*Recuperados 23, usados 3. Consulta completa en `registro/consultas/2026-09-17-010355.json`.*

## (a) Segun Thilliez 2010, que hipotesis sobre M exige el resultado de estabilidad para ecuaciones algebraicas y en que clase quedan las soluciones?

EL CORPUS DICE

Notación: la de [thilliez-2010]. Thilliez exige que $M$ sea fuertemente regular. [thilliez-2010:p7, Teorema 3]

Si $a_j\in\mathcal{A}_M(S_{\gamma,r})$ y $h\in\mathcal{A}^\infty(S_{\gamma,r})$ satisface $\varphi(z,h(z))=0$, entonces $h\in\mathcal{A}_M(S_{\gamma',r'})$ para todo $\gamma'<\gamma$ y $r'<r$. [thilliez-2010:p7, Teorema 3]

USADOS: [thilliez-2010:p7, Teorema 3]

*Recuperados 20, usados 1. Consulta completa en `registro/consultas/2026-09-17-010401.json`.*

## (b) Que relacion demuestran Jimenez-Garrido y Sanz (2016) entre gamma(M) y omega(M), y bajo que condicion?

EL CORPUS DICE

Notación: la de [jimenez-garrido-sanz-2016]. Para toda sucesión fuertemente regular $\M$, $\omega(\M)\geq\gamma(\M)$. [jimenez-garrido-sanz-2016:p21, Proposicion 4.18]

Si además se cumple
$\displaystyle \lim_{p\to\infty}\frac{\log(m_p)}{\log p}=\omega(\M)$,
entonces demuestran que $\omega(\M)=\gamma(\M)$. [jimenez-garrido-sanz-2016:p21, Teorema 4.19]

La condición anterior es equivalente a que $d_\M(t)$ satisfaga la condición $(\mathrm{OA3:1})$. [jimenez-garrido-sanz-2016:p11, teorema, etiqueta LaTeX: teorcondicion3caracterizacion]

CONOCIMIENTO GENERAL

La segunda afirmación es una implicación condicional: la regularidad fuerte sola garantiza $\gamma(\M)\leq\omega(\M)$, pero no por sí sola la igualdad.

USADOS: [jimenez-garrido-sanz-2016:p21, Proposicion 4.18]; [jimenez-garrido-sanz-2016:p21, Teorema 4.19]; [jimenez-garrido-sanz-2016:p11, teorema, etiqueta LaTeX: teorcondicion3caracterizacion]

*Recuperados 23, usados 3. Consulta completa en `registro/consultas/2026-09-17-010410.json`.*

## (c) Como se define la M-sumabilidad en una direccion en Lastra-Malek-Sanz 2015 y que papel juega el orden aproximado asociado a M?

EL CORPUS DICE

Notación: la de [lastra-malek-sanz-2015]. Para $d\in\mathbb R$, $\hat f=\sum_{n\geq0}(f_n/n!)z^n$ es $\mathcal M$-sumable en dirección $d$ si existe una región sectorial $G=G(d,\gamma)$, con $\gamma>\omega(\mathcal M)$, y una función $f\in\widetilde{\mathcal A}_{\mathcal M}(G)$ tal que $f\sim_{\mathcal M}\hat f$. [lastra-malek-sanz-2015:p7, definicion, etiqueta LaTeX: defisumable]

El orden aproximado asociado que usan es $d(r)=\log(M(r))/\log r$. Si $d(r)$ es un orden aproximado y $\omega(\mathcal M)<2$, toda función $V\in\mathfrak B(2\omega(\mathcal M),d(r))$ produce un núcleo de $\mathcal M$-sumabilidad mediante $e_V(z)=\omega(\mathcal M)^{-1}z\exp(-V(z))$ en $S_{\omega(\mathcal M)}$. [lastra-malek-sanz-2015:p19, teorema, etiqueta LaTeX: teorconstrkernels]

Ese núcleo determina su función momento $m_e(\lambda)=\int_0^\infty t^{\lambda-1}e(t)\,dt$ y la función entera $E(z)=\sum_{n\geq0}z^n/m_e(n)$; por tanto permite definir las transformadas de tipo Laplace y Borel empleadas en la teoría. [lastra-malek-sanz-2015:p8, definicion, etiqueta LaTeX: defikernelMsumm]

La condición de que $d(r)$ sea orden aproximado equivale, entre otras, a que $\lim_{p\to\infty}(p+1)/M(m_p)=1/\omega(\mathcal M)=\rho[M]$. [lastra-malek-sanz-2015:p20, Proposicion 4.13]

Para $\omega(\mathcal M)\geq2$, reducen al caso $\omega(\mathcal M^{(1/s)})<2$ con $\mathcal M^{(1/s)}=(M_n^{1/s})$, y recuperan un núcleo para $\mathcal M$ a partir de uno para $\mathcal M^{(1/s)}$. Además, $d$ es orden aproximado si y solo si lo es la función asociada a la sucesión transformada. [lastra-malek-sanz-2015:p20, Observacion 4.12]

CONOCIMIENTO GENERAL

Un orden aproximado refina el concepto de orden constante de crecimiento: permite construir funciones analíticas con crecimiento angular controlado. Aquí su función técnica es proporcionar los núcleos para las transformadas integrales; no forma parte de la definición básica de $\mathcal M$-sumabilidad citada.

USADOS: [lastra-malek-sanz-2015:p7, definicion, etiqueta LaTeX: defisumable]; [lastra-malek-sanz-2015:p19, teorema, etiqueta LaTeX: teorconstrkernels]; [lastra-malek-sanz-2015:p8, definicion, etiqueta LaTeX: defikernelMsumm]; [lastra-malek-sanz-2015:p20, Proposicion 4.13]; [lastra-malek-sanz-2015:p20, Observacion 4.12]

*Recuperados 18, usados 5. Consulta completa en `registro/consultas/2026-09-17-010421.json`.*

## (d) En Jimenez-Garrido-Sanz-Schindl 2019, que indice separa las aberturas de sector con aplicacion de Borel inyectiva, y cual las de sobreyectiva?

EL CORPUS DICE

Notación: la de [jimenez-garrido-sanz-schindl-2019-injectivity]. Para una sucesión fuertemente regular $\mathbb M$, el índice de Thilliez $\gamma(\mathbb M)$ separa, en sentido suficiente, los regímenes: si la apertura es $\pi\gamma$ con $0<\gamma<\gamma(\mathbb M)$, el mapa de Borel es sobreyectivo; si $\gamma>\omega(\mathbb M)$, es inyectivo, mientras que si $\gamma<\omega(\mathbb M)$ no es inyectivo. [jimenez-garrido-sanz-schindl-2019-injectivity:p28, teorema, etiqueta LaTeX: th.ThilliezSurjectivity] [jimenez-garrido-sanz-schindl-2019-injectivity:p11, Teorema 3.4]

Por tanto, no es un único índice en general: $\gamma(\mathbb M)$ controla la frontera de sobreyectividad y $\omega(\mathbb M)$ la de inyectividad. [jimenez-garrido-sanz-schindl-2019-injectivity:p28, teorema, etiqueta LaTeX: th.ThilliezSurjectivity] [jimenez-garrido-sanz-schindl-2019-injectivity:p15, Corolario 3.16]

USADOS: [jimenez-garrido-sanz-schindl-2019-injectivity:p28, teorema, etiqueta LaTeX: th.ThilliezSurjectivity]; [jimenez-garrido-sanz-schindl-2019-injectivity:p11, Teorema 3.4]; [jimenez-garrido-sanz-schindl-2019-injectivity:p15, Corolario 3.16]

*Recuperados 39, usados 3. Consulta completa en `registro/consultas/2026-09-17-010434.json`.*

## (e) Que prueba el corpus sobre la sumabilidad de soluciones de ecuaciones algebraicas con raices multiples, via poligono de Newton, en clases ultraholomorfas?

EL CORPUS DICE

Notacion: la de [thilliez-2010]. El Teorema 2 de Thilliez establece que, si $\mathcal E_1(M)$ es cuasianalítica y estable por derivación, los coeficientes $a_j$ de $\varphi(x,y)$ pertenecen a $\mathcal E_1(M)$ y un germen $C^\infty$ $h$ satisface $\varphi(x,h(x))=0$, entonces $h\in\mathcal E_1(M)$. El fragmento no formula este resultado mediante polígono de Newton ni como un teorema de sumabilidad. [thilliez-2010:p4, Teorema 2]

La observación posterior indica que los métodos considerados no se aplican a raíces de polinomios generales de Weierstrass. [thilliez-2010:p4, Observacion 1]

Para EDO lineales, Balser recoge que los algoritmos escalares se basan usualmente en la construcción del polígono de Newton y el algoritmo de Newton. [balser-2000:p221] En el caso regular-singular, si una raíz $\mu$ de la ecuación indicial tiene multiplicidad al menos $k\geq2$ y cumple la condición indicada allí, el ejercicio pide obtener una solución con potencias de $\log z$ hasta orden $k-1$. [balser-2000:p53]

La tesis de Jiménez-Garrido atribuye a Braaksma la extensión, en 1992, de la multisumabilidad de soluciones formales desde ecuaciones lineales meromorfas a ecuaciones no lineales; el fragmento no especifica raíces múltiples ni polígono de Newton. [jimenez-garrido-tesis-2018:p10] El artículo de Lastra--Malek--Sanz introduce una noción de sumabilidad en clases ultraholomorfas de Carleman generales y anuncia una aplicación a ciertas ecuaciones diferenciales parciales de momentos. [lastra-malek-sanz-2015:p1]

No esta en el corpus (segunda busqueda en todo el corpus con: Newton polygon multiple roots algebraic equations).

USADOS: [thilliez-2010:p4, Teorema 2]; [thilliez-2010:p4, Observacion 1]; [balser-2000:p221]; [balser-2000:p53]; [jimenez-garrido-tesis-2018:p10]; [lastra-malek-sanz-2015:p1]

*Recuperados 19, usados 7. Consulta completa en `registro/consultas/2026-09-17-010451.json`.*

## Tabla de veredictos

| # | Pregunta | Fragmentos usados | Veredicto de Mariano |
|---|---|---|---|
| 0 | que condiciones sobre la sucesion M usa el teorema de extens... | [thilliez-2003:p5]; [jimenez-garrido-cantero-sanz-schindl-2023:p16]; [thilliez-2003:p10] | |
| a | Segun Thilliez 2010, que hipotesis sobre M exige el resultad... | [thilliez-2010:p7] | |
| b | Que relacion demuestran Jimenez-Garrido y Sanz (2016) entre ... | [jimenez-garrido-sanz-2016:p11]; [jimenez-garrido-sanz-2016:p21]; [jimenez-garrido-sanz-2016:p21] | |
| c | Como se define la M-sumabilidad en una direccion en Lastra-M... | [lastra-malek-sanz-2015:p19]; [lastra-malek-sanz-2015:p8]; [lastra-malek-sanz-2015:p20]; [lastra-malek-sanz-2015:p20]; [lastra-malek-sanz-2015:p7] | correcta respecto a su fuente (arXiv v1, Prop. 4.13: (p+1)/M(m_p); igual en Sanz 2014, Prop. 4.9); la version de revista (JMAA 2015) dice (p-1)/M(m_p); mismo limite. Ronda 2 la dio por incorrecta en ese detalle; revisada el 2026-09-19 con el .tex. El corpus se queda con arXiv v1 |
| d | En Jimenez-Garrido-Sanz-Schindl 2019, que indice separa las ... | [jimenez-garrido-sanz-schindl-2019-injectivity:p11]; [jimenez-garrido-sanz-schindl-2019-injectivity:p15]; [jimenez-garrido-sanz-schindl-2019-injectivity:p28] | |
| e | Que prueba el corpus sobre la sumabilidad de soluciones de e... | [jimenez-garrido-tesis-2018:p10]; [lastra-malek-sanz-2015:p1]; [balser-2000:p221]; [balser-2000:p53]; [thilliez-2010:p4]; [balser-2000:p53]; [thilliez-2010:p4] | |
