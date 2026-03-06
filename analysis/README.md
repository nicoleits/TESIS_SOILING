# Sección Análisis

En esta carpeta se agrupan los **análisis** que usan los datos ya descargados y procesados por la sección **Data** (script `download_data.py`, carpeta `data/`).

## Subsecciones

- **`sr/`** — Cálculo de **Soiling Ratio (SR)** a partir de la sesión de mediodía solar.  
  Entrada: `data/soilingkit/soilingkit_solar_noon.csv`.  
  Salida: `analysis/sr/soilingkit_sr.csv`, `analysis/sr/grafico_sr.png`.  
  Se ejecuta aparte: `python -m analysis.sr.calcular_sr`.

## Informe unificado de metodologías

Para una visión conjunta de las metodologías (SR/ópticas y gravimétrica): **[informe_metodologias.md](informe_metodologias.md)**.

## Orden recomendado

1. **Data:** descarga y procesamiento (opciones 6, 9, 11, 12, 13).
2. **Análisis:** ejecutar `python -m analysis.sr.calcular_sr` cuando exista `data/soilingkit/soilingkit_solar_noon.csv`.

## Pipeline completo (actualizar todo el análisis)

Tras cambiar `analysis/config.py` (p. ej. periodo o REFCELLS_FECHA_MAX), ejecutar en este orden desde la raíz del proyecto con `PYTHONPATH=TESIS_SOILING`:

1. `python -m analysis.stats.agregacion_semanal` → genera sr_semanal_*.csv y gráficos en `analysis/stats/`
2. `python -m analysis.anova.anova_sr` → lee sr_semanal_norm_largo.csv, genera anova_report.md y figuras en `analysis/anova/`
3. `python -m analysis.correlacion.correlacion_cruzada` → lee sr_semanal_norm.csv, genera correlacion_report.md y figuras en `analysis/correlacion/`
4. `python -m analysis.grafico_sr_diario_intercomparacion` → genera intercomparacion_sr_diario.png y intercomparacion_sr_diario_corr.png
5. `python -m analysis.stats.analisis_estadistico <data_dir>` → análisis exploratorio, reporte en `analysis/stats/`
6. `python -m analysis.qaqc.analisis_efecto_qaqc <data_dir>` → embudo QAQC y figuras en `analysis/qaqc/`
