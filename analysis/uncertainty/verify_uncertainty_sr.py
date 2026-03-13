"""
Verificación de los cálculos de incertidumbre de SR.

Qué hace este script:
  Para cada metodología, toma UN valor de SR (ej. 100 %) y calcula u_c(SR) y U(SR)
  de DOS maneras:
    1) Con la función que usamos en la tabla (la que procesa todos los datos).
    2) Paso a paso con la fórmula, como si lo hicieras a mano en una calculadora.
  Si ambos resultados coinciden, la función está bien implementada.

Cómo ejecutarlo (desde carpeta TESIS_SOILING):
  python -m analysis.uncertainty.verify_uncertainty_sr
"""

import numpy as np

# Tolerancia para considerar "iguales" dos números (errores de redondeo)
RTOL = 1e-4
ATOL = 1e-6


def verify_u_ratio_sr_photodiodes():
    """
    PV Glasses / RefCells: SR = 100 × E_sucio/E_ref.
    u(E)² = u_add² + (u_scale×E)² → u(E)/E = sqrt((u_add/E)² + u_scale²).
    (u(SR)/SR)² = (u(E_sucio)/E_sucio)² + (u(E_ref)/E_ref)² → u_c(SR) [pp] = SR × (u(SR)/SR).
    """
    from .propagation import u_ratio_sr_photodiodes
    from . import constants

    u_add = constants.REFCELLS_U_ADD_W_M2   # 2.5 W/m² (k=1)
    u_scale = constants.REFCELLS_U_SCALE    # 0.0125 (k=1)
    e_ref = 1000.0
    k = 2.0

    # Caso: SR = 100 % → E_sucio = 1000 W/m². Ambos canales iguales.
    sr = 100.0
    e_sucio = (sr / 100.0) * e_ref  # 1000
    u_over_e_ref = np.sqrt((u_add / e_ref) ** 2 + u_scale ** 2)
    u_over_e_sucio = np.sqrt((u_add / e_sucio) ** 2 + u_scale ** 2)
    u_sr_rel = np.sqrt(u_over_e_sucio ** 2 + u_over_e_ref ** 2)
    u_c_pp_esperado = sr * u_sr_rel
    U_pp_esperado = k * u_c_pp_esperado

    u_c_pp, U_pp = u_ratio_sr_photodiodes(np.array([sr]), u_add, u_scale, e_ref_w_m2=e_ref, k=k)
    assert np.isclose(u_c_pp[0], u_c_pp_esperado, rtol=RTOL, atol=ATOL), (
        f"u_c_pp: obtenido {u_c_pp[0]:.6f}, esperado {u_c_pp_esperado:.6f}"
    )
    assert np.isclose(U_pp[0], U_pp_esperado, rtol=RTOL, atol=ATOL), (
        f"U_pp: obtenido {U_pp[0]:.6f}, esperado {U_pp_esperado:.6f}"
    )
    print("  Resultado de la función:  u_c = {:.4f} pp,  U = {:.4f} pp".format(u_c_pp[0], U_pp[0]))
    print("  Resultado paso a paso:   u_c = {:.4f} pp,  U = {:.4f} pp  →  Coinciden".format(u_c_pp_esperado, U_pp_esperado))
    return True


def verify_u_sr_dustiq():
    """
    DustIQ: u(SR)² = u_add² + (u_scale×SR)² con SR en %.
    u_add_pp en pp (k=1), u_scale adimensional → u_c [pp] = sqrt(u_add_pp² + (u_scale×SR)²).
    """
    from .propagation import u_sr_dustiq
    from . import constants

    u_add_pp = constants.DUSTIQ_U_ADD * 100   # 0.0005 → 0.05 pp
    u_scale = constants.DUSTIQ_U_SCALE        # 0.005
    k = 2.0

    # Caso SR = 100 %
    sr = 100.0
    u_c_pp_esperado = np.sqrt(u_add_pp ** 2 + (u_scale * sr) ** 2)
    U_pp_esperado = k * u_c_pp_esperado

    u_c_pp, U_pp = u_sr_dustiq(np.array([sr]), u_add_pp, u_scale, k=k)
    assert np.isclose(u_c_pp[0], u_c_pp_esperado, rtol=RTOL, atol=ATOL), (
        f"u_c_pp: obtenido {u_c_pp[0]:.6f}, esperado {u_c_pp_esperado:.6f}"
    )
    assert np.isclose(U_pp[0], U_pp_esperado, rtol=RTOL, atol=ATOL), (
        f"U_pp: obtenido {U_pp[0]:.6f}, esperado {U_pp_esperado:.6f}"
    )
    print("  Caso SR = 100 %:")
    print("    Función:     u_c = {:.4f} pp,  U = {:.4f} pp".format(u_c_pp[0], U_pp[0]))
    print("    Paso a paso: u_c = {:.4f} pp,  U = {:.4f} pp  →  Coinciden".format(u_c_pp_esperado, U_pp_esperado))

    # Caso SR = 0: solo aditiva
    sr0 = 0.0
    u_c_0_esperado = u_add_pp
    u_c_pp_0, _ = u_sr_dustiq(np.array([sr0]), u_add_pp, u_scale, k=k)
    assert np.isclose(u_c_pp_0[0], u_c_0_esperado, rtol=RTOL, atol=ATOL), (
        f"u_c(SR=0): obtenido {u_c_pp_0[0]:.6f}, esperado {u_c_0_esperado:.6f}"
    )
    print("  Caso SR = 0 % (solo término aditivo):")
    print("    Función:     u_c = {:.4f} pp".format(u_c_pp_0[0]))
    print("    Paso a paso: u_c = {:.4f} pp  →  Coinciden".format(u_c_0_esperado))
    return True


