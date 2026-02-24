# Análisis: Soiling Ratio (SR)

Esta carpeta es la **sección de análisis** del Soiling Ratio. No descarga ni procesa datos crudos; usa la salida de la **sección Data** (sesión mediodía solar).

## Entrada

- **`data/soilingkit/soilingkit_solar_noon.csv`**: generado por la opción 13 del menú (Soiling Kit: sesión mediodía solar). Debe contener al menos `timestamp`, `dist_solar_noon_min`, `Isc(e)`, `Isc(p)`.

## Qué hace

1. Lee el CSV de sesión mediodía solar.
2. Calcula **SR = 100 × Isc(p) / Isc(e)** (Soiling Ratio en %).
3. Aplica filtro de corriente (Isc ≥ 1 A) si aplica.
4. Guarda **`soilingkit_sr.csv`** y **`grafico_sr.png`** en esta carpeta.

## Cómo ejecutarlo (proceso separado de download_data.py)

- **Desde la raíz del proyecto:**  
  `python -m analysis.sr.calcular_sr`  
  Usa por defecto `data/soilingkit/soilingkit_solar_noon.csv` y `analysis/sr/`.
- **Con rutas:**  
  `python -m analysis.sr.calcular_sr [ruta_solar_noon.csv] [carpeta_salida]`

## Salidas

| Archivo            | Descripción                          |
|--------------------|--------------------------------------|
| `soilingkit_sr.csv`| Serie diaria con columna SR (%).     |
| `grafico_sr.png`   | Gráfico de SR en el tiempo.          |
