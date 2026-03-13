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
    import locale
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    try:
        locale.setlocale(locale.LC_NUMERIC, "es_ES.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_NUMERIC, "es_ES")
        except locale.Error:
            pass
    plt.rcParams["axes.formatter.use_locale"] = True
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from analysis.config import PERIODO_ANALISIS_INICIO, PERIODO_ANALISIS_FIN, REFCELLS_FECHA_MAX
except ImportError:
    PERIODO_ANALISIS_INICIO = "2024-08-03"
    PERIODO_ANALISIS_FIN = "2025-08-04"
    REFCELLS_FECHA_MAX = "2025-05-20"

try:
    from analysis.uncertainty.sr_metodologias import U_pp_por_metodologia
except ImportError:
    U_pp_por_metodologia = None

# ---------------------------------------------------------------------------
# Configuración: (nombre_display, ruta_csv, columna_SR, fecha_max_override).
# fecha_max_override=None → usar PERIODO_ANALISIS_FIN.
# PVStand e IV600: solo series corregidas (T), con Pmax e Isc por separado; etiquetas sin "corr".
# ---------------------------------------------------------------------------
def _build_config(sr_dir):
    # PV Glasses se incorpora aparte por semana de exposición (ver _cargar_pv_glasses_por_semana_exposicion).
    return [
        ("Soiling Kit",   os.path.join(sr_dir, "soilingkit_sr.csv"),       "SR",                  None),
        ("DustIQ",        os.path.join(sr_dir, "dustiq_sr.csv"),            "SR",                  None),
        ("RefCells",      os.path.join(sr_dir, "refcells_sr.csv"),         "SR",                  REFCELLS_FECHA_MAX),
        ("PVStand Pmax",  os.path.join(sr_dir, "pvstand_sr_corr.csv"),     "SR_Pmax_corr",        None),
        ("PVStand Isc",   os.path.join(sr_dir, "pvstand_sr_corr.csv"),     "SR_Isc_corr",         None),
        ("IV600 Pmax",    os.path.join(sr_dir, "iv600_sr_corr.csv"),       "SR_Pmax_corr_434",    None),
        ("IV600 Isc",     os.path.join(sr_dir, "iv600_sr_corr.csv"),       "SR_Isc_corr_434",     None),
    ]


def _cargar_pv_glasses_por_semana_exposicion(project_root, reference_week_dates, col_sr="sr_q25"):
    """
    Carga PV Glasses desde pv_glasses_por_periodo.csv y agrupa por semana de exposición:
    semana_exp = round(dias_exposicion / 7). Para cada semana_exp (1, 2, 3, ...) calcula
    Q25(sr_q25) y std sobre las filas; asigna ese valor a la fecha reference_week_dates[semana_exp - 1].
    Así la "primera semana" del gráfico muestra todos los periodos que duraron ~1 semana, etc.

    reference_week_dates: lista o Index de fechas (inicio de semana, lunes) en orden, índice 0 = semana 1.
    Devuelve (q25_series, std_series, n_series) con index = fechas, o (None, None, None) si no hay datos.
    """
    path_pg = os.path.join(project_root, "analysis", "pv_glasses", "pv_glasses_por_periodo.csv")
    if not os.path.isfile(path_pg):
        return None, None, None
    df = pd.read_csv(path_pg)
    if col_sr not in df.columns or "dias_exposicion" not in df.columns:
        return None, None, None
    df = df.dropna(subset=[col_sr])
    df = df[df[col_sr] >= 80.0]
    if df.empty:
        return None, None, None
    ref_dates = pd.DatetimeIndex(reference_week_dates)
    df["semana_exp"] = (df["dias_exposicion"] / 7.0).round().clip(lower=1).astype(int)
    # Solo semanas que caben en el eje del gráfico
    max_semana = len(ref_dates)
    df = df[df["semana_exp"] <= max_semana]
    if df.empty:
        return None, None, None
    agg = df.groupby("semana_exp")[col_sr].agg([lambda x: x.quantile(0.25), "std", "count"])
    agg.columns = ["q25", "std", "n"]
    agg["std"] = agg["std"].fillna(0)
    # Mapear semana_exp (1, 2, ...) a fecha: ref_dates[semana_exp - 1]
    fechas = ref_dates[agg.index.values - 1]
    q25_series = pd.Series(agg["q25"].values, index=fechas, name="PV Glasses")
    std_series = pd.Series(agg["std"].values, index=fechas)
    n_series = pd.Series(agg["n"].values, index=fechas)
    return q25_series, std_series, n_series


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def cargar_sr_diario(ruta, col_sr, fecha_min=None, fecha_max=None):
    """Carga el CSV de SR, devuelve Serie indexada por fecha con los valores de col_sr.
    fecha_min, fecha_max: str 'YYYY-MM-DD' opcionales — limita datos al rango [fecha_min, fecha_max] inclusive.
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
    if fecha_min is not None:
        corte_ini = pd.to_datetime(fecha_min).date()
        antes = len(df)
        df = df[df["fecha"] >= corte_ini]
        logger.debug("   Corte fecha_min %s: %d → %d filas", fecha_min, antes, len(df))
    if fecha_max is not None:
        corte_fin = pd.to_datetime(fecha_max).date()
        antes = len(df)
        df = df[df["fecha"] <= corte_fin]
        logger.debug("   Corte fecha_max %s: %d → %d filas", fecha_max, antes, len(df))
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


def normalizar_desde_inicio(q25, std):
    """
    Normaliza q25 y std al primer valor válido de q25:
      q25_norm(t) = 100 × q25(t) / q25(t0)
      std_norm(t) = 100 × std(t) / q25(t0)
    Devuelve (q25_norm, std_norm) o (None, None) si no hay datos.
    """
    if q25 is None or q25.dropna().empty:
        return None, None
    t0_val = q25.dropna().iloc[0]
    if abs(t0_val) < 1e-9:
        return None, None
    q25_norm = 100.0 * q25 / t0_val
    std_norm = 100.0 * std / t0_val if std is not None else pd.Series(0.0, index=q25.index)
    return q25_norm, std_norm


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


def grafico_norm_superpuesto(datos_norm, out_path):
    """Todas las series normalizadas superpuestas en un único panel."""
    fig, ax = plt.subplots(figsize=(14, 6))
    colors = plt.cm.tab10.colors
    for i, (nombre, (q25_n, std_n)) in enumerate(datos_norm.items()):
        color = colors[i % len(colors)]
        errs = std_n.fillna(0).values
        ax.plot(q25_n.index, q25_n.values, "o-", color=color,
                linewidth=1.3, markersize=3, label=nombre, alpha=0.85)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Semana (inicio lunes)")
    ax.set_ylabel("SR normalizado (%)")
    ax.set_title("SR Semanal Q25 Normalizado (t₀ = 100%) — todos los instrumentos")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico norm superpuesto: %s", out_path)


def grafico_norm_superpuesto_sombra(datos_norm, out_path):
    """Todas las series normalizadas superpuestas con área sombreada ±1 std."""
    fig, ax = plt.subplots(figsize=(14, 6))
    colors = plt.cm.tab10.colors
    for i, (nombre, (q25_n, std_n)) in enumerate(datos_norm.items()):
        color = colors[i % len(colors)]
        errs = std_n.fillna(0).values
        ax.plot(q25_n.index, q25_n.values, "o-", color=color,
                linewidth=1.3, markersize=3, label=nombre, alpha=0.85)
        ax.fill_between(q25_n.index, q25_n.values - errs, q25_n.values + errs,
                        alpha=0.12, color=color)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("SR (%)")
    ax.set_title("SR Semanal Q25 Normalizado ± std (t₀ = 100%) — todos los instrumentos")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico norm superpuesto con sombra: %s", out_path)


def _cargar_incertidumbre_u_pp(project_root):
    """
    Carga U(SR) mediana [pp] por metodología desde resumen_incertidumbre_sr_por_metodologia.csv.
    Devuelve dict: nombre_display -> U_pp (float).
    Para series no en la tabla (PVStand Isc, IV600 Pmax) usa valores coherentes con la fórmula.
    """
    path_csv = os.path.join(project_root, "analysis", "uncertainty", "results",
                            "resumen_incertidumbre_sr_por_metodologia.csv")
    out = {}
    if os.path.isfile(path_csv):
        df = pd.read_csv(path_csv)
        for _, row in df.iterrows():
            met = row["Metodología"]
            u_med = row["U(SR) mediana [pp]"]
            if isinstance(u_med, (int, float)) and not np.isnan(u_med):
                out[met] = float(u_med)
    # Mapeo nombre del gráfico -> clave tabla (o valor fijo)
    # PVStand Pmax = PVStand; PVStand Isc y IV600 Pmax no están en tabla → uso IV600/Soiling Kit tipo
    if "PVStand" in out and "PVStand Pmax" not in out:
        out["PVStand Pmax"] = out["PVStand"]
    if "PVStand Isc" not in out:
        # Isc: misma escala que Soiling Kit / IV600 Isc → U ≈ 0,28 pp
        out["PVStand Isc"] = out.get("Soiling Kit", 0.28)
    if "IV600" in out:
        out["IV600 Isc"] = out["IV600"]
        if "IV600 Pmax" not in out:
            out["IV600 Pmax"] = out["IV600"]
    return out


def grafico_norm_superpuesto_incertidumbre(datos_norm, out_path, uncertainty_pp_series_by_name):
    """
    Mismo layout que grafico_norm_superpuesto_sombra pero la banda es ± U(SR) [pp]
    (incertidumbre expandida por propagación; depende del valor en cada semana).
    uncertainty_pp_series_by_name: dict nombre -> pd.Series con U(SR) en unidades del eje Y
    (normalizado, mismo índice que q25_n). Se dibuja primero la banda y luego la línea.
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    colors = plt.cm.tab10.colors
    y_min, y_max = 80, 105
    for i, (nombre, (q25_n, _)) in enumerate(datos_norm.items()):
        color = colors[i % len(colors)]
        u_series = uncertainty_pp_series_by_name.get(nombre)
        if u_series is not None and hasattr(u_series, "reindex"):
            errs = u_series.reindex(q25_n.index).fillna(0).values
        else:
            errs = np.full_like(q25_n.values, float(u_series) if u_series is not None else 0.5, dtype=float)
        low = np.clip(q25_n.values - errs, y_min, y_max)
        high = np.clip(q25_n.values + errs, y_min, y_max)
        ax.fill_between(q25_n.index, low, high, alpha=0.2, color=color, zorder=0)
        ax.plot(q25_n.index, q25_n.values, "o-", color=color,
                linewidth=1.5, markersize=4, label=nombre, alpha=0.9, zorder=2)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%", zorder=1)
    ax.set_xlabel("Fecha")
    ax.set_ylabel("SR (%)")
    ax.set_ylim(y_min, y_max)
    # pad: separación título–eje en puntos; +6 pt ≈ 2 mm para subir el título
    ax.set_title("SR Semanal Q25 Normalizado ± U(SR) (t₀ = 100%) — incertidumbre expandida [pp]", pad=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico norm superpuesto con incertidumbre: %s", out_path)


def grafico_norm_superpuesto_barras_incertidumbre(datos_norm, out_path, uncertainty_pp_series_by_name):
    """
    Mismas series que grafico_norm_superpuesto_incertidumbre pero con barras de error
    ± U(SR) [pp] en cada punto (incertidumbre por propagación, distinta por semana).
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    colors = plt.cm.tab10.colors
    for i, (nombre, (q25_n, _)) in enumerate(datos_norm.items()):
        color = colors[i % len(colors)]
        u_series = uncertainty_pp_series_by_name.get(nombre)
        if u_series is not None and hasattr(u_series, "reindex"):
            errs = u_series.reindex(q25_n.index).fillna(0).values
        else:
            errs = np.full_like(q25_n.values, float(u_series) if u_series is not None else 0.5, dtype=float)
        ax.plot(q25_n.index, q25_n.values, "o-", color=color,
                linewidth=1.3, markersize=3, label=nombre, alpha=0.85)
        ax.errorbar(q25_n.index, q25_n.values, yerr=errs, fmt="none",
                    ecolor=color, elinewidth=1.0, capsize=2.5, capthick=1.0, alpha=0.7)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("SR (%)")
    ax.set_title("SR Semanal Q25 Normalizado ± U(SR) (t₀ = 100%) — barras = incertidumbre expandida [pp]")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico norm superpuesto con barras de incertidumbre: %s", out_path)


def grafico_norm_barras_t(datos_norm, out_path):
    """Un subplot por instrumento con SR normalizado y barras T (±1 std escalado)."""
    nombres = list(datos_norm.keys())
    n_inst = len(nombres)
    ncols = 2
    nrows = (n_inst + 1) // ncols
    colors = plt.cm.tab10.colors

    # Límites Y globales sobre datos normalizados
    all_lower, all_upper = [], []
    for nombre, (q25_n, std_n) in datos_norm.items():
        errs = std_n.fillna(0).values
        all_lower.append((q25_n.values - errs).min())
        all_upper.append((q25_n.values + errs).max())
    y_min = max(75, np.floor(min(all_lower)) - 2)
    y_max = min(105, np.ceil(max(all_upper)) + 1)

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3.5 * nrows), sharex=False)
    axes = axes.flatten()

    for i, nombre in enumerate(nombres):
        ax = axes[i]
        q25_n, std_n = datos_norm[nombre]
        color = colors[i % len(colors)]
        fechas = q25_n.index
        vals = q25_n.values
        errs = std_n.fillna(0).values

        ax.plot(fechas, vals, "o-", color=color, linewidth=1.4, markersize=4, label="Q25 norm.")
        ax.errorbar(fechas, vals, yerr=errs, fmt="none",
                    ecolor=color, elinewidth=1.0, capsize=3, capthick=1.2, alpha=0.7)
        ax.fill_between(fechas, vals - errs, vals + errs, alpha=0.15, color=color, label="±1 std")
        ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_title(nombre, fontsize=10, fontweight="bold")
        ax.set_ylabel("SR norm. (%)", fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.tick_params(axis="x", labelsize=7, rotation=30)
        ax.tick_params(axis="y", labelsize=7)
        ax.grid(True, alpha=0.25)
        ax.set_ylim(y_min, y_max)
        ax.legend(fontsize=7, loc="lower left")

    for j in range(n_inst, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("SR Semanal Q25 Normalizado (t₀ = 100%) ± std — por instrumento",
                 fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico norm barras T: %s", out_path)


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
    datos_norm = {}      # nombre -> (q25_norm, std_norm) para gráficos normalizados
    disp_rows = []

    for nombre, ruta, col_sr, fecha_max_override in config:
        fecha_max = fecha_max_override if fecha_max_override is not None else PERIODO_ANALISIS_FIN
        serie_diaria = cargar_sr_diario(ruta, col_sr, fecha_min=PERIODO_ANALISIS_INICIO, fecha_max=fecha_max)
        if serie_diaria is None or serie_diaria.empty:
            logger.info("Omite %s: sin datos.", nombre)
            continue
        semanal = agregar_semanal_q25(serie_diaria, nombre)
        if semanal is None or semanal.empty:
            logger.info("Omite %s: sin semanas.", nombre)
            continue
        q25, std, n = agregar_semanal_q25_y_std(serie_diaria, nombre)
        if nombre == "RefCells" and len(semanal) > 1:
            semanal = semanal.iloc[:-1]
            q25 = q25.iloc[:-1]
            std = std.iloc[:-1] if std is not None else std
            n = n.iloc[:-1] if n is not None else n
        series_semanales[nombre] = semanal
        datos_con_std[nombre] = (q25, std, n)
        q25_n, std_n = normalizar_desde_inicio(q25, std)
        if q25_n is not None:
            datos_norm[nombre] = (q25_n, std_n)
        disp = dispersion_entre_semanas(semanal, nombre)
        if disp:
            disp_rows.append(disp)
        logger.info("%-15s: %d semanas, Q25 media=%.2f%%, std=%.2f%%, CV=%.2f%%",
                    nombre, disp["n_semanas"], disp["mean"], disp["std"], disp["cv_pct"])

    if not series_semanales:
        logger.error("No se encontraron datos SR.")
        return False

    # --- PV Glasses por semana de exposición (alineado al primer dato graficado)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ref_dates = sorted(set().union(*[dn[0].index for dn in datos_norm.values()]))
    q25_pg, std_pg, n_pg = _cargar_pv_glasses_por_semana_exposicion(project_root, ref_dates)
    if q25_pg is not None and not q25_pg.empty:
        series_semanales["PV Glasses"] = q25_pg
        datos_con_std["PV Glasses"] = (q25_pg, std_pg, n_pg)
        q25_pg_n, std_pg_n = normalizar_desde_inicio(q25_pg, std_pg)
        if q25_pg_n is not None:
            datos_norm["PV Glasses"] = (q25_pg_n, std_pg_n)
        disp_pg = dispersion_entre_semanas(q25_pg, "PV Glasses")
        if disp_pg:
            disp_rows.append(disp_pg)
            logger.info("%-15s: %d semanas (por exp.), Q25 media=%.2f%%, std=%.2f%%, CV=%.2f%%",
                        "PV Glasses", len(q25_pg), disp_pg["mean"], disp_pg["std"], disp_pg["cv_pct"])
        else:
            logger.info("%-15s: %d semanas (por semana de exposición)", "PV Glasses", len(q25_pg))

    # --- Incertidumbre U(SR) por semana (propagación: depende del valor Q25 de cada semana)
    datos_u_pp_norm = {}
    datos_u_pp_orig = {}  # U(SR) en pp (escala original) para exportar en CSV
    for nombre in list(datos_norm.keys()):
        q25, _, _ = datos_con_std[nombre]
        q25_0 = float(q25.dropna().iloc[0])
        if q25_0 < 1e-9:
            continue
        if U_pp_por_metodologia is not None:
            U_pp = U_pp_por_metodologia(nombre, q25.values)
            u_norm = np.where(np.isfinite(U_pp), U_pp * (100.0 / q25_0), 0.0)
            datos_u_pp_orig[nombre] = pd.Series(np.where(np.isfinite(U_pp), U_pp, np.nan), index=q25.index)
        else:
            u_by_name = _cargar_incertidumbre_u_pp(project_root)
            u_const = u_by_name.get(nombre, 0.5)
            u_norm = np.full(len(q25), u_const * (100.0 / q25_0))
            datos_u_pp_orig[nombre] = pd.Series(np.full(len(q25), u_const), index=q25.index)
        datos_u_pp_norm[nombre] = pd.Series(u_norm, index=q25.index)

    # --- CSV formato ancho (original)
    df_ancho = pd.DataFrame(series_semanales)
    df_ancho.index.name = "semana"
    df_ancho.to_csv(os.path.join(out_dir, "sr_semanal_q25.csv"))
    logger.info("CSV ancho: %s", os.path.join(out_dir, "sr_semanal_q25.csv"))

    # --- CSV formato largo (original)
    largo_rows = []
    for nombre, s in series_semanales.items():
        for fecha, val in s.items():
            largo_rows.append({"semana": fecha, "instrumento": nombre, "sr_q25": val})
    df_largo = pd.DataFrame(largo_rows)
    df_largo.to_csv(os.path.join(out_dir, "sr_semanal_q25_largo.csv"), index=False)

    # --- CSV normalizado (ancho)
    norm_series = {nombre: q25_n for nombre, (q25_n, _) in datos_norm.items()}
    df_norm = pd.DataFrame(norm_series)
    df_norm.index.name = "semana"
    df_norm.to_csv(os.path.join(out_dir, "sr_semanal_norm.csv"))
    logger.info("CSV norm: %s", os.path.join(out_dir, "sr_semanal_norm.csv"))

    # --- CSV normalizado (largo)
    norm_largo_rows = []
    for nombre, (q25_n, _) in datos_norm.items():
        for fecha, val in q25_n.items():
            norm_largo_rows.append({"semana": fecha, "instrumento": nombre, "sr_norm": val})
    df_norm_largo = pd.DataFrame(norm_largo_rows)
    df_norm_largo.to_csv(os.path.join(out_dir, "sr_semanal_norm_largo.csv"), index=False)
    logger.info("CSV norm largo: %s", os.path.join(out_dir, "sr_semanal_norm_largo.csv"))

    # --- CSV gráfico incertidumbre: sr_norm + U(SR) por semana e instrumento (todo en un solo archivo)
    incert_rows = []
    for nombre, (q25_n, _) in datos_norm.items():
        u_norm_s = datos_u_pp_norm.get(nombre)
        u_pp_s = datos_u_pp_orig.get(nombre)
        for fecha in q25_n.index:
            sr_norm = q25_n.loc[fecha]
            u_sr_norm = u_norm_s.reindex([fecha]).fillna(0).iloc[0] if u_norm_s is not None else 0.0
            u_sr_pp = u_pp_s.reindex([fecha]).fillna(np.nan).iloc[0] if u_pp_s is not None else np.nan
            incert_rows.append({
                "semana": fecha,
                "instrumento": nombre,
                "sr_norm": round(sr_norm, 4),
                "U_SR_pp": round(u_sr_pp, 4) if np.isfinite(u_sr_pp) else "",
                "U_sr_norm": round(u_sr_norm, 4),
            })
    df_incert = pd.DataFrame(incert_rows)
    path_incert = os.path.join(out_dir, "sr_semanal_norm_incertidumbre.csv")
    df_incert.to_csv(path_incert, index=False)
    logger.info("CSV gráfico incertidumbre: %s", path_incert)

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
        grafico_norm_superpuesto(datos_norm,
                                 os.path.join(out_dir, "sr_semanal_norm.png"))
        grafico_norm_superpuesto_sombra(datos_norm,
                                        os.path.join(out_dir, "sr_semanal_norm_sombra.png"))
        grafico_norm_barras_t(datos_norm,
                              os.path.join(out_dir, "sr_semanal_norm_barras_t.png"))
        # Gráfico mismo layout pero bandas = ± U(SR) [pp] por semana (propagación según valor)
        grafico_norm_superpuesto_incertidumbre(
            datos_norm,
            os.path.join(out_dir, "sr_semanal_norm_incertidumbre.png"),
            datos_u_pp_norm,
        )
        grafico_norm_superpuesto_barras_incertidumbre(
            datos_norm,
            os.path.join(out_dir, "sr_semanal_norm_incertidumbre_barras.png"),
            datos_u_pp_norm,
        )

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
