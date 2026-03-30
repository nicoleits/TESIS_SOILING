# Proceso completo de cálculo de errores (incertidumbre de medida)

Este documento explica **cómo se calculan** las incertidumbres de medida (SR y Δm) siguiendo la GUM. El **objetivo es que otro agente o proyecto pueda reproducir los cálculos** en su propio código: por eso **no se incluyen rutas ni nombres de archivos** (cada proyecto tendrá los suyos). Solo fórmulas, magnitudes de entrada, propagación y criterios de agregación.

---

## 1. ¿De qué “errores” hablamos?

Aquí **“error”** no significa equivocación ni fallo. Se refiere a la **incertidumbre de medida**: cuánto puede alejarse el valor verdadero del valor que hemos medido o calculado.

- **Ejemplo:** Si la balanza marca 15.289 g y su incertidumbre es ±0.2 mg, el valor verdadero está (con alta probabilidad) en el intervalo **[15.2888 g , 15.2892 g]**.
- **En el proyecto** se cuantifica la incertidumbre de:
  - Las **diferencias de masa** (soiled − clean) en mg.
  - El **Soiling Ratio (SR)** en % para cada metodología (RefCells, DustIQ, Soiling Kit, PVStand, IV600, PV Glasses).

Todo esto se hace siguiendo la **GUM** (Guía para la expresión de la incertidumbre de medida), que es el estándar internacional para esto.

---

## 2. Incertidumbre estándar (k=1) e incertidumbre expandida (k=2)

- **Incertidumbre estándar** se denota **u** y corresponde a **una desviación típica** (nivel de confianza aproximado del 68 %).
- **Incertidumbre expandida** se denota **U** y se obtiene multiplicando **u** por un factor **k** (factor de cobertura). Con **k = 2**, el intervalo **[valor − U , valor + U]** tiene un nivel de confianza aproximado del **95 %**.

En el proyecto se trabaja casi siempre con **k = 2** para reportar resultados:

- **u** = incertidumbre estándar (k=1)  
- **U = k × u** con **k = 2** → “error” que se suele poner en gráficos y tablas.

Cuando veas “barras de error” en un gráfico, normalmente representan **U** (incertidumbre expandida k=2).

---

## 3. Idea general del proceso en el proyecto

El flujo es siempre el mismo en concepto:

1. **Definir las magnitudes que se miden** (irradiancia, corriente, masa, SR directo, etc.).
2. **Asignar una incertidumbre a cada magnitud de entrada** (según fabricante, certificado de calibración o estimación, si es este ultimo mostrar alerta).
3. **Escribir la fórmula** que da la magnitud de interés (SR o Δm).
4. **Propagar** la incertidumbre de las entradas hasta la magnitud de salida (SR o Δm) usando la **ley de propagación de incertidumbres** (derivadas parciales y varianzas).
5. **Opcional:** Agregar en el tiempo (día, semana, mes) y asignar una incertidumbre a cada valor agregado.
6. **Exportar** los resultados (SR o Δm con u y U) en el formato que use el proyecto.
7. **Usar** U (o u) en gráficos como barras de error cuando corresponda.

En el código hay **dos flujos**:

- **Flujo A:** Incertidumbre del **Soiling Ratio (SR)** para cada metodología (RefCells, DustIQ, Soiling Kit, PVStand, IV600, PV Glasses).
- **Flujo B:** Incertidumbre de las **diferencias de masa** (Δm) en el análisis de muestras de PV Glasses.

A continuación se explica cada uno de forma autocontenida.

---

## 4. Modelo típico de incertidumbre de un sensor (aditivo + escala)

Muchos sensores se modelan con **dos componentes**:

- **Aditiva:** no depende del valor medido. Ejemplo: “±0.1 mg” en una balanza.
- **De escala (proporcional):** proporcional al valor. Ejemplo: “±1 % de la lectura”.

Si **x** es el valor medido y **u_add** y **u_scale** son las incertidumbres estándar (k=1) de cada componente, la incertidumbre estándar de **x** es:

```
u(x)² = u_add² + (u_scale × x)²
u(x)  = √[ u_add² + (u_scale × x)² ]
```

- **u_add** tiene las mismas unidades que **x** (W/m², A, g, %, etc.).
- **u_scale** es adimensional (ej. 0.01 = 1 %).

En el proyecto, cada módulo de incertidumbre (RefCells, DustIQ, Soiling Kit, PVStand, IV600, PV Glasses, masas) define sus propios **u_add** y **u_scale** según especificaciones del fabricante o certificados, y luego usa esta fórmula (o una variante) para **u** de cada magnitud de entrada.

---