def verify_u_sr_ratio_scale_only():
    """
    Soiling Kit / PVStand / IV600 (Isc): SR = cociente, misma u_scale en numerador y denominador.
    u(SR)/SR = sqrt(2)*u_scale → u_c(SR) [pp] = SR × u_scale × sqrt(2).
    """
    from .propagation import u_sr_ratio_scale_only
    from . import constants

    u_scale = constants.SOILING_KIT_U_ISC_SCALE   # 0.001 (k=1)
    k = 2.0

    sr = 100.0
    u_c_pp_esperado = sr * u_scale * np.sqrt(2.0)
    U_pp_esperado = k * u_c_pp_esperado

    u_c_pp, U_pp = u_sr_ratio_scale_only(np.array([sr]), u_scale, k=k)
    assert np.isclose(u_c_pp[0], u_c_pp_esperado, rtol=RTOL, atol=ATOL), (
        f"u_c_pp: obtenido {u_c_pp[0]:.6f}, esperado {u_c_pp_esperado:.6f}"
    )
    assert np.isclose(U_pp[0], U_pp_esperado, rtol=RTOL, atol=ATOL), (
        f"U_pp: obtenido {U_pp[0]:.6f}, esperado {U_pp_esperado:.6f}"
    )
    print("  Resultado de la función:  u_c = {:.4f} pp,  U = {:.4f} pp".format(u_c_pp[0], U_pp[0]))
    print("  Resultado paso a paso:   u_c = {:.4f} pp,  U = {:.4f} pp  →  Coinciden".format(u_c_pp_esperado, U_pp_esperado))
    return True


def verify_consistency_with_real_data():
    """
    Comprueba que un valor típico de la tabla (p. ej. mediana PV Glasses) sea coherente
    con la función al aplicarla a un SR cercano a esa mediana.
    """
    from .sr_pv_glasses import add_uncertainty_sr_pv_glasses
    from . import constants

    # PV Glasses: mediana u_c ≈ 1.74 pp para SR típico ~98–100 %
    df = __import__("pandas").DataFrame({"sr_q25": [98.0, 100.0]})
    out = add_uncertainty_sr_pv_glasses(df, col_sr="sr_q25")
    u_c = out["u_c_SR_pp"].values
    # Debe estar en el rango razonable 1.7–1.8 pp para SR 98–100
    assert 1.6 < u_c[0] < 1.9 and 1.6 < u_c[1] < 1.9, (
        f"u_c fuera de rango esperado: {u_c}"
    )
    print("  u_c(SR=98) = {:.4f} pp,  u_c(SR=100) = {:.4f} pp".format(u_c[0], u_c[1]))
    print("  (la tabla da mediana ~1.74 pp; estos valores están en ese rango)  →  OK")
    return True


def run_all():
    print("=" * 60)
    print("VERIFICACIÓN DE INCERTIDUMBRE DE SR")
    print("=" * 60)
    print("\nSe compara: resultado de la función vs. resultado paso a paso")
    print("(mismo valor = la fórmula en el código es correcta).\n")

    print("1. PV Glasses / RefCells (SR = 100 %)")
    verify_u_ratio_sr_photodiodes()
    print("")

    print("2. DustIQ")
    verify_u_sr_dustiq()
    print("")

    print("3. Soiling Kit (cociente Isc sucio / Isc limpio)")
    verify_u_sr_ratio_scale_only()
    print("")

    print("4. Coherencia con datos reales (PV Glasses SR 98–100 %)")
    verify_consistency_with_real_data()
    print("")

    print("=" * 60)
    print("Todas las comprobaciones pasaron.")
    print("=" * 60)


if __name__ == "__main__":
    run_all()
