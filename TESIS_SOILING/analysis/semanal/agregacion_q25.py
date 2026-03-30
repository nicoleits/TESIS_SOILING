"""
Agregación semanal de SR con Cuantil 25 (Q25) por metodología.

Para cada metodología se lee el CSV de SR diario, se limita al periodo de análisis
(mismo que intercomparación Soiling Ratio) y se resamplea por semana ISO (lunes–domingo)
calculando el percentil 25 (Q25) de los valores de esa semana.

Salidas en analysis/semanal/:
  - <metodologia>_sr_semanal_q25.csv  : por metodología (columnas: semana, sr_q25)
  - sr_semanal_q25.csv                : todas las metodologías en formato ancho
  - sr_semanal_q25_largo.csv         : todas en formato largo (semana, instrumento, sr_q25)
  - dispersion_semanal.csv            : estadísticos descriptivos por instrumento
  - sr_semanal_q25_series.png         : gráfico series superpuestas
  - sr_semanal_q25_boxplot.png        : boxplot dispersión por instrumento
  - sr_semanal_q25_norm.png           : series normalizadas (t₀=100%)

Metodologías: Soiling Kit, DustIQ, RefCells, PVStand, PVStand corr, PVStand Isc, IV600, IV600 corr, IV600 Isc.
RefCells usa REFCELLS_FECHA_MAX como fecha máxima.

Uso (desde si_test con PYTHONPATH=TESIS_SOILING):
  python -m analysis.semanal.agregacion_q25
  python -m analysis.semanal.agregacion_q25 [sr_dir] [out_dir]
"""
import os
import sys
import re
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from analysis.plot_metodos import configure_matplotlib_for_thesis

