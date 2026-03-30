"""
Propagación de incertidumbres (GUM).

Modelo aditivo + escala para sensores:
  u(x)² = u_add² + (u_scale * x)²

Propagación para Δm (independencia m_soiled, m_clean):
  u(Δm)² = u(m_soiled)² + u(m_clean)²
"""

import numpy as np


def u_sensor(x, u_add, u_scale):
    """
    Incertidumbre estándar (k=1) de una magnitud con modelo aditivo + escala.

    u(x)² = u_add² + (u_scale * x)²

    Parámetros
    ----------
    x : float o array
        Valor(es) de la magnitud (mismas unidades que u_add).
    u_add : float
        Incertidumbre estándar aditiva (k=1), mismas unidades que x.
    u_scale : float
        Incertidumbre de escala (k=1), adimensional (ej. 0.01 = 1%).

    Returns
    -------
    float o array
        u(x) en las mismas unidades que x.
    """
    x = np.asarray(x, dtype=float)
    return np.sqrt(u_add ** 2 + (u_scale * x) ** 2)


def u_delta_m(u_m_soiled, u_m_clean):
    """
    Incertidumbre estándar de Δm = m_soiled - m_clean (masas independientes).

    u(Δm)² = u(m_soiled)² + u(m_clean)²

    Parámetros
    ----------
    u_m_soiled, u_m_clean : float o array
        Incertidumbres estándar (k=1) de cada pesada, mismas unidades.

    Returns
    -------
    float o array
        u(Δm) en las mismas unidades.
    """
    u_m_soiled = np.asarray(u_m_soiled, dtype=float)
    u_m_clean = np.asarray(u_m_clean, dtype=float)
    return np.sqrt(u_m_soiled ** 2 + u_m_clean ** 2)


def u_expanded(u_std, k=2):
    """Incertidumbre expandida U = k * u (p. ej. k=2 → ~95 %)."""
    return k * np.asarray(u_std, dtype=float)


def u_ratio_sr_photodiodes(sr_pct, u_add_w_m2, u_scale, e_ref_w_m2=1000.0, k=2):
    """
    Incertidumbre estándar u_c(SR) e expandida U(SR) para SR = 100 × E_sucio/E_ref,
    con E en W/m² y u(E)² = u_add² + (u_scale×E)² por canal (fotoceldas independientes).

    Parámetros
    ----------
    sr_pct : array-like
        SR en % (0–100).
    u_add_w_m2 : float
        Incertidumbre estándar aditiva (k=1) en W/m².
    u_scale : float
        Incertidumbre de escala (k=1), adimensional.
    e_ref_w_m2 : float
        Irradiancia de referencia típica (W/m²) para evaluar u(E_ref)/E_ref.
    k : float
        Factor de cobertura para U.

    Returns
    -------
    u_c_pp : np.ndarray
        Incertidumbre combinada u_c(SR) en puntos porcentuales (pp).
    U_pp : np.ndarray
        Incertidumbre expandida U(SR) en pp.
    """
    sr = np.asarray(sr_pct, dtype=float)
    e_ref = e_ref_w_m2
    e_sucio = (sr / 100.0) * e_ref
    # u(E)/E para cada canal
    u_over_e_ref = np.sqrt((u_add_w_m2 / e_ref) ** 2 + u_scale ** 2)
    u_over_e_sucio = np.where(
        e_sucio > 1e-9,
        np.sqrt((u_add_w_m2 / e_sucio) ** 2 + u_scale ** 2),
        np.nan,
    )
    # (u(SR)/SR)² = (u(E_sucio)/E_sucio)² + (u(E_ref)/E_ref)²
    u_sr_rel = np.sqrt(u_over_e_sucio ** 2 + u_over_e_ref ** 2)
    # u_c(SR) en % = (u(SR)/SR)*SR → mismo valor numérico en pp
    u_c_pp = np.where(sr > 0, sr * u_sr_rel, np.nan)
    U_pp = k * u_c_pp
    return u_c_pp, U_pp


def u_sr_dustiq(sr_pct, u_add_pp, u_scale, k=2):
    """
    Incertidumbre SR para DustIQ: u(SR)² = u_add² + (u_scale×SR)² (SR en %).
    u_add_pp: incertidumbre aditiva en pp (k=1). u_scale: adimensional (ej. 0.005 = 0,5 %).
    Devuelve u_c(SR) y U(SR) en pp.
    """
    sr = np.asarray(sr_pct, dtype=float)
    u_c_pp = np.sqrt(u_add_pp ** 2 + (u_scale * sr) ** 2)
    u_c_pp = np.where(np.isfinite(sr), u_c_pp, np.nan)
    return u_c_pp, k * u_c_pp


def u_sr_ratio_scale_only(sr_pct, u_scale, k=2):
    """
    Incertidumbre SR para cociente de dos magnitudes con la misma u_scale (ej. Soiling Kit,
    PVStand, IV600 Isc). u(SR)/SR = sqrt(2)*u_scale → u_c(SR) en pp = SR * u_scale * sqrt(2).
    """
    sr = np.asarray(sr_pct, dtype=float)
    u_c_pp = np.where(sr > 0, sr * u_scale * np.sqrt(2.0), np.nan)
    return u_c_pp, k * u_c_pp


def u_sr_ratio_scale_and_temperature(sr_pct, u_scale, u_T_c, T_typical_c, coef_per_c, k=2):
    """
    Incertidumbre SR para cociente con corrección por temperatura (IEC 60891).
    SR = 100 × (X_s/(1+coef*(T_s-25))) / (X_r/(1+coef*(T_r-25))).
    Combina: (1) escala en ambos canales → u_rel = sqrt(2)*u_scale,
             (2) PT100 en ambos canales → u_rel_T = sqrt(2) * |coef|/(1+coef*(T_typ-25)) * u_T_c.
    u_T_c: incertidumbre estándar de T en °C (k=1). coef_per_c: α_Isc o β_Pmax (/°C).
    """
    sr = np.asarray(sr_pct, dtype=float)
    denom = 1.0 + coef_per_c * (T_typical_c - 25.0)
    if abs(denom) < 1e-9:
        u_rel_t = 0.0
    else:
        u_rel_t = np.sqrt(2.0) * (abs(coef_per_c) / abs(denom)) * u_T_c
    u_rel_scale = np.sqrt(2.0) * u_scale
    u_sr_rel = np.sqrt(u_rel_scale ** 2 + u_rel_t ** 2)
    u_c_pp = np.where(sr > 0, sr * u_sr_rel, np.nan)
    return u_c_pp, k * u_c_pp
