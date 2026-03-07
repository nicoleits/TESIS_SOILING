# Cálculo de incertidumbres (GUM)

Esta carpeta concentra **todo el cálculo de incertidumbres de medida** del proyecto (SR y Δm), de forma ordenada y reproducible, según el proceso descrito en `PROCESO_COMPLETO_CALCULO_DE_ERRORES.md` y `PROPUESTA_IMPLEMENTACION_INCERTIDUMBRES.md` (raíz del repo).

---

## Estructura de la carpeta

```
TESIS_SOILING/analysis/uncertainty/
├── README.md                 ← Este documento (estructura, fases, parámetros)
├── PARAMETROS_INCERTIDUMBRE.md   ← Parámetros a confirmar (no asumir)
├── constants.py              ← Constantes u_add, u_scale (k=1) por sensor/balanza
├── propagation.py            ← Modelo aditivo+escala y propagación GUM
├── mass.py                   ← Flujo B: u(Δm), U(Δm) por muestra
├── sr_*.py                   ← Flujo A por metodología (cuando se implemente)
├── __init__.py
└── results/                  ← Salidas: CSVs/tablas con u_*, U_* (opcional)
```

- **Entradas:** Los módulos reciben DataFrames o rutas a CSVs ya definidos (p. ej. tabla oficial de masas, resultados_diferencias_masas, SR por metodología).
- **Salidas:** Se escriben en `results/` o en la ruta que se indique (p. ej. integración con `pv_glasses/`). Nombres de columnas: `u_Delta_m_A_mg`, `U_Delta_m_A_mg`, etc., y para SR: `u_SR`, `U_SR`.

---

## Orden de implementación (fases)

| Fase | Contenido | Estado |
|------|-----------|--------|
| **1** | Incertidumbre de **masas** (Δm): constantes balanza, propagación, columnas u(Δm) y U(Δm) en resultados. | **Implementado** (mass.py; integrado en pv_glasses_calendario) |
| **2** | Incertidumbre **SR** RefCells y DustIQ. | Pendiente |
| **3** | Incertidumbre SR Soiling Kit, PVStand, IV600, PV Glasses. | Pendiente |
| **4** | Agregación temporal (semanal/mensual) con u; uso de U en gráficos. | Pendiente |

Solo se implementará código una vez **confirmados los parámetros** necesarios para cada fase (ver abajo y `PARAMETROS_INCERTIDUMBRE.md`).

---

## Parámetros que hay que confirmar (no se asume ninguno)

Para avanzar con la **Fase 1 (masas)** hace falta que confirmes o proporciones:

### Balanza (masas)

- **Modelo o identificador** de la balanza usada para las pesadas de PV Glasses (para documentación).
- **Cuando solo tienes el error instrumental:** se toma como única contribución a u(m). **u_scale = 0** y **u_add = error instrumental en k=1** (si te dan ±E con k=2 → u_add = E/2). Así u(m) = u_add en cada pesada y **u(Δm) = √2·u_add**. Detalle en `PARAMETROS_INCERTIDUMBRE.md` (Fase 1).
- **u_add (k=1):** valor numérico y unidad (g o mg). **u_scale:** 0 si solo error instrumental.

Si tienes **certificado de calibración** de la balanza, indica la página o párrafo donde aparecen incertidumbre expandida (U) o estándar (u) y factor k, para que los valores en el código queden referenciados.

---

### Fases 2–4 (SR y agregación) — para más adelante

- **RefCells / PV Glasses (fotoceldas):** U_ADD y U_SCALE (k=2) según fabricante/certificado; confirmar si REF = (FC1+FC2)/2 y nombres de columnas en los CSVs.
- **DustIQ, Soiling Kit, PVStand, IV600:** Valores de incertidumbre según especificación o certificado (no asumir).
- **Agregación:** Criterio para incertidumbre por ventana (promedio de u(SR) en la ventana, solo sobre puntos con SR válido, etc.).
- **NaN/outliers:** Criterio escrito (p. ej. si SR &lt; 80 → u(SR) y U(SR) también NaN).

Nada de esto se implementará con valores inventados; cuando quieras seguir con SR o agregación, se definirán los parámetros igual que para masas.

---

## Referencias

- **Proceso y fórmulas:** `PROCESO_COMPLETO_CALCULO_DE_ERRORES.md` (raíz del repo).
- **Propuesta de módulos y fases:** `PROPUESTA_IMPLEMENTACION_INCERTIDUMBRES.md` (raíz del repo).
- **Datos de masas actuales:** `pv_glasses/verificacion/tabla_oficial_masas.csv` y `pv_glasses/resultados_diferencias_masas.csv` (columnas Masa_*_Soiled_g, Masa_*_Clean_g, Diferencia_Masa_*_mg).

Cuando tengas los valores de la balanza (y, si aplica, referencia al certificado), se puede implementar la Fase 1 en esta carpeta y dejar los resultados de incertidumbre en una subcarpeta específica (p. ej. `uncertainty/results/` o integrados en `pv_glasses/` según prefieras).
