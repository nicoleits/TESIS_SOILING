"""
Constantes de incertidumbre (k=1) por sensor/balanza.

Los valores deben tomarse de certificados de calibración o especificaciones
del fabricante. No se asumen valores por defecto hasta que estén confirmados
en PARAMETROS_INCERTIDUMBRE.md.

Conversión k=2 → k=1: u = U_k2 / 2.
"""

# -----------------------------------------------------------------------------
# Balanza (masas, PV Glasses) — Modelo LF224(R) (Sartorius)
# -----------------------------------------------------------------------------
# Especificación: d (readability) = 0,0001 g. Incertidumbre estándar por resolución
# (GUM, distribución rectangular): u_add = d/√3 ≈ 5,77e-5 g.
# u(m)² = BALANZA_U_ADD_G² + (BALANZA_U_SCALE * m)²; solo resolución → u_scale = 0.

BALANZA_READABILITY_G = 0.0001   # d (g), datasheet LF224(R)
BALANZA_U_ADD_G = BALANZA_READABILITY_G / (3 ** 0.5)   # d/√3 ≈ 5.77e-5 g
BALANZA_U_SCALE = 0.0

# Factor de cobertura para incertidumbre expandida U = K_COVERAGE * u
K_COVERAGE = 2

# -----------------------------------------------------------------------------
# Área del vidrio (PV Glasses) — 3×4 cm, regla milimetrada
# -----------------------------------------------------------------------------
# Dimensiones medidas con regla común (resolución 1 mm = 0,1 cm).
# u(L) = 0,1/√3 cm por lado; A = L1*L2 → u(A)² = L2² u(L1)² + L1² u(L2)².

AREA_VIDRIO_CM2 = 12.0   # 3 × 4 cm
RULER_RESOLUTION_CM = 0.1
U_LENGTH_CM = RULER_RESOLUTION_CM / (3 ** 0.5)   # 0.1/√3 ≈ 0.0577 cm
# u(A) con L1=3, L2=4: u(A) = sqrt(4² * u(L)² + 3² * u(L)²) = sqrt(25) * u(L) = 5 * 0.1/√3
U_AREA_CM2 = 5.0 * U_LENGTH_CM   # ≈ 0.289 cm²

# -----------------------------------------------------------------------------
# SR — RefCells y PV Glasses (fotoceldas Si-V-10TC-T). Fase 2/3.
# -----------------------------------------------------------------------------
# Mismas fotoceldas en ambos: incertidumbre aditiva k=2 → 5,0 W/m², escala k=2 → 2,5 %.
# En k=1: u = U_k2/2. u(irradiancia)² = u_add² + (u_scale × E)² (E en W/m²).

REFCELLS_U_ADD_K2_W_M2 = 5.0    # incertidumbre expandida aditiva (k=2)
REFCELLS_U_SCALE_K2 = 0.025     # 2,5 % (k=2)
REFCELLS_U_ADD_W_M2 = REFCELLS_U_ADD_K2_W_M2 / 2.0   # 2.5 W/m² (k=1)
REFCELLS_U_SCALE = REFCELLS_U_SCALE_K2 / 2.0         # 0.0125 (k=1)

# PV Glasses: mismas fotoceldas que RefCells → mismas incertidumbres por canal.
PV_GLASSES_U_ADD_W_M2 = REFCELLS_U_ADD_W_M2
PV_GLASSES_U_SCALE = REFCELLS_U_SCALE

# -----------------------------------------------------------------------------
# DustIQ — SR directo del sensor (aditiva + escala sobre SR en %)
# -----------------------------------------------------------------------------
# Especificación: aditiva k=2 → 0,1 %; escala k=2 → 1 %. En k=1: u = U_k2/2.
# u(SR)² = u_add² + (u_scale × SR)² (SR en %; u_add y u_scale en fracción o % según convención).

DUSTIQ_U_ADD_K2 = 0.001    # 0,1 % (k=2)
DUSTIQ_U_SCALE_K2 = 0.01   # 1 % (k=2)
DUSTIQ_U_ADD = DUSTIQ_U_ADD_K2 / 2.0    # 0.0005 (0,05 %) k=1
DUSTIQ_U_SCALE = DUSTIQ_U_SCALE_K2 / 2.0  # 0.005 (0,5 %) k=1

