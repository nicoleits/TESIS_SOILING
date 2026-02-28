# Informe Comparativo: ANOVA y Correlación Cruzada entre Instrumentos de Soiling

**Variable de análisis:** SR semanal Q25 normalizado (t₀ = 100%)  
**Período:** agosto 2024 – julio 2025 (según disponibilidad por instrumento)  
**Instrumentos:** Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, IV600, IV600 corr  
**Nivel de significancia:** α = 0.05  

> **Nota sobre normalización:** Todos los SR se normalizaron al valor de la primera semana disponible de cada instrumento (t₀ = 100%). Esto elimina el sesgo de nivel absoluto entre instrumentos y permite comparar únicamente la **evolución temporal relativa** del soiling.

> **Nota sobre RefCells:** Los datos de RefCells se limitan hasta el 18 de mayo de 2025 por problema instrumental posterior a esa fecha.

---

## 1. Estadísticos descriptivos del SR semanal Q25

| Instrumento | N semanas | Media Q25 (%) | Std (pp) | CV (%) | Rango P95–P05 (pp) |
|---|---|---|---|---|---|
| Soiling Kit | 53 | 97.14 | 1.67 | 1.72 | 5.08 |
| DustIQ | 53 | 96.91 | 0.94 | 0.97 | 2.85 |
| RefCells | 36 | 97.71 | 1.33 | 1.36 | 3.38 |
| PVStand | 53 | 88.52 | 2.52 | 2.85 | 7.55 |
| PVStand corr | 50 | 89.44 | 2.79 | 3.12 | 8.17 |
| IV600 | 30 | 96.76 | 1.16 | 1.19 | 3.41 |
| IV600 corr | 29 | 98.07 | 1.27 | 1.29 | 3.80 |

**Observaciones:**
- PVStand y PVStand corr registran un SR medio ~8–9 pp por debajo del resto de instrumentos, lo que indica un **sesgo sistemático de nivel absoluto**.
- DustIQ e IV600 presentan la menor dispersión semanal (CV < 1.2%), siendo los instrumentos más estables.
- La corrección de temperatura en IV600 eleva la media de 96.8% → 98.1%, sugiriendo un leve sesgo térmico sin corregir.

---

## 2. ANOVA de un factor

### 2.1 Pregunta de investigación

> ¿Existe diferencia estadísticamente significativa en el SR normalizado medio entre los distintos instrumentos?

### 2.2 Verificación de supuestos

**Normalidad (Shapiro-Wilk, pool completo):**

| Instrumento | W | p | ¿Normal? |
|---|---|---|---|
| DustIQ | 0.9305 | 0.0042 | ✗ |
| IV600 | 0.9235 | 0.0332 | ✗ |
| IV600 corr | 0.9299 | 0.0547 | ✓ |
| PVStand | 0.9293 | 0.0038 | ✗ |
| PVStand corr | 0.9625 | 0.1136 | ✓ |
| RefCells | 0.9079 | 0.0056 | ✗ |
| Soiling Kit | 0.9372 | 0.0078 | ✗ |

**Homocedasticidad (Levene):** estadístico = 9.72, p ≈ 0.000 → **varianzas heterogéneas**.

Los supuestos del ANOVA paramétrico clásico **no se cumplen** en la mayoría de los grupos. Por tanto, el **Kruskal-Wallis** (no paramétrico) es el test de referencia, aunque ambos se reportan para completitud.

### 2.3 Resultados

| Conjunto | Test | Estadístico | p-valor | Conclusión |
|---|---|---|---|---|
| Pool (N=304) | ANOVA (F) | 111.63 | < 0.001 | Significativo |
| Pool (N=304) | Kruskal-Wallis (H) | 186.22 | < 0.001 | Significativo |
| Intersección (N=182, 26 semanas) | ANOVA (F) | 128.75 | < 0.001 | Significativo |
| Intersección (N=182, 26 semanas) | Kruskal-Wallis (H) | 117.77 | < 0.001 | Significativo |

Ambos tests, en ambos conjuntos de datos, rechazan la hipótesis nula. **Existe diferencia altamente significativa en el SR normalizado medio entre instrumentos.**

### 2.4 Post-hoc Tukey HSD y Dunn–Bonferroni

