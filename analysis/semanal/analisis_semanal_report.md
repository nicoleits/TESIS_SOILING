# Análisis de agregación semanal SR (Q25)

Resultados del resample semanal (Q25) por metodología y su análisis estadístico.

## 1. Resumen

- **Metodologías:** 7
- **Semanas (máx.):** 54
- **Periodo:** mismo que intercomparación SR (config: PERIODO_ANALISIS_INICIO/FIN, RefCells hasta REFCELLS_FECHA_MAX).

## 2. Estadísticos descriptivos (SR Q25 semanal)

| Instrumento | n_semanas | media | std | CV (%) | min | p50 | max |
|------------|-----------|-------|-----|--------|-----|-----|-----|
| Soiling Kit | 54 | 97.10 | 1.68 | 1.73 | 94.37 | 97.04 | 99.82 |
| DustIQ | 54 | 96.89 | 0.95 | 0.98 | 95.55 | 96.72 | 99.20 |
| RefCells | 37 | 97.65 | 1.36 | 1.40 | 94.59 | 97.19 | 99.77 |
| PVStand | 54 | 88.50 | 2.70 | 3.05 | 84.62 | 87.82 | 98.80 |
| PVStand corr | 50 | 89.47 | 2.90 | 3.24 | 85.04 | 88.80 | 98.91 |
| IV600 | 30 | 96.76 | 1.16 | 1.19 | 94.90 | 96.36 | 99.21 |
| IV600 corr | 29 | 98.07 | 1.27 | 1.29 | 95.90 | 97.63 | 100.15 |


## 3. Correlación entre metodologías (Pearson, semanas comunes)

Pares con |r| ≥ 0,7:

| Metodología i | Metodología j | r | p-value |
|---------------|---------------|-----|---------|
| PVStand | PVStand corr | 0.962 | 0.0000 |
| RefCells | IV600 | 0.943 | 0.0000 |
| Soiling Kit | DustIQ | 0.924 | 0.0000 |
| Soiling Kit | RefCells | 0.921 | 0.0000 |
| DustIQ | RefCells | 0.908 | 0.0000 |
| Soiling Kit | IV600 | 0.900 | 0.0000 |
| IV600 | IV600 corr | 0.887 | 0.0000 |
| DustIQ | IV600 corr | 0.868 | 0.0000 |
| Soiling Kit | PVStand corr | 0.852 | 0.0000 |
| PVStand | IV600 | 0.848 | 0.0000 |
| DustIQ | PVStand corr | 0.843 | 0.0000 |
| RefCells | IV600 corr | 0.832 | 0.0000 |
| DustIQ | PVStand | 0.831 | 0.0000 |
| DustIQ | IV600 | 0.831 | 0.0000 |
| Soiling Kit | IV600 corr | 0.829 | 0.0000 |
| Soiling Kit | PVStand | 0.827 | 0.0000 |
| PVStand | IV600 corr | 0.772 | 0.0000 |
| PVStand corr | IV600 corr | 0.738 | 0.0000 |
| PVStand corr | IV600 | 0.709 | 0.0000 |
| RefCells | PVStand | 0.704 | 0.0000 |


## 4. Interpretación breve

- **Dispersión (CV):** mayor CV indica más variabilidad del SR Q25 semanal entre semanas para esa metodología.
- **Correlación:** valores de r próximos a 1 indican que dos metodologías evolucionan de forma similar en el tiempo (semanas comunes).
- Los resultados semanales (Q25) permiten comparar tendencias de soiling entre instrumentos con menor ruido que la serie diaria.
