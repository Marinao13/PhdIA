# Aceptacion de la Fase 1: seis preguntas a `ask` (2026-09-16)

Modelo: gpt-6-astra, esfuerzo bajo, k=8, tope 2 por documento. Cada respuesta va con los
fragmentos que el modelo declaro usar. **La comprobacion contra el PDF es de Mariano**:
marca cada fila como correcta / incompleta / incorrecta en la tabla del final.

La (e) es control negativo: la respuesta buena es "no esta en el corpus" o una cita real;
nunca una sintesis sin cita.


## (0) que condiciones sobre la sucesion M usa el teorema de extension de Thilliez

## EL CORPUS DICE

El teorema de extensión de **Thilliez (2003, Th. 3.2.1)** supone que $M$ es **fuertemente regular** y proporciona operadores de extensión lineales y continuos para $0<\delta<\gamma(M)$. [jimenez-garrido-cantero-sanz-schindl-2022:p16, sec 3.2]

Ser fuertemente regular significa:
- ser logarítmicamente convexa;
- ser fuertemente no casianalítica;
- tener crecimiento moderado: existe $A>0$ tal que $M_{p+q}\le A^{p+q}M_pM_q$ para todos $p,q\in\mathbb N_0$. [jimenez-garrido-tesis-2018:p13]

El corpus solo cubre los nombres de las dos primeras condiciones, no sus fórmulas ni su normalización exacta.

## CONOCIMIENTO GENERAL

USADOS: [jimenez-garrido-cantero-sanz-schindl-2022:p16, sec 3.2]; [jimenez-garrido-tesis-2018:p13]

*Recuperados 10, usados 2. Consulta completa en `registro/consultas/2026-09-16-161647.json`.*

## (a) Segun Thilliez 2010, que hipotesis sobre M exige el resultado de estabilidad para ecuaciones algebraicas y en que clase quedan las soluciones?

## EL CORPUS DICE

- **Hipótesis sobre $M$:** el enunciado exige que sea **fuertemente regular**. La introducción menciona crecimiento moderado y no cuasianaliticidad fuerte, pero las definiciones precisas no están en los fragmentos. [thilliez-2010:p7, sec 3.2, main2] [thilliez-2010:p1, sec 1]
- **Datos:** polinomio mónico $\varphi(z,w)=w^d+a_1(z)w^{d-1}+\cdots+a_d(z)$, con $a_j\in\mathcal A_M(S_{\gamma,r})$, y solución $h\in\mathcal A^\infty(S_{\gamma,r})$. [thilliez-2010:p7, sec 3.2, main2]
- **Conclusión:** $h\in\mathcal A_M(S_{\gamma',r'})$ para todo $0<\gamma'<\gamma$ y $0<r'<r$: se conserva la sucesión $M$, reduciendo el sector y el radio. [thilliez-2010:p7, sec 3.2, main2]

## CONOCIMIENTO GENERAL

USADOS: [thilliez-2010:p7, sec 3.2, main2]; [thilliez-2010:p1, sec 1]

*Recuperados 11, usados 2. Consulta completa en `registro/consultas/2026-09-16-161659.json`.*

## (b) Que relacion demuestran Jimenez-Garrido y Sanz (2016) entre gamma(M) y omega(M), y bajo que condicion?

EL CORPUS DICE

- Para toda sucesión $M$ **fuertemente regular**, demuestran $\gamma(M)\leq\omega(M)$. [jimenez-garrido-sanz-2021:p21, sec 4, pro.gamma.menor.omega]
- Si preguntas por la **igualdad**, la tesis indica que admitir un **orden aproximado no nulo** implica $\gamma(M)=\omega(M)$; la regularidad fuerte por sí sola no basta. [jimenez-garrido-tesis-2018:p16]

La atribución de esta igualdad al artículo de 2016 **No esta en el corpus** proporcionado.

CONOCIMIENTO GENERAL

—

USADOS: [jimenez-garrido-sanz-2021:p21, sec 4, pro.gamma.menor.omega]; [jimenez-garrido-tesis-2018:p16]

*Recuperados 11, usados 2. Consulta completa en `registro/consultas/2026-09-16-161709.json`.*

## (c) Como se define la M-sumabilidad en una direccion en Lastra-Malek-Sanz 2015 y que papel juega el orden aproximado asociado a M?

## EL CORPUS DICE

**Definición.** La serie $\hat f=\sum_{n\ge0}(f_n/n!)z^n$ es $\mathcal M$-sumable en dirección $d$ si existen una región sectorial $G=G(d,\gamma)$, con $\gamma>\omega(\mathcal M)$, y una función $f\in\tilde{\mathcal A}_{\mathcal M}(G)$ tal que $f\sim_{\mathcal M}\hat f$. [lastra-malek-sanz-2022:p7, sec 3, defisumable]

**Papel del orden aproximado.** No aparece como hipótesis explícita en esa definición; interviene en la construcción de los núcleos de sumabilidad. Concretamente, si $\mathcal M$ es fuertemente regular, $\omega(\mathcal M)<2$ y $d(r)=\log M(r)/\log r$ es un orden aproximado, entonces para cada $V\in\mathfrak B(2\omega(\mathcal M),d(r))$,
$e_V(z)=\frac{z}{\omega(\mathcal M)}\exp(-V(z))$
es un núcleo de $\mathcal M$-sumabilidad en $S_{\omega(\mathcal M)}$. [lastra-malek-sanz-2022:p7, sec 3, defisumable] [lastra-malek-sanz-2022:p19, sec 4, teorconstrkernels]

