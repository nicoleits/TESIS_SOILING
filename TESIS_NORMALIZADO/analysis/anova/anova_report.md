# Análisis ANOVA — SR Semanal Q25 (t₀=100% excepto IV600 Pmax/Isc en valor absoluto)

**Variable dependiente:** SR semanal Q25 (t₀=100% excepto IV600 Pmax/Isc en valor absoluto)  
**Nivel de significancia:** α = 0.05  
**Factor:** instrumento (Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, IV600 Pmax, IV600 Isc)

---
## Conjunto: Pool completo

**N total de observaciones:** 313  
**Semanas por instrumento:**

- DustIQ: n=54
- IV600 Isc: n=29
- IV600 Pmax: n=29
- PV Glasses: n=11
- PVStand Isc: n=50
- PVStand Pmax: n=50
- RefCells: n=36
- Soiling Kit: n=54

### 1. Supuestos

#### Normalidad (Shapiro-Wilk por grupo)

| Instrumento | n | W | p | ¿Normal α=0.05? |
|---|---|---|---|---|
| DustIQ | 54 | 0.9327 | 0.0047 | ✗ |
| IV600 Isc | 29 | 0.8713 | 0.0022 | ✗ |
| IV600 Pmax | 29 | 0.9299 | 0.0547 | ✓ |
| PV Glasses | 11 | 0.9070 | 0.2245 | ✓ |
| PVStand Isc | 50 | 0.9414 | 0.0153 | ✗ |
| PVStand Pmax | 50 | 0.9503 | 0.0351 | ✗ |
| RefCells | 36 | 0.9079 | 0.0057 | ✗ |
| Soiling Kit | 54 | 0.9355 | 0.0061 | ✗ |

#### Homocedasticidad (Levene)

- Estadístico: 13.9891  
- p-valor: 0.0  
- Resultado: ✗ heterocedástico

### 2. ANOVA paramétrico (f_oneway)

- F = 83.3474,  **p < 0.001** → diferencia altamente significativa (ANOVA)

### 3. Kruskal-Wallis (no paramétrico)

- H = 130.0405,  **p < 0.001** → diferencia altamente significativa (Kruskal-Wallis)

### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)

| Par | Diferencia de medias | p_adj |
|---|---|---|
| DustIQ vs PV Glasses | -3.367 pp | 0.0000 |
| DustIQ vs PVStand Pmax | -7.210 pp | 0.0000 |
| IV600 Isc vs PV Glasses | -3.515 pp | 0.0000 |
| IV600 Isc vs PVStand Pmax | -7.358 pp | 0.0000 |
| IV600 Pmax vs PV Glasses | -3.770 pp | 0.0000 |
| IV600 Pmax vs PVStand Pmax | -7.613 pp | 0.0000 |
| PV Glasses vs PVStand Isc | 2.872 pp | 0.0004 |
| PV Glasses vs PVStand Pmax | -3.843 pp | 0.0000 |
| PV Glasses vs RefCells | 4.199 pp | 0.0000 |
| PV Glasses vs Soiling Kit | 2.973 pp | 0.0002 |
| PVStand Isc vs PVStand Pmax | -6.715 pp | 0.0000 |
| PVStand Isc vs RefCells | 1.327 pp | 0.0463 |
| PVStand Pmax vs RefCells | 8.042 pp | 0.0000 |
| PVStand Pmax vs Soiling Kit | 6.815 pp | 0.0000 |

### 5. Post-hoc Dunn + Bonferroni (pares significativos, p_adj < 0.05)

| Par | p_adj (Bonferroni) |
|---|---|
| DustIQ vs PVStand Pmax | 0.0000 |
| IV600 Isc vs PVStand Pmax | 0.0000 |
| IV600 Pmax vs PVStand Pmax | 0.0000 |
| PV Glasses vs RefCells | 0.0342 |
| PVStand Isc vs PVStand Pmax | 0.0000 |
| PVStand Isc vs RefCells | 0.0187 |
| PVStand Pmax vs RefCells | 0.0000 |
| PVStand Pmax vs Soiling Kit | 0.0000 |
| RefCells vs Soiling Kit | 0.0428 |