try:
    import locale
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
    try:
        locale.setlocale(locale.LC_NUMERIC, "es_ES.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_NUMERIC, "es_ES")
        except locale.Error:
            pass
    configure_matplotlib_for_thesis()
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

SPANISH_MONTHS = ["ene", "feb", "mar", "abr", "may", "jun",
                  "jul", "ago", "sep", "oct", "nov", "dic"]


def _fmt_month_es(x, pos=None):
    dt = mdates.num2date(x)
    mes_idx = dt.month - 1
    mes = SPANISH_MONTHS[mes_idx] if 0 <= mes_idx < len(SPANISH_MONTHS) else dt.strftime("%b")
    return f"{mes} {dt.year}"

try:
    from analysis.config import PERIODO_ANALISIS_INICIO, PERIODO_ANALISIS_FIN, REFCELLS_FECHA_MAX
except ImportError:
    PERIODO_ANALISIS_INICIO = "2024-08-03"
    PERIODO_ANALISIS_FIN = "2025-08-04"
    REFCELLS_FECHA_MAX = "2025-05-20"

# IV600 (Pmax e Isc): no se normalizan a 100%; se mantienen en SR absoluto (%).
NO_NORMALIZAR_IV600 = {"IV600", "IV600 corr", "IV600 Isc"}

# ---------------------------------------------------------------------------
# Configuración: (nombre_display, ruta_csv relativa a sr_dir, columna_SR, fecha_max_override).
# fecha_max_override=None → usar PERIODO_ANALISIS_FIN.
# ---------------------------------------------------------------------------
def _build_config(sr_dir):
    return [
        ("Soiling Kit",   os.path.join(sr_dir, "soilingkit_sr.csv"),     "SR",                None),
        ("DustIQ",        os.path.join(sr_dir, "dustiq_sr.csv"),        "SR",                None),
        ("RefCells",      os.path.join(sr_dir, "refcells_sr.csv"),      "SR",                REFCELLS_FECHA_MAX),
        ("PVStand",       os.path.join(sr_dir, "pvstand_sr.csv"),       "SR_Pmax",           None),
        ("PVStand corr",  os.path.join(sr_dir, "pvstand_sr_corr.csv"),  "SR_Pmax_corr",      None),
        ("PVStand Isc",   os.path.join(sr_dir, "pvstand_sr_corr.csv"),  "SR_Isc_corr",       None),
        ("IV600",         os.path.join(sr_dir, "iv600_sr.csv"),         "SR_Pmax_434",       None),
        ("IV600 corr",    os.path.join(sr_dir, "iv600_sr_corr.csv"),     "SR_Pmax_corr_434",  None),
        ("IV600 Isc",     os.path.join(sr_dir, "iv600_sr_corr.csv"),     "SR_Isc_corr_434",   None),
    ]


def _nombre_a_slug(nombre):
    """Convierte nombre para display a nombre de archivo (sin espacios, minúsculas)."""
    s = nombre.lower().strip()
    s = re.sub(r"\s+", "_", s)
    return s


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def cargar_sr_diario(ruta, col_sr, fecha_min=None, fecha_max=None):
    """
    Carga el CSV de SR y devuelve Serie con índice datetime (fecha) y valores de col_sr.
    Limita al rango [fecha_min, fecha_max]. Filtra SR >= 80 y elimina duplicados por día.
    """
    if not os.path.isfile(ruta):
        return None
    df = pd.read_csv(ruta)
    tc = _get_time_col(df)
    if not tc or col_sr not in df.columns:
        return None
    df[tc] = pd.to_datetime(df[tc], utc=True)
    df = df.dropna(subset=[col_sr])
    df = df[df[col_sr] >= 80.0]
    df["fecha"] = df[tc].dt.date
    if fecha_min is not None:
        df = df[df["fecha"] >= pd.to_datetime(fecha_min).date()]
    if fecha_max is not None:
        df = df[df["fecha"] <= pd.to_datetime(fecha_max).date()]
    df = df.drop_duplicates("fecha")
    if df.empty:
        return None
    serie = df.set_index("fecha")[col_sr]
    serie.index = pd.DatetimeIndex(pd.to_datetime(serie.index))
    return serie


def resample_semanal_q25(serie):
    """
    Agrupa por semana ISO (lunes inicio) y calcula Q25.
    Devuelve Serie con índice = inicio de semana y valores = Q25.
    """
    if serie is None or serie.empty:
        return None
    semanal = serie.resample("W-MON", label="left", closed="left").quantile(0.25)
    semanal = semanal.dropna()
    return semanal


def resample_semanal_q25_y_std(serie):
    """Agrupa por semana ISO; devuelve (q25, std, n)."""
    if serie is None or serie.empty:
        return None, None, None
    resamp = serie.resample("W-MON", label="left", closed="left")
    q25 = resamp.quantile(0.25).dropna()
    std = resamp.std().reindex(q25.index)
    n = resamp.count().reindex(q25.index)
    return q25, std, n


def normalizar_desde_inicio(q25, std):
    """Normaliza Q25 y std al primer valor: q25_norm = 100 * q25 / q25(t0)."""
    if q25 is None or q25.dropna().empty:
        return None, None
    t0_val = q25.dropna().iloc[0]
    if abs(t0_val) < 1e-9:
        return None, None
    q25_norm = 100.0 * q25 / t0_val
    std_norm = 100.0 * std / t0_val if std is not None else pd.Series(0.0, index=q25.index)
    return q25_norm, std_norm


def dispersion_entre_semanas(serie_semanal, nombre):
    """Estadísticos descriptivos sobre la serie semanal Q25."""
    vals = serie_semanal.dropna()
    if len(vals) < 2:
        return None
    return {
        "instrumento": nombre,
        "n_semanas": len(vals),
        "mean": vals.mean(),
        "std": vals.std(),
        "cv_pct": 100.0 * vals.std() / vals.mean() if vals.mean() > 0 else np.nan,
        "min": vals.min(),
        "p05": vals.quantile(0.05),
        "p25": vals.quantile(0.25),
        "p50": vals.quantile(0.50),
        "p75": vals.quantile(0.75),
        "p95": vals.quantile(0.95),
        "max": vals.max(),
        "rango_p95_p05": vals.quantile(0.95) - vals.quantile(0.05),
    }


def _grafico_series_semanales(df_ancho, out_path):
    """Gráfico de líneas: SR Q25 semanal por instrumento (todos superpuestos)."""
    if not MATPLOTLIB_AVAILABLE:
        return
    fig, ax = plt.subplots(figsize=(14, 6))
    colors = ["#D32F2F", "#FF6F00", "#388E3C", "#1976D2", "#7B1FA2", "#C2185B", "#0097A7"]
    for i, col in enumerate(df_ancho.columns):
        s = df_ancho[col].dropna()
        ax.plot(s.index, s.values, ".-", label=col, alpha=0.85, linewidth=1.2, color=colors[i % len(colors)])
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Semana (inicio lunes)", fontsize=15)
    ax.set_ylabel("SR Q25 semanal (%)", fontsize=15)
    ax.set_title("Soiling Ratio — Agregación semanal Q25 por metodología", fontsize=16, pad=12)
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt_month_es))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.legend(loc="lower left", fontsize=13, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=80)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico series: %s", out_path)


def _grafico_boxplot_dispersion(df_largo, out_path):
    """Boxplot de la distribución del SR Q25 semanal por instrumento."""
    if not MATPLOTLIB_AVAILABLE:
        return
    instrumentos = df_largo["instrumento"].unique()
    data = [df_largo[df_largo["instrumento"] == inst]["sr_q25"].dropna().values for inst in instrumentos]
    fig, ax = plt.subplots(figsize=(12, 6))
    bp = ax.boxplot(data, tick_labels=instrumentos, patch_artist=True,
                    medianprops=dict(color="black", linewidth=1.5))
    colors = ["#D32F2F", "#FF6F00", "#388E3C", "#1976D2", "#7B1FA2", "#C2185B", "#0097A7"]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_ylabel("SR Q25 semanal (%)", fontsize=15)
    ax.set_title("Dispersión del SR semanal (Q25) por metodología", fontsize=16, pad=12)
    ax.set_ylim(bottom=80)
    plt.xticks(rotation=25, ha="right")
    ax.tick_params(axis="both", labelsize=13)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico boxplot: %s", out_path)


