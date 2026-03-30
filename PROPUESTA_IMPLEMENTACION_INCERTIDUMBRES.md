# Propuesta de implementacion: incertidumbres GUM (SR y Delta m)

Integracion del calculo de incertidumbres segun PROCESO_COMPLETO_CALCULO_DE_ERRORES.md.

## 1. Estado actual

- **Existe:** Calculo de SR en TESIS_SOILING/analysis/sr/ (Soiling Kit, RefCells, DustIQ, PV Glasses, PVStand, IV600). Agregacion Q25 en analysis/semanal/. masas_analysis.py calcula Delta m y guarda resultados_diferencias_masas.csv pero intenta importar analysis.sr_uncertainty_mass que NO EXISTE (dummy). dispersion_masas.py usa std como yerr (dispersion, no U(Delta m)).
- **No existe:** Modulo incertidumbre masas; modulo incertidumbre SR; constantes u_add/u_scale centralizadas; columnas u_SR, U_SR, u_Delta_m, U_Delta_m en CSVs.

## 2. Estructura propuesta

TESIS_SOILING/analysis/uncertainty/
  constants.py   (u_add, u_scale k=1 por sensor)
  propagation.py (modelo aditivo+escala, propagacion)
  mass.py        (Flujo B: u(Delta m), U(Delta m))
  sr_*.py        (Flujo A por metodologia: refcells, dustiq, soilingkit, pvstand, iv600, pv_glasses)

## 3. Flujo B - Masas (prioridad 1)

- Fichero: analysis/uncertainty/mass.py. Llamado desde masas_analysis.py.
- Entrada: DataFrame con Masa_*_Soiled_g, Masa_*_Clean_g (A,B,C).
- Constantes: balanza u_add (ej. 0.1 mg k=1), u_scale=0.
- u(m)^2 = u_add^2 + (u_scale*m)^2; u(Delta m)^2 = u(m_soiled)^2 + u(m_clean)^2; U(Delta m)=2*u(Delta m).
- Salida: anadir columnas u_Delta_m_A_mg, U_Delta_m_A_mg (y B, C) al CSV.
- Import: masas_analysis debe anadir TESIS_SOILING al path e importar desde analysis.uncertainty.mass.

## 4. Flujo A - SR (prioridad 2 en adelante)

- constants.py con valores PROCESO (RefCells 5 W/m2 2.5%, DustIQ 0.1%+1%, Soiling Kit Isc 0.2%, PT100, PVStand, IV600, PV Glasses).
- propagation.py: u_sensor(x,u_add,u_scale); propagacion cociente y=100*a/b.
- Por metodologia: leer CSV alineado, u(entradas), formula SR, propagacion, devolver SR, u_SR, U_SR.
- Integracion: anadir u_SR, U_SR a los CSVs de SR (desde calcular_sr*.py o paso posterior).
- Agregacion: incertidumbre ventana = promedio de u(SR) en la ventana.

## 5. Graficos

- Masas: mantener media +/- std; opcional anadir media +/- U(Delta m) o leyenda.
- SR: donde se quiera incertidumbre de medida, yerr = U(SR).

## 6. Orden implementacion

1. Fase 1: uncertainty/ + mass.py + integracion masas_analysis + columnas u/U en CSV masas.
2. Fase 2: RefCells y DustIQ (sr_refcells, sr_dustiq).
3. Fase 3: Soiling Kit, PVStand, IV600, PV Glasses.
4. Fase 4: Agregacion semanal/mensual con u; U en graficos.

## 7. Informacion que falta o hay que decidir

### 7.1 Especificaciones de sensores (valores k=2 en documento, pasar a k=1 en codigo)

| Sensor / Metodologia | Valores en PROCESO | Que falta |
|----------------------|--------------------|-----------|
| RefCells Si-V-10TC-T | U_ADD_K2=5 W/m2, U_SCALE_K2=0.025 | Confirmar con certificado/datasheet real |
| DustIQ | 0.1% + 1% lectura | Confirmar que no hay otro termino |
| Soiling Kit (SENECA T201DC) | Isc 0.2%, aditiva 0 | Confirmar |
| PVStand (IV tracer) | Isc 0.2%, Pmax 0.4% | Modelo exacto y hoja de calibracion |
| IV600 | Isc 0.2%; Pmax 1%+6 dgt | Certificado de calibracion oficial |
| Balanza | u_add ej. 0.1 mg k=1 | Modelo y certificado para u_add y u_scale |
| PT100 Clase A | 0.15+0.002|t| °C | Confirmar clase en vuestro equipo |

### 7.2 Correlaciones

El PROCESO asume Cov(S,C)=0 (RefCells), rho=0 en PV Glasses. Si en la practica hay correlacion (mismo multiplexor, mismo sensor), hay que definir rho o Cov para las formulas.

### 7.3 Incertidumbre por ventana (semanal/mensual)

Decidir: promedio de u(SR) o de U(SR) en la ventana; solo sobre instantes con SR valido (no NaN); si se usa incertidumbre de campana (promedio global U_rel), como se calcula.

### 7.4 Rutas y nombres de columnas

Para cada modulo: ruta del CSV alineado de entrada; nombres de columnas (timestamp, S, C, Isc(e), Isc(p), REF, R_FC3_Avg, etc.); ruta y nombres del CSV de salida (u_SR, U_SR, u_rel, etc.).

### 7.5 PV Glasses

Confirmar que REF = (FC1+FC2)/2 y que u(REF)^2 = (1/4)[u(R_FC1)^2+u(R_FC2)^2] con las columnas reales del CSV.

### 7.6 Tratamiento de NaN y outliers

Si SR < 80 se pone NaN: u(SR) y U(SR) tambien NaN en esos instantes. En agregacion, promediar u solo sobre puntos con SR valido. Dejar criterio escrito.

---

**Resumen:** Implementar primero Fase 1 (masas); documentar constantes y formato CSV; luego SR por metodologia. Falta fijar valores de certificados, criterios de ventana/NaN y nombres de archivos/columnas.