## 5. Propagación a una magnitud derivada (fórmula y derivadas)

Si la magnitud de interés **y** se calcula a partir de varias magnitudes **x₁, x₂, …** con una fórmula **y = f(x₁, x₂, …)**, la **ley de propagación de incertidumbres** (GUM) dice que, si las entradas no están correlacionadas:

```
u(y)² = (∂f/∂x₁)² · u(x₁)² + (∂f/∂x₂)² · u(x₂)² + …
```

Si hay correlación entre algunas entradas, se añaden términos con covarianzas; en el proyecto a menudo se supone **correlación 0** (independencia).

**Ejemplo — RefCells (SR a partir de dos irradiancias):**

- **SR = 100 × S / C**  
  S = irradiancia celda sucia (W/m²), C = irradiancia celda limpia (W/m²).

- Se calcula **u(S)** y **u(C)** con el modelo aditivo+escala.
- Derivadas:
  - ∂SR/∂S = 100/C  
  - ∂SR/∂C = −100×S/C²  
- Entonces:
  - **u(SR)² = (100/C)² · u(S)² + (−100×S/C²)² · u(C)²**  
  (y si se asume correlación S–C, se suma un término con covarianza; en el código suele ser 0.)
- **u(SR)** es la incertidumbre estándar del SR en %; **U(SR) = 2 × u(SR)** es la expandida k=2.

Ese mismo esquema (fórmula → derivadas → propagación) se usa en Soiling Kit, PVStand, IV600, etc., con sus propias fórmulas (SR con Isc, Pmax, temperatura, etc.). En DustIQ el SR viene directo del sensor, así que **u(SR)** se aplica directamente al valor SR con el modelo aditivo+escala. En **masas**, la magnitud es **Δm = m_soiled − m_clean**, y **u(Δm)² = u(m_soiled)² + u(m_clean)²** (con u(m) del modelo de la balanza).

---

## 6. Flujo A: Incertidumbre del Soiling Ratio (SR) por metodología

### 6.1 Módulos y fórmulas (resumen)

| Metodología   | Fórmula principal (idea)                    | Entradas con incertidumbre |
|---------------|---------------------------------------------|----------------------------|
| RefCells      | SR = 100 × S / C                            | S, C (irradiancia; aditivo+escala) |
| DustIQ        | SR = lectura del sensor                     | SR (aditivo+escala)        |
| Soiling Kit   | SR = 100 × Isc(p)/Isc(e); corrección T      | Isc, T, α_Isc              |
| PVStand       | SR = 100 × Pmax_s/Pmax_r o Isc_s/Isc_r; corr. T | Pmax, Isc, T               |
| IV600         | SR por comparación de módulos               | Isc, Pmax                  |
| PV Glasses    | SR = 100 × FC_sucio / REF                    | Canales FC, REF            |

**Flujo genérico para cada metodología:**

1. Cargar las series de entrada (por minuto o por día, según el caso).
2. Calcular **u** para cada magnitud de entrada (modelo aditivo+escala o el que corresponda).
3. Aplicar la fórmula del SR y la **propagación** (derivadas parciales) para obtener **u(SR)** en cada instante.
4. Calcular **U(SR) = 2 × u(SR)** (k=2).
5. Opcionalmente calcular **incertidumbre relativa** u_rel = u(SR)/SR.
6. **Agregar en el tiempo:** diario (Q25), semanal (Q25), mensual (Q25); para cada ventana usar incertidumbre **local** (promedio de u en esa ventana) o de campaña.
7. Exportar resultados (SR con u y U, y agregados si aplica) en el formato que use el proyecto.

### 6.2 Cálculo paso a paso por metodología

A continuación se describe **cómo se calcula la incertidumbre** en cada metodología: fórmula del SR, magnitudes de entrada y sus u(·), ecuación de propagación (y derivadas) y parámetros numéricos. Sin rutas ni nombres de archivo.

---

#### 6.2.1 RefCells

- **Fórmula del SR:**  
  **SR = 100 × S / C**  
  donde **S** = irradiancia celda sucia (W/m²), **C** = irradiancia celda limpia (W/m²).

- **Incertidumbres de entrada (fabricante Si-V-10TC-T, k=2 → se pasan a k=1):**
  - **U_ADD_K2 = 5.0 W/m²** → u_add = 2.5 W/m²  
  - **U_SCALE_K2 = 0.025** (2.5 %) → u_scale = 0.0125 (1.25 %)  
  - Por canal: **u(S)² = u_add² + (u_scale × S)²** y **u(C)² = u_add² + (u_scale × C)²**; **u(S)** y **u(C)** en W/m² (k=1).

