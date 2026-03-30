# Análisis de tendencias — SR semanal Q25 (IV600 Pmax/Isc valor absoluto)

Regresión lineal **SR = a + b × (semana)** por metodología. La pendiente **b** es la tasa de cambio en % por semana.

## Resumen

| Instrumento | Pendiente (%/semana) | Pendiente (%/mes) | R² | p-value | n_semanas |
|-------------|---------------------|-------------------|-----|---------|-----------|
| Soiling Kit | -0.1032 | -0.4489 | 0.9278 | 0.0000 | 54 |
| DustIQ | -0.0575 | -0.2499 | 0.8895 | 0.0000 | 54 |
| RefCells | -0.1174 | -0.5104 | 0.8534 | 0.0000 | 36 |
| PVStand Pmax | -0.1754 | -0.7628 | 0.7626 | 0.0000 | 50 |
| PVStand Isc | -0.1222 | -0.5314 | 0.9367 | 0.0000 | 50 |
| IV600 Pmax | -0.1342 | -0.5837 | 0.8107 | 0.0000 | 29 |
| IV600 Isc | -0.0961 | -0.4180 | 0.6785 | 0.0000 | 29 |

## Interpretación

- **Pendiente negativa:** el SR tiende a bajar en el tiempo (acumulación de soiling o deriva).
- **Pendiente ≈ 0:** el SR se mantiene estable en promedio.
- **Pendiente positiva:** el SR tiende a subir (recuperación, lluvia, o efecto estacional).
- **R²** mide cuánto de la variabilidad del SR se explica por la tendencia lineal.
- **p-value < 0,05** sugiere que la pendiente es estadísticamente significativa.
