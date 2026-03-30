# Análisis ANOVA — SR Semanal Q25 (SIN normalizar)

**Variable dependiente:** SR semanal Q25 (SIN normalizar)  
**Nivel de significancia:** α = 0.05  
**Factor:** instrumento (Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, IV600 Pmax, IV600 Isc)

---
## Conjunto: Pool completo

**N total de observaciones:** 315  
**Semanas por instrumento:**

- DustIQ: n=54
- IV600 Isc: n=29
- IV600 Pmax: n=29
- PV Glasses: n=11
- PVStand Isc: n=51
- PVStand Pmax: n=51
- RefCells: n=36
- Soiling Kit: n=54

### 1. Supuestos

#### Normalidad (Shapiro-Wilk por grupo)

| Instrumento | n | W | p | ¿Normal α=0.05? |
|---|---|---|---|---|
| DustIQ | 54 | 0.9327 | 0.0047 | ✗ |
| IV600 Isc | 29 | 0.8576 | 0.0011 | ✗ |
| IV600 Pmax | 29 | 0.9330 | 0.0659 | ✓ |
| PV Glasses | 11 | 0.9070 | 0.2245 | ✓ |
| PVStand Isc | 51 | 0.9388 | 0.0110 | ✗ |
| PVStand Pmax | 51 | 0.9539 | 0.0461 | ✗ |
| RefCells | 36 | 0.9079 | 0.0057 | ✗ |
| Soiling Kit | 54 | 0.9354 | 0.0060 | ✗ |

#### Homocedasticidad (Levene)

- Estadístico: 13.9324  
- p-valor: 0.0  
- Resultado: ✗ heterocedástico

### 2. ANOVA paramétrico (f_oneway)

- F = 109.9268,  **p < 0.001** → diferencia altamente significativa (ANOVA)

### 3. Kruskal-Wallis (no paramétrico)

- H = 155.6723,  **p < 0.001** → diferencia altamente significativa (Kruskal-Wallis)

### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)

| Par | Diferencia de medias | p_adj |
|---|---|---|
| DustIQ vs PV Glasses | -5.938 pp | 0.0000 |
| DustIQ vs PVStand Pmax | -7.504 pp | 0.0000 |
| IV600 Isc vs PV Glasses | -6.908 pp | 0.0000 |
| IV600 Isc vs PVStand Pmax | -8.474 pp | 0.0000 |
| IV600 Pmax vs PV Glasses | -7.156 pp | 0.0000 |
| IV600 Pmax vs PVStand Isc | -1.448 pp | 0.0350 |
| IV600 Pmax vs PVStand Pmax | -8.722 pp | 0.0000 |
| PV Glasses vs PVStand Isc | 5.709 pp | 0.0000 |
| PV Glasses vs RefCells | 6.765 pp | 0.0000 |
| PV Glasses vs Soiling Kit | 6.146 pp | 0.0000 |
| PVStand Isc vs PVStand Pmax | -7.275 pp | 0.0000 |
| PVStand Pmax vs RefCells | 8.331 pp | 0.0000 |
| PVStand Pmax vs Soiling Kit | 7.712 pp | 0.0000 |

### 5. Post-hoc Dunn + Bonferroni (pares significativos, p_adj < 0.05)

| Par | p_adj (Bonferroni) |
|---|---|
| DustIQ vs IV600 Pmax | 0.0355 |
| DustIQ vs PV Glasses | 0.0071 |
| DustIQ vs PVStand Pmax | 0.0000 |
| IV600 Isc vs PV Glasses | 0.0000 |
| IV600 Isc vs PVStand Pmax | 0.0000 |
| IV600 Pmax vs PV Glasses | 0.0000 |
| IV600 Pmax vs PVStand Isc | 0.0226 |
| IV600 Pmax vs PVStand Pmax | 0.0000 |
| PV Glasses vs PVStand Isc | 0.0116 |
| PV Glasses vs RefCells | 0.0000 |
| PV Glasses vs Soiling Kit | 0.0008 |
| PVStand Isc vs PVStand Pmax | 0.0000 |
| PVStand Pmax vs RefCells | 0.0000 |
| PVStand Pmax vs Soiling Kit | 0.0000 |

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

- Estadístico: 10.73  
- p-valor: 0.0  
- Resultado: ✗ heterocedástico

### 2. ANOVA paramétrico (f_oneway)

- F = 45.6076,  **p < 0.001** → diferencia altamente significativa (ANOVA)

### 3. Kruskal-Wallis (no paramétrico)

- H = 34.5646,  **p < 0.001** → diferencia altamente significativa (Kruskal-Wallis)

### 4. Post-hoc Tukey HSD (pares significativos, p_adj < 0.05)

| Par | Diferencia de medias | p_adj |
|---|---|---|
| DustIQ vs PV Glasses | -7.136 pp | 0.0000 |
| DustIQ vs PVStand Pmax | -7.416 pp | 0.0000 |
| IV600 Isc vs PV Glasses | -8.220 pp | 0.0000 |
| IV600 Isc vs PVStand Pmax | -8.501 pp | 0.0000 |
| IV600 Pmax vs PV Glasses | -8.582 pp | 0.0000 |
| IV600 Pmax vs PVStand Pmax | -8.863 pp | 0.0000 |
| PV Glasses vs PVStand Isc | 7.483 pp | 0.0000 |
| PV Glasses vs RefCells | 7.831 pp | 0.0000 |
| PV Glasses vs Soiling Kit | 7.847 pp | 0.0000 |
| PVStand Isc vs PVStand Pmax | -7.763 pp | 0.0000 |
| PVStand Pmax vs RefCells | 8.111 pp | 0.0000 |
| PVStand Pmax vs Soiling Kit | 8.127 pp | 0.0000 |

### 5. Post-hoc Dunn + Bonferroni (pares significativos, p_adj < 0.05)

| Par | p_adj (Bonferroni) |
|---|---|
| IV600 Isc vs PV Glasses | 0.0053 |
| IV600 Isc vs PVStand Pmax | 0.0063 |
| IV600 Pmax vs PV Glasses | 0.0010 |
| IV600 Pmax vs PVStand Pmax | 0.0012 |

---
## Conclusión general

El análisis ANOVA evalúa si los instrumentos
evolucionan de forma estadísticamente equivalente una vez eliminado el sesgo
de nivel absoluto. Un resultado significativo indica que la **tasa de cambio**
del SR difiere entre instrumentos, lo que implica que no son intercambiables
para el seguimiento del soiling.