- **Propagación al SR (cociente):**
  - ∂SR/∂S = 100/C  
  - ∂SR/∂C = −100×S/C²  
  - **Var(SR) = (∂SR/∂S)² u(S)² + (∂SR/∂C)² u(C)² + 2 (∂SR/∂S)(∂SR/∂C) Cov(S,C)**  
  - En el código se usa Cov(S,C) = 0 (independencia) por defecto; si se usara correlación ρ, Cov(S,C) = ρ u(S) u(C).  
  - **u(SR) = √Var(SR)** en % (k=1); **U(SR) = 2×u(SR)** (k=2).

- **Agregación:** Minuto a minuto → diario (Q25), semanal (Q25), mensual (Q25). Incertidumbre de la ventana = promedio local de u (o U) en esa ventana.

- **Resultados a producir:** Series de SR con u_SR (k=1) y U_SR (k=2), absoluta y relativa; opcionalmente agregados diario/semanal/mensual con su incertidumbre.

---

#### 6.2.2 DustIQ

- **Fórmula del SR:**  
  El **SR no se calcula por cociente**; viene **directo del sensor** (una lectura o promedio de varias). No hay propagación desde irradiancias.

- **Incertidumbre del SR (modelo aditivo + escala sobre el propio SR):**
  - Especificación fabricante: “±0.1 % of reading ±1 %” → **U_SR_ADD_K2 = 0.1 %**, **U_SR_SCALE_K2 = 0.01** (1 %) (k=2); en k=1: u_add = 0.05 %, u_scale = 0.005.  
  - **u(SR)² = u_add² + (u_scale × SR)²** → **u(SR)** en % (k=1).  
  - **U(SR) = 2×u(SR)** (k=2).

- **Agregación:** u(SR) minuto a minuto; luego agregar a diario/semanal/mensual con incertidumbre local (promedio de u en la ventana).

- **Resultados a producir:** SR con u(SR) y U(SR), absoluta y relativa; agregados si aplica.

---

#### 6.2.3 Soiling Kit

- **Fórmula del SR:**  
  **SR = 100 × Isc(p) / Isc(e)**  
  donde **Isc(p)** = corriente protegida (referencia), **Isc(e)** = corriente expuesta (sucio). Con corrección de temperatura:  
  **Isc_corr = Isc × (1 + α_Isc × (T_ref − T))**  
  y **SR = 100 × Isc_p_corr / Isc_e_corr** (α_Isc = 0.0004 /°C, T_ref = 25 °C).

- **Magnitudes de entrada y sus incertidumbres:**
  - **Isc:** Sensor SENECA T201DC → **U_ISC_SCALE_K2 = 0.002** (0.2 %), U_ISC_ADD_K2 = 0 → u(Isc)² = (u_scale × Isc)².  
  - **T:** PT100 Clase A (IEC 60751): tolerancia ±(0.15 + 0.002|t|) °C → **u(T)² = u_add² + (u_scale×|T|)²** con u_add = 0.15/√3, u_scale = 0.002/√3.  
  - **α_Isc:** constante del datasheet → **u(α) = 0**.

- **Cadena de cálculo:**
  1. u(Isc_e), u(Isc_p) y u(T_e), u(T_p) con los modelos anteriores.  
  2. **Isc_corr** con derivadas ∂Isc_corr/∂Isc, ∂Isc_corr/∂T, ∂Isc_corr/∂α → **u(Isc_corr)** por propagación.  
  3. **SR = 100 × Isc_p_corr / Isc_e_corr** con ∂SR/∂Isc_p_corr = 100/Isc_e_corr, ∂SR/∂Isc_e_corr = −100×Isc_p_corr/Isc_e_corr².  
  4. **Var(SR) = (∂SR/∂Isc_p_corr)² u(Isc_p_corr)² + (∂SR/∂Isc_e_corr)² u(Isc_e_corr)²** (+ término covarianza si ρ≠0).  
  5. **u(SR) = √Var(SR)**, **U(SR) = 2×u(SR)**.

- **Agregación:** Minuto a minuto → diario, semanal, mensual (Q25 de SR); incertidumbre de ventana = promedio local de u (o U).

- **Resultados a producir:** SR con u(SR) y U(SR); agregados diario/semanal/mensual con su incertidumbre.

---

#### 6.2.4 PVStand

- **Fórmulas del SR:**  
  - **SR_Isc = 100 × Isc_soiled / Isc_reference**  
  - **SR_Pmax = 100 × Pmax_soiled / Pmax_reference**  
  Con corrección de temperatura:  
  **Isc_corr = Isc / (1 + α_Isc × (T − T_ref))**  
  **Pmax_corr = Pmax / (1 + β_Pmax × (T − T_ref))**  
  (α_Isc = 0.0004 /°C, β_Pmax = −0.0036 /°C, T_ref = 25 °C).

