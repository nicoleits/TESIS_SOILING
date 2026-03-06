# Agregación semanal SR (Q25)

Resample de cada metodología de Soiling Ratio a **agregación semanal** usando el **cuantil 25 (Q25)**. Incluye gráficos y análisis estadístico.

## Periodo

Mismo que la intercomparación de SR: `PERIODO_ANALISIS_INICIO`–`PERIODO_ANALISIS_FIN` desde `analysis/config.py`. RefCells usa `REFCELLS_FECHA_MAX` como fecha máxima.

## Semanas

Semanas ISO (lunes a domingo). Cada semana se etiqueta por el **lunes de inicio** (`resample("W-MON", label="left", closed="left")`). Para cada semana se calcula el percentil 25 de los valores diarios de SR.

## Metodologías

- Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, IV600, IV600 corr (mismas fuentes que `analysis/sr/*.csv`).

## Salidas

### CSV (agregación)
| Archivo | Descripción |
|--------|-------------|
| `soiling_kit_sr_semanal_q25.csv` … `iv600_corr_sr_semanal_q25.csv` | SR Q25 semanal por metodología (semana, sr_q25) |
| `sr_semanal_q25.csv` | Todas en formato ancho |
| `sr_semanal_q25_largo.csv` | Todas en formato largo (semana, instrumento, sr_q25) |
| `dispersion_semanal.csv` | Estadísticos descriptivos por instrumento (n_semanas, mean, std, CV, percentiles) |

### Gráficos
| Archivo | Descripción |
|--------|-------------|
| `sr_semanal_q25_series.png` | Series de SR Q25 semanal superpuestas (todas las metodologías) |
| `sr_semanal_q25_boxplot.png` | Boxplot de dispersión del SR Q25 por metodología |
| `sr_semanal_q25_norm.png` | Series normalizadas (primer valor = 100%) superpuestas |

### Análisis (tras `analisis_semanal.py`)
| Archivo | Descripción |
|--------|-------------|
| `correlacion_semanal.csv` | Pares de metodologías con coeficiente de Pearson (r) y p-value |
| `correlacion_semanal_matrix.csv` | Matriz de correlación (ancho) |
| `analisis_semanal_report.md` | Reporte con resumen, tabla descriptiva, correlaciones destacadas e interpretación |

## Uso

**1. Agregación + gráficos** (desde la raíz del repo con `PYTHONPATH=TESIS_SOILING`):

```bash
python -m analysis.semanal.agregacion_q25
```

**2. Análisis (correlación y reporte):**

```bash
python -m analysis.semanal.analisis_semanal
```

Con rutas opcionales:

```bash
python -m analysis.semanal.agregacion_q25 [sr_dir] [out_dir]
python -m analysis.semanal.analisis_semanal [semanal_dir]
```
