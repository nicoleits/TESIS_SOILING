"""
IV600: SR con corrección de temperatura (IEC 60891).

Lee iv600_aligned_solar_noon.csv y temperatura_aligned_solar_noon.csv.
439 = referencia (limpio), 434 = sucio. Asigna 1TE418(C) al módulo 439 y 1TE416(C) a 434.
Aplica corrección a 25 °C (α_Isc, β_Pmax) y calcula SR_corr = 100 × pmp_corr / pmp_439_corr.
Genera iv600_sr_corr.csv y iv600_sr_corr.png (solo SR corregido del módulo 434).

Uso (desde TESIS_SOILING):
  python -m analysis.sr.calcular_sr_iv600_corr
  python -m analysis.sr.calcular_sr_iv600_corr [data_dir] [output_dir]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# IV600: 439 = referencia (limpio), 434 = sucio
IV600_MODULO_REF = "1MD439"
IV600_MODULO_SUCIO = "1MD434"
# IEC 60891
T_REF_C = 25.0
ALPHA_ISC = 0.0004
BETA_PMAX = -0.0036
UMBRAL_SR_MIN = 80.0  # SR < este valor se considera outlier y se descarta (NaN)
# Temperatura: 1TE418 = ref (439), 1TE416 = sucio (434)
COL_T_REF = "1TE418(C)"
COL_T_SUCIO = "1TE416(C)"
TOLERANCIA_MERGE_TEMP_MIN = 15


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def run_iv600_sr_corr(data_dir, output_dir):
    """
    Carga IV600 y temperatura alineados, aplica corrección de temperatura y guarda
    iv600_sr_corr.csv y iv600_sr_corr.png.
    """
    data_dir = os.path.abspath(data_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    time_col = "timestamp"

    iv_path = os.path.join(data_dir, "iv600", "iv600_aligned_solar_noon.csv")
    temp_path = os.path.join(data_dir, "temperatura", "temperatura_aligned_solar_noon.csv")
    if not os.path.isfile(iv_path):
        logger.error("No existe %s", iv_path)
        return None
    if not os.path.isfile(temp_path):
        logger.error("No existe %s", temp_path)
        return None

    df = pd.read_csv(iv_path)
    df[time_col] = pd.to_datetime(df[time_col])
    df_temp = pd.read_csv(temp_path)
    df_temp[time_col] = pd.to_datetime(df_temp[time_col])
    if COL_T_REF not in df_temp.columns or COL_T_SUCIO not in df_temp.columns:
        logger.error("Temperatura debe tener columnas %s y %s", COL_T_REF, COL_T_SUCIO)
        return None

    # Unir temperatura (merge_asof)
    df_temp = df_temp.sort_values(time_col)
    df = df.sort_values(time_col)
    df = pd.merge_asof(
        df,
        df_temp[[time_col, COL_T_REF, COL_T_SUCIO]].rename(columns={COL_T_REF: "T_ref", COL_T_SUCIO: "T_sucio"}),
        on=time_col,
        direction="nearest",
        tolerance=pd.Timedelta(minutes=TOLERANCIA_MERGE_TEMP_MIN),
    )
    # T por módulo: 439 usa T_ref, resto usa T_sucio. Excluir Unknown Module.
    df = df[df["module"] != "Unknown Module"].copy()
    df["T_mod"] = np.where(df["module"] == IV600_MODULO_REF, df["T_ref"], df["T_sucio"])

    # Corrección a 25 °C por fila
    df["pmp_corr"] = df["pmp"] / (1.0 + BETA_PMAX * (df["T_mod"] - T_REF_C))
    df["isc_corr"] = df["isc"] / (1.0 + ALPHA_ISC * (df["T_mod"] - T_REF_C))

    # Ref 439 corregido por timestamp
    ref_corr = df[df["module"] == IV600_MODULO_REF][[time_col, "pmp_corr", "isc_corr"]].drop_duplicates(time_col)
    ref_corr = ref_corr.rename(columns={"pmp_corr": "pmp_439_corr", "isc_corr": "isc_439_corr"})

    # Una fila por timestamp: SR para 434 vs 439
    ref_corr = ref_corr.merge(
        df[df["module"] == "1MD434"][[time_col, "pmp_corr", "isc_corr"]].drop_duplicates(time_col).rename(columns={"pmp_corr": "pmp434_corr", "isc_corr": "isc434_corr"}),
        on=time_col, how="outer",
    )
    ref_corr["SR_Pmax_corr_434"] = np.where(ref_corr["pmp_439_corr"].abs() > 1e-9, 100.0 * ref_corr["pmp434_corr"] / ref_corr["pmp_439_corr"], np.nan)
    ref_corr["SR_Isc_corr_434"] = np.where(ref_corr["isc_439_corr"].abs() > 1e-9, 100.0 * ref_corr["isc434_corr"] / ref_corr["isc_439_corr"], np.nan)
    out = ref_corr[[time_col, "SR_Pmax_corr_434", "SR_Isc_corr_434"]].copy()

    # Filtro outliers: SR < UMBRAL_SR_MIN → NaN
    sr_cols = ["SR_Pmax_corr_434", "SR_Isc_corr_434"]
    for col_sr in sr_cols:
        mask_outlier = out[col_sr] < UMBRAL_SR_MIN
        if mask_outlier.any():
            out.loc[mask_outlier, sr_cols] = np.nan
            logger.info("   Filtro outliers %s < %.0f%%: %d filas descartadas.", col_sr, UMBRAL_SR_MIN, mask_outlier.sum())
            break

    out_csv = os.path.join(output_dir, "iv600_sr_corr.csv")
    out.to_csv(out_csv, index=False)
    logger.info("iv600_sr_corr: %s (%d filas)", out_csv, len(out))

    if MATPLOTLIB_AVAILABLE:
        try:
            plt.figure()
            out_plot = out.copy()
            out_plot[time_col] = pd.to_datetime(out_plot[time_col])
            out_plot = out_plot.sort_values(time_col)
            plt.plot(out_plot[time_col], out_plot["SR_Pmax_corr_434"], ".-", label="434 SR_Pmax_corr", alpha=0.8)
            plt.plot(out_plot[time_col], out_plot["SR_Isc_corr_434"], ".-", label="434 SR_Isc_corr", alpha=0.8)
            plt.axhline(100, color="gray", linestyle="--", alpha=0.7)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            plt.gcf().autofmt_xdate()
            plt.xlabel("Fecha")
            plt.ylabel("SR (%)")
            plt.title("IV600 - Soiling Ratio (corregido a 25 °C)")
            plt.ylim(bottom=0)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            path_png = os.path.join(output_dir, "iv600_sr_corr.png")
            plt.savefig(path_png, dpi=150)
            plt.close()
            logger.info("   Gráfico: %s", path_png)
        except Exception as e:
            logger.warning("No se pudo generar gráfico: %s", e)

    return out_csv


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data")
    output_dir = os.path.join(project_root, "analysis", "sr")
    if len(sys.argv) > 1:
        data_dir = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = os.path.abspath(sys.argv[2])
    logger.info("Data: %s | Salida: %s", data_dir, output_dir)
    run_iv600_sr_corr(data_dir, output_dir)


if __name__ == "__main__":
    main()
