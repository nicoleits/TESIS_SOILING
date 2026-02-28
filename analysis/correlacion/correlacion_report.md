# Análisis de Correlación Cruzada entre Instrumentos

**Variable:** SR semanal Q25 normalizado (t₀ = 100%)  
**Método:** Correlación de Pearson pairwise (solo semanas con dato en ambos instrumentos)  
**Nivel de significancia:** α = 0.05

---
## Tabla de correlaciones por par (ordenado por r)

| Par | n semanas | r Pearson | Interpretación | p-valor | Sig. | Bias (pp) | RMSE (pp) |
|---|---|---|---|---|---|---|---|
| PVStand vs PVStand corr | 50 | 0.9599 | muy alta | 0.0000 | ✓ | -0.354 | 0.874 |
| RefCells vs IV600 | 26 | 0.9433 | muy alta | 0.0000 | ✓ | 0.711 | 0.814 |
| Soiling Kit vs DustIQ | 53 | 0.9216 | muy alta | 0.0000 | ✓ | -0.373 | 0.947 |
| Soiling Kit vs RefCells | 36 | 0.9140 | muy alta | 0.0000 | ✓ | -0.378 | 0.665 |
| DustIQ vs RefCells | 36 | 0.9003 | muy alta | 0.0000 | ✓ | -0.408 | 0.775 |
| Soiling Kit vs IV600 | 30 | 0.8999 | alta | 0.0000 | ✓ | 0.155 | 0.523 |
| IV600 vs IV600 corr | 29 | 0.8866 | alta | 0.0000 | ✓ | -0.875 | 1.050 |
| DustIQ vs IV600 corr | 29 | 0.8683 | alta | 0.0000 | ✓ | -0.673 | 1.050 |
| Soiling Kit vs PVStand corr | 50 | 0.8653 | alta | 0.0000 | ✓ | 5.344 | 5.585 |
| PVStand vs IV600 | 30 | 0.8475 | alta | 0.0000 | ✓ | -5.990 | 6.063 |
| DustIQ vs PVStand corr | 50 | 0.8435 | alta | 0.0000 | ✓ | 5.696 | 6.073 |
| Soiling Kit vs PVStand | 53 | 0.8415 | alta | 0.0000 | ✓ | 5.670 | 5.862 |
| DustIQ vs PVStand | 53 | 0.8325 | alta | 0.0000 | ✓ | 6.042 | 6.327 |
| RefCells vs IV600 corr | 26 | 0.8319 | alta | 0.0000 | ✓ | -0.254 | 0.715 |
| DustIQ vs IV600 | 30 | 0.8309 | alta | 0.0000 | ✓ | 0.215 | 0.774 |
| Soiling Kit vs IV600 corr | 29 | 0.8289 | alta | 0.0000 | ✓ | -0.710 | 0.997 |
| PVStand vs IV600 corr | 29 | 0.7720 | alta | 0.0000 | ✓ | -6.866 | 6.952 |
| PVStand corr vs IV600 corr | 29 | 0.7382 | moderada | 0.0000 | ✓ | -6.105 | 6.237 |
| RefCells vs PVStand | 36 | 0.7226 | moderada | 0.0000 | ✓ | 5.959 | 6.233 |
| PVStand corr vs IV600 | 29 | 0.7086 | moderada | 0.0000 | ✓ | -5.230 | 5.399 |
| RefCells vs PVStand corr | 36 | 0.6926 | moderada | 0.0000 | ✓ | 5.357 | 5.652 |

---
## Pares con correlación alta (r ≥ 0.75, significativa)

- **PVStand vs PVStand corr**: r = 0.9599, n = 50, RMSE = 0.874 pp
- **RefCells vs IV600**: r = 0.9433, n = 26, RMSE = 0.814 pp
- **Soiling Kit vs DustIQ**: r = 0.9216, n = 53, RMSE = 0.947 pp
- **Soiling Kit vs RefCells**: r = 0.9140, n = 36, RMSE = 0.665 pp
- **DustIQ vs RefCells**: r = 0.9003, n = 36, RMSE = 0.775 pp
- **Soiling Kit vs IV600**: r = 0.8999, n = 30, RMSE = 0.523 pp
- **IV600 vs IV600 corr**: r = 0.8866, n = 29, RMSE = 1.050 pp
- **DustIQ vs IV600 corr**: r = 0.8683, n = 29, RMSE = 1.050 pp
- **Soiling Kit vs PVStand corr**: r = 0.8653, n = 50, RMSE = 5.585 pp
- **PVStand vs IV600**: r = 0.8475, n = 30, RMSE = 6.063 pp
- **DustIQ vs PVStand corr**: r = 0.8435, n = 50, RMSE = 6.073 pp
- **Soiling Kit vs PVStand**: r = 0.8415, n = 53, RMSE = 5.862 pp
- **DustIQ vs PVStand**: r = 0.8325, n = 53, RMSE = 6.327 pp
- **RefCells vs IV600 corr**: r = 0.8319, n = 26, RMSE = 0.715 pp
- **DustIQ vs IV600**: r = 0.8309, n = 30, RMSE = 0.774 pp
- **Soiling Kit vs IV600 corr**: r = 0.8289, n = 29, RMSE = 0.997 pp
- **PVStand vs IV600 corr**: r = 0.7720, n = 29, RMSE = 6.952 pp

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