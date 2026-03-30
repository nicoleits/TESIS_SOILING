# Resultados de incertidumbres (GUM)

Carpeta dedicada a los **resultados de cálculo de incertidumbres** del proyecto. Aquí se guardan CSVs y tablas que incluyen columnas u(·) y U(·) (incertidumbre estándar e expandida k=2).

---

## Contenido

| Archivo | Descripción |
|---------|-------------|
| **masas_pv_glasses_con_incertidumbres.csv** | Diferencias de masa por evento (Periodo, Exposicion_dias) y vidrio (A, B, C), con columnas de incertidumbre: u_Delta_m_*_mg, U_Delta_m_*_mg, rho_m_*_mg_cm2, u_rho_m_*_mg_cm2, U_rho_m_*_mg_cm2. Generado automáticamente al ejecutar el pipeline de PV Glasses cuando se usa la tabla oficial de masas. |
| **resumen_incertidumbre_sr_por_metodologia.csv** / **.md** | Tabla comparativa por metodología: u_c(SR) y U(SR) en **puntos porcentuales (pp)** (mediana, P25–P75, máximo), n válido y fuente dominante del presupuesto. Entrada: SR en % absoluto desde `analysis/sr/` (y PV Glasses por período). |
| **resumen_incertidumbre_sr_por_metodologia_sin_normalizar.csv** / **.md** | Mismos números y columnas que la tabla anterior; nombre y texto en el `.md` dejan explícito el contexto **sin normalizar** el eje temporal (no anclar series al 100 % de la primera semana). Útil para TESIS_NO_NORM / memoria. Generado junto con el módulo `tabla_resumen_incertidumbre_sr`. |

En el futuro se podrán añadir aquí más salidas de incertidumbre de SR por metodología y agregaciones con u/U.

---

## Origen y actualización

- **masas_pv_glasses_con_incertidumbres.csv** se actualiza **automáticamente** al ejecutar el pipeline de PV Glasses con la tabla oficial de masas (`exportar_resultados_diferencias_desde_oficial`). Contiene los mismos datos y exclusiones que `pv_glasses/resultados_diferencias_masas.csv`.
- Si el archivo no incluye las columnas u(Δm), U(Δm), ρm, u(ρm), U(ρm) (p. ej. porque el módulo de incertidumbre no se cargó en el pipeline), puede generarlas con:
  ```bash
  python -m analysis.uncertainty.mass analysis/pv_glasses/resultados_diferencias_masas.csv -o analysis/uncertainty/results/masas_pv_glasses_con_incertidumbres.csv
  ```
  (ejecutar desde la raíz de `TESIS_SOILING` o ajustar rutas). Las constantes y criterios están en `PARAMETROS_INCERTIDUMBRE.md`.
