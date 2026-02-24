# Sección Análisis

En esta carpeta se agrupan los **análisis** que usan los datos ya descargados y procesados por la sección **Data** (script `download_data.py`, carpeta `data/`).

## Subsecciones

- **`sr/`** — Cálculo de **Soiling Ratio (SR)** a partir de la sesión de mediodía solar.  
  Entrada: `data/soilingkit/soilingkit_solar_noon.csv`.  
  Salida: `analysis/sr/soilingkit_sr.csv`, `analysis/sr/grafico_sr.png`.  
  Se ejecuta aparte: `python -m analysis.sr.calcular_sr`.

## Orden recomendado

1. **Data:** descarga y procesamiento (opciones 6, 9, 11, 12, 13).
2. **Análisis:** ejecutar `python -m analysis.sr.calcular_sr` cuando exista `data/soilingkit/soilingkit_solar_noon.csv`.
