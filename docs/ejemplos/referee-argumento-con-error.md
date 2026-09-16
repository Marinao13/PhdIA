# Prueba del referee: argumento con un error plantado

## Lema

Sea $M=(M_p)$ fuertemente regular y $S$ un sector de abertura $\gamma\pi$ con $\gamma < \gamma(M)$.
Sea $f \in \mathcal{A}_{\{M\}}(S)$ (clase de Roumieu), es decir, existe $A>0$ y $C>0$ tales que
$|f^{(p)}(z)| \le C A^p p! M_p$ para todo $z\in S$ y todo $p\in\mathbb{N}_0$.
Entonces $f \in \mathcal{A}_{(M)}(S)$ (clase de Beurling).

## Demostracion

Por hipotesis existe $A>0$ con la estimacion anterior. Dado cualquier $B>0$, como $M$ tiene
crecimiento moderado, existe una constante $K$ tal que $A^p \le K B^p$ para todo $p$, luego
$|f^{(p)}(z)| \le C K B^p p! M_p$. Como $B$ era arbitrario, $f$ esta en la clase de Beurling.
Ademas la estimacion es uniforme en todo el sector $S$ porque lo era en cada subsector propio
$S' \Subset S$ y basta tomar la union. Por el teorema de extension de Thilliez, la aplicacion de
Borel es entonces sobreyectiva en $\mathcal{A}_{(M)}(S)$.
