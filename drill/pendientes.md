# Pendientes

Una tarjeta por linea con el separador de dos puntos dobles.
Las generan cierre, lagunas y diagnostico. No fabriques tarjetas a mano.

Definicion de clase de Carleman-Roumieu A_{M}(S) :: existe A>0 tal que sup |f^(p)(z)| / (A^p p! M_p) < inf sobre z en S y p en N_0
Diferencia Roumieu / Beurling :: Roumieu existe A, Beurling para todo A

<!-- 2026-09-14 diagnostico -->
¿Qué hipótesis permiten aplicar la fórmula integral de Cauchy en un disco cerrado? :: Que f sea holomorfa en un abierto que contenga el disco cerrado D(a,R). Para n ≥ 0: f^(n)(a) = n!/(2πi) ∮ f(ζ)/(ζ−a)^(n+1) dζ, integrando sobre la circunferencia con orientación positiva.
¿Cuál es la estimación de Cauchy para f^(n)(a)? :: Si f es holomorfa cerca de D(a,R) y M_R = max_{|z−a|=R}|f(z)|, entonces |f^(n)(a)| ≤ n! M_R/R^n.
¿Cómo acotan las estimaciones de Cauchy los coeficientes de Taylor? :: Si f(z) = Σ c_n(z−a)^n, entonces c_n = f^(n)(a)/n! y |c_n| ≤ M_R/R^n.
¿Qué estimación interior se obtiene entre dos discos concéntricos? :: Si f es holomorfa en D(a,R), |f| ≤ M allí y 0 < r < R, entonces sup_{|z−a|≤r}|f^(n)(z)| ≤ n! M/(R−r)^n.
¿Qué control proporcionan las estimaciones de Cauchy? :: Transforman una cota de la función en cotas de sus derivadas y coeficientes de Taylor. La distancia disponible hasta el borde aparece en el denominador.
¿Por qué el principio del máximo en dominios acotados no basta para controlar una función en un sector infinito? :: Al truncar el sector aparece un arco exterior. Las cotas sobre los dos rayos no controlan por sí solas los valores en ese arco.
Enuncia una versión clásica de Phragmén-Lindelöf para un sector. :: Sea S un sector de abertura θ, con 0 < θ < 2π. Si f es holomorfa en S, continua en su cierre, |f| ≤ M en los rayos fronterizos y |f(z)| ≤ C exp(A|z|^ρ) en S, con A,C > 0 y 0 < ρ < π/θ, entonces |f| ≤ M en S.
¿Qué relación entre crecimiento y abertura aparece en esa versión de Phragmén-Lindelöf? :: La condición es ρ < π/θ, siendo θ la abertura total en radianes. Es una desigualdad estricta.
¿Por qué no puede incluirse sin más el exponente crítico en Phragmén-Lindelöf? :: En el semiplano derecho, de abertura π, f(z)=exp(z) tiene módulo 1 en la frontera y crecimiento de exponente 1, pero no está acotada dentro.
¿Qué afirma el teorema de Borel sobre jets suaves en un punto? :: Para cualquier sucesión (a_n) de números reales existe f ∈ C∞(R) tal que f^(n)(0)=a_n para todo n ≥ 0. Esta tarjeta usa la versión sobre jets suaves; hay que confirmar que sea la del diagnóstico.
¿Cómo se distinguen los valores de las derivadas y los coeficientes de Taylor en el teorema de Borel? :: Si f^(n)(0)=a_n, su serie de Taylor formal es Σ (a_n/n!)x^n. Para prescribir coeficientes c_n se prescriben derivadas n!c_n.
¿El teorema de Borel sobre jets garantiza analiticidad o unicidad? :: No. La serie prescrita puede divergir. Tampoco hay unicidad: pueden añadirse funciones suaves no nulas cuyas derivadas de todos los órdenes se anulan en 0.
¿Cómo se define la transformada de Laplace unilateral clásica? :: L[f](s)=∫_0^∞ exp(−st)f(t) dt, para los valores complejos de s en los que la integral converge.
Da una condición suficiente para la convergencia absoluta de la transformada de Laplace. :: Si f es localmente integrable en [0,∞) y |f(t)| ≤ C exp(at) para t suficientemente grande, la integral converge absolutamente cuando Re(s)>a.
¿Cuál es la transformada de Laplace de t^n, para n entero no negativo? :: L[t^n](s)=n!/s^(n+1), para Re(s)>0.
¿Cómo transforma Laplace una derivada? :: Si f ∈ C¹([0,∞)) y f y f' son de orden exponencial, entonces L[f'](s)=sL[f](s)−f(0), para Re(s) suficientemente grande.
¿Cuál es la definición exacta de la clase de Carleman-Roumieu utilizada en tu fuente? :: Pendiente de pegar la definición del paper. Hay que registrar dominio, estimación, normalización de la sucesión y orden completo de los cuantificadores; no completo la fórmula sin esa fuente. [VERIFICAR CON PAPER]
¿Cuál es la definición exacta de la clase de Carleman-Beurling utilizada en tu fuente? :: Pendiente de pegar la definición del paper. Hay que registrar la fórmula y sus cuantificadores literalmente antes de compararla con Roumieu. [VERIFICAR CON PAPER]
¿Qué significa «sucesión fuertemente regular» en el artículo que vas a estudiar? :: Pendiente de pegar la definición: condiciones completas, índices, constantes y normalización inicial. No reconstruyo de memoria las convenciones de (γ₁), (mg) o (dc). [VERIFICAR CON PAPER]
¿Cómo define tu fuente la transformada de Borel formal? :: Pendiente del fragmento correspondiente. La tarjeta definitiva debe incluir la acción sobre cada monomio, los parámetros y la normalización exacta. [VERIFICAR CON PAPER]
¿Qué significa que una serie sea k-sumable en una dirección según tu fuente? :: Pendiente de pegar la definición. Deben quedar especificados k, la dirección, los dominios y todas las condiciones exigidas, sin importar convenciones de otro texto. [VERIFICAR CON PAPER]
¿Qué definiciones necesitas fijar para leer el enunciado que recuerdas de Thilliez 2010? :: Pendiente de pegar el enunciado y las definiciones a las que remite. Solo entonces puede identificarse y desglosarse su vocabulario técnico sin inventarlo. [VERIFICAR CON PAPER]
