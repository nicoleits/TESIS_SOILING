# Análisis de sesgo respecto a PVStand Isc

Sesgo de cada metodología frente a **una única referencia operativa**: SR por Isc del PVStand (PVStand Isc).

- **Variable comparada**: SR semanal Q25 normalizado (misma definición que correlación; sin mezclar diario/semanal ni escalas).
- **Datos**: `analysis/stats/sr_semanal_norm.csv`. No se rellenan NaN: para cada método solo se usan semanas comunes con PVStand Isc.
- **Error con signo**: \( e_i = \mathrm{SR}_{m,i} - \mathrm{SR}_{\mathrm{PVStand\,Isc},i} \).  
  \( e_i > 0 \) → el método sobreestima; \( e_i < 0 \) → subestima.
- **Métricas**: MBE (pp), mediana del error (pp), P25, P75, SD del error (pp), RMSE (pp), y opcionalmente MBE (%).

## Cómo ejecutar

Desde la raíz del proyecto `TESIS_SOILING`:

```bash
python -m analysis.sesgo.sesgo_referencia
```

O con rutas explícitas:

```bash
python -m analysis.sesgo.sesgo_referencia [ruta_sr_semanal_norm.csv] [carpeta_salida]
```

Requiere tener generado antes `analysis/stats/sr_semanal_norm.csv` (p. ej. `python -m analysis.stats.agregacion_semanal`).

## Salidas

| Archivo | Descripción |
|--------|-------------|
| `sesgo_tabla.csv` | Por método: referencia, n, MBE (pp), mediana error (pp), P25, P75, SD error (pp), RMSE (pp), MBE (%) |
| `sesgo_barras_mbe.png` | Barras de MBE (pp) por método, línea en 0 |
| `sesgo_error_vs_semana.png` | Error \( e_i \) vs semana por método (subplots) |
