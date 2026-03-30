# Concordancia intermetodológica

Matrices y gráficos de concordancia entre todas las metodologías de SR. Datos: SR semanal Q25 (SIN normalizar); PVStand e IV600 corregidos por T.

## Archivos

- **matriz_correlacion.csv**: Correlación de Pearson entre pares de metodologías.
- **matriz_correlacion_spearman.csv**: Correlación de Spearman.
- **concordancia_pares.csv**: Por par: n_semanas, r_pearson, p_pearson, rho_spearman, CCC_Lin, bias_pp, sd_diferencia_pp, LoA (±1.96 SD), rmse_pp.
- **matriz_ccc_lin.csv**: Matriz del CCC de Lin (concordancia que combina precisión y exactitud).
- **heatmap_concordancia.png**: Heatmap de correlaciones Pearson (con n por celda).
- **heatmap_ccc_lin.png**: Heatmap del CCC de Lin (con n por celda).
- **scatter_concordancia.png**: Matriz de dispersión entre metodologías.

## Cómo generar

Desde la raíz del proyecto (TESIS_SOILING):

```bash
python -m analysis.concordancia.concordancia_intermetodologica
```

Requiere tener generado antes `analysis/stats/sr_semanal_q25.csv` (ej. `python -m analysis.stats.agregacion_semanal`).
