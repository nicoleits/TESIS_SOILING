"""
PVStand: SR con corrección de temperatura (IEC 60891).

Lee pvstand_aligned_solar_noon.csv y temperatura_aligned_solar_noon.csv,
aplica corrección a 25 °C (α_Isc, β_Pmax) y calcula SR_Pmax_corr y SR_Isc_corr.
Genera pvstand_sr_corr.csv y pvstand_sr_corr.png (incluye también SR sin corregir para comparar).

Temperaturas: 1TE416(C) = módulo sucio (440), 1TE418(C) = referencia (439).
Fórmulas: Pmax_corr = Pmax / (1 + β×(T−25)), Isc_corr = Isc / (1 + α×(T−25)).

Uso (desde TESIS_SOILING):
  python -m analysis.sr.calcular_sr_pvstand_corr
  python -m analysis.sr.calcular_sr_pvstand_corr [data_dir] [output_dir]
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

# PVStand: 439 = ref (perc2fixed), 440 = sucio (perc1fixed)
PVSTAND_MODULO_439_REF = "perc2fixed"
PVSTAND_MODULO_440_SUCIO = "perc1fixed"
UMBRAL_PMAX_FALLA_W = 10
# IEC 60891: T_ref = 25 °C
T_REF_C = 25.0
ALPHA_ISC = 0.0004   # /°C
BETA_PMAX = -0.0036  # /°C
UMBRAL_SR_MIN = 80.0  # SR < este valor se considera outlier y se descarta (NaN)
# Temperatura: columnas en temperatura_aligned_solar_noon.csv
COL_T_SUCIO = "1TE416(C)"   # 440
COL_T_REF = "1TE418(C)"     # 439
# Tolerancia para alinear timestamp pvstand con temperatura (minutos)
TOLERANCIA_MERGE_TEMP_MIN = 15


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def run_pvstand_sr_corr(data_dir, output_dir):
    """
    Carga pvstand y temperatura alineados, aplica corrección de temperatura y guarda
    pvstand_sr_corr.csv y pvstand_sr_corr.png.
    """
    data_dir = os.path.abspath(data_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    time_col = "timestamp"

    pv_path = os.path.join(data_dir, "pvstand", "pvstand_aligned_solar_noon.csv")
    temp_path = os.path.join(data_dir, "temperatura", "temperatura_aligned_solar_noon.csv")
    if not os.path.isfile(pv_path):
        logger.error("No existe %s", pv_path)
        return None
    if not os.path.isfile(temp_path):
        logger.error("No existe %s", temp_path)
        return None

    df_pv = pd.read_csv(pv_path)
    df_pv[time_col] = pd.to_datetime(df_pv[time_col])
    df_temp = pd.read_csv(temp_path)
    df_temp[time_col] = pd.to_datetime(df_temp[time_col])
    if COL_T_SUCIO not in df_temp.columns or COL_T_REF not in df_temp.columns:
        logger.error("Temperatura debe tener columnas %s y %s", COL_T_SUCIO, COL_T_REF)
        return None

    # Tabla 439 y 440 por timestamp (como en sr_pvstand)
    ref = df_pv[df_pv["module"] == PVSTAND_MODULO_439_REF][[time_col, "pmax", "imax"]].drop_duplicates(time_col)
    sucio = df_pv[df_pv["module"] == PVSTAND_MODULO_440_SUCIO][[time_col, "pmax", "imax"]].drop_duplicates(time_col)
    ref = ref.rename(columns={"pmax": "pmax439", "imax": "imax439"})
    sucio = sucio.rename(columns={"pmax": "pmax440", "imax": "imax440"})
    out = ref.merge(sucio, on=time_col, how="inner")

    # Unir temperatura (merge_asof: mismo día / más cercano dentro de tolerancia)
    df_temp = df_temp.sort_values(time_col)
    out = out.sort_values(time_col)
    out = pd.merge_asof(
        out,
        df_temp[[time_col, COL_T_REF, COL_T_SUCIO]].rename(columns={COL_T_REF: "T439", COL_T_SUCIO: "T440"}),
        on=time_col,
        direction="nearest",
        tolerance=pd.Timedelta(minutes=TOLERANCIA_MERGE_TEMP_MIN),
    )

    # Filtro falla: Pmax < 10 W
    mask_ok = (out["pmax439"] >= UMBRAL_PMAX_FALLA_W) & (out["pmax440"] >= UMBRAL_PMAX_FALLA_W)

    # SR sin corrección
    out["SR_Pmax"] = np.where(
        mask_ok & (out["pmax439"].abs() > 1e-9),
        100.0 * out["pmax440"] / out["pmax439"],
        np.nan,
    )
    out["SR_Isc"] = np.where(
        mask_ok & (out["imax439"].abs() > 1e-9),
        100.0 * out["imax440"] / out["imax439"],
        np.nan,
    )

    # Corrección a 25 °C (IEC 60891): Pmax_corr = Pmax / (1 + β*(T-25)), Isc_corr = Isc / (1 + α*(T-25))
    out["pmax439_corr"] = out["pmax439"] / (1.0 + BETA_PMAX * (out["T439"] - T_REF_C))
    out["pmax440_corr"] = out["pmax440"] / (1.0 + BETA_PMAX * (out["T440"] - T_REF_C))
    out["imax439_corr"] = out["imax439"] / (1.0 + ALPHA_ISC * (out["T439"] - T_REF_C))
    out["imax440_corr"] = out["imax440"] / (1.0 + ALPHA_ISC * (out["T440"] - T_REF_C))

    out["SR_Pmax_corr"] = np.where(
        mask_ok & (out["pmax439_corr"].abs() > 1e-9),
        100.0 * out["pmax440_corr"] / out["pmax439_corr"],
        np.nan,
    )
    out["SR_Isc_corr"] = np.where(
        mask_ok & (out["imax439_corr"].abs() > 1e-9),
        100.0 * out["imax440_corr"] / out["imax439_corr"],
        np.nan,
    )

    # Filtro outliers: SR < UMBRAL_SR_MIN → NaN en todas las columnas SR
    sr_cols = ["SR_Pmax", "SR_Isc", "SR_Pmax_corr", "SR_Isc_corr"]
    for col_sr in sr_cols:
        if col_sr in out.columns:
            mask_outlier = out[col_sr] < UMBRAL_SR_MIN
            if mask_outlier.any():
                out.loc[mask_outlier, sr_cols] = np.nan
                logger.info("   Filtro outliers %s < %.0f%%: %d filas descartadas.", col_sr, UMBRAL_SR_MIN, mask_outlier.sum())
                break  # un solo módulo puede afectar a todos, evitar doble conteo

    # Columnas de salida (sin columnas auxiliares)
    cols_out = [time_col, "SR_Pmax", "SR_Isc", "SR_Pmax_corr", "SR_Isc_corr", "T439", "T440"]
    out = out[[c for c in cols_out if c in out.columns]]

    out_csv = os.path.join(output_dir, "pvstand_sr_corr.csv")
    out.to_csv(out_csv, index=False)
    logger.info("pvstand_sr_corr: %s (%d filas)", out_csv, len(out))

    if MATPLOTLIB_AVAILABLE:
        try:
            plt.figure()
            out_plot = out.copy()
            out_plot[time_col] = pd.to_datetime(out_plot[time_col])
            out_plot = out_plot.sort_values(time_col)
            plt.plot(out_plot[time_col], out_plot["SR_Pmax_corr"], ".-", label="SR_Pmax_corr (T→25°C)", alpha=0.9)
            plt.plot(out_plot[time_col], out_plot["SR_Isc_corr"], ".-", label="SR_Isc_corr (T→25°C)", alpha=0.9)
            plt.axhline(100, color="gray", linestyle="--", alpha=0.7)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            plt.gcf().autofmt_xdate()
            plt.xlabel("Fecha")
            plt.ylabel("SR (%)")
            plt.title("PVStand - Soiling Ratio (corregido a 25 °C)")
            plt.ylim(bottom=0)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            path_png = os.path.join(output_dir, "pvstand_sr_corr.png")
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
    run_pvstand_sr_corr(data_dir, output_dir)


if __name__ == "__main__":
    main()