Los post-hoc identifican qué pares concretos difieren. Los resultados de Tukey y Dunn coinciden en ambos conjuntos:

**Pares significativos (p_adj < 0.05):**

| Par | Diferencia de medias | p_adj (Tukey) |
|---|---|---|
| DustIQ vs PVStand | −6.04 pp | < 0.001 |
| DustIQ vs PVStand corr | −5.66 pp | < 0.001 |
| IV600 vs PVStand | −5.86 pp | < 0.001 |
| IV600 vs PVStand corr | −5.48 pp | < 0.001 |
| IV600 corr vs PVStand | −6.73 pp | < 0.001 |
| IV600 corr vs PVStand corr | −6.35 pp | < 0.001 |
| PVStand vs RefCells | +6.85 pp | < 0.001 |
| PVStand vs Soiling Kit | +5.67 pp | < 0.001 |
| PVStand corr vs RefCells | +6.47 pp | < 0.001 |
| PVStand corr vs Soiling Kit | +5.29 pp | < 0.001 |

**Pares NO significativos** (todos los demás): Soiling Kit vs DustIQ, Soiling Kit vs RefCells, Soiling Kit vs IV600, DustIQ vs RefCells, DustIQ vs IV600, RefCells vs IV600, y sus variantes con corrección de temperatura.

### 2.5 Grupos estadísticos resultantes del ANOVA

El análisis post-hoc identifica dos grupos estadísticamente distinguibles:

| Grupo | Instrumentos | SR norm. medio |
|---|---|---|
| **Grupo A** | Soiling Kit, DustIQ, RefCells, IV600, IV600 corr | ~97–98% |
| **Grupo B** | PVStand, PVStand corr | ~88–89% |

Todos los pares A×B son significativos. Ningún par dentro de A ni dentro de B lo es.

---

## 3. Análisis de Correlación de Pearson

### 3.1 Pregunta de investigación

> ¿Los instrumentos siguen la misma tendencia temporal de soiling, independientemente de su nivel absoluto de SR?

### 3.2 Resultados completos

| Par | r Pearson | n semanas | Bias (pp) | RMSE (pp) |
|---|---|---|---|---|
| PVStand vs PVStand corr | **0.960** | 50 | −0.35 | 0.87 |
| RefCells vs IV600 | **0.943** | 26 | 0.71 | 0.81 |
| Soiling Kit vs DustIQ | **0.922** | 53 | −0.37 | 0.95 |
| Soiling Kit vs RefCells | **0.914** | 36 | −0.38 | 0.67 |
| DustIQ vs RefCells | **0.900** | 36 | −0.41 | 0.78 |
| Soiling Kit vs IV600 | **0.900** | 30 | 0.16 | 0.52 |
| IV600 vs IV600 corr | 0.887 | 29 | −0.88 | 1.05 |
| DustIQ vs IV600 corr | 0.868 | 29 | −0.67 | 1.05 |
| Soiling Kit vs PVStand corr | 0.865 | 50 | **5.34** | 5.59 |
| PVStand vs IV600 | 0.848 | 30 | **−5.99** | 6.06 |
| DustIQ vs PVStand corr | 0.844 | 50 | **5.70** | 6.07 |
| Soiling Kit vs PVStand | 0.842 | 53 | **5.67** | 5.86 |
| DustIQ vs PVStand | 0.833 | 53 | **6.04** | 6.33 |
| RefCells vs IV600 corr | 0.832 | 26 | −0.25 | 0.72 |
| DustIQ vs IV600 | 0.831 | 30 | 0.22 | 0.77 |
| Soiling Kit vs IV600 corr | 0.829 | 29 | −0.71 | 1.00 |
| PVStand vs IV600 corr | 0.772 | 29 | **−6.87** | 6.95 |
| PVStand corr vs IV600 corr | 0.738 | 29 | **−6.11** | 6.24 |
| RefCells vs PVStand | 0.723 | 36 | **5.96** | 6.23 |
| PVStand corr vs IV600 | 0.709 | 29 | **−5.23** | 5.40 |
| RefCells vs PVStand corr | 0.693 | 36 | **5.36** | 5.65 |

Todos los pares son estadísticamente significativos (p < 0.001).

---

## 4. Diferencias entre los resultados del ANOVA y de la Correlación