- **Magnitudes de entrada:**  
  - **Isc:** IV tracer → U_ISC_SCALE_K2 = 0.002 (0.2 %), aditiva 0 → u(Isc).  
  - **Pmax:** IV tracer → U_PMAX_SCALE_K2 = 0.004 (0.4 %), aditiva 0 → u(Pmax).  
  - **T:** PT100 Clase A igual que Soiling Kit → u(T).  
  - **α_Isc, β_Pmax:** constantes datasheet → u(α)=0, u(β)=0.

- **Propagación:**  
  1. u(Isc), u(Pmax), u(T) por canal.  
  2. **u(Isc_corr)** y **u(Pmax_corr)** con derivadas respecto a Isc/Pmax, T y α/β.  
  3. **SR** a partir de cocientes Isc_corr o Pmax_corr; **Var(SR)** con ∂SR/∂numerador y ∂SR/∂denominador.  
  4. **u(SR)** y **U(SR)=2×u(SR)** para SR_Isc y SR_Pmax por separado.

- **Agregación:** Q25 por ventana, incertidumbre local.

- **Resultados a producir:** SR_Isc y SR_Pmax, cada uno con u y U; agregados por ventana si aplica.

---

#### 6.2.5 IV600

- **Fórmulas del SR:**  
  Comparación de módulos: **SR_Isc = 100 × Isc_soiled / Isc_ref**, **SR_Pmax = 100 × Pmax_soiled / Pmax_ref**.  
  Un módulo (o varios) sucio(s) frente a un módulo de referencia. **No** se aplica corrección de temperatura.

- **Magnitudes de entrada (certificado de calibración IV600):**  
  - **Isc:** ±0.2 % lectura → U_ISC_SCALE_K2 = 0.002, U_ISC_ADD_K2 = 0 → u(Isc)² = (u_scale×Isc)².  
  - **Pmax:** ±(1.0 % lectura + 6 dgt) → U_PMAX_SCALE_K2 = 0.01, U_PMAX_ADD_K2 = 6 W → u(Pmax)² = u_add² + (u_scale×Pmax)².

- **Propagación:**  
  - Para **SR_Isc:** ∂SR_Isc/∂Isc_soiled = 100/Isc_ref, ∂SR_Isc/∂Isc_ref = −100×Isc_soiled/Isc_ref²; Var(SR_Isc) con u(Isc_soiled) y u(Isc_ref); covarianza 0 por defecto.  
  - Para **SR_Pmax:** análogo con Pmax_soiled y Pmax_ref.  
  - **u(SR_Isc)**, **u(SR_Pmax)** en % (k=1); **U_SR_Isc_k2_abs**, **U_SR_Pmax_k2_abs** = 2×u.

- **Agregación:** Minuto a minuto → diario, semanal, mensual (Q25); incertidumbre local por ventana.

- **Resultados a producir:** SR_Isc y SR_Pmax con u y U (abs/rel, k=2); agregados si aplica.

---

#### 6.2.6 PV Glasses

- **Fórmula del SR:**  
  **REF** = promedio de dos celdas de referencia (irradiancia), **SR = 100 × FC_sucio / REF** para cada celda sucia (p. ej. tres celdas). Mismas fotoceldas Si-V-10TC-T que RefCells.

- **Incertidumbres de entrada:**  
  - Por canal: **u(R_FCj)² = u_add² + (u_scale × R_FCj)²** con **U_ADD_K2 = 5.0 W/m²**, **U_SCALE_K2 = 0.025** (k=1: u_add=2.5, u_scale=0.0125).  
  - **u(REF)² = (1/4)[u(R_FC1)² + u(R_FC2)²]** si R_FC1 y R_FC2 son independientes (ρ=0); si ρ≠0 se incluye covarianza en Var(REF).

- **Propagación por celda sucia:**  
  - ∂SR/∂FC_sucio = 100/REF, ∂SR/∂REF = −100×FC_sucio/REF².  
  - **Var(SR) = (∂SR/∂FC_sucio)² u(FC_sucio)² + (∂SR/∂REF)² u(REF)²** (+ 2×cov si ρ≠0).  
  - **u(SR)** y **U(SR)=2×u(SR)** para cada celda sucia.

- **Agregación:** Por ventana temporal (diario/semanal/mensual) con Q25; incertidumbre local.

- **Resultados a producir:** SR por cada celda sucia con u(SR) y U(SR) (abs/rel); agregados si aplica.

