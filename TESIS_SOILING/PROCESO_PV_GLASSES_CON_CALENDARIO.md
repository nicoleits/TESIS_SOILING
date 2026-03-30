# Proceso Completo de Análisis del Módulo PV Glasses con Calendario de Muestras

**Proyecto:** Intercomparación de metodologías de estimación de Soiling Ratio  
**Sitio:** Desierto de Atacama, Chile  
**Coordenadas:** Lat -24.090°, Lon -69.929°, Alt 500 m s.n.m.  
**Período de datos:** 01-08-2024 — 31-07-2025  
**Documento actualizado:** Febrero 2026

---

## 1. Descripción del Equipo PV Glasses

El módulo **PV Glasses** es un instrumento de medición indirecta del soiling que utiliza cinco **fotoceldas de silicio** (FC) encastradas bajo muestras de vidrio de la misma composición que los módulos fotovoltaicos de campo:

| Celda | Rol | Columna en datos |
|-------|-----|-----------------|
| FC1 | Referencia limpia (sin vidrio expuesto) | `R_FC1_Avg` |
| FC2 | Referencia limpia (sin vidrio expuesto) | `R_FC2_Avg` |
| FC3 | Bajo vidrio expuesto a suciedad — **Muestra C** | `R_FC3_Avg` |
| FC4 | Bajo vidrio expuesto a suciedad — **Muestra B** | `R_FC4_Avg` |
| FC5 | Bajo vidrio expuesto a suciedad — **Muestra A** | `R_FC5_Avg` |

Las celdas FC1 y FC2 permanecen protegidas y actúan como referencia simultánea. Las celdas FC3, FC4 y FC5 tienen encima placas de vidrio que acumulan polvo atmosférico durante el período de exposición.

El instrumento registra la irradiancia en W/m² con resolución de **1 minuto**.

---

## 2. Principio de Medición y Fórmula del SR

El **Soiling Ratio** (SR) para cada celda soiled se calcula como la relación entre la irradiancia medida bajo el vidrio sucio y la irradiancia de referencia medida por las celdas limpias:

```
REF = (R_FC1_Avg + R_FC2_Avg) / 2

SR_FC3 [%] = 100 × R_FC3_Avg / REF
SR_FC4 [%] = 100 × R_FC4_Avg / REF
SR_FC5 [%] = 100 × R_FC5_Avg / REF
```

Un SR del 100% indica vidrio limpio (sin pérdida por suciedad). Un SR del 95% indica una reducción del 5% en la transmitancia del vidrio por acumulación de polvo.

**No se aplica corrección por temperatura** a las fotoceldas del PV Glasses, dado que las celdas de referencia y las celdas soiled operan bajo las mismas condiciones ambientales de forma simultánea, cancelándose los efectos térmicos en el cociente.

---

## 3. Calendario de Toma de Muestras

### 3.1 Diseño experimental

El experimento utiliza un esquema de **vidrios rotantes** con distintos períodos de exposición acumulada. En cada medición, se pesa cada muestra de vidrio antes y después de la limpieza, lo que permite cuantificar la masa de polvo depositada (mg).

**Estructuras de rotación:**
- **Fija → RC**: El vidrio pasa de la posición de exposición en campo hacia la celda de medición.
- **RC → Fija**: El vidrio regresa a su posición de exposición después de la medición (o se instala uno nuevo/limpio).

**Columnas clave del calendario:**

| Campo | Descripción |
|-------|-------------|
| `Semana` | Semana del experimento (correlativo desde inicio) |
| `Inicio Exposición` | Fecha en que el vidrio comenzó su exposición |
| `Fecha medición` | Fecha en que se realizó la medición gravimétrica |
| `Exposición` | Días de exposición acumulados al momento de la medición |
| `Periodo` | Tipo de período de exposición |
| `Masa A / B / C` | Peso del vidrio en gramos (corresponde a FC5 / FC4 / FC3) |
| `Estado` | `soiled` = sucio (antes de limpiar); `clean` = limpio (después de limpiar) |
| `Realizado` | `si` = medición efectivamente ejecutada |
| `Operador` | Siglas del técnico que realizó la medición |

### 3.2 Tipos de período de exposición

El diseño experimental incluye seis escalas de tiempo para caracterizar la acumulación de suciedad:

