"""
Incertidumbre de SR para RefCells, DustIQ, Soiling Kit, PVStand e IV600.

Cada metodología expone una función resumen_incertidumbre_sr_*(df, col_sr=...) que devuelve
el mismo dict que sr_pv_glasses: n_valido, u_c_mediana_pp, u_c_P25_pp, u_c_P75_pp,
U_mediana_pp, U_max_pp, fuente_dominante.
"""

import numpy as np
import pandas as pd

from . import constants
from .propagation import (
    u_ratio_sr_photodiodes,
    u_sr_dustiq,
    u_sr_ratio_scale_only,
    u_sr_ratio_scale_and_temperature,
)


def _resumen_from_uc_u(u_c_pp, U_pp, fuente_dominante):
    """Construye el dict de resumen a partir de arrays u_c_pp y U_pp (en pp)."""
    valid = np.isfinite(u_c_pp) & (u_c_pp > 0)
    u_c = u_c_pp[valid]
    U = U_pp[valid]
    if u_c.size == 0:
        return {
            "n_valido": 0,
            "u_c_mediana_pp": np.nan,
            "u_c_P25_pp": np.nan,
            "u_c_P75_pp": np.nan,
            "U_mediana_pp": np.nan,
            "U_max_pp": np.nan,
            "fuente_dominante": fuente_dominante,
        }
    return {
        "n_valido": int(valid.sum()),
        "u_c_mediana_pp": round(float(np.median(u_c)), 4),
        "u_c_P25_pp": round(float(np.percentile(u_c, 25)), 4),
        "u_c_P75_pp": round(float(np.percentile(u_c, 75)), 4),
        "U_mediana_pp": round(float(np.median(U)), 4),
        "U_max_pp": round(float(np.max(U)), 4),
        "fuente_dominante": fuente_dominante,
    }


# --- RefCells: mismas fotoceldas que PV Glasses, SR = 100×E_sucio/E_ref ---
def resumen_incertidumbre_sr_refcells(df, col_sr="SR"):
    u_add = constants.REFCELLS_U_ADD_W_M2
    u_scale = constants.REFCELLS_U_SCALE
    sr = pd.to_numeric(df[col_sr], errors="coerce").values
    u_c_pp, U_pp = u_ratio_sr_photodiodes(sr, u_add, u_scale, k=constants.K_COVERAGE)
    return _resumen_from_uc_u(
        u_c_pp, U_pp, fuente_dominante="escala (fotoceldas 2,5 % k=2)"
    )


# --- DustIQ: u(SR)² = u_add² + (u_scale×SR)², SR en % ---
def resumen_incertidumbre_sr_dustiq(df, col_sr="SR"):
    # u_add en pp: 0,05 % k=1 → 0.05 pp
    u_add_pp = constants.DUSTIQ_U_ADD * 100  # fracción → pp
    u_scale = constants.DUSTIQ_U_SCALE
    sr = pd.to_numeric(df[col_sr], errors="coerce").values
    u_c_pp, U_pp = u_sr_dustiq(sr, u_add_pp, u_scale, k=constants.K_COVERAGE)
    return _resumen_from_uc_u(
        u_c_pp, U_pp, fuente_dominante="aditiva 0,1 % + escala 1 % (k=2)"
    )


# --- Soiling Kit: SR = 100×Isc(p)/Isc(e), cociente con misma u_scale ---
def resumen_incertidumbre_sr_soilingkit(df, col_sr="SR"):
    u_scale = constants.SOILING_KIT_U_ISC_SCALE
    sr = pd.to_numeric(df[col_sr], errors="coerce").values
    u_c_pp, U_pp = u_sr_ratio_scale_only(sr, u_scale, k=constants.K_COVERAGE)
    return _resumen_from_uc_u(
        u_c_pp, U_pp, fuente_dominante="escala Isc 0,2 % (k=2)"
    )


def _u_T_pt100_c(T_typical_c):
    """Incertidumbre estándar de temperatura PT100 Clase A (k=1) en °C."""
    return (constants.PT100_TOLERANCE_ADD_C + constants.PT100_TOLERANCE_SCALE * abs(T_typical_c)) / (3 ** 0.5)


# --- PVStand: SR_Pmax_corr / SR_Isc_corr; cociente con escala + corrección T (IEC 60891, PT100) ---
def resumen_incertidumbre_sr_pvstand(df, col_sr="SR_Pmax"):
    if col_sr not in df.columns:
        col_sr = "SR"
    # Pmax: escala 0,4 % k=2 + contribución temperatura (β_Pmax)
    u_scale = constants.PVSTAND_U_PMAX_SCALE
    T_typ = getattr(constants, "PT100_T_TYPICAL_C", 35.0)
    u_T = _u_T_pt100_c(T_typ)
    sr = pd.to_numeric(df[col_sr], errors="coerce").values
    u_c_pp, U_pp = u_sr_ratio_scale_and_temperature(
        sr, u_scale, u_T, T_typ, constants.IEC60891_BETA_PMAX, k=constants.K_COVERAGE
    )
    return _resumen_from_uc_u(
        u_c_pp, U_pp, fuente_dominante="escala Pmax 0,4 % (k=2) + PT100 (corrección T)"
    )


def resumen_incertidumbre_sr_pvstand_isc(df, col_sr="SR_Isc"):
    """PVStand Isc: escala 0,2 % + PT100 (α_Isc)."""
    if col_sr not in df.columns:
        col_sr = "SR"
    u_scale = constants.PVSTAND_U_ISC_SCALE
    T_typ = getattr(constants, "PT100_T_TYPICAL_C", 35.0)
    u_T = _u_T_pt100_c(T_typ)
    sr = pd.to_numeric(df[col_sr], errors="coerce").values
    u_c_pp, U_pp = u_sr_ratio_scale_and_temperature(
        sr, u_scale, u_T, T_typ, constants.IEC60891_ALPHA_ISC, k=constants.K_COVERAGE
    )
    return _resumen_from_uc_u(
        u_c_pp, U_pp, fuente_dominante="escala Isc 0,2 % (k=2) + PT100 (corrección T)"
    )


