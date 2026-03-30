# Soiling Kit – Sección Data (datos oficiales)

Esta carpeta es la **sección Data** del Soiling Kit: descarga (tabla soilingkit), filtrado por irradiancia y sesión de mediodía solar. **No** incluye el cálculo de SR ni el gráfico; eso está en la **sección Análisis** (`analysis/sr/`).

- **Menú Data:** opción 6 (descarga) → opción 12 (filtrado) → opción 13 (sesión mediodía solar).
- **Archivos:** `soilingkit_raw_data.csv`, `soilingkit_poa_500_clear_sky.csv`, `soilingkit_solar_noon.csv`, `soilingkit_solar_noon_dist_stats.csv`.
- **SR y gráfico:** proceso aparte `python -m analysis.sr.calcular_sr` → salida en `analysis/sr/`.
- Detalle en **PROCEDIMIENTO.md** (raíz del proyecto).
