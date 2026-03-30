# Informe unificado: metodologías de soiling

Este documento enlaza los análisis realizados con las distintas metodologías (ópticas / SR y gravimétrica) para evaluar el soiling.

---

## 1. Metodologías basadas en Soiling Ratio (SR)

**Variable:** SR semanal Q25 normalizado (t₀ = 100%).  
**Instrumentos:** Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, IV600, IV600 corr.  

**Por qué PV Glasses (SR) no se incluye:** Cada medición de PV Glasses corresponde a un **periodo de exposición** distinto (una semana, dos semanas, mensual, etc.). Un mismo “día” puede ser SR tras 7 días de exposición y al día siguiente SR tras 35 días; no hay una serie “un valor por semana” con la misma interpretación que el resto. La comparación ANOVA/disporsión exige una serie temporal comparable (mismo concepto por semana); el análisis de PV Glasses por periodo y por masas sigue en la sección 2.

| Recurso | Descripción |
|--------|-------------|
| [informe_comparativo.md](informe_comparativo.md) | Comparación entre instrumentos: estadísticos descriptivos (media, std, CV, rango P95–P05), ANOVA, correlación cruzada e interpretación. |
| [anova/anova_report.md](anova/anova_report.md) | ANOVA y Kruskal-Wallis del SR semanal por instrumento; post-hoc Tukey y Dunn. |
| [correlacion/correlacion_report.md](correlacion/correlacion_report.md) | Correlación de Pearson entre pares de instrumentos y matriz de dispersión. |
| [stats/agregacion_semanal](stats/agregacion_semanal.py) | Agregación semanal Q25 + análisis de dispersión entre semanas (`dispersion_semanal.csv`, boxplot). |
| [stats/analisis_estadistico_report.md](stats/analisis_estadistico_report.md) | Estadísticos de datos filtrados/alineados (ventana 5 min, entre días) por módulo. |

---

## 2. Metodología gravimétrica (PV Glasses)

**Variable:** Diferencia de masa Δm = masa soiled − masa clean (mg), por periodo de exposición.  
**Origen:** Vidrios colocados en estructura fija y en fotoceldas (RC); emparejamiento por ciclo (Inicio Exposición + Fila) según calendario de muestras.

| Recurso | Descripción |
|--------|-------------|
| [pv_glasses/resultados_diferencias_masas.csv](pv_glasses/resultados_diferencias_masas.csv) | Pares soiled/clean con Δm para Masa A, B y C por medición (y número de fila). |
| [pv_glasses/dispersion_masas_report.md](pv_glasses/dispersion_masas_report.md) | **Análisis de dispersión:** por periodo: N, media, std, CV(%), rango P95–P05, media de la std entre vidrios A/B/C. |
| [pv_glasses/dispersion_masas_por_periodo.csv](pv_glasses/dispersion_masas_por_periodo.csv) | Tabla numérica de los estadísticos de dispersión por periodo. |
| [pv_glasses/pv_glasses_promedio_soiling_por_periodo.png](pv_glasses/pv_glasses_promedio_soiling_por_periodo.png) | Gráfico de barras: promedio general (A+B+C)/3 por periodo de exposición (mg). |
| [pv_glasses/dispersion_masas_barras_error.png](pv_glasses/dispersion_masas_barras_error.png) | Media por periodo con barras de error ±1 std. |
| [pv_glasses/dispersion_masas_boxplot.png](pv_glasses/dispersion_masas_boxplot.png) | Boxplot de (A+B+C)/3 por periodo. |
| [pv_glasses/RESUMEN_PV_GLASSES.md](pv_glasses/RESUMEN_PV_GLASSES.md) | Resumen del análisis PV Glasses (SR y masas). |

**Resumen de dispersión (método gravimétrico):**  
Los periodos con más mediciones (p. ej. semanal, N=18) permiten estimar mejor la variabilidad (std, CV). La columna *Media_std_entre_vidrios_mg* indica la dispersión entre los tres vidrios (A, B, C) en la misma medición. Ver [pv_glasses/dispersion_masas_report.md](pv_glasses/dispersion_masas_report.md) para la tabla completa.

---

## 3. Cómo reproducir el análisis

1. **Masas (gravimétrico):**  
   - Generar diferencias: `python masas_analysis.py --excel "data/calendario/20241114 Calendario toma de muestras soiling.xlsx"` (desde `si_test`).  
   - Gráfico promedio por periodo: `python -m analysis.pv_glasses.grafico_promedio_soiling_por_periodo` (desde `TESIS_SOILING`).  
   - Dispersión: `python -m analysis.pv_glasses.dispersion_masas` (desde `TESIS_SOILING`).

2. **SR (ópticos):**  
   - Agregación semanal y dispersión: `python -m analysis.stats.agregacion_semanal` (desde `TESIS_SOILING`).  
   - ANOVA: ver `analysis/anova/`.  
   - Correlación: ver `analysis/correlacion/`.

3. **Estadísticos de datos alineados:**  
   - `python -m analysis.stats.analisis_estadistico [data_dir]` (desde `TESIS_SOILING`).
