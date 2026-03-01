# Resumen de resultados — PV Glasses

## 1. Método

- **Instrumento:** 5 fotoceldas (FC1–FC2 referencias limpias, FC3–FC5 con vidrios sucios A, B, C).
- **SR:** \( \mathrm{SR}_{FCi} = 100 \times R_{FCi} / \mathrm{REF} \), con \( \mathrm{REF} = (R_{FC1} + R_{FC2})/2 \). Se aplica corrección **+7.5%** por transmitancia del vidrio.
- **Ventana de medición:** 5 días tras la llegada del vidrio a la fotocelda (ventana post-“Fija a RC, soiled”), datos en ventana 14–17 UTC (mediodía solar). Fuente: `pv_glasses_poa_500_clear_sky.csv` (364 días).
- **Mapeo:** Vidrio A → FC5, Vidrio B → FC4, Vidrio C → FC3.
- **Métricas:** Q25 (percentil 25, conservador) y mediana por (período, vidrio). Total **82 mediciones** (incl. período 1 año).

---

## 2. Resultados por período (agregado)

| Período       | Días ref. | n   | SR Q25 (%) | SR mediana (%) | Pérdida (pp) |
|---------------|-----------|---|------------|----------------|--------------|
| Semanal       | 7         | 50 | 96.45      | 96.84          | 3.55         |
| 2 semanas     | 14        | 4  | 96.32      | 97.76          | 3.68         |
| Mensual       | 30        | 6  | 92.69      | 94.80          | 7.31         |
| Trimestral    | 91        | 5  | 94.25      | 94.52          | 5.75         |
| Cuatrimestral | 120       | 8  | 87.87      | 90.81          | 12.13        |
| Semestral     | 182       | 6  | 88.45      | 90.66          | 11.55        |
| **1 año**     | **365**   | **3** | **80.28** | **80.52**      | **19.72**    |

- **Mayor pérdida:** 1 año (19.72 pp).
- **Menor pérdida:** semanal (3.55 pp).
- Tasa lineal aproximada: ~16 pp/año (ajuste lineal sobre Q25).

---

## 3. Resultados por vidrio (Q25)

| Período       | Vidrio A (Q25) | Vidrio B (Q25) | Vidrio C (Q25) |
|---------------|----------------|----------------|----------------|
| Semanal       | 96.33          | 96.32          | **99.50**      |
| 2 semanas     | 96.57          | 95.58          | **99.13**      |
| Mensual       | 92.69          | 92.54          | **97.22**      |
| Trimestral    | 90.98          | 95.24          | 95.09          |
| Cuatrimestral | 89.45          | 86.91          | **91.18**      |
| Semestral     | 88.97          | 87.08          | **91.69**      |
| 1 año         | 80.52          | 80.04          | **86.91**      |

- **Vidrio C (FC3)** mantiene sistemáticamente **SR más alto** que A y B (~2–3 pp en semanal, ~6–7 pp en 1 año).
- **Vidrio B (FC4)** suele ser el más afectado en períodos largos (cuatrimestral, semestral, 1 año).

---

## 4. Hallazgos principales

1. **Tendencia con días de exposición:** a mayor tiempo de exposición, mayor pérdida de SR (semanal ~96.5% → 1 año ~80.3%).
2. **Estacionalidad:** hay incongruencias aparentes (p. ej. trimestral mejor que mensual en algunos eventos) por **época del año** en que se mide (verano vs invierno), no por error de método.
3. **Diferencias entre vidrios:** C consistentemente más limpio; A y B más similares; en 1 año los tres caen (A≈80.5%, B≈80.0%, C≈86.9%).
4. **Período anual:** una sola ventana de medición (ago 2025), 3 puntos (uno por vidrio); SR Q25 global 80.28%, pérdida 19.72 pp.

---

## 5. Archivos generados

- **Datos:** `pv_glasses_por_periodo.csv`, `pv_glasses_resumen.csv`
- **Tablas:** `pv_glasses_sr_por_periodo_por_vidrio.csv`, `pv_glasses_resumen_q25_y_mediana.md`
- **Gráficos:** `pv_glasses_sr_por_periodo.png`, `pv_glasses_sr_por_periodo_por_vidrio.png`, `pv_glasses_sr_por_vidrio.png`, `pv_glasses_sr_vs_dias.png`, `pv_glasses_curva_acumulacion.png`, `pv_glasses_datos_detalle.png`, `pv_glasses_sr_vs_masa.png`
- **Reporte:** `pv_glasses_report.md`

---

## 6. Limitaciones

- Días con FC2 ≈ 0 se excluyen (SR = NaN).
- Períodos con n = 1 o 2 tienen mayor incertidumbre (p. ej. 2 semanas, 1 año).
- La ventana de 5 días post-llegada es fija; no se corrige por lluvia o eventos puntuales en esa ventana.
- **Hueco en datos PV Glasses:** La referencia Solys2 se generó con el archivo completo (`raw_solys2_data.csv`), pero los datos crudos de PV Glasses (`raw_pv_glasses_data.csv`) tienen un hueco **2024-08-11 → 2024-09-05**; por eso 2 de los 4 eventos “Mensual” del calendario no aportan datos (ventanas 14–18 ago y 28 ago–1 sep). Para completarlos haría falta un export completo de PV Glasses para ese periodo.
