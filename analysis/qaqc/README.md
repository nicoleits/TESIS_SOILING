# Análisis del efecto del QA/QC

Este módulo cuantifica el efecto de los filtros de calidad (QA/QC) sobre el conjunto de datos y ayuda a que el lector entienda **qué quedó después de aplicar los filtros** y por qué la comparación entre módulos es justa.

## Salidas

### Tablas
| Archivo | Descripción |
|---------|-------------|
| `qaqc_embudo_dias.csv` / `qaqc_embudo_dias.md` | Tabla tipo embudo: días en cada etapa del filtrado (iniciales → irradiancia/cielo despejado → ventana mediodía solar → estabilidad → finales comparables). |
| `qaqc_indicador_estabilidad_por_dia.csv` | Valor del indicador de estabilidad por día (para transparencia). |

### Figuras del proceso y resultado
| Archivo | Descripción |
|---------|-------------|
| **`qaqc_resumen_visual.png`** | **Figura resumen en una sola imagen**: embudo de días (A), distribución de cercanía al mediodía solar (B) y distribución del indicador de estabilidad (C). Ideal para ver todo el proceso y resultado de la limpieza de un vistazo. |
| `qaqc_embudo_visual.png` | Embudo de días en barras horizontales: se ve cómo se estrecha el conjunto en cada filtro, con las pérdidas (−4, −12, −11) anotadas. |
| `qaqc_waterfall_filtros.png` | Waterfall: barras por etapa con anotaciones de días perdidos entre etapas. |
| `qaqc_dist_solar_noon_min.png` | Distribución de la distancia (min) ventana–mediodía solar y umbral (50 min). |
| `qaqc_estabilidad_umbral.png` | Distribución del indicador de estabilidad y umbral (10%). |

## Uso

Desde la raíz del proyecto **TESIS_SOILING**:

```bash
python -m analysis.qaqc.analisis_efecto_qaqc
```

Con directorio de datos custom:

```bash
python -m analysis.qaqc.analisis_efecto_qaqc /ruta/a/data
```

## Interpretación

- **Embudo**: La tabla muestra cuántos días se pierden en cada paso (irradiancia suficiente y cielo despejado, ventana de mediodía solar, estabilidad intraventana). Los **días finales comparables** son los que se usan para alinear todos los módulos y calcular SR; así se garantiza que las comparaciones se hacen en las mismas fechas y bajo criterios objetivos.
- **dist_solar_noon_min**: Valores concentrados y por debajo del umbral (50 min) indican que la selección de la sesión «cercana al mediodía solar» es consistente.
- **Estabilidad**: La mayoría de los días con sesión de mediodía solar cumplen el umbral de estabilidad; los que no se excluyen para evitar ventanas con alta variación de irradiancia (nubes pasajeras, etc.).
