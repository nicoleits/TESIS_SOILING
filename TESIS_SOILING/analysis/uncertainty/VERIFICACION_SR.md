# Verificación de los cálculos de incertidumbre de SR

## ¿Qué estamos comprobando?

La tabla `resumen_incertidumbre_sr_por_metodologia.csv` tiene, para cada metodología, la **incertidumbre combinada u_c(SR)** y la **incertidumbre expandida U(SR)** en puntos porcentuales (pp). Esas cifras salen de **fórmulas** implementadas en el código (en `propagation.py` y `sr_metodologias.py`).

La verificación sirve para asegurarnos de que **esas fórmulas están bien programadas**: que el número que sale del código es el mismo que obtendrías si hicieras el cálculo a mano con una calculadora.

---

## ¿Cómo se comprueba?

El script `verify_uncertainty_sr.py` hace lo siguiente para cada tipo de cálculo:

1. **Elige un caso concreto** (por ejemplo: SR = 100 %).
2. **Calcula u_c y U de dos maneras:**
   - Llamando a la **función** que usa el programa para generar la tabla.
   - Calculando **paso a paso** con la fórmula (igual que en papel o calculadora).
3. **Compara** los dos resultados. Si son iguales (salvo redondeos), la función está bien.

Al ejecutar el script verás algo así:

```
1. PV Glasses / RefCells (SR = 100 %)
  Resultado de la función:  u_c = 1.8028 pp,  U = 3.6056 pp
  Resultado paso a paso:   u_c = 1.8028 pp,  U = 3.6056 pp  →  Coinciden
```

Si en algún momento no coincidieran, el script se detendría y mostraría un error (y entonces habría que revisar la fórmula en el código).

---

## Cómo ejecutar la verificación

Desde la carpeta **TESIS_SOILING**:

```bash
python -m analysis.uncertainty.verify_uncertainty_sr
```

(Si usas un entorno virtual, activa primero el `.venv` o usa su `python`.)

Al final debe aparecer: **"Todas las comprobaciones pasaron."**

---

## Comprobar tú mismo con calculadora (opcional)

Si quieres comprobar **un solo número** a mano, el caso más simple es **DustIQ** con SR = 100 %:

- Fórmula: **u_c(SR) = √( 0,05² + (0,005 × SR)² )** en pp.
- Para SR = 100: u_c = √(0,0025 + 0,25) = √0,2525 ≈ **0,5025 pp**.
- U = 2 × u_c ≈ **1,005 pp**.

Eso es exactamente lo que debe dar el script para DustIQ (SR=100 %). Si tu calculadora da lo mismo, la verificación “a mano” coincide con el programa.
