# Análisis de Correlación Cruzada entre Instrumentos

**Variable:** SR semanal Q25 (SIN normalizar)  
**Método:** Correlación de Pearson pairwise (solo semanas con dato en ambos instrumentos)  
**Nivel de significancia:** α = 0.05

---
## Tabla de correlaciones por par (ordenado por r)

| Par | n semanas | r Pearson | Interpretación | p-valor | Sig. | Bias (pp) | RMSE (pp) |
|---|---|---|---|---|---|---|---|
| Soiling Kit vs PVStand Isc | 51 | 0.9817 | muy alta | 0.0000 | ✓ | 0.488 | 0.609 |
| PVStand Isc vs IV600 Isc | 29 | 0.9684 | muy alta | 0.0000 | ✓ | -0.798 | 0.840 |
| RefCells vs PVStand Isc | 36 | 0.9445 | muy alta | 0.0000 | ✓ | 0.161 | 0.470 |
| RefCells vs IV600 Isc | 26 | 0.9324 | muy alta | 0.0000 | ✓ | -0.454 | 0.593 |
| Soiling Kit vs DustIQ | 54 | 0.9244 | muy alta | 0.0000 | ✓ | 0.208 | 0.898 |
| Soiling Kit vs RefCells | 36 | 0.9141 | muy alta | 0.0000 | ✓ | 0.222 | 0.589 |
| DustIQ vs PVStand Isc | 51 | 0.9139 | muy alta | 0.0000 | ✓ | 0.260 | 1.073 |
| Soiling Kit vs IV600 Isc | 29 | 0.9059 | muy alta | 0.0000 | ✓ | -0.372 | 0.575 |
| Soiling Kit vs PV Glasses | 11 | 0.9007 | muy alta | 0.0002 | ✓ | 7.421 | 8.247 |
| DustIQ vs RefCells | 36 | 0.9001 | muy alta | 0.0000 | ✓ | -0.410 | 0.771 |
| PVStand Isc vs PV Glasses | 11 | 0.8805 | alta | 0.0003 | ✓ | 7.003 | 7.822 |
| DustIQ vs IV600 Pmax | 29 | 0.8771 | alta | 0.0000 | ✓ | -1.182 | 1.415 |
| DustIQ vs PV Glasses | 11 | 0.8600 | alta | 0.0007 | ✓ | 6.789 | 7.831 |
| PVStand Pmax vs PVStand Isc | 51 | 0.8596 | alta | 0.0000 | ✓ | -7.275 | 7.455 |
| Soiling Kit vs PVStand Pmax | 51 | 0.8587 | alta | 0.0000 | ✓ | 7.763 | 7.946 |
| DustIQ vs PVStand Pmax | 51 | 0.8482 | alta | 0.0000 | ✓ | 7.535 | 7.841 |
| DustIQ vs IV600 Isc | 29 | 0.8407 | alta | 0.0000 | ✓ | -0.933 | 1.093 |
| PVStand Isc vs IV600 Pmax | 29 | 0.8400 | alta | 0.0000 | ✓ | -1.047 | 1.241 |
| Soiling Kit vs IV600 Pmax | 29 | 0.8303 | alta | 0.0000 | ✓ | -0.620 | 0.924 |
| IV600 Pmax vs IV600 Isc | 29 | 0.8286 | alta | 0.0000 | ✓ | 0.248 | 0.733 |
| RefCells vs IV600 Pmax | 26 | 0.8263 | alta | 0.0000 | ✓ | -0.766 | 1.013 |
| PVStand Pmax vs PV Glasses | 11 | 0.8145 | alta | 0.0023 | ✓ | 0.037 | 2.814 |
| PVStand Pmax vs IV600 Pmax | 29 | 0.7732 | alta | 0.0000 | ✓ | -8.429 | 8.510 |
| RefCells vs PVStand Pmax | 36 | 0.6745 | moderada | 0.0000 | ✓ | 7.147 | 7.396 |
| PVStand Pmax vs IV600 Isc | 29 | 0.6634 | moderada | 0.0001 | ✓ | -8.180 | 8.297 |
| RefCells vs PV Glasses | 10 | 0.6162 | moderada | 0.0578 | ✗ | 6.470 | 7.138 |
| IV600 Isc vs PV Glasses | 6 | 0.3591 | baja | 0.4845 | ✗ | 8.220 | 8.703 |
| IV600 Pmax vs PV Glasses | 6 | 0.3276 | baja | 0.5262 | ✗ | 8.582 | 9.041 |

---
## Pares con correlación alta (r ≥ 0.75, significativa)

- **Soiling Kit vs PVStand Isc**: r = 0.9817, n = 51, RMSE = 0.609 pp
- **PVStand Isc vs IV600 Isc**: r = 0.9684, n = 29, RMSE = 0.840 pp
- **RefCells vs PVStand Isc**: r = 0.9445, n = 36, RMSE = 0.470 pp
- **RefCells vs IV600 Isc**: r = 0.9324, n = 26, RMSE = 0.593 pp
- **Soiling Kit vs DustIQ**: r = 0.9244, n = 54, RMSE = 0.898 pp
- **Soiling Kit vs RefCells**: r = 0.9141, n = 36, RMSE = 0.589 pp
- **DustIQ vs PVStand Isc**: r = 0.9139, n = 51, RMSE = 1.073 pp
- **Soiling Kit vs IV600 Isc**: r = 0.9059, n = 29, RMSE = 0.575 pp
- **Soiling Kit vs PV Glasses**: r = 0.9007, n = 11, RMSE = 8.247 pp
- **DustIQ vs RefCells**: r = 0.9001, n = 36, RMSE = 0.771 pp
- **PVStand Isc vs PV Glasses**: r = 0.8805, n = 11, RMSE = 7.822 pp
- **DustIQ vs IV600 Pmax**: r = 0.8771, n = 29, RMSE = 1.415 pp
- **DustIQ vs PV Glasses**: r = 0.8600, n = 11, RMSE = 7.831 pp
- **PVStand Pmax vs PVStand Isc**: r = 0.8596, n = 51, RMSE = 7.455 pp
- **Soiling Kit vs PVStand Pmax**: r = 0.8587, n = 51, RMSE = 7.946 pp
- **DustIQ vs PVStand Pmax**: r = 0.8482, n = 51, RMSE = 7.841 pp
- **DustIQ vs IV600 Isc**: r = 0.8407, n = 29, RMSE = 1.093 pp
- **PVStand Isc vs IV600 Pmax**: r = 0.8400, n = 29, RMSE = 1.241 pp
- **Soiling Kit vs IV600 Pmax**: r = 0.8303, n = 29, RMSE = 0.924 pp
- **IV600 Pmax vs IV600 Isc**: r = 0.8286, n = 29, RMSE = 0.733 pp
- **RefCells vs IV600 Pmax**: r = 0.8263, n = 26, RMSE = 1.013 pp
- **PVStand Pmax vs PV Glasses**: r = 0.8145, n = 11, RMSE = 2.814 pp
- **PVStand Pmax vs IV600 Pmax**: r = 0.7732, n = 29, RMSE = 8.510 pp

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