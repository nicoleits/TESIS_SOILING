"""
Incertidumbre de las diferencias de masa Δm y de la densidad superficial ρm (Flujo B, GUM).

- Δm: u(Δm)² = u(m_soiled)² + u(m_clean)²; U(Δm) = k·u(Δm) (k=2). Salida en mg.
- ρm = Δm/A (mg/cm²): propagación cociente (u(ρm)/ρm)² = (u(Δm)/Δm)² + (u(A)/A)²;
  u(A) desde regla milimetrada (constants.U_AREA_CM2).
"""

import os
import logging
import pandas as pd
import numpy as np

from . import constants
from .propagation import u_sensor, u_delta_m, u_expanded

logger = logging.getLogger(__name__)

# Columnas esperadas en el DataFrame de masas (nombres en español o inglés)
MASAS_COLS = {
    "A": ("Masa_A_Soiled_g", "Masa_A_Clean_g"),
    "B": ("Masa_B_Soiled_g", "Masa_B_Clean_g"),
    "C": ("Masa_C_Soiled_g", "Masa_C_Clean_g"),
}


def add_uncertainty_mass(df, u_add_g=None, u_scale=None, k=2):
    """
    Añade columnas de incertidumbre estándar u(Δm) y expandida U(Δm) por vidrio (A, B, C).

    Espera columnas Masa_*_Soiled_g y Masa_*_Clean_g. Genera u_Delta_m_*_mg y U_Delta_m_*_mg
    (en mg para ser coherente con Diferencia_Masa_*_mg).

    Parámetros
    ----------
    df : pandas.DataFrame
        Debe contener las columnas Masa_X_Soiled_g, Masa_X_Clean_g para X in (A, B, C).
    u_add_g : float, opcional
        Incertidumbre estándar aditiva de la balanza en g (k=1). Por defecto constants.BALANZA_U_ADD_G.
    u_scale : float, opcional
        Incertidumbre de escala (k=1). Por defecto constants.BALANZA_U_SCALE.
    k : int o float, opcional
        Factor de cobertura para U. Por defecto constants.K_COVERAGE (2).

    Returns
    -------
    pandas.DataFrame
        Copia del DataFrame con columnas añadidas u_Delta_m_A_mg, U_Delta_m_A_mg, etc.
    """
    if u_add_g is None:
        u_add_g = constants.BALANZA_U_ADD_G
    if u_scale is None:
        u_scale = constants.BALANZA_U_SCALE

    out = df.copy()
    for vidrio, (col_soiled, col_clean) in MASAS_COLS.items():
        if col_soiled not in out.columns or col_clean not in out.columns:
            logger.warning("Columnas %s / %s no encontradas; se omiten incertidumbres para vidrio %s.", col_soiled, col_clean, vidrio)
            continue

        m_soiled = pd.to_numeric(out[col_soiled], errors="coerce")
        m_clean = pd.to_numeric(out[col_clean], errors="coerce")

        u_m_soiled = u_sensor(m_soiled, u_add_g, u_scale)
        u_m_clean = u_sensor(m_clean, u_add_g, u_scale)
        u_dm_g = u_delta_m(u_m_soiled, u_m_clean)
        U_dm_g = u_expanded(u_dm_g, k=k)

        # Pasar a mg (1 g = 1000 mg) para las columnas de salida
        out[f"u_Delta_m_{vidrio}_mg"] = u_dm_g * 1000.0
        out[f"U_Delta_m_{vidrio}_mg"] = U_dm_g * 1000.0

    # Densidad superficial ρm = Δm/A (mg/cm²) e incertidumbre por propagación del cociente
    area_cm2 = getattr(constants, "AREA_VIDRIO_CM2", 12.0)
    u_area_cm2 = getattr(constants, "U_AREA_CM2", 0.289)
    for vidrio in ("A", "B", "C"):
        col_dm = f"Diferencia_Masa_{vidrio}_mg"
        col_u_dm = f"u_Delta_m_{vidrio}_mg"
        if col_dm not in out.columns or col_u_dm not in out.columns:
            continue
        delta_mg = pd.to_numeric(out[col_dm], errors="coerce")
        u_dm_mg = out[col_u_dm]
        rho = delta_mg / area_cm2
        # (u(ρm)/ρm)² = (u(Δm)/Δm)² + (u(A)/A)²; si Δm=0 o ρm=0 → NaN
        rel_dm = np.where(delta_mg > 0, u_dm_mg / delta_mg, np.nan)
        rel_A = u_area_cm2 / area_cm2
        u_rho_rel = np.sqrt(rel_dm.astype(float) ** 2 + rel_A ** 2)
        u_rho = np.where(rho > 0, rho * u_rho_rel, np.nan)
        out[f"rho_m_{vidrio}_mg_cm2"] = rho
        out[f"u_rho_m_{vidrio}_mg_cm2"] = u_rho
        out[f"U_rho_m_{vidrio}_mg_cm2"] = u_expanded(u_rho, k=k)

    return out


def run(csv_path, out_path=None, u_add_g=None, u_scale=None, k=2):
    """
    Lee un CSV de diferencias de masa, añade columnas u(Δm) y U(Δm) por vidrio y guarda.

    Espera columnas Masa_*_Soiled_g, Masa_*_Clean_g (y opcionalmente Diferencia_Masa_*_mg).
    Si out_path es None, sobrescribe el archivo de entrada.

    Parámetros
    ----------
    csv_path : str
        Ruta al CSV (p. ej. resultados_diferencias_masas.csv).
    out_path : str, opcional
        Ruta de salida. Si es None, se usa csv_path (sobrescritura).
    u_add_g, u_scale, k
        Igual que en add_uncertainty_mass.

    Returns
    -------
    str
        Ruta del archivo escrito.
    """
    df = pd.read_csv(csv_path)
    df = add_uncertainty_mass(df, u_add_g=u_add_g, u_scale=u_scale, k=k)
    dest = out_path if out_path is not None else csv_path
    df.to_csv(dest, index=False)
    logger.info("Incertidumbres de masa añadidas: %s", dest)
    return dest


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse
    p = argparse.ArgumentParser(description="Añadir u(Δm) y U(Δm) a CSV de diferencias de masa.")
    p.add_argument("csv", nargs="?", default=None, help="CSV de diferencias de masa.")
    p.add_argument("-o", "--out", default=None, help="CSV de salida (por defecto sobrescribe entrada).")
    args = p.parse_args()
    if args.csv and os.path.isfile(args.csv):
        run(args.csv, out_path=args.out)
    else:
        print("Uso: python -m TESIS_SOILING.analysis.uncertainty.mass <ruta_resultados_diferencias_masas.csv> [-o salida.csv]")
        print("O ejecutar desde pv_glasses_calendario (integración automática).")
