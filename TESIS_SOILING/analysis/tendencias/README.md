# Análisis de tendencias

Regresión lineal del **SR semanal Q25 normalizado** (t₀ = 100%) frente al tiempo (semana 0, 1, 2, …) por metodología. La **pendiente** es la tasa de cambio en % por semana.

## Entrada

- `analysis/stats/sr_semanal_norm.csv` (generado por `python -m analysis.stats.agregacion_semanal`).

## Salidas

| Archivo | Descripción |
|--------|-------------|
| `tendencias_resumen.csv` | Por instrumento: pendiente (%/semana), pendiente (%/mes), R², p-value, n_semanas |
| `tendencias_grafico.png` | Series observadas + rectas de tendencia por metodología |
| `tendencias_pendientes.png` | Barras de pendiente por instrumento |
| `tendencias_report.md` | Tabla resumen e interpretación |

## Interpretación

- **Pendiente negativa:** el SR tiende a bajar (soiling acumulado o deriva).
- **Pendiente ≈ 0:** SR estable.
- **Pendiente positiva:** tendencia al alza (recuperación, lluvia, estacionalidad).
- **R²** alto: la tendencia lineal explica bien la evolución.
- **p-value < 0,05:** pendiente estadísticamente significativa.

## Uso

```bash
python -m analysis.tendencias.analisis_tendencias
```

Con rutas:

```bash
python -m analysis.tendencias.analisis_tendencias [ruta_sr_semanal_norm.csv] [carpeta_salida]
```
