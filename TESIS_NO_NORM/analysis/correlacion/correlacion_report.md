# Análisis de Correlación Cruzada entre Instrumentos

**Variable:** SR semanal Q25 (SIN normalizar)  
**Método:** Correlación de Pearson pairwise (solo semanas con dato en ambos instrumentos)  
**Nivel de significancia:** α = 0.05

---
## Tabla de correlaciones por par (ordenado por r)

| Par | n semanas | r Pearson | Interpretación | p-valor | Sig. | Bias (pp) | RMSE (pp) |
|---|---|---|---|---|---|---|---|
| Soiling Kit vs PVStand Isc | 50 | 0.9810 | muy alta | 0.0000 | ✓ | 0.486 | 0.609 |
| PVStand Isc vs IV600 Isc | 29 | 0.9535 | muy alta | 0.0000 | ✓ | -0.758 | 0.820 |
| RefCells vs PVStand Isc | 36 | 0.9445 | muy alta | 0.0000 | ✓ | 0.161 | 0.470 |
| Soiling Kit vs DustIQ | 54 | 0.9244 | muy alta | 0.0000 | ✓ | 0.209 | 0.898 |
| RefCells vs IV600 Isc | 26 | 0.9185 | muy alta | 0.0000 | ✓ | -0.408 | 0.584 |
| Soiling Kit vs RefCells | 36 | 0.9141 | muy alta | 0.0000 | ✓ | 0.223 | 0.589 |
| DustIQ vs PVStand Isc | 50 | 0.9112 | muy alta | 0.0000 | ✓ | 0.232 | 1.058 |
| Soiling Kit vs PV Glasses | 11 | 0.9007 | muy alta | 0.0002 | ✓ | 7.421 | 8.247 |
| DustIQ vs RefCells | 36 | 0.9001 | muy alta | 0.0000 | ✓ | -0.410 | 0.771 |
| Soiling Kit vs IV600 Isc | 29 | 0.8807 | alta | 0.0000 | ✓ | -0.331 | 0.595 |
| PVStand Isc vs PV Glasses | 11 | 0.8805 | alta | 0.0003 | ✓ | 7.003 | 7.822 |
| DustIQ vs IV600 Pmax | 29 | 0.8683 | alta | 0.0000 | ✓ | -1.148 | 1.402 |
| DustIQ vs PV Glasses | 11 | 0.8600 | alta | 0.0007 | ✓ | 6.789 | 7.831 |
| PVStand Pmax vs PVStand Isc | 50 | 0.8535 | alta | 0.0000 | ✓ | -7.235 | 7.415 |
| Soiling Kit vs PVStand Pmax | 50 | 0.8523 | alta | 0.0000 | ✓ | 7.720 | 7.902 |
| PVStand Isc vs IV600 Pmax | 29 | 0.8443 | alta | 0.0000 | ✓ | -1.013 | 1.214 |
| DustIQ vs PVStand Pmax | 50 | 0.8426 | alta | 0.0000 | ✓ | 7.467 | 7.767 |
| RefCells vs IV600 Pmax | 26 | 0.8319 | alta | 0.0000 | ✓ | -0.728 | 0.987 |
| Soiling Kit vs IV600 Pmax | 29 | 0.8289 | alta | 0.0000 | ✓ | -0.586 | 0.911 |
| IV600 Pmax vs IV600 Isc | 29 | 0.8285 | alta | 0.0000 | ✓ | 0.255 | 0.746 |
| PVStand Pmax vs PV Glasses | 11 | 0.8145 | alta | 0.0023 | ✓ | 0.037 | 2.814 |
| DustIQ vs IV600 Isc | 29 | 0.8084 | alta | 0.0000 | ✓ | -0.893 | 1.085 |
| PVStand Pmax vs IV600 Pmax | 29 | 0.7382 | moderada | 0.0000 | ✓ | -8.395 | 8.485 |
| RefCells vs PVStand Pmax | 36 | 0.6745 | moderada | 0.0000 | ✓ | 7.147 | 7.396 |
| RefCells vs PV Glasses | 10 | 0.6162 | moderada | 0.0578 | ✗ | 6.470 | 7.138 |
| PVStand Pmax vs IV600 Isc | 29 | 0.5838 | moderada | 0.0009 | ✓ | -8.140 | 8.274 |
| IV600 Isc vs PV Glasses | 6 | 0.3591 | baja | 0.4845 | ✗ | 8.220 | 8.703 |
| IV600 Pmax vs PV Glasses | 6 | 0.3276 | baja | 0.5262 | ✗ | 8.582 | 9.041 |

