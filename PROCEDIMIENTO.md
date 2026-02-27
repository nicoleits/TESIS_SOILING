# Procedimiento: Descarga, Procesamiento de Irradiancia y Filtrado de Datos

Este documento describe con detalle el flujo completo implementado para la descarga de datos de sistemas fotovoltaicos, el procesamiento de irradiancia (Solys2) para obtener una base de referencia, y la aplicación de filtros al Soiling Kit en función de esa irradiancia.

---

## Estructura y rutas del proyecto

- **Raíz del proyecto:** la carpeta **`TESIS_SOILING/`**. Todas las rutas que aparecen en este documento (`data/`, `analysis/`, etc.) son **relativas a TESIS_SOILING**.
- **Datos:** se guardan en **`TESIS_SOILING/data/`** (soilingkit, solys2, iv600, etc.). Estos archivos (CSV, PNG) **no se suben a git** (`.gitignore` en el repositorio).
- **Análisis SR:** salidas en **`TESIS_SOILING/analysis/sr/`** (`soilingkit_sr.csv`, `grafico_sr.png`).

---

## Requisitos previos

- **Entorno:** Python 3 con dependencias instaladas (`pip install -r requirements.txt` desde `TESIS_SOILING/`).
- **Dependencias principales:** `pandas`, `numpy`, `clickhouse-connect`, `matplotlib`, `plotly`, **`pvlib`** (necesario para POA y modelo clear-sky).
- **Conexión:** Acceso a la base de datos ClickHouse configurada en el script (host, puerto, usuario, contraseña).

**Ejecución del script de descarga:**

- Desde la carpeta **TESIS_SOILING:**  
  `python download_data.py`  
  (o `../.venv/bin/python download_data.py` si el venv está en la carpeta padre).
- Desde la carpeta padre del repositorio (p. ej. `si_test`):  
  `python TESIS_SOILING/download_data.py`  
  (con el venv activado o usando la ruta al intérprete que tenga las dependencias).

En ambos casos los archivos de salida se escriben en **`TESIS_SOILING/data/`**, organizados en subcarpetas por tipo de dato.

---

# 1) Descarga de datos

La descarga se realiza desde **ClickHouse** mediante el script `download_data.py`, que ofrece un menú interactivo.

## 1.1 Configuración inicial

Al ejecutar el script:

1. **Fechas:** Se pide fecha de inicio y fecha de fin (por defecto: 01/07/2024 – 31/12/2025). Las fechas se interpretan en UTC.
2. **Menú:** Se muestra el menú de opciones numeradas (0–13). El cálculo de SR se hace en un proceso separado.

La conexión a ClickHouse usa la configuración definida en el script:

- Host, puerto, usuario y contraseña (por ejemplo `CLICKHOUSE_CONFIG`).
- Las consultas se ejecutan en el esquema **PSDA** y en tablas concretas según el tipo de dato.

## 1.2 Opciones de descarga (menú)

| Opción | Descripción | Tabla / Origen | Archivo de salida (en `TESIS_SOILING/data/`) |
|--------|-------------|----------------|---------------------------------|
| 1 | IV600 (puntos característicos) | ClickHouse | `iv600/raw_iv600_data.csv` |
| 2 | Curvas IV600 completas | ClickHouse (rango horario configurable) | `iv600/raw_iv600_curves.csv` |
| 3 | IV600 + PV Glasses | ClickHouse | `iv600/...`, `pv_glasses/raw_pv_glasses_data.csv` |
| 4 | PV Glasses (fotoceldas RFC1–RFC5) | ClickHouse | `pv_glasses/raw_pv_glasses_data.csv` |
| 5 | DustIQ | ClickHouse | `dustiq/raw_dustiq_data.csv` |
| 6 | **Soiling Kit** | ClickHouse, tabla `PSDA.soilingkit` | `soilingkit/soilingkit_raw_data.csv` |
| 7 | PVStand | ClickHouse | `pvstand/raw_pvstand_iv_data.csv` |
| 8 | Temperatura de módulos | ClickHouse | `temperatura/data_temp.csv` |
| 9 | **Solys2 (radiación solar)** | ClickHouse, tabla `PSDA.meteo6857` | `solys2/raw_solys2_data.csv` |
| 10 | RefCells | ClickHouse | `refcells/refcells_data.csv` |
| 11 | Procesar Solys2 → base de referencia | (procesamiento) | `solys2/solys2_poa_500_clear_sky.csv` |
| 12 | Aplicar filtro POA/clear-sky a todos los módulos | (procesamiento, Data) | En cada carpeta: `<modulo>_poa_500_clear_sky.csv` |
| 13 | Soiling Kit (soilingkit): sesión mediodía solar | (procesamiento, Data) | `soilingkit/soilingkit_solar_noon.csv` |