# -----------------------------------------------------------------------------
# PT100 Clase A (IEC 60751) — temperatura (PVStand, IV600). Soiling Kit no usa corrección T.
# -----------------------------------------------------------------------------
# Tolerancia: ±(0,15 + 0,002|t|) °C (t = temperatura en °C).
# Incertidumbre estándar (rectangular): u(T) = (0,15 + 0,002×|t|) / √3

PT100_TOLERANCE_ADD_C = 0.15     # °C (término constante)
PT100_TOLERANCE_SCALE = 0.002    # por °C (término proporcional a |t|)
# u(T) en °C = (PT100_TOLERANCE_ADD_C + PT100_TOLERANCE_SCALE * abs(t)) / sqrt(3)

# Temperatura típica para propagación cuando no hay T por fila (°C)
PT100_T_TYPICAL_C = 35.0

# -----------------------------------------------------------------------------
# IEC 60891 — coeficientes de corrección a 25 °C (mismos que en calcular_sr_*_corr)
# -----------------------------------------------------------------------------
# Pmax_corr = Pmax / (1 + β×(T−25)),  Isc_corr = Isc / (1 + α×(T−25))
IEC60891_T_REF_C = 25.0
IEC60891_ALPHA_ISC = 0.0004    # /°C (Isc)
IEC60891_BETA_PMAX = -0.0036   # /°C (Pmax)

# -----------------------------------------------------------------------------
# PVStand (IV tracer) — Isc, voltaje, Pmax + corrección T (PT100)
# -----------------------------------------------------------------------------
# Especificación: voltaje y corriente k=2 → 0,2 %; potencia k=2 → 0,4 %. Aditiva 0.
# En k=1: u = U_k2/2. u(x)² = (u_scale × x)² (solo escala).

PVSTAND_U_ISC_SCALE_K2 = 0.002    # 0,2 % (k=2) corriente
PVSTAND_U_VOLTAGE_SCALE_K2 = 0.002 # 0,2 % (k=2) voltaje
PVSTAND_U_PMAX_SCALE_K2 = 0.004   # 0,4 % (k=2) potencia
PVSTAND_U_ISC_SCALE = PVSTAND_U_ISC_SCALE_K2 / 2.0       # 0.001 (k=1)
PVSTAND_U_VOLTAGE_SCALE = PVSTAND_U_VOLTAGE_SCALE_K2 / 2.0
PVSTAND_U_PMAX_SCALE = PVSTAND_U_PMAX_SCALE_K2 / 2.0     # 0.002 (k=1)

# -----------------------------------------------------------------------------
# IV600 — Isc (solo escala), Pmax (aditiva + escala), corrección T (PT100)
# -----------------------------------------------------------------------------
# Isc: escala k=2 → 0,2 %, aditiva 0. Pmax: 1 % lectura + 6 W (6 dgt), k=2 → u_add = 3 W, u_scale = 0,005 (k=1).
# u(Pmax)² = u_add² + (u_scale × Pmax)² (Pmax en W). Temperatura: misma PT100 Clase A que PVStand.

IV600_U_ISC_SCALE_K2 = 0.002   # 0,2 % (k=2) corriente, solo escala
IV600_U_ISC_SCALE = IV600_U_ISC_SCALE_K2 / 2.0   # 0.001 (k=1)
IV600_U_ISC_ADD_W = 0.0

IV600_U_PMAX_ADD_K2_W = 6.0    # 6 W (6 dgt) k=2
IV600_U_PMAX_SCALE_K2 = 0.01   # 1 % (k=2)
IV600_U_PMAX_ADD_W = IV600_U_PMAX_ADD_K2_W / 2.0  # 3 W (k=1)
IV600_U_PMAX_SCALE = IV600_U_PMAX_SCALE_K2 / 2.0  # 0.005 (k=1)

# -----------------------------------------------------------------------------
# Soiling Kit — sensor de corriente Seneca (Isc). Sin corrección de temperatura.
# -----------------------------------------------------------------------------
# Isc: escala k=2 → 0,2 %, aditiva 0. u(Isc)² = (u_scale × Isc)². No se usa PT100 (sensor T se hizo a perder).

SOILING_KIT_U_ISC_SCALE_K2 = 0.002   # 0,2 % (k=2)
SOILING_KIT_U_ISC_SCALE = SOILING_KIT_U_ISC_SCALE_K2 / 2.0   # 0.001 (k=1)
SOILING_KIT_U_ISC_ADD = 0.0
