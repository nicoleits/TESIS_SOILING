# Análisis de tendencias — SR semanal Q25 (SIN normalizar) (IV600 Pmax/Isc valor absoluto)

Regresión lineal **SR = a + b × (semana)** por metodología. La pendiente **b** es la tasa de cambio en % por semana.

## Resumen

| Instrumento | Pendiente (%/semana) | Pendiente (%/mes) | R² | p-value | n_semanas |
|-------------|---------------------|-------------------|-----|---------|-----------|
| Soiling Kit | -0.1030 | -0.4481 | 0.9278 | 0.0000 | 54 |
| DustIQ | -0.0570 | -0.2479 | 0.8895 | 0.0000 | 54 |
| RefCells | -0.1164 | -0.5063 | 0.8534 | 0.0000 | 36 |
| PVStand Pmax | -0.1735 | -0.7545 | 0.7626 | 0.0000 | 50 |
| PVStand Isc | -0.1216 | -0.5289 | 0.9367 | 0.0000 | 50 |
| IV600 Pmax | -0.1342 | -0.5837 | 0.8107 | 0.0000 | 29 |
| IV600 Isc | -0.0961 | -0.4180 | 0.6785 | 0.0000 | 29 |

## Interpretación

- **Pendiente negativa:** el SR tiende a bajar en el tiempo (acumulación de soiling o deriva).
- **Pendiente ≈ 0:** el SR se mantiene estable en promedio.
- **Pendiente positiva:** el SR tiende a subir (recuperación, lluvia, o efecto estacional).
- **R²** mide cuánto de la variabilidad del SR se explica por la tendencia lineal.
- **p-value < 0,05** sugiere que la pendiente es estadísticamente significativa.

## Tendencias mensuales

**Método en esta ejecución:** Q25 de datos diarios por mes (PV Glasses: media de Q25 semanales).
Regresión lineal **SR_mes = a + b × (índice de mes con dato)**; **b** = % SR por mes.

Serie numérica: `sr_mensual_q25_desde_datos_diarios.csv` + `tendencias_mensuales_resumen.csv` + gráficos `tendencias_mensuales_*.png`.

### Cambio mes a mes (punto a punto)

- `pendientes_entre_meses.csv`: **pendiente_pp** entre meses consecutivos **en la serie observada**; **meses_calendario_entre_puntos**; **pendiente_pp_por_mes_calendario**.
- `pendientes_entre_meses_tramo_1_mes_calendario.csv`: solo cuando entre fechas hay **1 mes** de calendario.
- `pendientes_entre_meses_resumen_por_instrumento.csv`: medias / desviaciones.

## Pendientes entre semanas

- `pendientes_entre_semanas.csv`: entre cada par de semanas **consecutivas en la serie observada** (solo días con dato),
  **pendiente_pp** = cambio de SR; **semanas_calendario** = días/7 entre fechas; **pendiente_pp_por_semana_calendario** = pendiente_pp / semanas_calendario.
- `pendientes_entre_semanas_tramo_1_semana_calendario.csv`: solo tramos con **7 días** entre fechas (semanas ISO contiguas).
- `pendientes_entre_semanas_resumen_por_instrumento.csv`: medias y desviaciones por instrumento.
- `delta_semanal_sr_q25_punto_a_punto.csv`: columnas antiguas (delta_pp = pendiente_pp).
