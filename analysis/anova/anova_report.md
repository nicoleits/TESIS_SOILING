# Análisis ANOVA — SR Semanal Q25 Normalizado

**Variable dependiente:** SR semanal Q25 normalizado a t₀ = 100%  
**Nivel de significancia:** α = 0.05  
**Factor:** instrumento (Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, IV600, IV600 corr)

---
## Conjunto: Pool completo

**N total de observaciones:** 308  
**Semanas por instrumento:**

- DustIQ: n=54
- IV600: n=30
- IV600 corr: n=29
- PVStand: n=54
- PVStand corr: n=50
- RefCells: n=37
- Soiling Kit: n=54

### 1. Supuestos

#### Normalidad (Shapiro-Wilk por grupo)

| Instrumento | n | W | p | ¿Normal α=0.05? |
|---|---|---|---|---|
| DustIQ | 54 | 0.9327 | 0.0047 | ✗ |
| IV600 | 30 | 0.9235 | 0.0332 | ✗ |
| IV600 corr | 29 | 0.9299 | 0.0547 | ✓ |
| PVStand | 54 | 0.9062 | 0.0005 | ✗ |
| PVStand corr | 50 | 0.9503 | 0.0351 | ✗ |
| RefCells | 37 | 0.9141 | 0.0074 | ✗ |
| Soiling Kit | 54 | 0.9355 | 0.0061 | ✗ |

#### Homocedasticidad (Levene)

- Estadístico: 8.6841  
- p-valor: 0.0  
- Resultado: ✗ heterocedástico

### 2. ANOVA paramétrico (f_oneway)

- F = 182.3813,  **p < 0.001** → diferencia altamente significativa (ANOVA)

### 3. Kruskal-Wallis (no paramétrico)

- H = 200.6049,  **p < 0.001** → diferencia altamente significativa (Kruskal-Wallis)

### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)

| Par | Diferencia de medias | p_adj |
|---|---|---|
| DustIQ vs PVStand | -8.100 pp | 0.0000 |
| DustIQ vs PVStand corr | -7.210 pp | 0.0000 |
| IV600 vs PVStand | -7.961 pp | 0.0000 |
| IV600 vs PVStand corr | -7.071 pp | 0.0000 |
| IV600 corr vs PVStand | -8.834 pp | 0.0000 |
| IV600 corr vs PVStand corr | -7.945 pp | 0.0000 |
| PVStand vs RefCells | 8.870 pp | 0.0000 |
| PVStand vs Soiling Kit | 7.705 pp | 0.0000 |
| PVStand corr vs RefCells | 7.980 pp | 0.0000 |
| PVStand corr vs Soiling Kit | 6.815 pp | 0.0000 |

### 5. Post-hoc Dunn + Bonferroni (pares significativos, p_adj < 0.05)

| Par | p_adj (Bonferroni) |
|---|---|
| DustIQ vs PVStand | 0.0000 |
| DustIQ vs PVStand corr | 0.0000 |
| IV600 vs PVStand | 0.0000 |
| IV600 vs PVStand corr | 0.0000 |
| IV600 corr vs PVStand | 0.0000 |
| IV600 corr vs PVStand corr | 0.0000 |
| PVStand vs RefCells | 0.0000 |
| PVStand vs Soiling Kit | 0.0000 |
| PVStand corr vs RefCells | 0.0000 |
| PVStand corr vs Soiling Kit | 0.0000 |

---
## Conjunto: Intersección

**N total de observaciones:** 182  
**Semanas por instrumento:**

- DustIQ: n=26
- IV600: n=26
- IV600 corr: n=26
- PVStand: n=26
- PVStand corr: n=26
- RefCells: n=26
- Soiling Kit: n=26

### 1. Supuestos

#### Normalidad (Shapiro-Wilk por grupo)

| Instrumento | n | W | p | ¿Normal α=0.05? |
|---|---|---|---|---|
| DustIQ | 26 | 0.9724 | 0.6855 | ✓ |
| IV600 | 26 | 0.9131 | 0.0310 | ✗ |
| IV600 corr | 26 | 0.9186 | 0.0416 | ✗ |
| PVStand | 26 | 0.8860 | 0.0077 | ✗ |
| PVStand corr | 26 | 0.9162 | 0.0367 | ✗ |
| RefCells | 26 | 0.8382 | 0.0008 | ✗ |
| Soiling Kit | 26 | 0.9333 | 0.0930 | ✓ |

#### Homocedasticidad (Levene)

- Estadístico: 4.5494  
- p-valor: 0.0003  
- Resultado: ✗ heterocedástico

### 2. ANOVA paramétrico (f_oneway)

- F = 223.6409,  **p < 0.001** → diferencia altamente significativa (ANOVA)

### 3. Kruskal-Wallis (no paramétrico)

- H = 118.4655,  **p < 0.001** → diferencia altamente significativa (Kruskal-Wallis)

### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)

| Par | Diferencia de medias | p_adj |
|---|---|---|
| DustIQ vs PVStand | -8.322 pp | 0.0000 |
| DustIQ vs PVStand corr | -7.046 pp | 0.0000 |
| IV600 vs PVStand | -8.107 pp | 0.0000 |
| IV600 vs PVStand corr | -6.831 pp | 0.0000 |
| IV600 corr vs PVStand | -9.072 pp | 0.0000 |
| IV600 corr vs PVStand corr | -7.796 pp | 0.0000 |
| PVStand vs PVStand corr | 1.276 pp | 0.0111 |
| PVStand vs RefCells | 8.796 pp | 0.0000 |
| PVStand vs Soiling Kit | 8.294 pp | 0.0000 |
| PVStand corr vs RefCells | 7.520 pp | 0.0000 |
| PVStand corr vs Soiling Kit | 7.018 pp | 0.0000 |

### 5. Post-hoc Dunn + Bonferroni (pares significativos, p_adj < 0.05)

| Par | p_adj (Bonferroni) |
|---|---|
| DustIQ vs PVStand | 0.0000 |
| DustIQ vs PVStand corr | 0.0000 |
| IV600 vs PVStand | 0.0000 |
| IV600 vs PVStand corr | 0.0001 |
| IV600 corr vs PVStand | 0.0000 |
| IV600 corr vs PVStand corr | 0.0000 |
| PVStand vs RefCells | 0.0000 |
| PVStand vs Soiling Kit | 0.0000 |
| PVStand corr vs RefCells | 0.0000 |
| PVStand corr vs Soiling Kit | 0.0000 |

---
## Conclusión general

El análisis ANOVA sobre los datos normalizados evalúa si los instrumentos
evolucionan de forma estadísticamente equivalente una vez eliminado el sesgo
de nivel absoluto. Un resultado significativo indica que la **tasa de cambio**
del SR difiere entre instrumentos, lo que implica que no son intercambiables
para el seguimiento del soiling.
