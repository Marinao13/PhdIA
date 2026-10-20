# Cuaderno de errores

La pieza que mas compone y la primera que se abandona. Revision los viernes.
Los tipos que se repiten se convierten en el drill de la semana siguiente.

## Taxonomia

| Cod | Tipo |
|-----|------|
| Q   | Cuantificador Roumieu (existe A) frente a Beurling (para todo A) |
| C   | Uniformidad de constantes: A depende de f, de p, del subsector, del multiindice |
| S   | Sector completo frente a subsector propio y acotado |
| M   | Confusion entre condiciones sobre M (lc, mg, dc, gamma_1) y sus implicaciones |
| A   | Isotropo frente a anisotropo: control por \|alpha\| frente a control por alpha |
| F   | Serie formal frente a suma: que se afirma de cual |
| E   | Estimacion perdida: sabias que hacia falta y no diste con ella |
| P   | Abandono prematuro: consultaste antes de agotar los 25 minutos |

Q va a ser tu tipo mas frecuente. Tu proyecto vive justo en esa frontera.

## Formato

```
### AAAA-MM-DD  [COD]  contexto
Creia:
Es:
Posicion a repasar:
```

## Entradas

### 2026-09-15  [M]  EJEMPLO, borralo: Thilliez 2003, definicion de (gamma_1)
Creia: la condicion era sum 1/m_q convergente
Es: lleva un factor (q+1) en el denominador y esta en forma relativa a M_p/M_{p+1}
Posicion a repasar: seccion 1 del paper

### 2026-10-20  [E]  Tras obtener una cota para $h_M(|t|)$, se escribe una cota para $\log h_N(|t|)$.
Creia: La cota para $h_M$ se transmite directamente a $h_N$.
Es: Falta explicitar la definición de $N$ y la relación cuantitativa que permite ese cambio de función.
Posicion a repasar: Fase 3, después de «Por tanto, tomando logaritmos»

### 2026-10-20  [E]  Se afirma que «lo mismo pasa si dividimos por $1+t^2$».
Creia: Que $1+t^2\geq1$ basta para conservar sin más la estimación necesaria.
Es: No se escribe qué expresión se divide, qué sentido tiene la desigualdad tras dividir ni cuál es el integrando resultante.
Posicion a repasar: Fase 3, frase sobre dividir por $1+t^2$

### 2026-10-20  [E]  El estudio de la integral se refiere al «segundo sumando» sin haberlo definido.
Creia: La convergencia por tramos identifica por sí sola la estimación final.
Es: Se pierde el vínculo entre los exponentes calculados en los tramos y la integral concreta que concluye el lema.
Posicion a repasar: Fase 3, último párrafo
