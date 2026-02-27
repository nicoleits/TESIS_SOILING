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

---

# SR de todos los módulos filtrados

El script **`calcular_sr_modulos.py`** calcula un indicador tipo Soiling Ratio para cada módulo a partir de los CSVs **alineados** (`*_aligned_solar_noon.csv`).

## Definiciones por módulo

| Módulo     | Fórmula / criterio |
|------------|---------------------|
| **soilingkit** | SR = 100 × Isc(p) / Isc(e) |
| **dustiq**     | SR = SR_C11_Avg (sensor en %) |
| **refcells**   | SR = 100 × (Sucia/Limpia); 1RC412 = limpia, 1RC411 = sucia. Los datos de refcells se filtran por irradiancia POA ≥ 500 W/m² en ambas celdas (en el pipeline de datos y al calcular SR). |
| **pv_glasses** | SR por celda = 100 × R_FCi / REF; SR = media de las 5 celdas |
| **pvstand**    | 439 = ref (limpio), 440 = sucio. **SR_Pmax** = 100×Pmax440/Pmax439, **SR_Isc** = 100×Isc440/Isc439 (imax como Isc). Una fila por timestamp. Filtro de falla: si Pmax439 o Pmax440 < 10 W se considera falla de equipo/sensor y SR_Pmax/SR_Isc = NaN. |
| **iv600**      | SR = 100 × pmp / P95(pmp) por módulo (referencia = percentil 95) |

### PVStand con corrección de temperatura (IEC 60891)

Script aparte **`calcular_sr_pvstand_corr.py`**: usa `pvstand_aligned_solar_noon.csv` y **`temperatura_aligned_solar_noon.csv`** (columnas 1TE416(C) = T módulo sucio 440, 1TE418(C) = T referencia 439). Aplica corrección a 25 °C (α_Isc = 0.0004, β_Pmax = −0.0036) y genera **`pvstand_sr_corr.csv`** y **`pvstand_sr_corr.png`** con SR_Pmax, SR_Isc, SR_Pmax_corr y SR_Isc_corr.

```bash
python -m analysis.sr.calcular_sr_pvstand_corr
```

Opcional: `python -m analysis.sr.calcular_sr_pvstand_corr [data_dir] [output_dir]`

## Ejecución

Desde **TESIS_SOILING** (después de la alineación):

```bash
python -m analysis.sr.calcular_sr_modulos
```

Opcional: `python -m analysis.sr.calcular_sr_modulos [data_dir] [output_dir]`

## Salidas

En `analysis/sr/`: `<modulo>_sr.csv` y `<modulo>_sr.png` para cada módulo (soilingkit, dustiq, refcells, pv_glasses, pvstand, iv600).