# --- IV600: SR con corrección T; Isc (escala + PT100 α), Pmax (escala + PT100 β) ---
def resumen_incertidumbre_sr_iv600(df, col_sr="SR_Isc_434"):
    """IV600 Isc: escala 0,2 % + PT100 (α_Isc)."""
    if col_sr not in df.columns:
        col_sr = "SR"
    u_scale = constants.IV600_U_ISC_SCALE
    T_typ = getattr(constants, "PT100_T_TYPICAL_C", 35.0)
    u_T = _u_T_pt100_c(T_typ)
    sr = pd.to_numeric(df[col_sr], errors="coerce").values
    u_c_pp, U_pp = u_sr_ratio_scale_and_temperature(
        sr, u_scale, u_T, T_typ, constants.IEC60891_ALPHA_ISC, k=constants.K_COVERAGE
    )
    return _resumen_from_uc_u(
        u_c_pp, U_pp, fuente_dominante="escala Isc 0,2 % (k=2) + PT100 (corrección T)"
    )


def resumen_incertidumbre_sr_iv600_pmax(df, col_sr="SR_Pmax_corr_434"):
    """IV600 Pmax: escala 1 % (k=2) + PT100 (β_Pmax)."""
    if col_sr not in df.columns:
        col_sr = "SR"
    u_scale = constants.IV600_U_PMAX_SCALE
    T_typ = getattr(constants, "PT100_T_TYPICAL_C", 35.0)
    u_T = _u_T_pt100_c(T_typ)
    sr = pd.to_numeric(df[col_sr], errors="coerce").values
    u_c_pp, U_pp = u_sr_ratio_scale_and_temperature(
        sr, u_scale, u_T, T_typ, constants.IEC60891_BETA_PMAX, k=constants.K_COVERAGE
    )
    return _resumen_from_uc_u(
        u_c_pp, U_pp, fuente_dominante="escala Pmax 1 % (k=2) + PT100 (corrección T)"
    )


def U_pp_por_metodologia(metodologia, sr_pct):
    """
    Incertidumbre expandida U(SR) en pp para cada valor de SR (propagación, depende del valor).

    Parámetros
    ----------
    metodologia : str
        Nombre tal como en los gráficos: "Soiling Kit", "DustIQ", "RefCells",
        "PVStand Pmax", "PVStand Isc", "IV600 Pmax", "IV600 Isc", "PV Glasses".
    sr_pct : array-like
        SR en % (0–100), un valor por semana o por punto.

    Returns
    -------
    np.ndarray
        U(SR) en puntos porcentuales (pp), mismo tamaño que sr_pct.
    """
    sr = np.asarray(sr_pct, dtype=float)
    k = constants.K_COVERAGE
    T_typ = getattr(constants, "PT100_T_TYPICAL_C", 35.0)

    if metodologia == "Soiling Kit":
        _, U_pp = u_sr_ratio_scale_only(sr, constants.SOILING_KIT_U_ISC_SCALE, k=k)
    elif metodologia == "DustIQ":
        u_add_pp = constants.DUSTIQ_U_ADD * 100
        _, U_pp = u_sr_dustiq(sr, u_add_pp, constants.DUSTIQ_U_SCALE, k=k)
    elif metodologia == "RefCells":
        _, U_pp = u_ratio_sr_photodiodes(
            sr, constants.REFCELLS_U_ADD_W_M2, constants.REFCELLS_U_SCALE, k=k
        )
    elif metodologia == "PVStand Pmax":
        u_T = _u_T_pt100_c(T_typ)
        _, U_pp = u_sr_ratio_scale_and_temperature(
            sr, constants.PVSTAND_U_PMAX_SCALE, u_T, T_typ,
            constants.IEC60891_BETA_PMAX, k=k
        )
    elif metodologia == "PVStand Isc":
        u_T = _u_T_pt100_c(T_typ)
        _, U_pp = u_sr_ratio_scale_and_temperature(
            sr, constants.PVSTAND_U_ISC_SCALE, u_T, T_typ,
            constants.IEC60891_ALPHA_ISC, k=k
        )
    elif metodologia == "IV600 Pmax":
        u_T = _u_T_pt100_c(T_typ)
        _, U_pp = u_sr_ratio_scale_and_temperature(
            sr, constants.IV600_U_PMAX_SCALE, u_T, T_typ,
            constants.IEC60891_BETA_PMAX, k=k
        )
    elif metodologia == "IV600 Isc":
        u_T = _u_T_pt100_c(T_typ)
        _, U_pp = u_sr_ratio_scale_and_temperature(
            sr, constants.IV600_U_ISC_SCALE, u_T, T_typ,
            constants.IEC60891_ALPHA_ISC, k=k
        )
    elif metodologia == "PV Glasses":
        u_add = getattr(constants, "PV_GLASSES_U_ADD_W_M2", constants.REFCELLS_U_ADD_W_M2)
        u_scale = getattr(constants, "PV_GLASSES_U_SCALE", constants.REFCELLS_U_SCALE)
        _, U_pp = u_ratio_sr_photodiodes(sr, u_add, u_scale, k=k)
    else:
        # Fallback: constante 0,5 pp (como antes)
        U_pp = np.full_like(sr, 0.5, dtype=float)
    return np.where(np.isfinite(sr) & (sr > 0), U_pp, np.nan)
