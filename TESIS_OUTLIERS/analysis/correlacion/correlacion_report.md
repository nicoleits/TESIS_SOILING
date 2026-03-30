# Análisis de Correlación Cruzada entre Instrumentos

**Variable:** SR semanal Q25 (SIN normalizar)  
**Método:** Correlación de Pearson pairwise (solo semanas con dato en ambos instrumentos)  
**Nivel de significancia:** α = 0.05

---
## Tabla de correlaciones por par (ordenado por r)

| Par | n semanas | r Pearson | Interpretación | p-valor | Sig. | Bias (pp) | RMSE (pp) |
|---|---|---|---|---|---|---|---|
| Soiling Kit vs PVStand Isc | 50 | 0.9810 | muy alta | 0.0000 | ✓ | 0.486 | 0.609 |
| PVStand Isc vs IV600 Isc | 29 | 0.9666 | muy alta | 0.0000 | ✓ | -0.785 | 0.830 |
| RefCells vs PVStand Isc | 36 | 0.9459 | muy alta | 0.0000 | ✓ | 0.177 | 0.469 |
| Soiling Kit vs DustIQ | 54 | 0.9244 | muy alta | 0.0000 | ✓ | 0.209 | 0.898 |
| Soiling Kit vs RefCells | 36 | 0.9133 | muy alta | 0.0000 | ✓ | 0.207 | 0.580 |
| RefCells vs IV600 Isc | 26 | 0.9122 | muy alta | 0.0000 | ✓ | -0.439 | 0.616 |
| DustIQ vs PVStand Isc | 50 | 0.9112 | muy alta | 0.0000 | ✓ | 0.232 | 1.058 |
| DustIQ vs RefCells | 36 | 0.9013 | muy alta | 0.0000 | ✓ | -0.425 | 0.754 |
| Soiling Kit vs PV Glasses | 11 | 0.9007 | muy alta | 0.0002 | ✓ | 7.421 | 8.247 |
| Soiling Kit vs IV600 Isc | 29 | 0.8929 | alta | 0.0000 | ✓ | -0.358 | 0.589 |
| PVStand Isc vs PV Glasses | 11 | 0.8805 | alta | 0.0003 | ✓ | 7.003 | 7.822 |
| DustIQ vs IV600 Pmax | 29 | 0.8682 | alta | 0.0000 | ✓ | -1.146 | 1.402 |
| DustIQ vs PV Glasses | 11 | 0.8600 | alta | 0.0007 | ✓ | 6.789 | 7.831 |
| PVStand Pmax vs PVStand Isc | 50 | 0.8498 | alta | 0.0000 | ✓ | -7.257 | 7.434 |
| Soiling Kit vs PVStand Pmax | 50 | 0.8489 | alta | 0.0000 | ✓ | 7.742 | 7.921 |
| PVStand Isc vs IV600 Pmax | 29 | 0.8435 | alta | 0.0000 | ✓ | -1.011 | 1.214 |
| DustIQ vs PVStand Pmax | 50 | 0.8370 | alta | 0.0000 | ✓ | 7.489 | 7.783 |
| RefCells vs IV600 Pmax | 26 | 0.8319 | alta | 0.0000 | ✓ | -0.728 | 0.987 |
| Soiling Kit vs IV600 Pmax | 29 | 0.8280 | alta | 0.0000 | ✓ | -0.584 | 0.913 |
| IV600 Pmax vs IV600 Isc | 29 | 0.8220 | alta | 0.0000 | ✓ | 0.226 | 0.750 |
| DustIQ vs IV600 Isc | 29 | 0.8123 | alta | 0.0000 | ✓ | -0.920 | 1.100 |
| PVStand Pmax vs PV Glasses | 11 | 0.8043 | alta | 0.0028 | ✓ | -0.063 | 2.882 |
| PVStand Pmax vs IV600 Pmax | 29 | 0.7381 | moderada | 0.0000 | ✓ | -8.393 | 8.483 |
| RefCells vs PVStand Pmax | 36 | 0.6772 | moderada | 0.0000 | ✓ | 7.193 | 7.435 |
| RefCells vs PV Glasses | 10 | 0.6162 | moderada | 0.0578 | ✗ | 6.470 | 7.138 |
| PVStand Pmax vs IV600 Isc | 29 | 0.5758 | moderada | 0.0011 | ✓ | -8.167 | 8.303 |
| IV600 Isc vs PV Glasses | 6 | 0.3591 | baja | 0.4845 | ✗ | 8.220 | 8.703 |
| IV600 Pmax vs PV Glasses | 6 | 0.3276 | baja | 0.5262 | ✗ | 8.582 | 9.041 |

---
## Pares con correlación alta (r ≥ 0.75, significativa)

- **Soiling Kit vs PVStand Isc**: r = 0.9810, n = 50, RMSE = 0.609 pp
- **PVStand Isc vs IV600 Isc**: r = 0.9666, n = 29, RMSE = 0.830 pp
- **RefCells vs PVStand Isc**: r = 0.9459, n = 36, RMSE = 0.469 pp
- **Soiling Kit vs DustIQ**: r = 0.9244, n = 54, RMSE = 0.898 pp
- **Soiling Kit vs RefCells**: r = 0.9133, n = 36, RMSE = 0.580 pp
- **RefCells vs IV600 Isc**: r = 0.9122, n = 26, RMSE = 0.616 pp
- **DustIQ vs PVStand Isc**: r = 0.9112, n = 50, RMSE = 1.058 pp
- **DustIQ vs RefCells**: r = 0.9013, n = 36, RMSE = 0.754 pp
- **Soiling Kit vs PV Glasses**: r = 0.9007, n = 11, RMSE = 8.247 pp
- **Soiling Kit vs IV600 Isc**: r = 0.8929, n = 29, RMSE = 0.589 pp
- **PVStand Isc vs PV Glasses**: r = 0.8805, n = 11, RMSE = 7.822 pp
- **DustIQ vs IV600 Pmax**: r = 0.8682, n = 29, RMSE = 1.402 pp
- **DustIQ vs PV Glasses**: r = 0.8600, n = 11, RMSE = 7.831 pp
- **PVStand Pmax vs PVStand Isc**: r = 0.8498, n = 50, RMSE = 7.434 pp
- **Soiling Kit vs PVStand Pmax**: r = 0.8489, n = 50, RMSE = 7.921 pp
- **PVStand Isc vs IV600 Pmax**: r = 0.8435, n = 29, RMSE = 1.214 pp
- **DustIQ vs PVStand Pmax**: r = 0.8370, n = 50, RMSE = 7.783 pp
- **RefCells vs IV600 Pmax**: r = 0.8319, n = 26, RMSE = 0.987 pp
- **Soiling Kit vs IV600 Pmax**: r = 0.8280, n = 29, RMSE = 0.913 pp
- **IV600 Pmax vs IV600 Isc**: r = 0.8220, n = 29, RMSE = 0.750 pp
- **DustIQ vs IV600 Isc**: r = 0.8123, n = 29, RMSE = 1.100 pp
- **PVStand Pmax vs PV Glasses**: r = 0.8043, n = 11, RMSE = 2.882 pp

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