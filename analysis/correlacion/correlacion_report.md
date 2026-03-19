# Análisis de Correlación Cruzada entre Instrumentos

**Variable:** SR semanal Q25 (t₀=100% excepto IV600 Pmax/Isc en valor absoluto)  
**Método:** Correlación de Pearson pairwise (solo semanas con dato en ambos instrumentos)  
**Nivel de significancia:** α = 0.05

---
## Tabla de correlaciones por par (ordenado por r)

| Par | n semanas | r Pearson | Interpretación | p-valor | Sig. | Bias (pp) | RMSE (pp) |
|---|---|---|---|---|---|---|---|
| Soiling Kit vs PVStand Isc | 50 | 0.9810 | muy alta | 0.0000 | ✓ | 0.200 | 0.421 |
| PVStand Isc vs IV600 Isc | 29 | 0.9535 | muy alta | 0.0000 | ✓ | -0.292 | 0.429 |
| RefCells vs PVStand Isc | 36 | 0.9445 | muy alta | 0.0000 | ✓ | 0.479 | 0.654 |
| Soiling Kit vs DustIQ | 54 | 0.9244 | muy alta | 0.0000 | ✓ | -0.395 | 0.957 |
| RefCells vs IV600 Isc | 26 | 0.9185 | muy alta | 0.0000 | ✓ | 0.377 | 0.564 |
| Soiling Kit vs RefCells | 36 | 0.9141 | muy alta | 0.0000 | ✓ | -0.384 | 0.669 |
| DustIQ vs PVStand Isc | 50 | 0.9112 | muy alta | 0.0000 | ✓ | 0.550 | 1.172 |
| Soiling Kit vs PV Glasses | 11 | 0.9007 | muy alta | 0.0002 | ✓ | 4.249 | 5.678 |
| DustIQ vs RefCells | 36 | 0.9001 | muy alta | 0.0000 | ✓ | -0.411 | 0.776 |
| Soiling Kit vs IV600 Isc | 29 | 0.8807 | alta | 0.0000 | ✓ | -0.153 | 0.518 |
| PVStand Isc vs PV Glasses | 11 | 0.8805 | alta | 0.0003 | ✓ | 4.121 | 5.506 |
| DustIQ vs IV600 Pmax | 29 | 0.8683 | alta | 0.0000 | ✓ | -0.366 | 0.882 |
| DustIQ vs PV Glasses | 11 | 0.8600 | alta | 0.0007 | ✓ | 4.225 | 5.867 |
| PVStand Pmax vs PVStand Isc | 50 | 0.8535 | alta | 0.0000 | ✓ | -6.715 | 6.913 |
| Soiling Kit vs PVStand Pmax | 50 | 0.8523 | alta | 0.0000 | ✓ | 6.914 | 7.123 |
| PVStand Isc vs IV600 Pmax | 29 | 0.8443 | alta | 0.0000 | ✓ | -0.547 | 0.864 |
| DustIQ vs PVStand Pmax | 50 | 0.8426 | alta | 0.0000 | ✓ | 7.265 | 7.580 |
| RefCells vs IV600 Pmax | 26 | 0.8319 | alta | 0.0000 | ✓ | 0.056 | 0.669 |
| Soiling Kit vs IV600 Pmax | 29 | 0.8289 | alta | 0.0000 | ✓ | -0.407 | 0.808 |
| IV600 Pmax vs IV600 Isc | 29 | 0.8285 | alta | 0.0000 | ✓ | 0.255 | 0.746 |
| PVStand Pmax vs PV Glasses | 11 | 0.8145 | alta | 0.0023 | ✓ | -2.315 | 3.739 |
| DustIQ vs IV600 Isc | 29 | 0.8084 | alta | 0.0000 | ✓ | -0.111 | 0.624 |
| PVStand Pmax vs IV600 Pmax | 29 | 0.7382 | moderada | 0.0000 | ✓ | -7.408 | 7.513 |
| RefCells vs PVStand Pmax | 36 | 0.6745 | moderada | 0.0000 | ✓ | 6.937 | 7.199 |
| RefCells vs PV Glasses | 10 | 0.6162 | moderada | 0.0578 | ✗ | 3.871 | 4.982 |
| PVStand Pmax vs IV600 Isc | 29 | 0.5838 | moderada | 0.0009 | ✓ | -7.154 | 7.310 |
| IV600 Isc vs PV Glasses | 6 | 0.3591 | baja | 0.4845 | ✗ | 4.899 | 5.727 |
| IV600 Pmax vs PV Glasses | 6 | 0.3276 | baja | 0.5262 | ✗ | 5.261 | 6.032 |

