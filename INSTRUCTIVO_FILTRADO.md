# Instructivo: proceso de filtrado por irradiancia (conceptual)

Este documento describe **solo la lógica del filtrado**, paso a paso, sin nombres de archivos, rutas ni código. Sirve como base para entender qué se hace y en qué orden.

---

## Información necesaria para los cálculos de irradiancia estimada

Para poder ejecutar los pasos de **POA** y **GHI clear-sky** hace falta definir lo siguiente (valores de ejemplo entre paréntesis; deben adaptarse al sitio real):

### Ubicación del sitio

- **Latitud** (grados decimales, p. ej. −24,09).
- **Longitud** (grados decimales, p. ej. −69,93).
- **Altitud** (metros sobre el nivel del mar, p. ej. 500).
- **Zona horaria** de los timestamps (p. ej. UTC), para que posición solar y modelo clear-sky sean coherentes con la hora.

### Geometría del panel (para POA)

- **Inclinación del panel** (grados desde la horizontal, p. ej. 20°).
- **Acimut del panel** (grados; convención según la librería usada: en muchas, 0° = Sur, 180° = Norte).

### Datos de entrada por instante (para POA)

- **Timestamp** de cada medición (fecha y hora).
- **GHI** (irradiancia global horizontal, W/m²).
- **DHI** (irradiancia difusa horizontal, W/m²).
- **DNI** (irradiancia directa normal, W/m²).

Con ubicación y timestamp se calcula la **posición solar** (ángulo cenital, acimut); con esa posición y la geometría del panel se descompone GHI/DHI/DNI en el plano del array y se obtiene el **POA**.

### Modelo clear-sky (para GHI clear-sky)

- **Nombre del modelo** (p. ej. Ineichen). El modelo estima la GHI teórica en cielo claro; internamente suele usar ángulo cenital, masa de aire y turbidez (p. ej. Linke), que muchas librerías calculan a partir de ubicación y timestamp.
- Los **mismos timestamps** que la base de irradiancia.
- La **misma ubicación** (latitud, longitud, altitud, zona horaria).

### Umbrales del filtro (para la base de referencia)

- **Umbral de POA** (W/m²): mínimo de irradiancia en el plano del panel para considerar el instante válido (p. ej. 500).
- **Umbral de ratio clear-sky** (adimensional): mínimo de *GHI medido / GHI clear-sky* para considerar cielo suficientemente despejado (p. ej. 0,8).

### Tolerancia temporal (para el filtrado de módulos)

- **Ventana de tiempo** (p. ej. 5 minutos): un registro de un módulo se conserva si existe un instante de la base de referencia dentro de esa ventana (antes o alrededor de ese registro).

Con estos datos se pueden reproducir los cálculos de irradiancia estimada (POA y GHI clear-sky) y el filtrado sin depender de archivos o rutas concretas.

---

## Objetivo

Quedarse con **solo aquellos registros** de los distintos módulos/sensores que corresponden a **instantes con irradiancia suficiente y cielo suficientemente despejado**. Así se evita analizar Soiling Ratio (SR) en condiciones de poca luz o nubosidad, que distorsionan el resultado.

---

## Paso 1: Base de irradiancia global (GHI, DHI, DNI)

- Se parte de datos de **radiación solar en horizontal**: GHI (global), DHI (difusa), DNI (directa), típicamente en W/m², con timestamp.
- Esa base suele provenir de un **piranómetro / estación meteorológica** y cubrir el mismo rango de fechas que el resto de sensores.

---

## Paso 2: Cálculo de POA (irradiancia en el plano del panel)

- A partir de **GHI, DHI y DNI** y de la **geometría del sitio** (inclinación y acimut del panel, latitud, longitud, altitud), se calcula la **irradiancia en el plano del array (POA)** para cada timestamp.
- Así cada instante tiene un valor de **POA** (W/m²) que representa la irradiancia que “ve” el panel.

---

## Paso 3: GHI clear-sky (modelo teórico)

- Se calcula la **GHI que habría en condiciones de cielo claro** (sin nubes) para cada timestamp, usando un **modelo de cielo claro** (p. ej. Ineichen) y la misma ubicación y hora. Para esto usa pvlib.
- El resultado es una serie **GHI clear-sky** (W/m²) con la que se va a comparar la GHI medida.

---

## Paso 4: Ratio clear-sky

- Se calcula el **ratio**  
  **clear_sky_ratio = GHI medido / GHI clear-sky**  
  (solo cuando GHI clear-sky es mayor que un umbral mínimo para evitar divisiones por cero).
- Valores **cercanos a 1** indican cielo despejado; valores **mucho menores que 1** indican nubosidad o atenuación.

---

## Paso 5: Construcción de la base de referencia (filtro sobre la irradiancia)

- Se aplican **dos condiciones** sobre la base de irradiancia (la que tiene GHI, POA, clear_sky_ratio):
  1. **POA ≥ 500 W/m²**: suficiente irradiancia en el plano del panel.
  2. **clear_sky_ratio ≥ 0,8**: cielo suficientemente despejado.
- Se **conservan solo** los instantes (timestamps) que cumplen **ambas** condiciones.
- El resultado es la **base de referencia**: un conjunto de instantes en los que las condiciones de irradiancia son “válidas” para el análisis.

---

## Paso 6: Filtrado de cada módulo/sensor con la base de referencia