| Período | Días nominales | Cantidad de mediciones |
|---------|---------------|----------------------|
| Semanal | 7 días | 19 |
| 2 semanas | 14 días | 35 |
| Mensual | ~30 días | 18 |
| Trimestral | ~90 días | 8 |
| Cuatrimestral | ~120 días | 10 |
| Semestral | ~180 días | 6 |
| 1 año | ~365 días | 3 |

### 3.3 Calendario completo de mediciones (resumen)

La siguiente tabla resume el cronograma de exposiciones desde el inicio del experimento:

| Semana | Inicio Exposición | Fecha Medición | Exposición (días) | Período | Estado |
|--------|-------------------|----------------|-------------------|---------|--------|
| 1 | 23-07-2024 | 01-08-2024 | 9 | Semanal | soiled |
| 2 | 23-07-2024 | 06-08-2024 | 14 | 2 semanas | soiled/clean |
| 2 | 01-08-2024 | 06-08-2024 | 5 | Semanal | soiled |
| 3 | 01-08-2024 | 13-08-2024 | 12 | 2 semanas | soiled/clean |
| 3 | 23-07-2024 | 13-08-2024 | 21 | Mensual | soiled |
| 5 | 23-07-2024 | 27-08-2024 | 35 | Mensual | soiled/clean |
| 6 | 23-07-2024 | 03-09-2024 | 42 | 2 Meses | soiled/clean |
| 6 | 27-08-2024 | 03-09-2024 | 7 | Semanal | soiled |
| 7 | 27-08-2024 | 10-09-2024 | 14 | 2 semanas | soiled/clean |
| 8 | 03-09-2024 | 17-09-2024 | 14 | 2 semanas | soiled/clean |
| 8 | 23-07-2024 | 17-09-2024 | 56 | 2 Meses | soiled/clean |
| 9–13 | … | 24-09 — 22-10-2024 | 7–91 | semanas/trimestral | soiled/clean |
| 13 | 23-07-2024 | 22-10-2024 | 91 | Trimestral | soiled |
| 14 | 23-07-2024 | 29-10-2024 | 98 | Trimestral | soiled/clean |
| 17 | 23-07-2024 | 19-11-2024 | 119 | Cuatrimestral | soiled |
| 18 | 23-07-2024 | 26-11-2024 | 126 | Cuatrimestral | soiled/clean |
| 25 | 23-07-2024 | 16-01-2025 | 177 | Semestral | soiled |
| 26 | 23-07-2024 | 21-01-2025 | 182 | Semestral | soiled/clean |
| 27 | 16-01-2025 | 11-02-2025 | 26 | Mensual | soiled/clean |
| — | 19-11-2024 | 25-02-2025 | 98 | Trimestral | soiled/clean |
| — | 22-10-2024 | 04-03-2025 | 133 | Cuatrimestral | soiled/clean |
| — | 27-08-2024 | 11-03-2025 | 196 | Semestral | soiled/clean |
| — | 13-08-2024 | 12-08-2025 | 364 | 1 año | soiled/clean |

> **Nota:** Las rotaciones de período "2 Meses" aparecen en el calendario con denominación variable; corresponden a aproximadamente 42–56 días de exposición.

---

## 4. Fuente de Datos y Formato

### 4.1 Archivo de datos crudos

```
datos/raw_pv_glasses_data.csv
```

- **Resolución temporal:** 1 minuto
- **Volumen:** ~102 611 registros (agosto 2024 – julio 2025)
- **Zona horaria:** UTC

**Encabezado del archivo:**
```
_time, R_FC1_Avg, R_FC2_Avg, R_FC3_Avg, R_FC4_Avg, R_FC5_Avg, REF
```

Ejemplo de registro:
```
2024-08-01 13:00:00, 304.4, 294.4, 308.2, 307.7, 305.6, 299.4
```

---

## 5. Pipeline de Procesamiento

El procesamiento del PV Glasses sigue cuatro etapas secuenciales implementadas en scripts Python del directorio `scripts/`:

```
datos crudos
    │
    ▼
[ETAPA 1] Filtro de irradiancia
    │  scripts/apply_irradiance_filter.py
    ▼
datos_filtrados/pvglasses_filtered.csv
    │
    ▼
[ETAPA 2] Selección de sesión de mediodía solar
    │  scripts/process_solar_noon_sessions.py
    ▼
datos_filtrados/sesiones/pvglasses_sesiones.csv
    │
    ▼
[ETAPA 3] Cálculo del Soiling Ratio
    │  scripts/calculate_sr.py
    ▼
datos_filtrados/sr/sr_pvglasses.csv
    │
    ▼
[ETAPA 4] Visualización
    │  scripts/plot_sr_filtrado.py
    ▼
graficos/sr_pvglasses_diario_q25.png
```

---

## 6. Etapa 1 — Filtro de Irradiancia

**Script:** `scripts/apply_irradiance_filter.py`

### 6.1 Datos de referencia utilizados

El filtro se basa en la estación Solys2 como fuente de irradiancia de referencia:

```
datos/solys2/raw_solys2_data.csv
→ columnas: GHI, DHI, DNI (W/m²) con timestamps en UTC
```

### 6.2 Pasos del filtro

**Paso 1 — Cálculo de POA (Plane of Array):**  
Se calcula la irradiancia en el plano del módulo usando `pvlib`:
- Inclinación del panel (tilt): **20°**
- Acimut del panel: **0° (orientación Norte)**
- Latitud: -24.090°, Longitud: -69.929°, Altitud: 500 m
- Modelo de transposición: Perez

**Paso 2 — Cálculo de GHI Clear-Sky:**  
Se calcula la irradiancia global horizontal en condición de cielo despejado usando el modelo de **Ineichen** con datos de turbidez de Linke.

**Paso 3 — Ratio de Cielo Claro:**
```
clear_sky_ratio = GHI_medido / GHI_clear_sky
```

**Paso 4 — Construcción del conjunto de referencia:**  
Se retienen solo los instantes que cumplen simultáneamente:
- `POA ≥ 500 W/m²` (irradiancia suficiente para medición confiable)
- `clear_sky_ratio ≥ 0.8` (condición de cielo claro; sin nubes significativas)

**Paso 5 — Filtrado del PV Glasses:**  
Cada registro del PV Glasses se retiene si existe al menos un instante del conjunto de referencia dentro de una ventana de **±5 minutos** (usando `pd.merge_asof` con `tolerance=5 min`).

### 6.3 Resultado

```
datos_filtrados/pvglasses_filtered.csv
```

Los datos filtrados representan únicamente los instantes de alta irradiancia bajo cielo claro, eliminando mediciones nocturnas, con nubes o a bajo ángulo solar.

---

## 7. Etapa 2 — Selección de Sesión de Mediodía Solar

**Script:** `scripts/process_solar_noon_sessions.py`

### 7.1 Motivación

No se utiliza un simple promedio diario, sino que se selecciona una **única sesión de 5 minutos por día**, centrada en el entorno del mediodía solar, para minimizar la variación de irradiancia y obtener una medición representativa y reproducible.

### 7.2 Procedimiento

**Paso 1 — Cálculo del mediodía solar:**  
Para cada día del período se calcula la hora exacta del mediodía solar en UTC usando `pvlib.solarposition`. El mediodía solar en el sitio ocurre en torno a las **16:05–17:00 UTC** (media: ~16:44 UTC, equivalente a aproximadamente 12:05–13:00 hora local UTC-4). El 73% de los días seleccionan el bin de las 17:00 UTC y el 27% restante selecciona el bin de las ~16:05 UTC.

**Paso 2 — Agrupación en bins de 5 minutos:**  
Los datos filtrados de PV Glasses se agrupan en intervalos de 5 minutos, calculando el promedio de cada fotcelda en cada bin.

**Paso 3 — Selección del bin más cercano al mediodía solar:**  
Por día, se selecciona el único bin cuyo centro temporal minimiza la distancia temporal al mediodía solar calculado.

**Paso 4 — Filtros de validación del bin seleccionado:**

| Criterio | Valor umbral | Justificación |
|----------|--------------|---------------|
| Distancia al mediodía solar | ≤ 50 minutos | Evitar bins en horarios de alta inclinación solar |
| Estabilidad de irradiancia | Variación de REF < 10% en el bin | Garantizar condición estable de iluminación |

**Paso 5 — Alineación temporal:**  
El PV Glasses se procesa con este esquema en forma directa, pues sus datos son continuos. El timestamp del bin seleccionado queda registrado en la columna `bin`.