---
## Pares con correlación alta (r ≥ 0.75, significativa)

- **Soiling Kit vs PVStand Isc**: r = 0.9810, n = 50, RMSE = 0.421 pp
- **PVStand Isc vs IV600 Isc**: r = 0.9535, n = 29, RMSE = 0.429 pp
- **RefCells vs PVStand Isc**: r = 0.9445, n = 36, RMSE = 0.654 pp
- **Soiling Kit vs DustIQ**: r = 0.9244, n = 54, RMSE = 0.957 pp
- **RefCells vs IV600 Isc**: r = 0.9185, n = 26, RMSE = 0.564 pp
- **Soiling Kit vs RefCells**: r = 0.9141, n = 36, RMSE = 0.669 pp
- **DustIQ vs PVStand Isc**: r = 0.9112, n = 50, RMSE = 1.172 pp
- **Soiling Kit vs PV Glasses**: r = 0.9007, n = 11, RMSE = 5.678 pp
- **DustIQ vs RefCells**: r = 0.9001, n = 36, RMSE = 0.776 pp
- **Soiling Kit vs IV600 Isc**: r = 0.8807, n = 29, RMSE = 0.518 pp
- **PVStand Isc vs PV Glasses**: r = 0.8805, n = 11, RMSE = 5.506 pp
- **DustIQ vs IV600 Pmax**: r = 0.8683, n = 29, RMSE = 0.882 pp
- **DustIQ vs PV Glasses**: r = 0.8600, n = 11, RMSE = 5.867 pp
- **PVStand Pmax vs PVStand Isc**: r = 0.8535, n = 50, RMSE = 6.913 pp
- **Soiling Kit vs PVStand Pmax**: r = 0.8523, n = 50, RMSE = 7.123 pp
- **PVStand Isc vs IV600 Pmax**: r = 0.8443, n = 29, RMSE = 0.864 pp
- **DustIQ vs PVStand Pmax**: r = 0.8426, n = 50, RMSE = 7.580 pp
- **RefCells vs IV600 Pmax**: r = 0.8319, n = 26, RMSE = 0.669 pp
- **Soiling Kit vs IV600 Pmax**: r = 0.8289, n = 29, RMSE = 0.808 pp
- **IV600 Pmax vs IV600 Isc**: r = 0.8285, n = 29, RMSE = 0.746 pp
- **PVStand Pmax vs PV Glasses**: r = 0.8145, n = 11, RMSE = 3.739 pp
- **DustIQ vs IV600 Isc**: r = 0.8084, n = 29, RMSE = 0.624 pp

## Pares con correlación baja (r < 0.50)

- **IV600 Isc vs PV Glasses**: r = 0.3591, n = 6
- **IV600 Pmax vs PV Glasses**: r = 0.3276, n = 6

---
## Interpretación

Una correlación alta entre dos instrumentos indica que rastrean la **misma
tendencia temporal del soiling**, aunque puedan tener niveles absolutos distintos
(sesgo). Una correlación baja indica que los instrumentos responden a fenómenos
diferentes o que uno de ellos introduce ruido sistemático.

> **Nota:** La correlación se calcula sobre el SR semanal Q25 (IV600 Pmax/Isc sin normalizar).
> Los instrumentos con períodos de medición cortos (IV600: 30 semanas) tienen
> menos semanas en común con el resto, lo que puede afectar la estimación de r.