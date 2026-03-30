# Resumen comparativo: incertidumbre de SR por metodología (sin normalizar)

**Contexto sin normalizar (eje temporal de SR):** los SR de entrada son **porcentaje absoluto** según cada metodología (CSV en `analysis/sr/` y `sr_q25` por período en PV Glasses). **No** se reescalan las series al 100 % de la primera semana. Las incertidumbres u_c y U se obtienen propagando sobre esos valores (GUM, k=2 para U).

Incertidumbre combinada u_c(SR) e expandida U(SR) en **puntos porcentuales (pp)** para comparar con métricas de variabilidad en pp.

| Metodología | Salida usada para SR | n válido | u_c(SR) mediana [pp] | P25–P75 de u_c(SR) [pp] | U(SR) mediana [pp] | máximo de U(SR) [pp] | fuente dominante del presupuesto |
|-------------|----------------------|----------|----------------------|-------------------------------|-------------------|------------------------|------------------------------------|
| PV Glasses | pv_glasses_por_periodo.csv (sr_q25) | 82 | 1.7415 | 1.706–1.782 | 3.4829 | 3.6036 | escala (fotoceldas 2,5 % k=2) |
| RefCells | refcells_sr.csv (SR) | 287 | 1.7726 | 1.754–1.785 | 3.5452 | 3.6055 | escala (fotoceldas 2,5 % k=2) |
| DustIQ | dustiq_sr.csv (SR) | 347 | 0.4866 | 0.483–0.491 | 0.9732 | 0.999 | aditiva 0,1 % + escala 1 % (k=2) |
| Soiling Kit | soilingkit_sr.csv (SR) | 358 | 0.1374 | 0.136–0.139 | 0.2748 | 0.2831 | escala Isc 0,2 % (k=2) |
| PVStand | pvstand_sr_corr.csv (SR_Pmax_corr) | 306 | 0.2605 | 0.255–0.270 | 0.5209 | 0.5892 | escala Pmax 0,4 % (k=2) + PT100 (corrección T) |
| PVStand Isc | pvstand_sr_corr.csv (SR_Isc_corr) | 306 | 0.1368 | 0.135–0.140 | 0.2735 | 0.2827 | escala Isc 0,2 % (k=2) + PT100 (corrección T) |
| IV600 Pmax | iv600_sr_corr.csv (SR_Pmax_corr_434) | 154 | 0.6975 | 0.692–0.708 | 1.3951 | 1.4797 | escala Pmax 1 % (k=2) + PT100 (corrección T) |
| IV600 Isc | iv600_sr_corr.csv (SR_Isc_corr_434) | 154 | 0.1385 | 0.138–0.140 | 0.277 | 0.2906 | escala Isc 0,2 % (k=2) + PT100 (corrección T) |

