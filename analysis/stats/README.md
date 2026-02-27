# Análisis estadístico de datos filtrados/alineados

Script que genera un **análisis estadístico** de los datos ya alineados a las sesiones del Soiling Kit (ventana de 5 min por día).

## Módulos con datos cada 1 minuto (fotoceldas, dustiq, temperatura, refcells)

- Dentro de la ventana de 5 min hay **hasta 5 valores** por día.
- Por cada día y cada variable se calcula: **media, desviación estándar (std), mínimo, máximo, rango, CV (%)** (coeficiente de variación = 100·std/mean).
- Luego se resume **entre días**: media de std, mediana de std, p95 de std, media de CV, media del rango, etc.
- Interpretación: **menor CV** o **menor std** dentro de la ventana indica menor dispersión en esos 5 minutos.

## Módulos 5 min o irregulares (pvstand, iv600, soilingkit)

- Solo hay **un valor por día** (o por día y submódulo) en la ventana.
- No se puede calcular dispersión dentro de la ventana.
- Se reportan estadísticos **entre días**: count, mean, std, min, percentiles (p05, p25, p50, p75, p95), max.

## Salidas

- **`analysis/stats/analisis_estadistico_report.md`**: reporte en Markdown con todas las tablas.
- **`analysis/stats/analisis_estadistico_resumen.csv`**: resumen en CSV (modulo, tipo, variable, y columnas según tipo).

## Ejecución

Desde **TESIS_SOILING** (después de haber ejecutado la alineación):

```bash
python -m analysis.stats.analisis_estadistico
```

Opcional: `python -m analysis.stats.analisis_estadistico [ruta_a_data]`

Se usan solo los **días con estabilidad de irradiancia** (G < 10%) si existe `solys2_poa_500_clear_sky.csv`.
