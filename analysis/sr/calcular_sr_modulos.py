"""
Calcula un indicador tipo Soiling Ratio (SR) para cada módulo ya filtrado/alineado.

Definiciones por módulo:
- soilingkit: SR = 100 × Isc(p) / Isc(e) (ya implementado en calcular_sr.py; se usa aligned).
- dustiq: SR = SR_C11_Avg (el sensor reporta ya un ratio en %).
- refcells: SR = 100 × min(1RC411, 1RC412) / max(...) (ratio entre las dos celdas).
- pv_glasses: SR por celda = 100 × R_FCi / REF; se guarda SR medio y por celda.
- pvstand: SR = 100 × (pmax_sucio / pmax_referencia); referencia = perc2 (limpio), sucio = perc1. Opcional: corrección T a 25 °C (IEC 60891).
- iv600: SR = 100 × pmp / pmp_439; 439 = referencia (limpio), 434 = sucio. Mismo timestamp.

Entrada: CSVs alineados en data/<modulo>/<modulo>_aligned_solar_noon.csv
Salida: analysis/sr/<modulo>_sr.csv (y opcionalmente gráfico).

Uso (desde TESIS_SOILING):
  python -m analysis.sr.calcular_sr_modulos
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

# IV600: 439 = referencia (limpio), 434 = sucio. Una fila por timestamp con SR_Pmax_434 y SR_Isc_434.
IV600_MODULO_REF = "1MD439"
IV600_MODULO_SUCIO = "1MD434"

# PVStand: 439 = referencia (limpio), 440 = sucio. En datos: perc2fixed = 439, perc1fixed = 440.
# SR_Pmax = 100 × Pmax440/Pmax439,  SR_Isc = 100 × Isc440/Isc439 (usamos imax como corriente).
PVSTAND_MODULO_439_REF = "perc2fixed"
PVSTAND_MODULO_440_SUCIO = "perc1fixed"
UMBRAL_PMAX_FALLA_PVSTAND = 10  # W; si Pmax439 o Pmax440 < 10 se considera falla y SR_Pmax/SR_Isc = NaN
UMBRAL_SR_MIN = 80.0             # SR < este valor se considera outlier y se descarta (NaN)
T_REF_C = 25.0
ALPHA_ISC_TIPICO = 0.0004
BETA_PMAX_TIPICO = -0.0036


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def sr_soilingkit(df):
    """SR = 100 × Isc(p) / Isc(e)."""
    if "Isc(e)" not in df.columns or "Isc(p)" not in df.columns:
        return None
    df = df.copy()
    df["SR"] = np.where(
        df["Isc(e)"] > 1e-9,
        100.0 * df["Isc(p)"] / df["Isc(e)"],
        np.nan,
    )
    return df


def sr_dustiq(df):
    """SR = SR_C11_Avg (ya en %)."""
    if "SR_C11_Avg" not in df.columns:
        return None
    df = df.copy()
    df["SR"] = df["SR_C11_Avg"].astype(float)
    return df


def sr_refcells(df):
    """SR = 100 × min(1RC411, 1RC412) / max(...)."""
    c1, c2 = "1RC411(w.m-2)", "1RC412(w.m-2)"
    if c1 not in df.columns or c2 not in df.columns:
        return None
    df = df.copy()
    mn = df[[c1, c2]].min(axis=1)
    mx = df[[c1, c2]].max(axis=1)
    df["SR"] = np.where(mx > 1e-9, 100.0 * mn / mx, np.nan)
    return df


def sr_pv_glasses(df):
    """
    PV Glasses: FC1 y FC2 = celdas limpias (referencia); FC3, FC4, FC5 = sucias.
    REF = (FC1 + FC2) / 2  →  coincide con la columna REF del CSV.
    SR_FCi = 100 × R_FCi_Avg / REF   (i = 3, 4, 5)
    SR = media de SR_FC3, SR_FC4, SR_FC5
    """
    ref_col = "REF"
    dirty_cells = ["R_FC3_Avg", "R_FC4_Avg", "R_FC5_Avg"]
    available = [c for c in dirty_cells if c in df.columns]
    if not available or ref_col not in df.columns:
        return None
    df = df.copy()
    sr_cols = []
    for c in available:
        col_sr = f"SR_{c.replace('_Avg', '')}"
        df[col_sr] = np.where(
            df[ref_col].abs() > 1e-9,
            100.0 * df[c] / df[ref_col],
            np.nan,
        )
        sr_cols.append(col_sr)
    df["SR"] = df[sr_cols].mean(axis=1)
    # Conservar también FC1 y FC2 como columnas de información
    return df


def sr_pvstand(df):
    """
    PVStand: 439 = referencia (limpio), 440 = sucio.
    SR_Pmax = 100 × Pmax440/Pmax439,  SR_Isc = 100 × Isc440/Isc439 (Isc ≈ imax en datos).
    Una fila por timestamp con columnas SR_Pmax y SR_Isc.
    """
    if "pmax" not in df.columns or "module" not in df.columns:
        return None
    time_col = _get_time_col(df)
    if time_col is None:
        return None
    col_isc = "imax" if "imax" in df.columns else None  # usar imax como corriente
    cols_sel = [time_col, "pmax"] + (["imax"] if col_isc else [])
    ref = df[df["module"] == PVSTAND_MODULO_439_REF][cols_sel].drop_duplicates(time_col)
    sucio = df[df["module"] == PVSTAND_MODULO_440_SUCIO][cols_sel].drop_duplicates(time_col)
    ref = ref.rename(columns={"pmax": "pmax439", **({"imax": "imax439"} if col_isc else {})})
    sucio = sucio.rename(columns={"pmax": "pmax440", **({"imax": "imax440"} if col_isc else {})})
    out = ref.merge(sucio, on=time_col, how="inner")
    # Filtro falla: Pmax < 10 W en 439 o 440 → SR = NaN (evita picos por sensores/equipo)
    mask_ok = (out["pmax439"] >= UMBRAL_PMAX_FALLA_PVSTAND) & (out["pmax440"] >= UMBRAL_PMAX_FALLA_PVSTAND)
    out["SR_Pmax"] = np.where(
        mask_ok & (out["pmax439"].abs() > 1e-9),
        100.0 * out["pmax440"] / out["pmax439"],
        np.nan,
    )
    if col_isc and "imax439" in out.columns and "imax440" in out.columns:
        out["SR_Isc"] = np.where(
            mask_ok & (out["imax439"].abs() > 1e-9),
            100.0 * out["imax440"] / out["imax439"],
            np.nan,
        )
    else:
        out["SR_Isc"] = np.nan
    out["SR"] = out["SR_Pmax"]  # compatibilidad
    out = out.drop(columns=[c for c in ["pmax439", "pmax440", "imax439", "imax440"] if c in out.columns], errors="ignore")
    return out


def sr_iv600(df):
    """
    IV600: 439 = ref (limpio), 434 = sucio. SR 434 vs 439.
    Una fila por timestamp con SR_Pmax_434, SR_Isc_434 y los valores de pmp/isc usados.
    Se excluye Unknown Module.
    """
    if "pmp" not in df.columns or "module" not in df.columns or "isc" not in df.columns:
        return None
    time_col = _get_time_col(df)
    if time_col is None:
        return None
    df = df.copy()
    df = df[df["module"] != "Unknown Module"].copy()
    ref = df[df["module"] == IV600_MODULO_REF][[time_col, "pmp", "isc"]].drop_duplicates(time_col)
    ref = ref.rename(columns={"pmp": "pmp439", "isc": "isc439"})
    m434 = df[df["module"] == "1MD434"][[time_col, "pmp", "isc"]].drop_duplicates(time_col)
    m434 = m434.rename(columns={"pmp": "pmp434", "isc": "isc434"})
    out = ref.merge(m434, on=time_col, how="outer")
    out["SR_Pmax_434"] = np.where(out["pmp439"].abs() > 1e-9, 100.0 * out["pmp434"] / out["pmp439"], np.nan)
    out["SR_Isc_434"] = np.where(out["isc439"].abs() > 1e-9, 100.0 * out["isc434"] / out["isc439"], np.nan)
    out["SR"] = out["SR_Pmax_434"]
    return out


MODULOS_SR = [
    ("soilingkit", "soilingkit_aligned_solar_noon.csv", sr_soilingkit, "SR"),
    ("dustiq", "dustiq_aligned_solar_noon.csv", sr_dustiq, "SR"),
    ("refcells", "refcells_aligned_solar_noon.csv", sr_refcells, "SR"),
    ("pv_glasses", "pv_glasses_aligned_solar_noon.csv", sr_pv_glasses, "SR"),
    ("pvstand", "pvstand_aligned_solar_noon.csv", sr_pvstand, "SR"),
    ("iv600", "iv600_aligned_solar_noon.csv", sr_iv600, "SR"),
]


def _grafico_sr_modulo(df, modulo, output_dir, time_col="timestamp"):
    """Gráfico SR vs tiempo para un módulo."""
    if not MATPLOTLIB_AVAILABLE or "SR" not in df.columns:
        return
    try:
        plt.figure()
        df_plot = df.copy()
        df_plot[time_col] = pd.to_datetime(df_plot[time_col])
        if modulo == "iv600" and "SR_Pmax_434" in df_plot.columns:
            df_plot = df_plot.sort_values(time_col)
            plt.plot(df_plot[time_col], df_plot["SR_Pmax_434"], ".-", label="434 SR_Pmax", alpha=0.8)
            plt.plot(df_plot[time_col], df_plot["SR_Isc_434"], ".-", label="434 SR_Isc", alpha=0.8)
            plt.legend()
        elif "SR_Pmax" in df_plot.columns and "SR_Isc" in df_plot.columns:
            df_plot = df_plot.sort_values(time_col)
            plt.plot(df_plot[time_col], df_plot["SR_Pmax"], ".-", label="SR_Pmax (100×Pmax440/Pmax439)", alpha=0.8)
            plt.plot(df_plot[time_col], df_plot["SR_Isc"], ".-", label="SR_Isc (100×Isc440/Isc439)", alpha=0.8)
            plt.legend()
        elif "module" in df_plot.columns:
            for mod in df_plot["module"].unique():
                sub = df_plot[df_plot["module"] == mod].sort_values(time_col)
                plt.plot(sub[time_col], sub["SR"], ".-", label=mod, alpha=0.8)
            plt.legend()
        else:
            df_plot = df_plot.sort_values(time_col)
            plt.plot(df_plot[time_col], df_plot["SR"], "*", markersize=4, label="SR")
        plt.axhline(100, color="gray", linestyle="--", alpha=0.7)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        plt.gcf().autofmt_xdate()
        plt.xlabel("Fecha")
        plt.ylabel("SR (%)")
        plt.title(f"Soiling Ratio - {modulo}")
        plt.ylim(bottom=0)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        path = os.path.join(output_dir, f"{modulo}_sr.png")
        plt.savefig(path, dpi=150)
        plt.close()
        logger.info("   Gráfico: %s", path)
    except Exception as e:
        logger.warning("   No se pudo generar gráfico: %s", e)


def run_sr_modulos(data_dir, output_dir):
    """
    Lee los CSVs alineados de cada módulo, calcula SR y escribe <modulo>_sr.csv en output_dir.
    """
    data_dir = os.path.abspath(data_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    time_col = "timestamp"
    resultados = []
    for modulo, filename, func_sr, col_sr in MODULOS_SR:
        csv_path = os.path.join(data_dir, modulo, filename)
        if not os.path.isfile(csv_path):
            logger.info("Omite %s: no existe %s", modulo, csv_path)
            continue
        df = pd.read_csv(csv_path)
        tc = _get_time_col(df)
        if tc is None:
            logger.warning("Omite %s: sin columna de tiempo.", modulo)
            continue
        df = func_sr(df)
        if df is None or "SR" not in df.columns:
            logger.warning("Omite %s: no se pudo calcular SR.", modulo)
            continue
        # Filtro outliers: SR < UMBRAL_SR_MIN → NaN en todas las columnas SR
        sr_cols = [c for c in df.columns if c.startswith("SR")]
        n_antes = df["SR"].notna().sum()
        mask_outlier = df["SR"] < UMBRAL_SR_MIN
        if mask_outlier.any():
            df.loc[mask_outlier, sr_cols] = np.nan
            logger.info("   Filtro outliers SR < %.0f%%: %d filas descartadas.", UMBRAL_SR_MIN, mask_outlier.sum())
        # Orden: timestamp, SR, resto
        cols = [tc, "SR"] + [c for c in df.columns if c not in (tc, "SR")]
        df = df[[c for c in cols if c in df.columns]]
        out_csv = os.path.join(output_dir, f"{modulo}_sr.csv")
        df.to_csv(out_csv, index=False)
        logger.info("%s: %s (%d filas)", modulo, out_csv, len(df))
        resultados.append((modulo, out_csv))
        if MATPLOTLIB_AVAILABLE:
            _grafico_sr_modulo(df, modulo, output_dir, time_col=tc)
    return resultados


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data")
    output_dir = os.path.join(project_root, "analysis", "sr")
    if len(sys.argv) > 1:
        data_dir = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        output_dir = os.path.abspath(sys.argv[2])
    logger.info("Data: %s | Salida: %s", data_dir, output_dir)
    run_sr_modulos(data_dir, output_dir)


if __name__ == "__main__":
    main()