### 7.3 Resultado

```
datos_filtrados/sesiones/pvglasses_sesiones.csv
```

Cada fila representa una sesión diaria válida:
```
date, bin, R_FC1_Avg, R_FC2_Avg, R_FC3_Avg, R_FC4_Avg, R_FC5_Avg, REF
2024-08-01, 2024-08-01 16:05:00+00:00, 953.0, 919.8, 864.0, 842.2, 840.6, 936.4
```

---

## 8. Etapa 3 — Cálculo del Soiling Ratio

**Script:** `scripts/calculate_sr.py`

### 8.1 Fórmula aplicada

```python
ref_media = (R_FC1_Avg + R_FC2_Avg) / 2

SR_R_FC3 [%] = 100 × R_FC3_Avg / ref_media   # Muestra C
SR_R_FC4 [%] = 100 × R_FC4_Avg / ref_media   # Muestra B
SR_R_FC5 [%] = 100 × R_FC5_Avg / ref_media   # Muestra A
```

### 8.2 Correspondencia entre fotoceldas y muestras del calendario

| Fotocelda | Columna SR | Muestra en Calendario | Masa calendario |
|-----------|------------|----------------------|-----------------|
| FC3 | `SR_R_FC3` | Muestra C | `Masa C` |
| FC4 | `SR_R_FC4` | Muestra B | `Masa B` |
| FC5 | `SR_R_FC5` | Muestra A | `Masa A` |

### 8.3 Consideraciones de calidad

- No se aplican umbrales adicionales de corriente mínima ni corrección por temperatura, dada la naturaleza del sensor.
- Las sesiones sin valor en alguna columna (`NaN`) se excluyen automáticamente del cálculo del SR para ese canal.
- Los valores de REF y celdas soiled deben ser estrictamente positivos.

### 8.4 Resultado

```
datos_filtrados/sr/sr_pvglasses.csv
```

Ejemplo:
```
date,bin,R_FC1_Avg,R_FC2_Avg,R_FC3_Avg,R_FC4_Avg,R_FC5_Avg,ref_media,SR_R_FC3,SR_R_FC4,SR_R_FC5
2024-08-01,2024-08-01 16:05:00+00:00,953.0,919.8,864.0,842.2,840.6,936.4,92.27,89.94,89.77
```

**Estadísticas del SR calculado (agosto 2024 – julio 2025):**

| Estadístico | SR_FC3 (%) | SR_FC4 (%) | SR_FC5 (%) |
|-------------|-----------|-----------|-----------|
| Promedio | 92.0 | 90.1 | 90.8 |
| Desv. estándar | 3.4 | 4.8 | 5.1 |
| Mínimo | 82.2 | 79.6 | 81.1 |
| Mediana | 92.2 | 89.1 | 89.2 |
| Máximo | 101.8 | 98.5 | 98.8 |
| N días | 271 | 271 | 271 |

---

## 9. Etapa 4 — Visualización

**Script:** `scripts/plot_sr_filtrado.py`

Se genera un gráfico individual del SR diario de PV Glasses con tendencia semanal Q25:

```
graficos/sr_pvglasses_diario_q25.png
```

El filtro visual aplicado sobre los datos de SR para la visualización es:
- `SR_MIN_VALID = 70.0 %`
- `SR_MAX_VALID = 110.0 %`

Estos límites eliminan valores físicamente imposibles sin afectar el rango físicamente plausible de pérdidas por soiling.

---

## 10. Análisis Integrado con el Calendario

En el análisis de `analysis/pv_glasses_analyzer_q25.py` se cruzan los SR diarios calculados con la información del calendario de muestras para obtener el SR promedio por período de exposición:

### 10.1 Proceso de cruce con el calendario

1. Para cada fila del calendario con `Estado = soiled` y `Realizado = si`, se identifica el período de exposición acumulada.
2. Se extraen los SR diarios del archivo `sr_pvglasses.csv` correspondientes al intervalo `[Inicio Exposición, Fecha medición]`.
3. Se calcula el **cuantil 25 (Q25)** del SR sobre ese subconjunto de días, lo que otorga robustez frente a días atípicos o perturbados.
4. Los resultados se agrupan por tipo de período de exposición.

### 10.2 Resultados por período de exposición

