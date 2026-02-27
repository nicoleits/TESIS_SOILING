# Análisis ANOVA — SR Semanal Q25 Normalizado

**Variable dependiente:** SR semanal Q25 normalizado a t₀ = 100%  
**Nivel de significancia:** α = 0.05  
**Factor:** instrumento (Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, IV600, IV600 corr)

---
## Conjunto: Pool completo

**N total de observaciones:** 304  
**Semanas por instrumento:**

- DustIQ: n=53
- IV600: n=30
- IV600 corr: n=29
- PVStand: n=53
- PVStand corr: n=50
- RefCells: n=36
- Soiling Kit: n=53

### 1. Supuestos

#### Normalidad (Shapiro-Wilk por grupo)

| Instrumento | n | W | p | ¿Normal α=0.05? |
|---|---|---|---|---|
| DustIQ | 53 | 0.9305 | 0.0042 | ✗ |
| IV600 | 30 | 0.9235 | 0.0332 | ✗ |
| IV600 corr | 29 | 0.9299 | 0.0547 | ✓ |
| PVStand | 53 | 0.9293 | 0.0038 | ✗ |
| PVStand corr | 50 | 0.9625 | 0.1136 | ✓ |
| RefCells | 36 | 0.9079 | 0.0056 | ✗ |
| Soiling Kit | 53 | 0.9372 | 0.0078 | ✗ |

#### Homocedasticidad (Levene)

- Estadístico: 9.7231  
- p-valor: 0.0  
- Resultado: ✗ heterocedástico

### 2. ANOVA paramétrico (f_oneway)

- F = 111.626,  **p < 0.001** → diferencia altamente significativa (ANOVA)

### 3. Kruskal-Wallis (no paramétrico)

- H = 186.2179,  **p < 0.001** → diferencia altamente significativa (Kruskal-Wallis)

### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)

| Par | Diferencia de medias | p_adj |
|---|---|---|
| DustIQ vs PVStand | -6.042 pp | 0.0000 |
| DustIQ vs PVStand corr | -5.663 pp | 0.0000 |
| IV600 vs PVStand | -5.855 pp | 0.0000 |
| IV600 vs PVStand corr | -5.476 pp | 0.0000 |
| IV600 corr vs PVStand | -6.729 pp | 0.0000 |
| IV600 corr vs PVStand corr | -6.349 pp | 0.0000 |
| PVStand vs RefCells | 6.848 pp | 0.0000 |
| PVStand vs Soiling Kit | 5.670 pp | 0.0000 |
| PVStand corr vs RefCells | 6.468 pp | 0.0000 |
| PVStand corr vs Soiling Kit | 5.290 pp | 0.0000 |

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

- Estadístico: 4.7438  
- p-valor: 0.0002  
- Resultado: ✗ heterocedástico

### 2. ANOVA paramétrico (f_oneway)

- F = 128.7499,  **p < 0.001** → diferencia altamente significativa (ANOVA)

### 3. Kruskal-Wallis (no paramétrico)

- H = 117.7726,  **p < 0.001** → diferencia altamente significativa (Kruskal-Wallis)

### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)

| Par | Diferencia de medias | p_adj |
|---|---|---|
| DustIQ vs PVStand | -6.272 pp | 0.0000 |
| DustIQ vs PVStand corr | -5.434 pp | 0.0000 |
| IV600 vs PVStand | -6.032 pp | 0.0000 |
| IV600 vs PVStand corr | -5.194 pp | 0.0000 |
| IV600 corr vs PVStand | -6.998 pp | 0.0000 |
| IV600 corr vs PVStand corr | -6.159 pp | 0.0000 |
| PVStand vs RefCells | 6.744 pp | 0.0000 |
| PVStand vs Soiling Kit | 6.248 pp | 0.0000 |
| PVStand corr vs RefCells | 5.905 pp | 0.0000 |
| PVStand corr vs Soiling Kit | 5.410 pp | 0.0000 |

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
## Conclusión general

El análisis ANOVA sobre los datos normalizados evalúa si los instrumentos
evolucionan de forma estadísticamente equivalente una vez eliminado el sesgo
de nivel absoluto. Un resultado significativo indica que la **tasa de cambio**
del SR difiere entre instrumentos, lo que implica que no son intercambiables
para el seguimiento del soiling.