---
## Pares con correlación alta (r ≥ 0.75, significativa)

- **Soiling Kit vs PVStand Isc**: r = 0.9810, n = 50, RMSE = 0.609 pp
- **PVStand Isc vs IV600 Isc**: r = 0.9535, n = 29, RMSE = 0.820 pp
- **RefCells vs PVStand Isc**: r = 0.9445, n = 36, RMSE = 0.470 pp
- **Soiling Kit vs DustIQ**: r = 0.9244, n = 54, RMSE = 0.898 pp
- **RefCells vs IV600 Isc**: r = 0.9185, n = 26, RMSE = 0.584 pp
- **Soiling Kit vs RefCells**: r = 0.9141, n = 36, RMSE = 0.589 pp
- **DustIQ vs PVStand Isc**: r = 0.9112, n = 50, RMSE = 1.058 pp
- **Soiling Kit vs PV Glasses**: r = 0.9007, n = 11, RMSE = 8.247 pp
- **DustIQ vs RefCells**: r = 0.9001, n = 36, RMSE = 0.771 pp
- **Soiling Kit vs IV600 Isc**: r = 0.8807, n = 29, RMSE = 0.595 pp
- **PVStand Isc vs PV Glasses**: r = 0.8805, n = 11, RMSE = 7.822 pp
- **DustIQ vs IV600 Pmax**: r = 0.8683, n = 29, RMSE = 1.402 pp
- **DustIQ vs PV Glasses**: r = 0.8600, n = 11, RMSE = 7.831 pp
- **PVStand Pmax vs PVStand Isc**: r = 0.8535, n = 50, RMSE = 7.415 pp
- **Soiling Kit vs PVStand Pmax**: r = 0.8523, n = 50, RMSE = 7.902 pp
- **PVStand Isc vs IV600 Pmax**: r = 0.8443, n = 29, RMSE = 1.214 pp
- **DustIQ vs PVStand Pmax**: r = 0.8426, n = 50, RMSE = 7.767 pp
- **RefCells vs IV600 Pmax**: r = 0.8319, n = 26, RMSE = 0.987 pp
- **Soiling Kit vs IV600 Pmax**: r = 0.8289, n = 29, RMSE = 0.911 pp
- **IV600 Pmax vs IV600 Isc**: r = 0.8285, n = 29, RMSE = 0.746 pp
- **PVStand Pmax vs PV Glasses**: r = 0.8145, n = 11, RMSE = 2.814 pp
- **DustIQ vs IV600 Isc**: r = 0.8084, n = 29, RMSE = 1.085 pp

## Pares con correlación baja (r < 0.50)

- **IV600 Isc vs PV Glasses**: r = 0.3591, n = 6
- **IV600 Pmax vs PV Glasses**: r = 0.3276, n = 6

---
## Interpretación

Una correlación alta entre dos instrumentos indica que rastrean la **misma
tendencia temporal del soiling**, aunque puedan tener niveles absolutos distintos
(sesgo). Una correlación baja indica que los instrumentos responden a fenómenos
diferentes o que uno de ellos introduce ruido sistemático.

> **Nota:** La correlación se calcula sobre el SR semanal Q25 (SIN normalizar).
> Los instrumentos con períodos de medición cortos (IV600: 30 semanas) tienen
> menos semanas en común con el resto, lo que puede afectar la estimación de r.