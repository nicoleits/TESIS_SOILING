# PV Glasses — Análisis integrado con Calendario de Muestras

**Método:** Q25 del SR calculado durante la ventana [Fija→RC, RC→Fija),
es decir, los días en que el vidrio sucio está efectivamente sobre la fotocelda.  
**Mapeo:** FC5=Vidrio A · FC4=Vidrio B · FC3=Vidrio C  
**Total de mediciones procesadas:** 82  

---
## 1. SR Q25 por tipo de período de exposición

| Período | Días ref. | N mediciones | SR Q25 (%) | Pérdida (pp) | Std (pp) |
|---|---|---|---|---|---|
| semanal | 7 | 50 | 96.45 | 3.55 | 1.53 |
| 2 semanas | 14 | 4 | 96.32 | 3.68 | 1.93 |
| Mensual | 30 | 6 | 92.69 | 7.31 | 2.63 |
| Trimestral | 91 | 5 | 94.25 | 5.75 | 2.83 |
| Cuatrimestral | 120 | 8 | 87.87 | 12.13 | 3.95 |
| Semestral | 182 | 6 | 88.45 | 11.55 | 2.92 |
| 1 año | 365 | 3 | 80.28 | 19.72 | 3.84 |

---
## 1b. Correlación SR Q25 vs masa depositada (mg/cm²)

Objetivo del método: correlacionar pérdidas ópticas con masa acumulada.  
Masa por unidad de área (mg/cm²) es la métrica estándar en literatura para comparar deposición.  
- **R²** = 0.833  
- **Pendiente** = -13.9355 %/(mg/cm²) (regresión lineal SR Q25 vs masa/área)  
- N puntos (vidrio × período): 82  


---
## 2. Observaciones clave

- **Tasa de acumulación lineal:** -0.0443 pp/día (16.18 pp/año estimados)
- **Período con mayor pérdida (Q25):** 1 año (19.72 pp)
- **Período con menor pérdida (Q25):** semanal (3.55 pp)

---
## 3. Limitaciones

- Los días en que FC2 ≈ 0 el SR fue marcado NaN y excluido.
- Masa = 0 en algunos períodos indica muestra ausente (excluida).
- La ventana de medición excluye el día de salida (fin_salida).
