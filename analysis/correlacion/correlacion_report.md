# Análisis de Correlación Cruzada entre Instrumentos

**Variable:** SR semanal Q25 normalizado (t₀ = 100%)  
**Método:** Correlación de Pearson pairwise (solo semanas con dato en ambos instrumentos)  
**Nivel de significancia:** α = 0.05

---
## Tabla de correlaciones por par (ordenado por r)

| Par | n semanas | r Pearson | Interpretación | p-valor | Sig. | Bias (pp) | RMSE (pp) |
|---|---|---|---|---|---|---|---|
| PVStand vs PVStand corr | 50 | 0.9622 | muy alta | 0.0000 | ✓ | -0.795 | 1.121 |
| RefCells vs IV600 | 26 | 0.9433 | muy alta | 0.0000 | ✓ | 0.690 | 0.795 |
| Soiling Kit vs DustIQ | 54 | 0.9244 | muy alta | 0.0000 | ✓ | -0.395 | 0.957 |
| Soiling Kit vs RefCells | 37 | 0.9207 | muy alta | 0.0000 | ✓ | -0.395 | 0.672 |
| DustIQ vs RefCells | 37 | 0.9079 | muy alta | 0.0000 | ✓ | -0.391 | 0.767 |
| Soiling Kit vs IV600 | 30 | 0.8999 | alta | 0.0000 | ✓ | 0.127 | 0.515 |
| IV600 vs IV600 corr | 29 | 0.8866 | alta | 0.0000 | ✓ | -0.875 | 1.050 |
| DustIQ vs IV600 corr | 29 | 0.8683 | alta | 0.0000 | ✓ | -0.698 | 1.066 |
| Soiling Kit vs PVStand corr | 50 | 0.8523 | alta | 0.0000 | ✓ | 6.914 | 7.123 |
| PVStand vs IV600 | 30 | 0.8475 | alta | 0.0000 | ✓ | -8.064 | 8.115 |
| DustIQ vs PVStand corr | 50 | 0.8426 | alta | 0.0000 | ✓ | 7.265 | 7.580 |
| RefCells vs IV600 corr | 26 | 0.8319 | alta | 0.0000 | ✓ | -0.276 | 0.723 |
| DustIQ vs PVStand | 54 | 0.8310 | alta | 0.0000 | ✓ | 8.100 | 8.340 |
| DustIQ vs IV600 | 30 | 0.8309 | alta | 0.0000 | ✓ | 0.190 | 0.767 |
| Soiling Kit vs IV600 corr | 29 | 0.8289 | alta | 0.0000 | ✓ | -0.739 | 1.018 |
| Soiling Kit vs PVStand | 54 | 0.8268 | alta | 0.0000 | ✓ | 7.705 | 7.874 |
| PVStand vs IV600 corr | 29 | 0.7720 | alta | 0.0000 | ✓ | -8.940 | 9.003 |
| PVStand corr vs IV600 corr | 29 | 0.7382 | moderada | 0.0000 | ✓ | -7.740 | 7.840 |
| PVStand corr vs IV600 | 29 | 0.7086 | moderada | 0.0000 | ✓ | -6.865 | 6.989 |
| RefCells vs PVStand | 37 | 0.7035 | moderada | 0.0000 | ✓ | 7.980 | 8.222 |
| RefCells vs PVStand corr | 37 | 0.6915 | moderada | 0.0000 | ✓ | 6.964 | 7.220 |

---
## Pares con correlación alta (r ≥ 0.75, significativa)

- **PVStand vs PVStand corr**: r = 0.9622, n = 50, RMSE = 1.121 pp
- **RefCells vs IV600**: r = 0.9433, n = 26, RMSE = 0.795 pp
- **Soiling Kit vs DustIQ**: r = 0.9244, n = 54, RMSE = 0.957 pp
- **Soiling Kit vs RefCells**: r = 0.9207, n = 37, RMSE = 0.672 pp
- **DustIQ vs RefCells**: r = 0.9079, n = 37, RMSE = 0.767 pp
- **Soiling Kit vs IV600**: r = 0.8999, n = 30, RMSE = 0.515 pp
- **IV600 vs IV600 corr**: r = 0.8866, n = 29, RMSE = 1.050 pp
- **DustIQ vs IV600 corr**: r = 0.8683, n = 29, RMSE = 1.066 pp
- **Soiling Kit vs PVStand corr**: r = 0.8523, n = 50, RMSE = 7.123 pp
- **PVStand vs IV600**: r = 0.8475, n = 30, RMSE = 8.115 pp
- **DustIQ vs PVStand corr**: r = 0.8426, n = 50, RMSE = 7.580 pp
- **RefCells vs IV600 corr**: r = 0.8319, n = 26, RMSE = 0.723 pp
- **DustIQ vs PVStand**: r = 0.8310, n = 54, RMSE = 8.340 pp
- **DustIQ vs IV600**: r = 0.8309, n = 30, RMSE = 0.767 pp
- **Soiling Kit vs IV600 corr**: r = 0.8289, n = 29, RMSE = 1.018 pp
- **Soiling Kit vs PVStand**: r = 0.8268, n = 54, RMSE = 7.874 pp
- **PVStand vs IV600 corr**: r = 0.7720, n = 29, RMSE = 9.003 pp

## Pares con correlación baja (r < 0.50)

_Todos los pares tienen r ≥ 0.50._

---
## Interpretación

Una correlación alta entre dos instrumentos indica que rastrean la **misma
tendencia temporal del soiling**, aunque puedan tener niveles absolutos distintos
(sesgo). Una correlación baja indica que los instrumentos responden a fenómenos
diferentes o que uno de ellos introduce ruido sistemático.

> **Nota:** La correlación se calcula sobre el SR normalizado semanal Q25.
> Los instrumentos con períodos de medición cortos (IV600: 30 semanas) tienen
> menos semanas en común con el resto, lo que puede afectar la estimación de r.