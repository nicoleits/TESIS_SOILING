# Verificación de datos — ρm (densidad de masa superficial)

Esta carpeta reúne los datos necesarios para comprobar que se usan las masas y períodos correctos,
y que el cálculo de ρm y los estadísticos son coherentes.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| **masas_originales_con_periodos.csv** | Masas por vidrio y período de exposición usadas en el pipeline. `masa_inicial_g` = masa limpia (referencia del ciclo), `masa_final_g` = masa al llegar (soiled), `delta_m_g` = max(0, final − inicial). Una fila por (fecha_llegada, periodo, muestra). |
| **datos_procesados_rho.csv** | Mismas filas que se usan para el gráfico SR vs ρm y para la tabla de estadísticos. Incluye `delta_m_g`, `rho_m_mg_cm2` = Δm/área (área = 12 cm²). Opcionalmente SR Q25. |
| **estadisticos_rho_m_por_periodo.csv** / **.md** | Resumen por período: n, ρm mediana, P25, P75, Media, 1σ. |

## Tratamiento de inconsistencias (masa sucia &lt; masa limpia o Δm &lt; 0)

En todo el análisis de masas se aplica la misma regla:

- **Si la diferencia bruta es negativa** (masa sucia &lt; masa limpia, o `Diff_*_mg` &lt; 0 en la tabla oficial): **se considera Δm = 0**, no se elimina la fila.
- **Motivo:** se asume que valores negativos son por ruido de medida o rotación de muestra (acumulación física no negativa). Así se evita descartar eventos y se mantiene trazabilidad.
- **Dónde se aplica:**
  - **Tabla oficial → merge:** en `cargar_tabla_oficial_masas`, si `Diff_X_mg` &lt; 0 se guarda `delta_m_g = 0`.
  - **Export a resultados_diferencias_masas:** `Diferencia_Masa_*_mg = max(Diff, 0)`.
  - **Acumulación desde calendario** (sin tabla oficial): `delta_m_g = max(0, masa_final − masa_inicial)`.
  - **Dispersión (formato largo):** se excluyen filas con `Diferencia_mg` &lt; 0 (en la práctica ya vienen como 0).
- **Incertidumbre:** u(Δm) y U(Δm) se calculan siempre a partir de las pesadas (u(m_soiled), u(m_clean)); cuando Δm se ha forzado a 0, el valor reportado es 0 pero la incertidumbre sigue siendo la propagada de las dos masas.

Si en algún momento se quisiera **marcar** o **excluir** filas con diferencia bruta negativa en lugar de forzarlas a 0, habría que cambiar esta lógica en los puntos anteriores y documentarlo.

---

## Cadena de verificación

1. **Masas originales**: Revisar que `fecha_llegada`, `inicio_exposicion`, `periodo` y las masas correspondan al calendario de muestras y al emparejamiento soiled/clean que se espera.
2. **Datos procesados**: Comprobar que `rho_m_mg_cm2` = (`delta_m_g` × 1000) / área, con área = 12 cm² (4×3 cm).
3. **Estadísticos**: Comprobar que, por período, mediana/P25/P75/Media/1σ coinciden con los valores de `rho_m_mg_cm2` en *datos_procesados_rho.csv* agrupados por `periodo`.
