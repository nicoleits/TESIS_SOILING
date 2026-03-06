# Análisis de tendencias — SR semanal Q25 normalizado

## Cómo se obtiene la pendiente

1. **Datos de entrada:** el archivo `sr_semanal_norm.csv` (generado por la agregación semanal). Para cada metodología hay **un valor de SR por semana**: es el Q25 (percentil 25) del SR de esa semana, **normalizado** para que la primera semana valga 100 %.  
   - Ejemplo: semana 1 → 100 %, semana 10 → 99.2 %, semana 20 → 98.1 %, etc.

2. **Variable tiempo:** a cada semana se le asigna un número: **x = 0, 1, 2, 3, …** (semana 1 = 0, semana 2 = 1, etc.).

3. **Regresión lineal:** para cada instrumento se ajusta la recta  
   **SR = a + b × x**  
   donde:
   - **SR** = valor normalizado en % (eje Y),
   - **x** = número de semana (0, 1, 2, …),
   - **a** = ordenada en el origen,
   - **b** = **pendiente**: cuánto cambia el SR (en puntos %) cuando avanzamos **una semana**.

4. **Cálculo:** se usa regresión por mínimos cuadrados (`scipy.stats.linregress`). La **pendiente b** es lo que se reporta como “Pendiente (%/semana)”: si b = −0,10, en promedio el SR baja **0,10 puntos porcentuales por semana**.

5. **Pendiente por mes:** se convierte a “%/mes” multiplicando por el factor (semanas por mes):  
   `pendiente_por_mes ≈ pendiente_por_semana × 4,35`.

**En resumen:** la pendiente es la **tasa de cambio promedio** del SR normalizado en el tiempo (en % por semana). Una pendiente negativa significa que el SR tiende a bajar semana a semana (por ejemplo, por acumulación de soiling).

---

## Resumen

| Instrumento | Pendiente (%/semana) | Pendiente (%/mes) | R² | p-value | n_semanas |
|-------------|---------------------|-------------------|-----|---------|-----------|
| Soiling Kit | -0.1032 | -0.4489 | 0.9278 | 0.0000 | 54 |
| DustIQ | -0.0575 | -0.2499 | 0.8895 | 0.0000 | 54 |
| RefCells | -0.1179 | -0.5129 | 0.8643 | 0.0000 | 37 |
| PVStand Pmax | -0.1754 | -0.7628 | 0.7626 | 0.0000 | 50 |
| PVStand Isc | -0.1222 | -0.5314 | 0.9367 | 0.0000 | 50 |
| IV600 Pmax | -0.1347 | -0.5856 | 0.8107 | 0.0000 | 29 |
| IV600 Isc | -0.0965 | -0.4197 | 0.6785 | 0.0000 | 29 |

## Interpretación

- **Pendiente negativa:** el SR tiende a bajar en el tiempo (acumulación de soiling o deriva).
- **Pendiente ≈ 0:** el SR se mantiene estable en promedio.
- **Pendiente positiva:** el SR tiende a subir (recuperación, lluvia, o efecto estacional).
- **R²** mide cuánto de la variabilidad del SR se explica por la tendencia lineal.
- **p-value < 0,05** sugiere que la pendiente es estadísticamente significativa.
