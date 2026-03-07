# Parámetros de incertidumbre — checklist

**No se asume ningún valor.** Marca o escribe solo lo que hayas confirmado (certificado, datasheet o decisión explícita).

---

## Fase 1 — Masas (Δm)

### Cuando solo tienes el error instrumental

Si el fabricante o el certificado dan **solo un error instrumental** (p. ej. “±0,2 mg” o “incertidumbre 0,1 mg”):

1. **Interpretar como incertidumbre de cada pesada** (igual para todas las lecturas).
2. **u_scale = 0** (no hay componente proporcional a la lectura).
3. **u_add (k=1):** Si el dato viene como incertidumbre expandida U (k=2): u_add = U / 2 (mismas unidades). Si viene como incertidumbre estándar: u_add = ese valor.
4. **En el modelo:** u(m) = u_add para toda pesada; luego **u(Δm) = √2 × u_add** (porque u(Δm)² = 2 u_add²), **U(Δm) = 2 × u(Δm)** (k=2).

Así se usa **solo el error instrumental** sin añadir otros términos.

**Si solo tienes la resolución d (readability)** de la balanza (p. ej. d = 0,0001 g): la incertidumbre estándar por resolución se toma como **u_add = d/√3** (distribución rectangular: el valor verdadero se supone uniforme en un intervalo de amplitud d alrededor de la lectura; GUM / guías de metrología).

---

| Parámetro | Unidad | Origen (certificado / datasheet) | Valor a usar (k=1) | ¿Confirmado? |
|----------|--------|-----------------------------------|-------------------|---------------|
| **Balanza** | — | Modelo **LF224(R)** (Sartorius). Especificación: d = 0,0001 g (readability). | — | [x] |
| **Balanza — u_add** | g | Resolución d: incertidumbre estándar por resolución **u_add = d/√3** (distribución rectangular, GUM). d = 0,0001 g → u_add ≈ 5,77e-5 g (≈ 0,058 mg). | 5,77e-5 g | [x] |
| **Balanza — u_scale** | adimensional | Solo error instrumental (resolución) → 0 | 0 | [x] |
| **Factor de cobertura para U** | k = 2 (95 %) | GUM | 2 | [x] |

Nota: con solo error instrumental u(m)=u_add → u(Δm)=√2·u_add. U(Δm) = k×u(Δm).

---

### Área del vidrio (ρm = Δm / A)

| Parámetro | Unidad | Origen | Valor a usar (k=1) | ¿Confirmado? |
|-----------|--------|--------|-------------------|---------------|
| **Dimensiones** | cm | Vidrio 3×4 cm, medidas con **regla común milimetrada** (resolución 1 mm = 0,1 cm). | L1 = 3, L2 = 4 | [x] |
| **Área nominal** | cm² | A = L1×L2 | 12 cm² | [x] |
| **u(longitud)** | cm | Resolución 0,1 cm, distribución rectangular: u(L) = 0,1/√3 ≈ 0,0577 cm (por lado). | 0,1/√3 | [x] |
| **u(área)** | cm² | Propagación A = L1×L2, L1 y L2 independientes: u(A)² = L2² u(L1)² + L1² u(L2)² = 16×(0,1/√3)² + 9×(0,1/√3)² → u(A) ≈ 0,289 cm². | ≈ 0,29 cm² | [x] |

Incertidumbre de ρm = Δm/A: propagación del cociente (u(ρm)/ρm)² = (u(Δm)/Δm)² + (u(A)/A)². Implementado en mass.py: columnas rho_m_*_mg_cm2, u_rho_m_*_mg_cm2, U_rho_m_*_mg_cm2 en resultados_diferencias_masas.csv. [x]

---

## Fase 2 — SR RefCells / DustIQ

| Parámetro | Metodología | Valor (k=1 o k=2 según documento) | ¿Confirmado? |
|-----------|-------------|-----------------------------------|---------------|
| **RefCells** (Si-V-10TC-T) | — | Aditiva k=2: 5,0 W/m² → u_add = 2,5 W/m². Escala k=2: 2,5 % → u_scale = 0,0125. | [x] |
| U_ADD, U_SCALE (RefCells) | RefCells | U_ADD_k2 = 5,0 W/m², U_SCALE_k2 = 2,5 % | [x] |
| **DustIQ** | — | Aditiva k=2: 0,1 % → u_add = 0,05 % (0,0005). Escala k=2: 1 % → u_scale = 0,5 % (0,005). u(SR)² = u_add² + (u_scale×SR)² (SR en %). | [x] |
| U_ADD, U_SCALE (DustIQ) | DustIQ | U_ADD_k2 = 0,1 %, U_SCALE_k2 = 1 % | [x] |

---

## Fase 3 — Soiling Kit, PVStand, IV600, PV Glasses

- **PV Glasses (fotoceldas):** Las fotoceldas son las **mismas que RefCells** (Si-V-10TC-T) → **mismas incertidumbres**: aditiva 5,0 W/m² (k=2), escala 2,5 % (k=2); u_add = 2,5 W/m², u_scale = 0,0125. REF = promedio de celdas de referencia; SR = 100×FC_sucio/REF; propagación con las mismas u por canal. [x]
- **PVStand (IV tracer):** Voltaje y corriente k=2 → 0,2 % (u_scale = 0,001 k=1). Potencia k=2 → 0,4 % (u_scale = 0,002 k=1). Aditiva 0. **Temperatura:** PT100 Clase A (IEC 60751), tolerancia ±(0,15 + 0,002|t|) °C → u(T) = (0,15 + 0,002|t|)/√3 (distribución rectangular). SR por Isc o Pmax con corrección de temperatura. [x]
- **PT100 Clase A (IEC 60751):** Usada en **PVStand e IV600** para corrección por temperatura. Tolerancia ±(0,15 + 0,002|t|) °C (t en °C). u(T) = tolerancia/√3. [x]
- **IV600:** Corriente (Isc): solo escala k=2 → 0,2 % (u_scale = 0,001 k=1), aditiva 0. Potencia (Pmax): aditiva 6 W (k=2) + escala 1 % (k=2), “1 % lectura + 6 dgt” → u_add = 3 W (k=1), u_scale = 0,005 (k=1). u(Pmax)² = u_add² + (u_scale×Pmax)². **Temperatura:** misma PT100 Clase A (corrección T cuando se aplique). [x]
- **Soiling Kit:** Sensor de corriente **Seneca**: solo escala k=2 → 0,2 % (u_scale = 0,001 k=1), aditiva 0. u(Isc)² = (u_scale×Isc)². **Caso especial:** no se aplica corrección de temperatura (el sensor de T se hizo a perder). SR = 100×Isc(p)/Isc(e) sin corrección T. [x]

---

## Fase 4 — Agregación y gráficos

- Incertidumbre por ventana (semanal/mensual): ¿promedio de u(SR) en la ventana? [ ]  
- Criterio NaN/outliers (ej. SR < 80 → u, U = NaN): _______________

---

*Actualizar este archivo al confirmar cada parámetro; el código solo usará valores aquí documentados.*
