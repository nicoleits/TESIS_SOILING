"""
Incertidumbre de SR para metodología PV Glasses (fotoceldas Si-V-10TC-T, mismas que RefCells).

SR = 100 × E_sucio/E_ref; u(E)² = u_add² + (u_scale×E)² por canal.
Salida: u_c(SR) y U(SR) en puntos porcentuales (pp) para comparar con variabilidad en pp.
"""

import logging
import os
import numpy as np
import pandas as pd

from . import constants
from .propagation import u_ratio_sr_photodiodes

logger = logging.getLogger(__name__)

# Columna de SR esperada en DataFrames (en %)
COL_SR_PCT = "sr_q25"


def add_uncertainty_sr_pv_glasses(df, col_sr=COL_SR_PCT, k=2):
    """
    Añade columnas u_c(SR) y U(SR) en puntos porcentuales (pp) al DataFrame.

    Parámetros
    ----------
    df : pandas.DataFrame
        Debe contener col_sr (SR en %).
    col_sr : str
        Nombre de la columna con SR en %.
    k : float
        Factor de cobertura para U (por defecto 2).

    Returns
    -------
    pandas.DataFrame
        Copia del DataFrame con columnas u_c_SR_pp y U_SR_pp.
    """
    if col_sr not in df.columns:
        logger.warning("Columna %s no encontrada; no se añaden incertidumbres SR.", col_sr)
        return df.copy()
    u_add = getattr(constants, "PV_GLASSES_U_ADD_W_M2", constants.REFCELLS_U_ADD_W_M2)
    u_scale = getattr(constants, "PV_GLASSES_U_SCALE", constants.REFCELLS_U_SCALE)
    sr = pd.to_numeric(df[col_sr], errors="coerce")
    u_c_pp, U_pp = u_ratio_sr_photodiodes(sr.values, u_add, u_scale, k=k)
    out = df.copy()
    out["u_c_SR_pp"] = u_c_pp
    out["U_SR_pp"] = U_pp
    return out


def resumen_incertidumbre_sr_pv_glasses(df, col_sr=COL_SR_PCT):
    """
    Calcula resumen de incertidumbre SR para PV Glasses: n, mediana/P25–P75/máx de u_c y U (pp),
    y fuente dominante del presupuesto.

    Returns
    -------
    dict
        Claves: n_valido, u_c_mediana_pp, u_c_P25_pp, u_c_P75_pp, U_mediana_pp, U_max_pp, fuente_dominante.
    """
    out = add_uncertainty_sr_pv_glasses(df, col_sr=col_sr)
    valid = out["u_c_SR_pp"].notna()
    u_c = out.loc[valid, "u_c_SR_pp"]
    U = out.loc[valid, "U_SR_pp"]
    if u_c.empty:
        return {
            "n_valido": 0,
            "u_c_mediana_pp": np.nan,
            "u_c_P25_pp": np.nan,
            "u_c_P75_pp": np.nan,
            "U_mediana_pp": np.nan,
            "U_max_pp": np.nan,
            "fuente_dominante": "—",
        }
    # Fuente dominante: en fotoceldas RefCells/PV Glasses, escala 2,5 % (k=2) domina sobre aditiva 5 W/m²
    fuente_dominante = "escala (fotoceldas 2,5 % k=2)"
    return {
        "n_valido": int(valid.sum()),
        "u_c_mediana_pp": round(u_c.median(), 4),
        "u_c_P25_pp": round(u_c.quantile(0.25), 4),
        "u_c_P75_pp": round(u_c.quantile(0.75), 4),
        "U_mediana_pp": round(U.median(), 4),
        "U_max_pp": round(U.max(), 4),
        "fuente_dominante": fuente_dominante,
    }


def run(csv_path, out_path=None, col_sr=COL_SR_PCT):
    """
    Lee CSV con columna SR (%), añade u_c_SR_pp y U_SR_pp y guarda.
    Si out_path es None, sobrescribe el archivo de entrada.
    """
    df = pd.read_csv(csv_path)
    df = add_uncertainty_sr_pv_glasses(df, col_sr=col_sr)
    dest = out_path if out_path is not None else csv_path
    df.to_csv(dest, index=False)
    logger.info("Incertidumbres SR (PV Glasses) añadidas: %s", dest)
    return dest