Estos núcleos permiten introducir transformadas de tipo Borel y Laplace, formales y analíticas; mediante las transformadas correspondientes se reconstruye la $\mathcal M$-suma de una serie sumable en una dirección. [lastra-malek-sanz-2022:p1] [jimenez-garrido-tesis-2018:p14]

## CONOCIMIENTO GENERAL

USADOS: [lastra-malek-sanz-2022:p7, sec 3, defisumable]; [lastra-malek-sanz-2022:p19, sec 4, teorconstrkernels]; [lastra-malek-sanz-2022:p1]; [jimenez-garrido-tesis-2018:p14]

*Recuperados 12, usados 4. Consulta completa en `registro/consultas/2026-09-16-161723.json`.*

## (d) En Jimenez-Garrido-Sanz-Schindl 2019, que indice separa las aberturas de sector con aplicacion de Borel inyectiva, y cual las de sobreyectiva?

## EL CORPUS DICE

No esta en el corpus la respuesta del artículo de 2019.

- **Inyectividad:** la tesis sitúa un caso pendiente en la abertura $\pi\omega(M)$ para $\widetilde{\mathcal A}_M(S)$ cuando $M$ no admite un orden aproximado; no proporciona aquí el criterio completo. [jimenez-garrido-tesis-2018:p14]
- **Sobreyectividad:** plantea determinar cuál de los índices $\gamma(M)$ y $\omega(M)$ separa las aberturas de sobreyectividad de las de no sobreyectividad, sin resolverlo en este fragmento. [jimenez-garrido-tesis-2018:p14]

Pégame el resumen o los enunciados correspondientes del artículo de 2019.

USADOS: [jimenez-garrido-tesis-2018:p14]

*Recuperados 8, usados 2. Consulta completa en `registro/consultas/2026-09-16-161732.json`.*

## (e) Que prueba el corpus sobre la sumabilidad de soluciones de ecuaciones algebraicas con raices multiples, via poligono de Newton, en clases ultraholomorfas?

## EL CORPUS DICE

**No esta en el corpus** un resultado sobre sumabilidad de soluciones de ecuaciones algebraicas con raíces múltiples mediante polígono de Newton.

El corpus solo cubre estos aspectos relacionados:

- Una **mención a resultados de estabilidad de Thilliez**: para ecuaciones algebraicas con coeficientes en una clase ultraholomorfa definida por una sucesión fuertemente regular, las soluciones permanecen en la clase correspondiente. El fragmento no reproduce el enunciado ni sus hipótesis, ni precisa el tratamiento de raíces múltiples. [jimenez-garrido-sanz-2021:p1, sec 1]
- Una teoría de sumabilidad en clases de Carleman ultraholomorfas sectoriales mediante núcleos y transformadas de tipo Borel y Laplace. La aplicación anunciada concierne a ciertas ecuaciones en derivadas parciales de momentos, no a ecuaciones algebraicas con raíces múltiples. [lastra-malek-sanz-2022:p1]
- Perspectivas de aplicación de la multisumabilidad a ecuaciones en diferencias, incluyendo el nivel $1^+$ y dificultades que requieren aceleración. [jimenez-garrido-tesis-2018:p199]

## CONOCIMIENTO GENERAL

La estabilidad de una clase bajo resolución de ecuaciones y la sumabilidad de una solución formal son afirmaciones distintas: la primera no constituye por sí sola una prueba de la segunda.

USADOS: [jimenez-garrido-sanz-2021:p1, sec 1]; [lastra-malek-sanz-2022:p1]; [jimenez-garrido-tesis-2018:p199]

*Recuperados 8, usados 3. Consulta completa en `registro/consultas/2026-09-16-161744.json`.*

## Tabla de veredictos

| # | Pregunta | Fragmentos usados | Veredicto de Mariano |
|---|---|---|---|
| 0 | que condiciones sobre la sucesion M usa el teorema de extens... | [jimenez-garrido-cantero-sanz-schindl-2022:p16]; [jimenez-garrido-tesis-2018:p13] | |
| a | Segun Thilliez 2010, que hipotesis sobre M exige el resultad... | [thilliez-2010:p1]; [thilliez-2010:p7] | |
| b | Que relacion demuestran Jimenez-Garrido y Sanz (2016) entre ... | [jimenez-garrido-sanz-2021:p21]; [jimenez-garrido-tesis-2018:p16] | |
| c | Como se define la M-sumabilidad en una direccion en Lastra-M... | [lastra-malek-sanz-2022:p19]; [jimenez-garrido-tesis-2018:p14]; [lastra-malek-sanz-2022:p1]; [lastra-malek-sanz-2022:p7] | |
| d | En Jimenez-Garrido-Sanz-Schindl 2019, que indice separa las ... | [jimenez-garrido-tesis-2018:p14]; [jimenez-garrido-tesis-2018:p14] | |
| e | Que prueba el corpus sobre la sumabilidad de soluciones de e... | [jimenez-garrido-tesis-2018:p199]; [jimenez-garrido-sanz-2021:p1]; [lastra-malek-sanz-2022:p1] | |
