# Instrucciones para calcular el Soiling Ratio (SR) del PVStand

Documento para implementar el cálculo de SR en un proyecto distinto: qué datos se necesitan, qué correcciones aplicar y cómo calcular el SR. Los paths y nombres de archivos los define cada proyecto.

---

## 1. Contexto

El PVStand tiene **dos módulos** en el mismo tracker:
- **Módulo sucio**: expuesto al ambiente (se ensucia)."434 y 440"
- **Módulo referencia (limpio)**: usado como referencia. "439"

El **Soiling Ratio (SR)** es el rendimiento del módulo sucio respecto al de referencia, en porcentaje:

**SR = 100 × (valor_sucio / valor_referencia)**

Se calcula con **Isc** (corriente de cortocircuito) y con **Pmax** (potencia máxima), y en ambos casos puede aplicarse **corrección de temperatura** a condiciones estándar (25 °C) antes del ratio.

---

## 2. Datos necesarios

### 2.1. Datos IV (curvas IV)

Necesitas una serie temporal con, para **cada instante**:
- **Timestamp** (datetime, preferiblemente UTC).
- **Isc** (o Imax) del módulo sucio [A].
- **Isc** (o Imax) del módulo referencia [A].
- **Pmax** del módulo sucio [W].
- **Pmax** del módulo referencia [W].


### 2.2. Datos de temperatura

Serie temporal con:
- **Timestamp** (mismo criterio que IV, UTC).
- **Temperatura del módulo sucio** [°C]."1TE416"
- **Temperatura del módulo referencia** [°C]."1TE418"

Debe poder alinearse con los instantes de los datos IV (mismo rango de fechas; si la frecuencia es distinta, se alinea por tiempo más cercano dentro de una tolerancia razonable, p. ej. 1 min).

---

## 4. Corrección de temperatura (IEC 60891)

Objetivo: llevar Isc y Pmax a **25 °C** para comparar en condiciones equivalentes.

Temperatura de referencia: **T_ref = 25 °C**.

### 4.1. Coeficientes (datasheet del módulo)

- **α_Isc**: coeficiente de temperatura de la corriente de cortocircuito [/°C].  
  Ejemplo típico: **0.0004** (0.04 %/°C).
- **β_Pmax** (o γ_Pmpp): coeficiente de temperatura de la potencia máxima [/°C].  
  Ejemplo típico: **−0.0036** (−0.36 %/°C).

### 4.2. Fórmulas de corrección

**Isc:**

- `Isc_corr = Isc / (1 + α_Isc × (T − T_ref))`  
- Aplicar por separado al módulo sucio y al de referencia, con su propia T.

**Pmax:**

- `Pmax_corr = Pmax / (1 + β_Pmax × (T − T_ref))`  
- Igual: una corrección para sucio y otra para referencia.

Con T_ref = 25:

- Isc_corr = Isc / (1 + α_Isc × (T − 25))
- Pmax_corr = Pmax / (1 + β_Pmax × (T − 25))

Las unidades de T deben ser °C; Isc en A, Pmax en W.

---

## 5. Cálculo del SR

En todos los casos: **SR = 100 × (sucio / referencia)** (en %).

### 5.1. SR sin corrección de temperatura

- **SR_Isc** = 100 × (Isc_sucio / Isc_referencia)  


- **SR_Pmax** = 100 × (Pmax_sucio / Pmax_referencia)  

### 5.2. SR con corrección de temperatura

- **SR_Isc_corr** = 100 × (Isc_sucio_corr / Isc_ref_corr)  
  Donde Isc_corr se calcula con la fórmula del apartado 4.2.

- **SR_Pmax_corr** = 100 × (Pmax_sucio_corr / Pmax_ref_corr)  
  Con Pmax_corr según 4.2.
