# Verificación de datos — ρm (densidad de masa superficial)

Esta carpeta reúne los datos necesarios para comprobar que se usan las masas y períodos correctos,
y que el cálculo de ρm y los estadísticos son coherentes.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| **masas_originales_con_periodos.csv** | Masas por vidrio y período de exposición usadas en el pipeline. `masa_inicial_g` = masa limpia (referencia del ciclo), `masa_final_g` = masa al llegar (soiled), `delta_m_g` = max(0, final − inicial). Una fila por (fecha_llegada, periodo, muestra). |
| **datos_procesados_rho.csv** | Mismas filas que se usan para el gráfico SR vs ρm y para la tabla de estadísticos. Incluye `delta_m_g`, `rho_m_mg_cm2` = Δm/área (área = 12 cm²). Opcionalmente SR Q25. |
| **estadisticos_rho_m_por_periodo.csv** / **.md** | Resumen por período: n, ρm mediana, P25, P75, Media, 1σ (fuente: tabla oficial de masas cuando está disponible). |

## Cadena de verificación

1. **Masas originales**: Revisar que `fecha_llegada`, `inicio_exposicion`, `periodo` y las masas correspondan al calendario de muestras y al emparejamiento soiled/clean que se espera.
2. **Datos procesados**: Comprobar que `rho_m_mg_cm2` = (`delta_m_g` × 1000) / área, con área = 12 cm² (4×3 cm).
3. **Estadísticos**: Comprobar que, por período, mediana/P25/P75/Media/1σ coinciden con los valores de `rho_m_mg_cm2` en *datos_procesados_rho.csv* agrupados por `periodo`.
