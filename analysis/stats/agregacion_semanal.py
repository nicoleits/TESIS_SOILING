"""
Agregación semanal de SR (Q25) para todos los instrumentos + análisis de dispersión.

Para cada instrumento se toma la columna SR principal, se agrupa por semana ISO
(lunes–domingo) y se calcula el percentil 25 (Q25). Sobre esa serie semanal se
realiza un análisis de dispersión: std, CV, rango, percentiles entre semanas.

Salidas en analysis/stats/:
  - sr_semanal_q25.csv        : SR Q25 por semana e instrumento (formato ancho)
  - sr_semanal_q25_largo.csv  : mismo dato en formato largo
  - dispersion_semanal.csv    : estadísticos de dispersión entre semanas por instrumento
  - sr_semanal_q25.png        : gráfico de series semanales
  - dispersion_semanal.png    : boxplot de dispersión entre instrumentos

Uso (desde TESIS_SOILING):
  python -m analysis.stats.agregacion_semanal
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

# ---------------------------------------------------------------------------
# Configuración: (nombre_display, ruta_csv, columna_SR)
# ---------------------------------------------------------------------------
def _build_config(sr_dir):
    return [
        ("Soiling Kit",     os.path.join(sr_dir, "soilingkit_sr.csv"),       "SR"),
        ("DustIQ",          os.path.join(sr_dir, "dustiq_sr.csv"),            "SR"),
        ("RefCells",        os.path.join(sr_dir, "refcells_sr.csv"),          "SR"),
        # PV Glasses excluido: fórmula pendiente de validación rigurosa
        ("PVStand",         os.path.join(sr_dir, "pvstand_sr.csv"),           "SR_Pmax"),
        ("PVStand corr",    os.path.join(sr_dir, "pvstand_sr_corr.csv"),      "SR_Pmax_corr"),
        ("IV600",           os.path.join(sr_dir, "iv600_sr.csv"),             "SR_Pmax_434"),
        ("IV600 corr",      os.path.join(sr_dir, "iv600_sr_corr.csv"),        "SR_Pmax_corr_434"),
    ]


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def cargar_sr_diario(ruta, col_sr):
    """Carga el CSV de SR, devuelve Serie indexada por fecha con los valores de col_sr.
    Mantiene todos los registros diarios sin deduplicar para poder calcular std intrasemanal.
    """
    if not os.path.isfile(ruta):
        return None
    df = pd.read_csv(ruta, parse_dates=[0])
    tc = _get_time_col(df)
    if not tc or col_sr not in df.columns:
        return None
    df[tc] = pd.to_datetime(df[tc], utc=True)
    df = df.dropna(subset=[col_sr])
    df = df[df[col_sr] >= 80.0]  # respetar filtro outliers
    df["fecha"] = df[tc].dt.date
    # Un valor por día (tomar el primero si hubiera duplicados)
    df = df.drop_duplicates("fecha")
    serie = df.set_index("fecha")[col_sr]
    return serie


def agregar_semanal_q25(serie, nombre):
    """Agrupa por semana ISO y calcula Q25. Devuelve Serie indexada por semana."""
    if serie is None or serie.empty:
        return None
    idx = pd.to_datetime(pd.Series(serie.index.astype(str)))
    s = pd.Series(serie.values, index=pd.DatetimeIndex(idx))
    semanal = s.resample("W-MON", label="left", closed="left").quantile(0.25)
    semanal = semanal.dropna()
    semanal.name = nombre
    return semanal


def agregar_semanal_q25_y_std(serie, nombre):
    """Agrupa por semana ISO; devuelve (serie_q25, serie_std, serie_n)."""
    if serie is None or serie.empty:
        return None, None, None
    idx = pd.to_datetime(pd.Series(serie.index.astype(str)))
    s = pd.Series(serie.values, index=pd.DatetimeIndex(idx))
    resamp = s.resample("W-MON", label="left", closed="left")
    q25 = resamp.quantile(0.25).dropna()
    std = resamp.std().reindex(q25.index)
    n   = resamp.count().reindex(q25.index)
    q25.name = nombre
    return q25, std, n


def dispersion_entre_semanas(serie_semanal, nombre):
    """Estadísticos de dispersión sobre la serie semanal Q25."""
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


def grafico_series_semanales(df_ancho, out_path):
    """Gráfico de líneas: SR Q25 semanal por instrumento (todos superpuestos)."""
    fig, ax = plt.subplots(figsize=(14, 6))
    for col in df_ancho.columns:
        s = df_ancho[col].dropna()
        ax.plot(s.index, s.values, ".-", label=col, alpha=0.85, linewidth=1.2)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Semana (inicio lunes)")
    ax.set_ylabel("SR Q25 semanal (%)")
    ax.set_title("Soiling Ratio — Agregación semanal Q25 por instrumento")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=80)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico series semanales: %s", out_path)


def grafico_series_con_barras_error(datos_por_instrumento, out_path):
    """
    Un subplot por instrumento. Cada subplot muestra:
      - Línea con el Q25 semanal
      - Barras de error en T (±1 std de los valores diarios dentro de la semana)
      - Área sombreada (Q25 ± std)
    datos_por_instrumento: dict  nombre -> (q25, std, n)  — Series indexadas por semana
    """
    nombres = list(datos_por_instrumento.keys())
    n_inst = len(nombres)
    ncols = 2
    nrows = (n_inst + 1) // ncols
    colors = plt.cm.tab10.colors

    # Calcular límites Y globales considerando Q25 ± std de todos los instrumentos
    all_lower, all_upper = [], []
    for nombre in nombres:
        q25, std, _ = datos_por_instrumento[nombre]
        errs = std.fillna(0).values
        all_lower.append((q25.values - errs).min())
        all_upper.append((q25.values + errs).max())
    y_min = max(75, np.floor(min(all_lower)) - 2)
    y_max = min(103, np.ceil(max(all_upper)) + 1)

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3.5 * nrows), sharex=False)
    axes = axes.flatten()

    for i, nombre in enumerate(nombres):
        ax = axes[i]
        q25, std, n = datos_por_instrumento[nombre]
        color = colors[i % len(colors)]

        fechas = q25.index
        vals = q25.values
        errs = std.fillna(0).values

        # línea principal Q25
        ax.plot(fechas, vals, "o-", color=color, linewidth=1.4,
                markersize=4, label="Q25 semanal")
        # barras de error en T (±1 std)
        ax.errorbar(fechas, vals, yerr=errs, fmt="none",
                    ecolor=color, elinewidth=1.0, capsize=3, capthick=1.2, alpha=0.7)
        # área sombreada
        ax.fill_between(fechas, vals - errs, vals + errs,
                        alpha=0.15, color=color, label="±1 std diario")

        ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_title(nombre, fontsize=10, fontweight="bold")
        ax.set_ylabel("SR (%)", fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.tick_params(axis="x", labelsize=7, rotation=30)
        ax.tick_params(axis="y", labelsize=7)
        ax.grid(True, alpha=0.25)
        ax.set_ylim(y_min, y_max)  # eje Y estandarizado para todos los subplots
        ax.legend(fontsize=7, loc="lower left")

    # ocultar subplots vacíos
    for j in range(n_inst, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("SR Semanal Q25 ± Desviación estándar (barras T) — por instrumento",
                 fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico barras T: %s", out_path)


def grafico_boxplot_dispersion(df_largo, out_path):
    """Boxplot de la distribución semanal Q25 por instrumento."""
    instrumentos = df_largo["instrumento"].unique()
    data = [df_largo[df_largo["instrumento"] == inst]["sr_q25"].dropna().values
            for inst in instrumentos]

    fig, ax = plt.subplots(figsize=(12, 6))
    bp = ax.boxplot(data, tick_labels=instrumentos, patch_artist=True,
                    medianprops=dict(color="black", linewidth=1.5))
    colors = plt.cm.tab10.colors
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_ylabel("SR Q25 semanal (%)")
    ax.set_title("Dispersión del SR semanal (Q25) por instrumento")
    ax.set_ylim(bottom=80)
    plt.xticks(rotation=20, ha="right")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico boxplot dispersión: %s", out_path)


def run(sr_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    config = _build_config(sr_dir)

    series_semanales = {}
    datos_con_std = {}   # nombre -> (q25, std, n) para barras T
    disp_rows = []

    for nombre, ruta, col_sr in config:
        serie_diaria = cargar_sr_diario(ruta, col_sr)
        if serie_diaria is None or serie_diaria.empty:
            logger.info("Omite %s: sin datos.", nombre)
            continue
        semanal = agregar_semanal_q25(serie_diaria, nombre)
        if semanal is None or semanal.empty:
            logger.info("Omite %s: sin semanas.", nombre)
            continue
        series_semanales[nombre] = semanal
        q25, std, n = agregar_semanal_q25_y_std(serie_diaria, nombre)
        datos_con_std[nombre] = (q25, std, n)
        disp = dispersion_entre_semanas(semanal, nombre)
        if disp:
            disp_rows.append(disp)
        logger.info("%-15s: %d semanas, Q25 media=%.2f%%, std=%.2f%%, CV=%.2f%%",
                    nombre, disp["n_semanas"], disp["mean"], disp["std"], disp["cv_pct"])

    if not series_semanales:
        logger.error("No se encontraron datos SR.")
        return False

    # --- CSV formato ancho
    df_ancho = pd.DataFrame(series_semanales)
    df_ancho.index.name = "semana"
    df_ancho.to_csv(os.path.join(out_dir, "sr_semanal_q25.csv"))
    logger.info("CSV ancho: %s", os.path.join(out_dir, "sr_semanal_q25.csv"))

    # --- CSV formato largo
    largo_rows = []
    for nombre, s in series_semanales.items():
        for fecha, val in s.items():
            largo_rows.append({"semana": fecha, "instrumento": nombre, "sr_q25": val})
    df_largo = pd.DataFrame(largo_rows)
    df_largo.to_csv(os.path.join(out_dir, "sr_semanal_q25_largo.csv"), index=False)

    # --- CSV dispersión
    df_disp = pd.DataFrame(disp_rows).round(4)
    df_disp.to_csv(os.path.join(out_dir, "dispersion_semanal.csv"), index=False)
    logger.info("CSV dispersión: %s", os.path.join(out_dir, "dispersion_semanal.csv"))

    # --- Gráficos
    if MATPLOTLIB_AVAILABLE:
        grafico_series_semanales(df_ancho, os.path.join(out_dir, "sr_semanal_q25.png"))
        grafico_boxplot_dispersion(df_largo, os.path.join(out_dir, "dispersion_semanal.png"))
        grafico_series_con_barras_error(datos_con_std,
                                        os.path.join(out_dir, "sr_semanal_barras_t.png"))

    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sr_dir = os.path.join(project_root, "analysis", "sr")
    out_dir = os.path.join(project_root, "analysis", "stats")
    if len(sys.argv) > 1:
        sr_dir = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        out_dir = os.path.abspath(sys.argv[2])
    logger.info("SR dir: %s | Salida: %s", sr_dir, out_dir)
    ok = run(sr_dir, out_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