Los siguientes resultados provienen del análisis integrado con el calendario:

| Período | SR promedio (%) | Pérdida por soiling (%) |
|---------|----------------|------------------------|
| Semanal (7 días) | **97.7** | 2.3 |
| 2 semanas | **97.3** | 2.7 |
| Mensual (~30 días) | **95.2** | 4.8 |
| Trimestral (~90 días) | **94.9** | 5.1 |
| Cuatrimestral (~120 días) | **91.8** | 8.2 |
| Semestral (~180 días) | **91.1** | 8.9 |

> **Interpretación:** A medida que aumenta el período de exposición sin limpieza, la pérdida por soiling se incrementa progresivamente. El gradiente de pérdida es mayor entre 1 semana y 1 mes (~2.5 pp), y luego se modera entre los 3 y 6 meses (~3.8 pp adicionales).

---

## 11. Limitaciones y Consideraciones

1. **Vidrios con masa anómala:** En algunas filas del calendario se registran masas extremadamente altas (p. ej. 15.31 g cuando lo normal es ~0.0007 g de incremento), lo que indica que el vidrio fue colocado incorrectamente o no se limpió antes de la exposición. Estas filas quedan registradas con `Estado = soiled` pero con masa inicial elevada.

2. **Masa B faltante en algunos períodos:** A partir de cierta semana, la columna `Masa B` registra 0.0000, lo que indica que ese vidrio fue retirado del experimento temporalmente o no se pesó.

3. **Comentarios de operador:** La última fila activa del calendario (semana con inicio 04-03-2025) tiene el comentario: *"medición de estos vidrios tiene error. Se dejaran sobre celdas por un mes."*, indicando una irregularidad operacional documentada.

4. **Mediciones pendientes:** Las filas con `Realizado = NaN` corresponden a mediciones programadas pero aún no ejecutadas al cierre del presente análisis.

5. **Referencia FC2 ocasionalmente nula:** En algunos períodos `R_FC2_Avg` puede registrar valores de 0.0, lo que haría el promedio de REF no representativo. Se recomienda verificar la consistencia de FC1 vs FC2 antes de usar el REF promediado.

---

## 12. Archivos Generados

| Archivo | Ruta | Descripción |
|---------|------|-------------|
| Datos filtrados | `datos_filtrados/pvglasses_filtered.csv` | PV Glasses bajo condición de cielo claro y POA ≥ 500 W/m² |
| Sesiones diarias | `datos_filtrados/sesiones/pvglasses_sesiones.csv` | Una sesión de 5 min por día alrededor del mediodía solar |
| SR diario | `datos_filtrados/sr/sr_pvglasses.csv` | SR calculado por día para FC3, FC4 y FC5 |
| Gráfico SR diario | `graficos/sr_pvglasses_diario_q25.png` | SR diario con tendencia semanal Q25 |
| SR por período | `graficos_analisis_integrado_py/pv_glasses/SR_Promedios_Generales_por_Periodo.png` | Promedios de SR por tipo de período |
| SR barras por período | `graficos_analisis_integrado_py/pv_glasses/SR_Promedios_por_Periodo_Barras.png` | Gráfico de barras por período |
| SR periodos individuales | `graficos_analisis_integrado_py/pv_glasses/SR_Periodo_*.png` | SR con masas para cada tipo de período |
| Tabla de incertidumbre | `graficos_analisis_integrado_py/pv_glasses/tabla_incertidumbre_promedios.xlsx` | Incertidumbre expandida por período |

---

## 13. Flujo de Ejecución del Pipeline

Para reproducir el análisis completo desde cero:

```bash
# Activar entorno virtual
source venv/bin/activate

# Etapa 1: Filtro de irradiancia
python scripts/apply_irradiance_filter.py

# Etapa 2: Selección de sesiones de mediodía solar
python scripts/process_solar_noon_sessions.py

# Etapa 3: Cálculo del SR
python scripts/calculate_sr.py

# Etapa 4: Generación de gráficos de serie de tiempo
python scripts/plot_sr_filtrado.py

# Etapa 5 (análisis integrado con calendario):
python analysis/pv_glasses_analyzer_q25.py
```

---

*Documento generado como parte del proyecto ATAMOSTEC — Análisis de Soiling Ratio en el Desierto de Atacama.*
