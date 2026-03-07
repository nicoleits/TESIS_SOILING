# Resultados de incertidumbres (GUM)

Carpeta dedicada a los **resultados de cálculo de incertidumbres** del proyecto. Aquí se guardan CSVs y tablas que incluyen columnas u(·) y U(·) (incertidumbre estándar e expandida k=2).

---

## Contenido

| Archivo | Descripción |
|---------|-------------|
| **masas_pv_glasses_con_incertidumbres.csv** | Diferencias de masa por evento (Periodo, Exposicion_dias) y vidrio (A, B, C), con columnas de incertidumbre: u_Delta_m_*_mg, U_Delta_m_*_mg, rho_m_*_mg_cm2, u_rho_m_*_mg_cm2, U_rho_m_*_mg_cm2. Generado automáticamente al ejecutar el pipeline de PV Glasses cuando se usa la tabla oficial de masas. |

En el futuro se podrán añadir aquí salidas de incertidumbre de SR (RefCells, DustIQ, PV Glasses, etc.) y agregaciones con u/U.

---

## Origen

Los datos se generan desde los módulos de `analysis/uncertainty/` (p. ej. `mass.py`) y se escriben en esta carpeta al correr el pipeline correspondiente (p. ej. `pv_glasses_calendario`). Las constantes y criterios están documentados en `PARAMETROS_INCERTIDUMBRE.md`.
