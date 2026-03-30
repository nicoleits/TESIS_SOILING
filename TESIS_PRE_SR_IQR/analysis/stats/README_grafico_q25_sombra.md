# Gráfico `sr_semanal_q25_sombra*.png` y datos asociados

## Qué datos entran al cálculo

1. **Origen:** series diarias de SR (%) de cada instrumento, cargadas desde los CSV en `analysis/sr/` según la configuración interna de `agregacion_semanal.py` (Soiling Kit, DustIQ, RefCells, PVStand, IV600, etc.).
2. **Agregación semanal:** cada serie se re-muestrea con semanas **lunes–domingo** (`resample("W-MON", label="left", closed="left")` en pandas).
3. **Por semana e instrumento:**
   - **`sr_q25_pct`:** percentil 25 de los valores diarios de SR en esa semana.
   - **`std_diarios_en_semana_pct`:** desviación estándar de esos mismos valores diarios (si solo hay 1 día, queda vacío/NaN en esta columna).
   - **`n_dias_con_dato_en_semana`:** número de días con dato en la ventana semanal.
4. **El gráfico** dibuja la línea en `sr_q25_pct` y la sombra entre `sr_q25 ± std`. Donde la std es NaN, en el gráfico se usa **0** (sin banda visible). Eso coincide con las columnas `std_usada_en_grafico_pct`, `banda_inferior_pct` y `banda_superior_pct` en el CSV exportado.

## Archivos de salida (misma carpeta `analysis/stats/` que elijas al ejecutar el módulo)

| Archivo | Uso |
|--------|-----|
| `sr_semanal_q25_sombra.png` | Superposición **sin** PV Glasses |
| `sr_semanal_q25_sombra_completo.png` | Superposición con **todos** los instrumentos |
| `sr_semanal_q25_sombra_datos.csv` | Tabla larga = datos del PNG `_completo` |
| `sr_semanal_q25_sombra_datos_sin_pv_glasses.csv` | Misma tabla filtrada = datos del PNG principal |

## Cómo generarlo en `TESIS_NO_NORM`

Desde la raíz del repo `si_test`:

```bash
PYTHONPATH=TESIS_SOILING .venv/bin/python -m analysis.stats.agregacion_semanal \
  TESIS_SOILING/analysis/sr \
  TESIS_NO_NORM/analysis/stats \
  --solo-sin-normalizar
```

El flag **`--solo-sin-normalizar`** evita generar `sr_semanal_norm*` (CSV/PNG) y borra restos previos de esos archivos en la carpeta de salida.

O el pipeline completo:

```bash
.venv/bin/python run_tesis_analisis.py --modo sin_normalizar
```

(pasa `--solo-sin-normalizar` automáticamente a la agregación).

Los PNG y CSV “sin normalizar” quedarán en **`TESIS_NO_NORM/analysis/stats/`**.
