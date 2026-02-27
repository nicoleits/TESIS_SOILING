# Alineación de módulos con sesiones Soiling Kit

Alinea el resto de módulos a los mismos horarios (ventana de 5 min por día) que el Soiling Kit (sesión mediodía solar) y aplica un filtro de **estabilidad de irradiancia**.

## Reglas de alineación

| Frecuencia del módulo | Criterio |
|------------------------|----------|
| **1 min** (pv_glasses, dustiq, temperatura, refcells) | Se seleccionan los mismos 5 minutos diarios que el Soiling Kit y se promedia. |
| **5 min** (pvstand) | Se selecciona el dato más cercano al instante central del Soiling Kit. |
| **Irregular** (iv600) | Se selecciona el dato más cercano al Soiling Kit que no esté a más de **1 hora** de distancia. |

## Filtro de estabilidad

Al final se filtran los datos según estabilidad de irradiancia en la ventana de 5 min:

- **Criterio:** `(G_max - G_min) / G_med < 10%`
- **G:** columna POA del Solys2 (referencia `solys2_poa_500_clear_sky.csv`) en esa ventana.
- Solo se conservan los días que cumplen el criterio (para todos los módulos).

## Entradas

- `data/soilingkit/soilingkit_solar_noon.csv` (sesiones ya seleccionadas por mediodía solar).
- `data/solys2/solys2_poa_500_clear_sky.csv` (para estabilidad).
- CSVs filtrados de cada módulo (`*_poa_500_clear_sky.csv`).

## Salidas

En cada carpeta de módulo:

- `soilingkit_aligned_solar_noon.csv` (Soiling Kit solo filtrado por estabilidad).
- `<modulo>_aligned_solar_noon.csv` (una fila por día alineada, o varias si hay sub-módulos como pvstand).

## Ejecución

Desde **TESIS_SOILING**:

```bash
python -m analysis.align.align_to_soiling_kit
```

Con directorio de datos explícito:

```bash
python -m analysis.align.align_to_soiling_kit [ruta_a_data]
```