---

#### 6.2.7 Masas

- **Magnitud:** **Δm = m_soiled − m_clean** (en g; se reporta en mg). No es SR sino diferencia de masa.

- **Incertidumbre de cada pesada:** Modelo balanza **u(m)² = u_add² + (u_scale × m)²**. Por defecto u_scale = 0, u_add según especificación de la balanza (ej. 0.1 mg en k=1).

- **Propagación:** Independencia entre m_soiled y m_clean:  
  **u(Δm)² = u(m_soiled)² + u(m_clean)²**  
  **U(Δm) = 2×u(Δm)** (k=2).

- **Resultados a producir:** Δm con u(Δm) y U(Δm) por muestra. Los valores u_add y u_scale de la balanza se toman de su especificación o certificado.

---

### 6.3 Agregación temporal (semanal / mensual)

- El **SR** en cada ventana (semana o mes) se obtiene como **cuantil 0.25 (Q25)** de los SR de esa ventana.
- La **incertidumbre** asociada a esa semana (o mes) puede ser:
  - **Local:** promedio (u o U) de los minutos/días de esa ventana.
  - O una **incertidumbre de campaña** (promedio global de U_rel) aplicada al valor agregado.

Cuando hay datos minuto a minuto se usa agregación con incertidumbre local; el resultado (SR agregado + U por ventana) se exporta para uso en gráficos o informes.

### 6.4 Uso en los gráficos (barras de error)

- Para cada punto (fecha, SR) se usa la **incertidumbre expandida** correspondiente (U en % o en fracción, según cómo se haya guardado).
- La **barra de error vertical** en ese punto es la **incertidumbre absoluta** del SR en esa fecha:
  - Si U está en **%:** yerr = U × valor_SR / 100 (para pasar a mismas unidades que el eje).
  - Si U está en **fracción** (p. ej. en algunas implementaciones de IV600 o PV Glasses): yerr = U × valor_SR.


---

## 7. Flujo B: Incertidumbre de las diferencias de masa (Δm)

Aquí la magnitud es **Δm = m_soiled − m_clean** (en g; luego se pasa a mg).

- **u(m)** para cada pesada: modelo aditivo (y opcionalmente escala) de la balanza:  
  **u(m)² = u_add² + (u_scale × m)²**.  
  Por defecto u_scale = 0, u_add ≈ 0.1 mg (k=1).
- **Propagación:** se asume independencia entre m_soiled y m_clean:  
  **u(Δm)² = u(m_soiled)² + u(m_clean)²**  
  → **u(Δm) = √2 × u_add** si u_scale = 0.
- **U(Δm) = 2 × u(Δm)** (k=2).


---

## 8. Resumen: de dónde sale cada “error”

| Qué se representa | Cómo se obtiene |
|-----------------------------|---------------------------|
| Barras de error en SR (cualquier metodología) | Propagación GUM según la sección 6.2 correspondiente → u(SR) → U(SR)=2×u(SR) → agregación si aplica → usar U (o u) como yerr en el gráfico. |
| Incertidumbre de diferencias de masa (Δm) | u(m) por pesada (modelo balanza) → u(Δm) propagada → U(Δm)=2×u(Δm); exportar según el proyecto. |

---

## 9. Flujo de implementación (genérico)

- **SR (cualquier metodología):** Cargar series de entrada → calcular u de cada magnitud de entrada → aplicar fórmula del SR y propagación → u(SR), U(SR)=2×u(SR) → opcionalmente u_rel → agregar por ventana (Q25) con incertidumbre local → exportar resultados (SR, u, U; agregados si aplica).
- **Masas:** Cargar masas soiled/clean → u(m) por pesada → u(Δm), U(Δm) → exportar.
- **Valores u_add, u_scale, etc.:** Definirlos en el código según especificaciones del fabricante o certificados (k=2 → dividir por 2 para k=1).

---

## 10. Glosario mínimo

- **Incertidumbre estándar u:** incertidumbre expresada como una desviación típica (k=1).
- **Incertidumbre expandida U:** U = k×u; con k=2, intervalo de confianza ~95 %.
- **Propagación (GUM):** combinar las u de las magnitudes de entrada para obtener la u de la magnitud de salida usando la fórmula y las derivadas parciales.
- **Aditivo / escala:** componentes de la incertidumbre de un sensor (constante y proporcional al valor).
- **u_rel (incertidumbre relativa):** u / valor (adimensional o en %); permite comparar incertidumbres entre valores distintos.
- **Q25:** cuantil 25 %; en agregaciones temporales se usa como valor representativo del SR en esa ventana.