- **Opción 0:** Salir.
- **Opciones 11, 12, 13:** Procesamiento dentro de la **sección Data** (detallado en §2–4).
- **Cálculo de SR:** No está en el menú de `download_data.py`. Se ejecuta **en un proceso aparte** (sección Análisis, §5).

## 1.3 Detalle de los datos relevantes para irradiancia y filtrado

### Solys2 (opción 9)

- **Origen:** `PSDA.meteo6857`.
- **Columnas descargadas:** `timestamp`, `GHIAvg`, `DHIAvg`, `DNIAvg`.
- **Procesamiento en descarga:** Se renombran a `GHI`, `DHI`, `DNI` y el índice temporal se guarda como “fecha hora” en el CSV.
- **Salida:** `data/solys2/raw_solys2_data.csv` (timestamp + GHI, DHI, DNI en W/m²).
- **Importante:** Este archivo es la entrada para el **procesamiento de irradiancia** (paso 2). Debe cubrir el mismo rango de fechas (o mayor) que el Soiling Kit si se quiere filtrar correctamente.

### Soiling Kit (opción 6)

- **Origen:** tabla **`PSDA.soilingkit`** (formato largo: Stamptime, Attribute, Measure). El script pivotea a formato ancho.
- **Zona horaria:** Los datos están en **UTC (UTC+0)**. Los timestamps se guardan y procesan en UTC.
- **Columnas (tras pivot):** `timestamp`, y las columnas según atributos en BD (p. ej. `Isc(e)`, `Isc(p)`, `Te(C)`, `Tp(C)`).
  - **Isc(e):** Corriente de cortocircuito celda expuesta/sucia (A).
  - **Isc(p):** Corriente de cortocircuito celda protegida/limpia (A).
  - **Te(C):** Temperatura celda expuesta (°C).
  - **Tp(C):** Temperatura celda protegida (°C).
- **Salida:** `data/soilingkit/soilingkit_raw_data.csv` (ruta completa: `TESIS_SOILING/data/soilingkit/...`).
- **Importante:** Este archivo es la entrada para el **filtrado por irradiancia** (opción 12); el resultado se guarda en `soilingkit_poa_500_clear_sky.csv`.

## 1.4 Estructura de directorios de salida