---
## Conjunto: Intersección

**N total de observaciones:** 48  
**Semanas por instrumento:**

- DustIQ: n=6
- IV600 Isc: n=6
- IV600 Pmax: n=6
- PV Glasses: n=6
- PVStand Isc: n=6
- PVStand Pmax: n=6
- RefCells: n=6
- Soiling Kit: n=6

### 1. Supuestos

#### Normalidad (Shapiro-Wilk por grupo)

| Instrumento | n | W | p | ¿Normal α=0.05? |
|---|---|---|---|---|
| DustIQ | 6 | 0.9190 | 0.4984 | ✓ |
| IV600 Isc | 6 | 0.9660 | 0.8646 | ✓ |
| IV600 Pmax | 6 | 0.9664 | 0.8673 | ✓ |
| PV Glasses | 6 | 0.8410 | 0.1329 | ✓ |
| PVStand Isc | 6 | 0.9150 | 0.4703 | ✓ |
| PVStand Pmax | 6 | 0.8907 | 0.3221 | ✓ |
| RefCells | 6 | 0.8829 | 0.2826 | ✓ |
| Soiling Kit | 6 | 0.6863 | 0.0044 | ✗ |

#### Homocedasticidad (Levene)

- Estadístico: 11.19  
- p-valor: 0.0  
- Resultado: ✗ heterocedástico

### 2. ANOVA paramétrico (f_oneway)

- F = 27.3533,  **p < 0.001** → diferencia altamente significativa (ANOVA)

### 3. Kruskal-Wallis (no paramétrico)

- H = 27.8673,  **p < 0.001** → diferencia altamente significativa (Kruskal-Wallis)

### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)

| Par | Diferencia de medias | p_adj |
|---|---|---|
| DustIQ vs PV Glasses | -4.598 pp | 0.0000 |
| DustIQ vs PVStand Pmax | -7.213 pp | 0.0000 |
| IV600 Isc vs PV Glasses | -4.899 pp | 0.0000 |
| IV600 Isc vs PVStand Pmax | -7.513 pp | 0.0000 |
| IV600 Pmax vs PV Glasses | -5.261 pp | 0.0000 |
| IV600 Pmax vs PVStand Pmax | -7.875 pp | 0.0000 |
| PV Glasses vs PVStand Isc | 4.630 pp | 0.0000 |
| PV Glasses vs PVStand Pmax | -2.614 pp | 0.0431 |
| PV Glasses vs RefCells | 5.298 pp | 0.0000 |
| PV Glasses vs Soiling Kit | 4.705 pp | 0.0000 |
| PVStand Isc vs PVStand Pmax | -7.244 pp | 0.0000 |
| PVStand Pmax vs RefCells | 7.912 pp | 0.0000 |
| PVStand Pmax vs Soiling Kit | 7.319 pp | 0.0000 |

### 5. Post-hoc Dunn + Bonferroni (pares significativos, p_adj < 0.05)

| Par | p_adj (Bonferroni) |
|---|---|
| IV600 Isc vs PVStand Pmax | 0.0390 |
| IV600 Pmax vs PV Glasses | 0.0390 |
| IV600 Pmax vs PVStand Pmax | 0.0063 |
| PV Glasses vs RefCells | 0.0272 |
| PVStand Pmax vs RefCells | 0.0042 |

---
## Conclusión general

El análisis ANOVA evalúa si los instrumentos
evolucionan de forma estadísticamente equivalente una vez eliminado el sesgo
de nivel absoluto. Un resultado significativo indica que la **tasa de cambio**
del SR difiere entre instrumentos, lo que implica que no son intercambiables
para el seguimiento del soiling.