def _grafico_norm_superpuesto(datos_norm, out_path):
    """Todas las series normalizadas (t₀=100%) superpuestas."""
    if not MATPLOTLIB_AVAILABLE or not datos_norm:
        return
    fig, ax = plt.subplots(figsize=(14, 6))
    colors = ["#D32F2F", "#FF6F00", "#388E3C", "#1976D2", "#7B1FA2", "#C2185B", "#0097A7"]
    for i, (nombre, (q25_n, _)) in enumerate(datos_norm.items()):
        ax.plot(q25_n.index, q25_n.values, "o-", color=colors[i % len(colors)],
                linewidth=1.2, markersize=3, label=nombre, alpha=0.85)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6)
    ax.set_xlabel("Semana (inicio lunes)", fontsize=15)
    ax.set_ylabel("SR (%)", fontsize=15)
    ax.set_title("SR Semanal Q25 (t₀=100% norm.; IV600 Pmax/Isc valor absoluto)", fontsize=16, pad=12)
    ax.xaxis.set_major_formatter(FuncFormatter(_fmt_month_es))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.legend(loc="lower left", fontsize=13, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico normalizado: %s", out_path)


def run(sr_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    config = _build_config(sr_dir)
    series_semanales = {}
    datos_norm = {}
    disp_rows = []

    for nombre, ruta, col_sr, fecha_max_override in config:
        fecha_max = fecha_max_override if fecha_max_override is not None else PERIODO_ANALISIS_FIN
        serie_diaria = cargar_sr_diario(ruta, col_sr, fecha_min=PERIODO_ANALISIS_INICIO, fecha_max=fecha_max)
        if serie_diaria is None or serie_diaria.empty:
            logger.info("Omite %s: sin datos en periodo.", nombre)
            continue
        semanal = resample_semanal_q25(serie_diaria)
        if semanal is None or semanal.empty:
            logger.info("Omite %s: sin semanas con datos.", nombre)
            continue
        series_semanales[nombre] = semanal
        q25, std, _ = resample_semanal_q25_y_std(serie_diaria)
        if nombre in NO_NORMALIZAR_IV600:
            q25_n = q25.copy()
            std_n = std.copy() if std is not None else pd.Series(0.0, index=q25.index)
            datos_norm[nombre] = (q25_n, std_n)
        else:
            q25_n, std_n = normalizar_desde_inicio(q25, std)
            if q25_n is not None:
                datos_norm[nombre] = (q25_n, std_n)
        disp = dispersion_entre_semanas(semanal, nombre)
        if disp:
            disp_rows.append(disp)

        # Guardar CSV por metodología
        slug = _nombre_a_slug(nombre)
        df_one = pd.DataFrame({"semana": semanal.index, "sr_q25": semanal.values})
        path_one = os.path.join(out_dir, f"{slug}_sr_semanal_q25.csv")
        df_one.to_csv(path_one, index=False)
        logger.info("%s: %d semanas, media=%.2f%%, CV=%.2f%% → %s",
                    nombre, len(semanal), disp["mean"] if disp else 0, disp["cv_pct"] if disp else 0, path_one)

    if not series_semanales:
        logger.error("No se encontraron datos SR en el periodo.")
        return False

    # Formato ancho
    df_ancho = pd.DataFrame(series_semanales)
    df_ancho.index.name = "semana"
    df_ancho.to_csv(os.path.join(out_dir, "sr_semanal_q25.csv"))
    logger.info("CSV ancho: %s/sr_semanal_q25.csv", out_dir)

    # Formato largo
    largo_rows = []
    for nombre, s in series_semanales.items():
        for fecha, val in s.items():
            largo_rows.append({"semana": fecha, "instrumento": nombre, "sr_q25": val})
    df_largo = pd.DataFrame(largo_rows)
    df_largo.to_csv(os.path.join(out_dir, "sr_semanal_q25_largo.csv"), index=False)
    logger.info("CSV largo: %s/sr_semanal_q25_largo.csv", out_dir)

    # Dispersión por instrumento
    df_disp = pd.DataFrame(disp_rows).round(4)
    df_disp.to_csv(os.path.join(out_dir, "dispersion_semanal.csv"), index=False)
    logger.info("CSV dispersión: %s/dispersion_semanal.csv", out_dir)

    # Gráficos
    _grafico_series_semanales(df_ancho, os.path.join(out_dir, "sr_semanal_q25_series.png"))
    _grafico_boxplot_dispersion(df_largo, os.path.join(out_dir, "sr_semanal_q25_boxplot.png"))
    _grafico_norm_superpuesto(datos_norm, os.path.join(out_dir, "sr_semanal_q25_norm.png"))

    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sr_dir = os.path.join(project_root, "analysis", "sr")
    out_dir = os.path.join(project_root, "analysis", "semanal")
    if len(sys.argv) > 1:
        sr_dir = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        out_dir = os.path.abspath(sys.argv[2])
    logger.info("SR dir: %s | Salida: %s", sr_dir, out_dir)
    ok = run(sr_dir, out_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