Todas las rutas son relativas a **TESIS_SOILING/** (raíz del proyecto).

```
TESIS_SOILING/
├── download_data.py
├── requirements.txt
├── data/                  # Datos (no se versionan en git)
│   ├── iv600/
│   ├── pv_glasses/
│   ├── dustiq/
│   ├── soilingkit/        # Soiling Kit (Data): raw, filtrado, sesión mediodía solar
│   │   ├── soilingkit_raw_data.csv
│   │   ├── soilingkit_poa_500_clear_sky.csv   # opción 12
│   │   ├── soilingkit_solar_noon.csv         # opción 13 (entrada para Análisis SR)
│   │   └── soilingkit_solar_noon_dist_stats.csv
│   ├── pvstand/
│   ├── temperatura/
│   ├── solys2/            # Solys2 raw y base de referencia
│   │   ├── raw_solys2_data.csv
│   │   └── solys2_poa_500_clear_sky.csv      # generado en paso 2
│   ├── refcells/
│   └── ...
└── analysis/              # Sección Análisis (SR, etc.)
    └── sr/                # Soiling Ratio (proceso aparte: python -m analysis.sr.calcular_sr)
        ├── soilingkit_sr.csv
        └── grafico_sr.png
```

---

# 2) Procesamiento de irradiancia (base de referencia)

El objetivo de este paso es obtener una **base de referencia de irradiancia**: solo instantes en los que se cumple POA alto y cielo suficientemente despejado. Esa base se usa después para filtrar el Soiling Kit.

## 2.1 Entrada y salida

- **Entrada:** `data/solys2/raw_solys2_data.csv` (columnas: timestamp, GHI, DHI, DNI). Ruta completa: `TESIS_SOILING/data/solys2/...`.
- **Salida:** `data/solys2/solys2_poa_500_clear_sky.csv` (BASE DE REFERENCIA).
- **Función en código:** `procesar_solys2_base_referencia(solys2_csv_path, output_dir, umbral_poa=None, umbral_clear_sky=None)`.
- **Cómo ejecutarlo:**
  - **Opción 9:** Tras descargar Solys2, si `pvlib` está disponible, se ejecuta automáticamente este procesamiento.
  - **Opción 11:** Ejecutar solo el procesamiento (sin volver a descargar), usando el `raw_solys2_data.csv` ya existente.

## 2.2 Configuración del sitio

El cálculo de POA y de GHI clear-sky depende de la ubicación y de la geometría del panel. En el script está definido un diccionario **`SITE_CONFIG`** (y constantes de umbral):

| Parámetro | Variable | Valor (ejemplo) | Descripción |
|-----------|----------|-----------------|-------------|
| Latitud | `latitude` | -24.08992287800815 | Grados decimales |
| Longitud | `longitude` | -69.92873664034512 | Grados decimales |
| Altitud | `altitude` | 500 | Metros sobre el nivel del mar |
| Inclinación del panel | `surface_tilt` | 20 | Grados desde la horizontal |
| Azimut del panel | `surface_azimuth` | 0 | Grados (convención pvlib) |
| Zona horaria | `tz` | 'UTC' | Para fechas/horas |

Umbrales por defecto:

- **`UMBRAL_POA`** = 500 (W/m²).
- **`UMBRAL_CLEAR_SKY`** = 0.8 (adimensional).

Estos valores pueden pasarse como argumentos opcionales a `procesar_solys2_base_referencia` (`umbral_poa`, `umbral_clear_sky`).

## 2.3 Paso 2.1: Cálculo de POA (Plane of Array)

- **Objetivo:** Obtener la irradiancia en el plano del panel (POA) a partir de GHI, DHI y DNI medidos.
- **Herramienta:** Biblioteca **pvlib**:
  - Se crea un objeto **`Location`** con latitud, longitud, altitud y zona horaria.
  - Para cada timestamp del CSV se calcula la **posición solar** (`get_solarposition`): ángulo cenital aparente y acimut solar.
  - Con **`get_total_irradiance`** se calcula la irradiancia en el plano del array usando:
    - `surface_tilt`, `surface_azimuth` (geometría del panel),
    - ángulos solares,
    - DNI, GHI y DHI del CSV.
  - Se toma la componente **`poa_global`** (irradiancia global en el plano del panel) y se guarda en una columna **`POA`** (W/m²).

Así, cada fila del Solys2 raw tiene un valor de POA asociado a la geometría del sitio.

## 2.4 Paso 2.2: GHI clear-sky teórico (modelo Ineichen)

- **Objetivo:** Estimar la GHI que habría en condiciones de cielo claro (sin nubes) para comparar con la GHI medida.
- **Modelo:** **Ineichen** (implementado en pvlib).
  - Se usa el mismo `Location` y los mismos timestamps.
  - **`loc.get_clearsky(times, model='ineichen')`** devuelve, entre otras, la serie **GHI clear-sky** (W/m²).
  - Esa serie se alinea con el índice temporal del DataFrame y se guarda en una columna **`GHI_clear_sky`**.

El modelo Ineichen utiliza ángulo cenital, masa de aire y turbidez de Linke; pvlib calcula estos parámetros a partir de la ubicación y la fecha/hora.

## 2.5 Paso 2.3: Clear-sky ratio

- **Fórmula:**  
  **`clear_sky_ratio = GHI_medido / GHI_clear_sky`**
- **Condición:** Para evitar división por cero, solo se calcula el ratio cuando `GHI_clear_sky > 1e-6`; en caso contrario se deja `NaN`.
- **Interpretación:** Valores próximos a 1 indican que el cielo estaba cercano a “clear-sky”; valores muy bajos indican mayor nubosidad o atenuación. El umbral mínimo (p. ej. 0.8) garantiza que solo se consideren instantes con cielo suficientemente despejado.

## 2.6 Paso 2.4: Aplicación de filtros

Se conservan **solo** las filas que cumplen **ambas** condiciones:

1. **POA ≥ UMBRAL_POA** (por defecto 500 W/m²): suficiente irradiancia en el plano del panel.
2. **clear_sky_ratio ≥ UMBRAL_CLEAR_SKY** (por defecto 0.8): condición de cielo suficientemente despejado.

El resto de filas se descartan. El resultado es un DataFrame con menos filas que el Solys2 raw.

## 2.7 Paso 2.5: Guardado de la base de referencia

- **Archivo:** `data/solys2/solys2_poa_500_clear_sky.csv`.
- **Columnas típicas:**  
  `timestamp`, `GHI`, `DHI`, `DNI`, `POA`, `GHI_clear_sky`, `clear_sky_ratio`.
- **Semántica:** Cada fila representa un **instante en el que se cumplen las condiciones de referencia** (POA ≥ 500 W/m² y ratio ≥ 0.8). Este archivo es la **base de referencia** para el filtrado del Soiling Kit.

En los logs se indica el número de registros antes y después del filtro.

---

# 3) Aplicación de filtros POA/clear-sky a todos los módulos

El objetivo es **quedarse solo con los registros de cada módulo** que corresponden a instantes donde la irradiancia cumplía las condiciones de la base de referencia (POA ≥ 500 W/m² y clear_sky_ratio ≥ 0.8).

## 3.1 Entradas y salida

- **Entrada 1:** `data/soilingkit/soilingkit_raw_data.csv` (timestamp, Isc(e), Isc(p), Te(C), Tp(C), etc.).
- **Entrada 2:** `data/solys2/solys2_poa_500_clear_sky.csv` (base de referencia; al menos la columna de timestamp).
- **Salida:** `data/soilingkit/soilingkit_poa_500_clear_sky.csv` (mismas columnas que el Soiling Kit raw, pero solo filas “filtradas”).
- **Función en código:** `filtrar_por_irradiancia_referencia()` (genérica); `aplicar_filtro_poa_clear_sky_a_todos()` aplica a todos.
- **Cómo ejecutarlo:** **Opción 12** — "Aplicar filtro POA/clear-sky a todos los módulos". Tras **Descargar todo** (opción 14) también se aplica el filtro automáticamente.

## 3.2 Lógica del filtrado (merge_asof)

Los timestamps del Soiling Kit y de la base de referencia **no tienen por qué coincidir exactamente** (diferente frecuencia de muestreo). Por eso se usa un **merge por proximidad temporal**:

1. **Ordenación y zona horaria:** Tanto el Soiling Kit como la tabla de referencia se ordenan por timestamp. Los datos del Soiling Kit están en **UTC (UTC+0)**; la base de referencia también se genera en UTC. Si algún CSV no tiene zona horaria explícita, el script la asume UTC para el alineamiento.
2. **merge_asof (pandas):**
   - Para **cada fila del Soiling Kit** (timestamp \( t \)), se busca en la referencia el **último** timestamp de referencia **anterior o igual** a \( t \).
   - Si ese timestamp de referencia está a una distancia **≤ `tolerance_minutes`** (por defecto 5 minutos) de \( t \), se considera que el registro del Soiling Kit pertenece a un “período de buena irradiancia” y **se conserva**.
   - Si no hay tal referencia dentro de la ventana, la fila se **descarta**.
3. **Parámetro `direction='backward'`:** Solo se considera la referencia hacia atrás en el tiempo (último instante de referencia ya ocurrido).
4. **Parámetro `tolerance`:** Por defecto `pd.Timedelta(minutes=5)`; puede cambiarse con el argumento `tolerance_minutes` de la función.

En la práctica: se asocia cada medición del Soiling Kit al último instante de referencia “bueno” dentro de los últimos 5 minutos; si existe, la medición se mantiene.

## 3.3 Resultado

- **Archivo generado:** `data/soilingkit/soilingkit_poa_500_clear_sky.csv`.
- **Columnas:** Las mismas que el Soiling Kit raw: `timestamp`, `Isc(e)`, `Isc(p)`, `Te(C)`, `Tp(C)` (sin columnas añadidas de la referencia).
- **Interpretación:** Solo se incluyen mediciones del Soiling Kit tomadas en condiciones de irradiancia de referencia (POA ≥ 500 W/m² y clear_sky_ratio ≥ 0.8), según la ventana temporal definida por `tolerance_minutes`.

En los logs se indica el número de registros antes y después del filtrado.

---

# 4) Mediodía solar y sesión de 5 minutos (Soiling Kit)

**Orden del proceso (Data):** la selección de ventana es **procesamiento**, no descarga. Orden recomendado: **1) Descargar** → **2) Aplicar filtros generales** (POA/clear-sky) → **3) Selección ventana Soiling Kit** (sesión más cercana al mediodía solar). Así se obtienen los mismos resultados; solo queda claro que la selección va después de los filtros.

Tras el filtrado por irradiancia (opcional), se puede reducir el Soiling Kit a **una fila por día**: la sesión de 5 minutos cuyo instante central está **más cercana al mediodía solar** de ese día, con la restricción de que esa ventana no puede estar a más de **45 minutos** del mediodía solar.

## 4.1 Mediodía solar (UTC)

- **Definición:** El mediodía solar es el instante en que el sol alcanza su **máxima elevación** (ángulo cenital mínimo) en ese día y en la ubicación del sitio.
- **Cálculo:** Con **pvlib** se usa la configuración del sitio (`SITE_CONFIG`: latitud, longitud, altitud, zona horaria). Para cada fecha se generan timestamps cada minuto a lo largo del día en **UTC**; se calcula la posición solar (`get_solarposition`) y se toma el instante en que la elevación es máxima. Ese instante es el **mediodía solar en UTC** para esa fecha.

## 4.2 Sesión de 5 minutos y restricción de distancia

- Los datos del Soiling Kit pueden tener resolución de segundos (varias filas por minuto). Se agrupan en **ventanas de 5 minutos** (timestamp redondeado al inicio del intervalo de 5 min).
- Para cada ventana se calcula el **centro del intervalo** (inicio + 2,5 min) y se promedian las columnas de dato (Isc(e), Isc(p), Te(C), Tp(C)) dentro de esa ventana. Resultado: **una fila por ventana de 5 minutos** (timestamp = centro del intervalo, valores = promedios).
- Para **cada día** se calcula el mediodía solar en UTC y se elige, entre todas las ventanas de 5 min de ese día, la que tiene el **centro más cercano** (en tiempo) a ese mediodía solar. Esa fila es la “sesión de 5 min más cercana al mediodía solar”. Solo se acepta esa ventana si la distancia (valor absoluto) al mediodía solar es **≤ 50 min** (`MAX_DIST_SOLAR_NOON_MIN = 50`). Si se supera, el día se descarta; el log indica cuántos días se descartaron.

## 4.3 Distancia ventana–mediodía solar y estadísticos

- Para cada fila de salida se calcula la **distancia en minutos** (valor absoluto) entre el centro de la ventana y el mediodía solar. Se guarda en la columna **`dist_solar_noon_min`** del CSV.
- El script calcula y escribe en log **estadísticos**: mínimo, máximo, media, mediana, desviación típica; percentiles P05, P25, P75, P95; y **conteos por umbral**: días con distancia ≤ 10, ≤ 15, ≤ 30, ≤ 45 min (número y %).
- Esos estadísticos se guardan también en **`data/soilingkit/soilingkit_solar_noon_dist_stats.csv`**.

## 4.3.5 Filtro de corriente (Data)

- **Filtro de corriente:** Solo se conservan filas en las que **Isc(e) ≥ 1 A** e **Isc(p) ≥ 1 A** (`UMBRAL_ISC_MIN = 1.0`). Los días que no cumplen se descartan. El **cálculo de SR** se realiza en la **sección Análisis** (proceso aparte: `python -m analysis.sr.calcular_sr`), no aquí.

## 4.4 Entrada, salida y uso (Data)

- **Entrada:** CSV del Soiling Kit soilingkit (crudo o filtrado). Se recomienda el **filtrado** (`soilingkit_poa_500_clear_sky.csv`) si existe.
- **Salida (Data):** **`data/soilingkit/soilingkit_solar_noon.csv`**: una fila por día (ventana ≤ 45 min del mediodía solar, **Isc(e), Isc(p) ≥ 1 A**). Columnas: `timestamp`, **`dist_solar_noon_min`**, `Isc(e)`, `Isc(p)`, `Te(C)`, `Tp(C)` — **sin columna SR** (SR se calcula en la sección Análisis). **`soilingkit_solar_noon_dist_stats.csv`**: estadísticos de distancia. Timestamps en **UTC (UTC+0)**.
- **Función en código:** `soiling_kit_seleccionar_mediodia_solar(..., section='soilingkit')`.
- **Cómo ejecutarlo:** **Opción 13** (solo este paso) o **Opción 14** (Descargar todo: descarga → filtros → selección ventana Soiling Kit). En ambos casos se usa `soilingkit_poa_500_clear_sky.csv` si existe; si no, `soilingkit_raw_data.csv`.

## 4.5 Resumen (Data)

- Se calcula el **mediodía solar en UTC** para cada fecha (pvlib).
- Se agregan los datos en **ventanas de 5 min** y se selecciona **una ventana por día** (centro más próximo al mediodía solar, distancia ≤ 45 min).
- Se añade **`dist_solar_noon_min`** y estadísticos en `soilingkit_solar_noon_dist_stats.csv`.
- Se aplica **filtro de corriente** (Isc ≥ 1 A). El resultado es la serie diaria lista para la **sección Análisis SR** (ejecutar aparte: `python -m analysis.sr.calcular_sr`).

---

# 5) Sección Análisis: Soiling Ratio (SR)

El **cálculo de SR** y el **gráfico** se realizan en la **sección Análisis** (`analysis/sr/`), no en Data. Así se separa claramente: **Data** = descarga y procesamiento; **Análisis** = indicadores (SR).

## 5.1 Entrada

- **`data/soilingkit/soilingkit_solar_noon.csv`**: generado por la opción 13 (sesión mediodía solar). Debe contener `timestamp`, `dist_solar_noon_min`, `Isc(e)`, `Isc(p)` (y opcionalmente Te(C), Tp(C)).

## 5.2 Cálculo y salidas

- **Fórmula:** **SR = 100 × Isc(p) / Isc(e)** (Soiling Ratio en %, protegida / expuesta). Si Isc(e) es cero o despreciable, se asigna NaN.
- **Filtro:** Se aplica (o se reaplica) el filtro de corriente **Isc(e), Isc(p) ≥ 1 A**.
- **Salidas (en `analysis/sr/`):**
  - **`soilingkit_sr.csv`**: mismo contenido que el CSV de entrada más la columna **`SR`** (%). Una fila por día.
  - **`grafico_sr.png`**: gráfico de SR en el tiempo (marcadores *, línea de referencia SR = 100).

## 5.3 Cómo ejecutarlo (proceso separado de download_data.py)

El cálculo de SR **no está en el menú** de `download_data.py`. Hay que ejecutarlo por separado:

- **Línea de comandos (recomendado):** desde la carpeta **TESIS_SOILING** (para que las rutas por defecto sean correctas):
  ```bash
  cd TESIS_SOILING
  python -m analysis.sr.calcular_sr
  ```
  Usa por defecto `data/soilingkit/soilingkit_solar_noon.csv` (entrada) y `analysis/sr/` (salida), es decir `TESIS_SOILING/data/...` y `TESIS_SOILING/analysis/sr/`. Requiere haber ejecutado antes la opción 13 o 14 en `download_data.py`.

- **Con rutas explícitas:**  
  `python -m analysis.sr.calcular_sr [ruta_solar_noon.csv] [carpeta_salida]`

---

# 6) Alineación de otros módulos con sesiones Soiling Kit

Con las sesiones del Soiling Kit listas (una ventana de 5 min por día, mediodía solar), se alinean el resto de módulos a esos mismos horarios y se filtra por **estabilidad de irradiancia**.

## 6.1 Reglas de alineación

| Frecuencia del módulo | Criterio |
|------------------------|----------|
| **1 min** (pv_glasses, dustiq, temperatura, refcells) | Se seleccionan los mismos 5 minutos diarios que el Soiling Kit y se promedia. |
| **5 min** (pvstand) | Se selecciona el dato más cercano al instante central del Soiling Kit. |
| **Irregular** (iv600) | Se selecciona el dato más cercano al Soiling Kit que no esté a más de **1 hora** de distancia. |

## 6.2 Filtro de estabilidad de irradiancia

Al final se filtran los datos según estabilidad de G (POA del Solys2) en la ventana de 5 min:

- **Criterio:** `(G_max - G_min) / G_med < 10%`
- **G:** columna POA en `data/solys2/solys2_poa_500_clear_sky.csv` (1 min) en esa ventana.
- Solo se conservan los días que cumplen el criterio; se aplica a todos los módulos (incluido Soiling Kit).

## 6.3 Entradas y salidas

- **Entradas:** `soilingkit_solar_noon.csv`, `solys2_poa_500_clear_sky.csv`, y los CSVs filtrados de cada módulo (`*_poa_500_clear_sky.csv`).
- **Salidas (en cada carpeta de módulo):**
  - `soilingkit_aligned_solar_noon.csv` (Soiling Kit filtrado por estabilidad).
  - `<modulo>_aligned_solar_noon.csv` (pv_glasses, dustiq, temperatura, refcells, pvstand, iv600).

## 6.4 Cómo ejecutarlo

Desde **TESIS_SOILING**:

```bash
python -m analysis.align.align_to_soiling_kit
```

Opcional: `python -m analysis.align.align_to_soiling_kit [ruta_a_data]`

---

# 7) Análisis estadístico de datos filtrados/alineados

Tras la alineación: `python -m analysis.stats.analisis_estadistico`. Ver descripción en tabla de archivos (§ Resumen de archivos clave).

---

# 8) Soiling Ratio (SR) por módulo (datos filtrados)

A partir de los CSVs **alineados** se calcula un indicador tipo SR para cada módulo: `python -m analysis.sr.calcular_sr_modulos`

| Módulo | Definición de SR |
|--------|------------------|
| soilingkit | SR = 100 × Isc(p) / Isc(e) |
| dustiq | SR = SR_C11_Avg (sensor en %) |
| refcells | SR = 100 × min(1RC411, 1RC412) / max(...) |
| pv_glasses | SR = media de 100×R_FCi/REF (más columnas SR_R_FC1…SR_R_FC5) |
| pvstand | SR = 100 × pmax / P95(pmax) por módulo |
| iv600 | SR = 100 × pmp / P95(pmp) por módulo |

Salidas: `analysis/sr/<modulo>_sr.csv` y `analysis/sr/<modulo>_sr.png`.

---

# Flujo desde cero

Ejecutar el script de descarga desde **TESIS_SOILING** (`python download_data.py`) o desde la carpeta padre (`python TESIS_SOILING/download_data.py`). Se piden **fechas de inicio y fin**; los datos se guardan en **TESIS_SOILING/data/**.

## Opción A: Todo en un solo paso (recomendado)

| Paso | Acción | Resultado |
|------|--------|-----------|
| 1 | En el menú elegir **opción 14** — *Descargar todo* | **Orden:** descarga de los 8 módulos → base de referencia (Solys2) → **filtro POA/clear-sky a todos** → **selección ventana Soiling Kit** (sesión más cercana al mediodía solar). Se genera `soilingkit_solar_noon.csv` en el mismo flujo. |
| 2 | (Opcional) Responder *s* a “¿Crear gráficos?” | Gráficos estáticos en cada carpeta. |
| 3 | **(Opcional)** Alinear otros módulos a sesiones Soiling Kit: `python -m analysis.align.align_to_soiling_kit` | Genera `*_aligned_solar_noon.csv` en cada carpeta (mismos 5 min/día + filtro estabilidad G < 10%). |
| 4 | **Solo si quieres Soiling Ratio:** Desde **TESIS_SOILING**, en la terminal: `python -m analysis.sr.calcular_sr` | Lee `data/soilingkit/soilingkit_solar_noon.csv`, calcula SR y genera `analysis/sr/soilingkit_sr.csv` y `analysis/sr/grafico_sr.png`. (Opción 13 solo si no usaste 14 y necesitas generar o regenerar `soilingkit_solar_noon.csv`.) |

## Opción B: Paso a paso

| Paso | Acción | Resultado |
|------|--------|-----------|
| 1 | **Opción 9** — Descargar Solys2 | `data/solys2/raw_solys2_data.csv` y (si hay pvlib) `solys2_poa_500_clear_sky.csv` (en `TESIS_SOILING/data/`). |
| 2 | **Opción 11** (opcional) | Regenerar solo la base de referencia. |
| 3 | Descargar módulos (opciones 1, 4, 5, 6, 7, 8, 10) o **opción 14** (todos) | Archivos raw en cada carpeta de `data/`. |
| 4 | **Opción 12** — Aplicar filtro POA/clear-sky a todos | En cada carpeta: `<modulo>_poa_500_clear_sky.csv`. (Si usaste 14 en el paso 3, ya está aplicado.) |
| 5 | **Opción 13** — Soiling Kit: sesión mediodía solar | `data/soilingkit/soilingkit_solar_noon.csv` (entrada para SR). |
| 6 | **(Opcional)** Alinear módulos y filtro estabilidad: `python -m analysis.align.align_to_soiling_kit` | `*_aligned_solar_noon.csv` en cada carpeta. |
| 7 | Desde **TESIS_SOILING:** `python -m analysis.sr.calcular_sr` | SR y gráfico en `analysis/sr/`. |

**Resumen mínimo desde cero:** ejecutar `download_data.py` (desde TESIS_SOILING o con `python TESIS_SOILING/download_data.py`) → fechas → **14** (Descargar todo: descarga → filtros → selección ventana Soiling Kit). Para SR: desde **TESIS_SOILING** ejecutar `python -m analysis.sr.calcular_sr`. La opción 13 solo hace falta si no usaste 14 y quieres generar `soilingkit_solar_noon.csv` a partir de datos ya descargados.

---

# Orden recomendado (referencia)

1. **Solys2** (opción 9) para tener base de referencia; luego **opción 12** o **14** para filtrar todos los módulos.
2. **Opción 11** solo si quieres regenerar la referencia sin volver a descargar Solys2.
3. **Soiling Kit** (opción 6) o el resto de módulos (1, 4, 5, 7, 8, 10); o **14** para todo.
4. **Opción 13** para serie diaria del Soiling Kit (mediodía solar).
5. **(Opcional)** Alineación y estabilidad: `python -m analysis.align.align_to_soiling_kit`.
6. **SR:** ejecutar aparte `python -m analysis.sr.calcular_sr`.

La base de referencia debe generarse a partir de un Solys2 descargado para el mismo rango de fechas (opción 9 o 14).

---

# Resumen de archivos clave

Todas las rutas son relativas a **TESIS_SOILING/**.

| Archivo | Descripción |
|---------|-------------|
| `data/solys2/raw_solys2_data.csv` | Solys2 crudo (GHI, DHI, DNI) desde ClickHouse. |
| `data/solys2/solys2_poa_500_clear_sky.csv` | Base de referencia: instantes con POA ≥ 500 W/m² y clear_sky_ratio ≥ 0.8. |
| `data/soilingkit/soilingkit_raw_data.csv` | Soiling Kit (tabla soilingkit) crudo. Timestamps en **UTC (UTC+0)**. |
| `data/soilingkit/soilingkit_poa_500_clear_sky.csv` | Soiling Kit filtrado por irradiancia de referencia. |
| `data/soilingkit/soilingkit_solar_noon.csv` | Soiling Kit (Data): una fila por día (mediodía solar, ≤ 45 min, Isc ≥ 1 A). Columnas: `timestamp`, `dist_solar_noon_min`, `Isc(e)`, `Isc(p)`, etc. **Sin SR** (SR se calcula en Análisis). |
| `data/soilingkit/soilingkit_solar_noon_dist_stats.csv` | Estadísticos de la distancia ventana–mediodía solar. |
| `analysis/sr/soilingkit_sr.csv` | Soiling Ratio (Análisis): serie diaria con columna **SR** (%). Entrada: `soilingkit_solar_noon.csv`. |
| `analysis/sr/grafico_sr.png` | Gráfico de SR en el tiempo (sección Análisis). |
| `data/soilingkit/soilingkit_aligned_solar_noon.csv` | Soiling Kit alineado + filtro estabilidad (G &lt; 10%). |
| `data/<modulo>/<modulo>_aligned_solar_noon.csv` | Módulos alineados a sesiones Soiling Kit (pv_glasses, dustiq, temperatura, refcells, pvstand, iv600). |
| `analysis/stats/analisis_estadistico_report.md` | Reporte de análisis estadístico (dispersión en ventana 5 min y entre días). |
| `analysis/stats/analisis_estadistico_resumen.csv` | Resumen estadístico en CSV. |
| `analysis/sr/<modulo>_sr.csv` | SR por módulo (soilingkit, dustiq, refcells, pv_glasses, pvstand, iv600). |
| `analysis/sr/<modulo>_sr.png` | Gráfico de SR por módulo. |

**Organización:** **Data** (`data/`, opciones 6, 9, 11–14): descarga y procesamiento; datos en **TESIS_SOILING/data/** (no se versionan en git). **Análisis** (`analysis/sr/`): cálculo de SR; **analysis/align/**: alineación y filtro de estabilidad; **analysis/stats/**: análisis estadístico de datos alineados (`python -m analysis.stats.analisis_estadistico`, desde TESIS_SOILING).

Este documento refleja el procedimiento implementado en `download_data.py` hasta la fecha descrita.