Estos dos análisis responden **preguntas distintas** sobre los mismos datos, y sus resultados no son contradictorios sino complementarios.

### 4.1 Lo que detecta el ANOVA

El ANOVA compara los **niveles medios** del SR normalizado entre instrumentos. Encontró que PVStand y PVStand corr tienen una media significativamente más baja que el resto (~6–7 pp de diferencia). Esto implica que la **distribución central** de los valores de SR normalizado es diferente.

**Lo que no responde el ANOVA:** si esa diferencia se debe a que PVStand sigue una trayectoria temporal distinta, o simplemente a que tiene un sesgo constante hacia abajo.

### 4.2 Lo que detecta la Correlación

La correlación de Pearson mide si dos series **suben y bajan juntas** en el tiempo, independientemente del nivel. Aquí los resultados muestran que:

- PVStand correlaciona altamente con todos los demás instrumentos: r = 0.69–0.96.
- En particular, PVStand vs Soiling Kit (r = 0.84), PVStand vs DustIQ (r = 0.83), PVStand vs IV600 (r = 0.85).

**Lo que esto implica:** PVStand **sigue la misma tendencia temporal del soiling** que el resto. Cuando hay un evento de suciedad, PVStand lo detecta al mismo tiempo y con la misma dirección que los demás instrumentos.

### 4.3 Síntesis interpretativa

| Dimensión | ANOVA | Correlación | Diagnóstico |
|---|---|---|---|
| Nivel absoluto de SR | PVStand ≠ resto (p < 0.001) | No evalúa niveles | **Sesgo sistemático** en PVStand |
| Tendencia temporal | No evalúa tendencias | PVStand ↔ resto (r ≥ 0.70) | **Dinámica compartida** |
| ¿Son intercambiables? | No, por diferencia de nivel | Sí, por dinámica equivalente | Intercambiables **con corrección de sesgo** |

### 4.4 Hipótesis sobre el origen del sesgo en PVStand

El hecho de que PVStand registre SR ~8 pp menor que los demás instrumentos de forma persistente, pero siguiendo la misma evolución temporal, apunta a una o varias de estas causas físicas:

1. **Diferencia en el área expuesta al soiling** entre el módulo sucio (1MD440) y el de referencia (1MD439): si el módulo de referencia no está perfectamente limpio, el SR se subestima sistemáticamente.
2. **Efecto de la temperatura:** aunque se dispone de corrección de temperatura (PVStand corr), la diferencia de nivel persiste, lo que sugiere que la corrección no es la causa principal.
3. **Diferencia en el ángulo de inclinación o sombreado parcial** entre módulos, que afecta la irradiancia incidente de forma diferencial.
4. **Tipo de parámetro medido:** PVStand usa Pmax (potencia máxima), que integra tanto Isc como Voc y factor de forma, mientras que otros instrumentos usan Isc. La degradación de la curva IV por soiling puede afectar Pmax de forma diferente a Isc.

---

## 5. Conclusiones

1. **Todos los instrumentos detectan el mismo fenómeno de soiling** en términos de evolución temporal: correlaciones de Pearson entre r = 0.69 y r = 0.96, todas significativas.

2. **PVStand y PVStand corr forman un grupo estadísticamente separado** del resto en nivel absoluto de SR (~8–9 pp menor), lo que el ANOVA confirma con alta significancia (p < 0.001).

3. **La separación detectada por el ANOVA no implica una dinámica diferente**, sino un sesgo sistemático constante. La correlación cruzada confirma que PVStand es coherente temporalmente con los demás instrumentos.

4. **El par más cercano en ambas dimensiones** (nivel y tendencia) es Soiling Kit – DustIQ (r = 0.922, RMSE = 0.95 pp) y Soiling Kit – IV600 (r = 0.900, RMSE = 0.52 pp), siendo este último el par más preciso pese a tener solo 30 semanas en común.

5. **Para aplicaciones de monitoreo de soiling**, los instrumentos del Grupo A (Soiling Kit, DustIQ, RefCells, IV600) son estadísticamente equivalentes y pueden ser usados de forma complementaria. PVStand requeriría una corrección de sesgo para ser comparado directamente con los demás.

---

*Generado: análisis/informe_comparativo.md*  
*Scripts: analysis/anova/anova_sr.py · analysis/correlacion/correlacion_cruzada.py*