- Para **cada tipo de dato** (Soiling Kit, IV, temperatura, refcells, etc.):
  - Se toma la serie de registros con sus timestamps.
  - Se **asocia cada registro** al instante de la base de referencia **más cercano en tiempo** (por ejemplo, dentro de una ventana de tolerancia de pocos minutos).
  - **Se conservan solo** los registros para los que existe un instante de referencia dentro de esa ventana; el resto se descarta.
- Así, **todos los módulos quedan filtrados** con el mismo criterio: solo registros que coinciden (en tiempo) con condiciones de irradiancia buenas (POA alto + cielo despejado).

---

## Paso 7: Casos con irradiancia propia (opcional)

- Si algún sensor **mide irradiancia en el plano** (p. ej. celdas de referencia con POA propia), además del filtrado por la base de referencia se puede aplicar un **filtro adicional**: conservar solo filas donde la irradiancia medida por ese sensor (en las celdas relevantes) sea **≥ 500 W/m²** (o el umbral definido) en **todas** las celdas usadas para el cálculo. Así se evitan puntos con poca luz en ese sensor concreto.

---

## Pasos posteriores al filtrado

Una vez aplicado el filtrado por irradiancia (pasos 1–7), el flujo continúa así, siempre sobre los datos ya filtrados:

### 1. Soiling Kit: sesión de mediodía solar

- Los datos del Soiling Kit (filtrados) se agrupan en **ventanas de 5 minutos** y se promedian las magnitudes dentro de cada ventana.
- Para **cada día** se calcula el **mediodía solar** (instante de máxima elevación del sol en esa ubicación) y se elige la ventana de 5 min cuyo **centro está más cerca** de ese instante.

**Cálculo del mediodía solar (con pvlib):** Se usa la misma **ubicación** del sitio (latitud, longitud, altitud, zona horaria). Para cada fecha se generan instantes **cada minuto** a lo largo del día en UTC; con **`Location.get_solarposition(times)`** se obtiene la **posición solar** (entre otras, la **elevación** en grados). El **mediodía solar** es el instante en que la elevación es **máxima** (o, equivalentemente, el ángulo cenital es mínimo). Ese instante se toma como mediodía solar en UTC para esa fecha.
- Solo se aceptan días en los que esa ventana queda a una **distancia máxima** del mediodía solar (p. ej. ≤ 50 min); si no, el día se descarta.
- Se puede aplicar filtro de **corriente mínima** (p. ej. Isc expuesta y protegida ≥ 1 A) para descartar puntos con poca señal.
- **Resultado:** una fila por día del Soiling Kit, representativa del mediodía solar, lista para calcular Soiling Ratio (SR).

### 2. Alineación del resto de módulos a las sesiones Soiling Kit

- Se toman los **mismos instantes (ventanas de 5 min por día)** definidos en el paso anterior y se **alinean** el resto de módulos (IV, temperatura, celdas de referencia, etc.) a esos horarios:
  - Si el módulo tiene datos cada 1 min: se promedian los valores en esa ventana de 5 min.
  - Si tiene resolución 5 min: se toma el valor más cercano al centro de la ventana.
  - Si la frecuencia es irregular: se toma el registro más cercano dentro de una ventana máxima (p. ej. 1 h).
- **Filtro de estabilidad de irradiancia:** solo se conservan los días en los que la irradiancia (POA) en esa ventana de 5 min es estable; *(G_max − G_min) / G_med &lt; 10 %*.
- **Resultado:** cada módulo queda con **una fila por día** (o una por módulo por día si hay varios canales), sincronizada con las sesiones del Soiling Kit y con días de irradiancia estable.

### 3. Cálculo de Soiling Ratio (SR) por módulo

- A partir de los datos **alineados**, se calcula un **Soiling Ratio** para cada módulo según su definición (p. ej. 100 × referencia/expuesto para Isc o Pmax, o el indicador que proporcione el sensor).
- **Resultado:** series temporales de SR por módulo (CSV y gráficos).

### 4. Opcional: corrección por temperatura

- Para módulos con medición de temperatura (p. ej. trazas IV), se puede aplicar **corrección a 25 °C** (p. ej. IEC 60891) y calcular un **SR corregido** para reducir el efecto de la temperatura en el indicador.

### 5. Opcional: análisis estadístico

- Sobre los datos alineados se puede ejecutar un **análisis estadístico** (dispersión en la ventana de 5 min, entre días, etc.) para caracterizar la calidad y variabilidad de las series.

---

## Resumen del flujo (solo filtrado)

1. Base con **GHI (y DHI, DNI)** para calcular **POA**.
2. Cálculo de **POA** a partir de GHI/DHI/DNI y geometría del sitio.
3. Cálculo de **GHI clear-sky** (modelo teórico).
4. Cálculo del **ratio** GHI_medido / GHI_clear_sky.
5. **Filtro sobre la irradiancia**: solo instantes con **POA ≥ 500** y **ratio ≥ 0,8** → **base de referencia**.
6. **Filtrado de cada módulo**: conservar solo registros cuyo timestamp coincide (con tolerancia) con la base de referencia.
7. **Opcional**: en sensores con irradiancia propia, filtro adicional por POA ≥ 500 en sus celdas.

A continuación se aplican los **pasos posteriores al filtrado** (sesión mediodía solar, alineación, SR, y opcionalmente corrección por temperatura y análisis estadístico).
