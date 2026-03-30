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
  - sr_semanal_q25_sombra.png : todas las series Q25 superpuestas ± std (sin PV Glasses)
  - sr_semanal_q25_sombra_completo.png : igual con todos los instrumentos
  - sr_semanal_q25_sombra_datos.csv : tabla larga con Q25, std diaria en semana y n° días (equiv. a _completo)
  - sr_semanal_q25_sombra_datos_sin_pv_glasses.csv : mismo dato filtrado (equiv. al PNG principal sin PV Glasses)
  - dispersion_semanal.png    : boxplot de dispersión entre instrumentos

Uso (desde TESIS_SOILING):
  python -m analysis.stats.agregacion_semanal [SR_DIR] [OUT_DIR] [--solo-sin-normalizar]

  Con --solo-sin-normalizar: no escribe CSV/PNG normalizados (sr_semanal_norm*), y al inicio
  borra restos sr_semanal_norm* en OUT_DIR. Útil para carpetas tipo TESIS_NO_NORM.
"""
import glob
import os
import sys
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from analysis.plot_metodos import (
    color_metodo,
    configure_matplotlib_for_thesis,
    etiqueta_metodo_mathtext,
    orden_instrumentos,
    ticklabels_mathtext,
    titulo_reemplazar_iv600_pmax_isc,
)

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
    # Formateador explícito coma decimal, siempre 1 decimal (100 → "100,0", 97,5 → "97,5")
    def _formatter_coma(x, pos=None):
        return ("%.1f" % x).replace(".", ",")
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FuncFormatter = None
    _formatter_coma = None

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

# Instrumentos que no se normalizan a 100%: se mantienen en SR absoluto (%). IV600 Pmax e Isc.
NO_NORMALIZAR_IV600 = {"IV600 Pmax", "IV600 Isc"}
# PV Glasses: se excluye de los gráficos/CSV principales; se generan versiones _completo con todos.
INSTRUMENTO_PV_GLASSES = "PV Glasses"

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
    for col in orden_instrumentos(df_ancho.columns):
        if col not in df_ancho.columns:
            continue
        s = df_ancho[col].dropna()
        if s.empty:
            continue
        ax.plot(
            s.index, s.values, ".-",
            label=etiqueta_metodo_mathtext(col),
            color=color_metodo(col),
            alpha=0.85, linewidth=1.2,
        )
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_xlabel("Semana (inicio lunes)")
    ax.set_ylabel("SR Q25 semanal (%)")
    ax.set_title("Soiling Ratio — Agregación semanal Q25 por instrumento")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=13, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=80)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
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
    nombres = orden_instrumentos(datos_por_instrumento.keys())
    n_inst = len(nombres)
    ncols = 2
    nrows = (n_inst + 1) // ncols

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
        color = color_metodo(nombre)

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
        ax.set_title(etiqueta_metodo_mathtext(nombre), fontsize=12, fontweight="bold")
        ax.set_ylabel("SR (%)", fontsize=11)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.tick_params(axis="x", labelsize=10, rotation=30)
        ax.tick_params(axis="y", labelsize=10)
        ax.grid(True, alpha=0.25)
        ax.set_ylim(y_min, y_max)  # eje Y estandarizado para todos los subplots
        ax.legend(fontsize=11, loc="lower left")
        if _formatter_coma is not None and FuncFormatter is not None:
            ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))

    # ocultar subplots vacíos
    for j in range(n_inst, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("SR Semanal Q25 ± Desviación estándar (barras T) — por instrumento",
                 fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico barras T: %s", out_path)


def grafico_norm_superpuesto(datos_norm, out_path):
    """Todas las series normalizadas superpuestas en un único panel."""
    fig, ax = plt.subplots(figsize=(14, 6))
    for nombre in orden_instrumentos(datos_norm.keys()):
        if nombre not in datos_norm:
            continue
        q25_n, std_n = datos_norm[nombre]
        color = color_metodo(nombre)
        errs = std_n.fillna(0).values
        ax.plot(q25_n.index, q25_n.values, "o-", color=color,
                linewidth=1.3, markersize=3, label=etiqueta_metodo_mathtext(nombre), alpha=0.85)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Semana (inicio lunes)")
    ax.set_ylabel("SR (%)")
    ax.set_title(titulo_reemplazar_iv600_pmax_isc(
        "SR Semanal Q25 (t₀=100% normalizado; IV600 Pmax/Isc en valor absoluto)"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=13, ncol=2)
    ax.grid(True, alpha=0.3)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Gráfico norm superpuesto: %s", out_path)


def grafico_norm_superpuesto_sombra(datos_norm, out_path):
    """Todas las series normalizadas superpuestas con área sombreada ±1 std."""
    fig, ax = plt.subplots(figsize=(14, 6))
    for nombre in orden_instrumentos(datos_norm.keys()):
        if nombre not in datos_norm:
            continue
        q25_n, std_n = datos_norm[nombre]
        color = color_metodo(nombre)
        errs = std_n.fillna(0).values
        ax.plot(q25_n.index, q25_n.values, "o-", color=color,
                linewidth=1.3, markersize=3, label=etiqueta_metodo_mathtext(nombre), alpha=0.85)
        ax.fill_between(q25_n.index, q25_n.values - errs, q25_n.values + errs,
                        alpha=0.12, color=color)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Fecha", fontsize=15)
    ax.set_ylabel("SR (%)", fontsize=15)
    ax.set_title("SR Semanal Q25 Normalizado ± std (t₀=100%) — todos los instrumentos", fontsize=17, pad=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=14, ncol=2)
    ax.tick_params(axis="both", labelsize=13)
    ax.grid(True, alpha=0.3)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Gráfico norm superpuesto con sombra: %s", out_path)


def grafico_q25_superpuesto_sombra(datos_q25, out_path):
    """
    Igual que grafico_norm_superpuesto_sombra pero con SR semanal Q25 sin normalizar
    (banda ±1 std entre semanas, no t₀=100%).
    datos_q25: dict nombre -> (q25, std) con mismas convenciones que datos_norm.
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    for nombre in orden_instrumentos(datos_q25.keys()):
        if nombre not in datos_q25:
            continue
        q25, std_s = datos_q25[nombre]
        color = color_metodo(nombre)
        errs = std_s.fillna(0).values
        ax.plot(q25.index, q25.values, "o-", color=color,
                linewidth=1.3, markersize=3, label=etiqueta_metodo_mathtext(nombre), alpha=0.85)
        ax.fill_between(q25.index, q25.values - errs, q25.values + errs,
                        alpha=0.12, color=color)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Fecha", fontsize=15)
    ax.set_ylabel("SR (%)", fontsize=15)
    ax.set_title("SR Semanal Q25 (sin normalizar) ± std — todos los instrumentos", fontsize=17, pad=10)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=14, ncol=2)
    ax.tick_params(axis="both", labelsize=13)
    ax.grid(True, alpha=0.3)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Gráfico Q25 superpuesto con sombra (sin normalizar): %s", out_path)


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
    y_min, y_max = 80, 105
    for nombre in orden_instrumentos(datos_norm.keys()):
        if nombre not in datos_norm:
            continue
        q25_n, _ = datos_norm[nombre]
        color = color_metodo(nombre)
        u_series = uncertainty_pp_series_by_name.get(nombre)
        if u_series is not None and hasattr(u_series, "reindex"):
            errs = u_series.reindex(q25_n.index).fillna(0).values
        else:
            errs = np.full_like(q25_n.values, float(u_series) if u_series is not None else 0.5, dtype=float)
        low = np.clip(q25_n.values - errs, y_min, y_max)
        high = np.clip(q25_n.values + errs, y_min, y_max)
        ax.fill_between(q25_n.index, low, high, alpha=0.2, color=color, zorder=0)
        ax.plot(q25_n.index, q25_n.values, "o-", color=color,
                linewidth=1.5, markersize=4, label=etiqueta_metodo_mathtext(nombre), alpha=0.9, zorder=2)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%", zorder=1)
    ax.set_xlabel("Fecha", fontsize=14)
    ax.set_ylabel("SR (%)", fontsize=14)
    ax.set_ylim(y_min, y_max)
    # pad: separación título–eje en puntos; +6 pt ≈ 2 mm para subir el título
    ax.set_title(
        titulo_reemplazar_iv600_pmax_isc(
            "SR Semanal Q25 (t₀=100% norm.; IV600 Pmax/Isc valor absoluto) ± U(SR) [pp]"
        ),
        pad=12, fontsize=16,
    )
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.tick_params(axis="both", labelsize=13)
    ax.legend(loc="lower left", fontsize=14, ncol=2)
    ax.grid(True, alpha=0.3)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Gráfico norm superpuesto con incertidumbre: %s", out_path)


def grafico_norm_superpuesto_barras_incertidumbre(datos_norm, out_path, uncertainty_pp_series_by_name):
    """
    Mismas series que grafico_norm_superpuesto_incertidumbre pero con barras de error
    ± U(SR) [pp] en cada punto (incertidumbre por propagación, distinta por semana).
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    for nombre in orden_instrumentos(datos_norm.keys()):
        if nombre not in datos_norm:
            continue
        q25_n, _ = datos_norm[nombre]
        color = color_metodo(nombre)
        u_series = uncertainty_pp_series_by_name.get(nombre)
        if u_series is not None and hasattr(u_series, "reindex"):
            errs = u_series.reindex(q25_n.index).fillna(0).values
        else:
            errs = np.full_like(q25_n.values, float(u_series) if u_series is not None else 0.5, dtype=float)
        ax.plot(q25_n.index, q25_n.values, "o-", color=color,
                linewidth=1.3, markersize=3, label=etiqueta_metodo_mathtext(nombre), alpha=0.85)
        ax.errorbar(q25_n.index, q25_n.values, yerr=errs, fmt="none",
                    ecolor=color, elinewidth=1.0, capsize=2.5, capthick=1.0, alpha=0.7)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("SR (%)")
    ax.set_title(titulo_reemplazar_iv600_pmax_isc(
        "SR Semanal Q25 (t₀=100% norm.; IV600 Pmax/Isc valor absoluto) ± U(SR) [pp]"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=13, ncol=2)
    ax.grid(True, alpha=0.3)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Gráfico norm superpuesto con barras de incertidumbre: %s", out_path)


def grafico_q25_superpuesto_incertidumbre(datos_q25, out_path, uncertainty_pp_series_by_name):
    """
    Gráfico superpuesto de SR semanal Q25 (SIN normalizar) con banda ± U(SR) [pp].
    datos_q25: dict nombre -> (q25, std) ; se usa solo q25 (el std no se usa aquí).
    uncertainty_pp_series_by_name: dict nombre -> pd.Series U(SR) en pp, mismo índice que q25.
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    y_min, y_max = 80, 105
    for nombre in orden_instrumentos(datos_q25.keys()):
        if nombre not in datos_q25:
            continue
        q25, _ = datos_q25[nombre]
        color = color_metodo(nombre)
        u_series = uncertainty_pp_series_by_name.get(nombre)
        if u_series is not None and hasattr(u_series, "reindex"):
            errs = u_series.reindex(q25.index).fillna(0).values
        else:
            errs = np.full_like(q25.values, float(u_series) if u_series is not None else 0.5, dtype=float)

        low = np.clip(q25.values - errs, y_min, y_max)
        high = np.clip(q25.values + errs, y_min, y_max)
        ax.fill_between(q25.index, low, high, alpha=0.2, color=color, zorder=0)
        ax.plot(q25.index, q25.values, "o-", color=color,
                linewidth=1.5, markersize=4, label=etiqueta_metodo_mathtext(nombre), alpha=0.9, zorder=2)

    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Fecha", fontsize=14)
    ax.set_ylabel("SR (%)", fontsize=14)
    ax.set_ylim(y_min, y_max)
    ax.set_title("SR Semanal Q25 (SIN normalizar) ± U(SR) [pp]", pad=12, fontsize=16)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.tick_params(axis="both", labelsize=13)
    ax.legend(loc="lower left", fontsize=14, ncol=2)
    ax.grid(True, alpha=0.3)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Gráfico Q25 sin normalizar con incertidumbre: %s", out_path)


def grafico_q25_superpuesto_barras_incertidumbre(datos_q25, out_path, uncertainty_pp_series_by_name):
    """
    Gráfico superpuesto de SR semanal Q25 (SIN normalizar) con barras de error ± U(SR) [pp].
    datos_q25: dict nombre -> (q25, std) ; se usa solo q25.
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    for nombre in orden_instrumentos(datos_q25.keys()):
        if nombre not in datos_q25:
            continue
        q25, _ = datos_q25[nombre]
        color = color_metodo(nombre)
        u_series = uncertainty_pp_series_by_name.get(nombre)
        if u_series is not None and hasattr(u_series, "reindex"):
            errs = u_series.reindex(q25.index).fillna(0).values
        else:
            errs = np.full_like(q25.values, float(u_series) if u_series is not None else 0.5, dtype=float)

        ax.plot(q25.index, q25.values, "o-", color=color,
                linewidth=1.3, markersize=3, label=etiqueta_metodo_mathtext(nombre), alpha=0.85)
        ax.errorbar(q25.index, q25.values, yerr=errs, fmt="none",
                    ecolor=color, elinewidth=1.0, capsize=2.5, capthick=1.0, alpha=0.7)

    ax.axhline(100, color="gray", linestyle="--", linewidth=0.9, alpha=0.6, label="SR = 100%")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("SR (%)")
    ax.set_title("SR Semanal Q25 (SIN normalizar) ± U(SR) [pp]")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    ax.legend(loc="lower left", fontsize=13, ncol=2)
    ax.grid(True, alpha=0.3)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Gráfico Q25 sin normalizar con barras de incertidumbre: %s", out_path)


def grafico_norm_barras_t(datos_norm, out_path):
    """Un subplot por instrumento con SR normalizado y barras T (±1 std escalado)."""
    nombres = orden_instrumentos(datos_norm.keys())
    n_inst = len(nombres)
    ncols = 2
    nrows = (n_inst + 1) // ncols

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
        color = color_metodo(nombre)
        fechas = q25_n.index
        vals = q25_n.values
        errs = std_n.fillna(0).values

        ax.plot(fechas, vals, "o-", color=color, linewidth=1.4, markersize=4, label="Q25 norm.")
        ax.errorbar(fechas, vals, yerr=errs, fmt="none",
                    ecolor=color, elinewidth=1.0, capsize=3, capthick=1.2, alpha=0.7)
        ax.fill_between(fechas, vals - errs, vals + errs, alpha=0.15, color=color, label="±1 std")
        ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
        ax.set_title(etiqueta_metodo_mathtext(nombre), fontsize=12, fontweight="bold")
        ax.set_ylabel("SR norm. (%)", fontsize=11)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.tick_params(axis="x", labelsize=10, rotation=30)
        ax.tick_params(axis="y", labelsize=10)
        ax.grid(True, alpha=0.25)
        ax.set_ylim(y_min, y_max)
        ax.legend(fontsize=11, loc="lower left")
        if _formatter_coma is not None and FuncFormatter is not None:
            ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))

    for j in range(n_inst, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle(
        titulo_reemplazar_iv600_pmax_isc(
            "SR Semanal Q25 (t₀=100% norm.; IV600 Pmax/Isc valor absoluto) ± std — por instrumento"
        ),
        fontsize=14, fontweight="bold", y=1.01,
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close()
    logger.info("Gráfico norm barras T: %s", out_path)


def grafico_boxplot_dispersion(df_largo, out_path):
    """Boxplot de la distribución semanal Q25 por instrumento."""
    instrumentos = orden_instrumentos(df_largo["instrumento"].unique())
    data = [df_largo[df_largo["instrumento"] == inst]["sr_q25"].dropna().values
            for inst in instrumentos]

    fig, ax = plt.subplots(figsize=(12, 6))
    bp = ax.boxplot(data, tick_labels=ticklabels_mathtext(instrumentos), patch_artist=True,
                    medianprops=dict(color="black", linewidth=1.5))
    for patch, inst in zip(bp["boxes"], instrumentos):
        patch.set_facecolor(color_metodo(inst))
        patch.set_alpha(0.7)
    ax.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_ylabel("SR Q25 semanal (%)")
    ax.set_title("Dispersión del SR semanal (Q25) por instrumento")
    ax.set_ylim(bottom=80)
    plt.xticks(rotation=20, ha="right")
    ax.grid(True, axis="y", alpha=0.3)
    if _formatter_coma is not None and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    plt.tight_layout()
    plt.savefig(out_path, dpi=220)
    plt.close()
    logger.info("Gráfico boxplot dispersión: %s", out_path)


def run(sr_dir, out_dir, solo_sin_normalizar=False):
    os.makedirs(out_dir, exist_ok=True)
    if solo_sin_normalizar:
        for pat in ("sr_semanal_norm*.csv", "sr_semanal_norm*.png"):
            for f in glob.glob(os.path.join(out_dir, pat)):
                try:
                    os.remove(f)
                    logger.info("Eliminado (--solo-sin-normalizar): %s", f)
                except OSError as exc:
                    logger.warning("No se pudo eliminar %s: %s", f, exc)
        logger.info("Modo solo sin normalizar: no se generarán salidas sr_semanal_norm*.")

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
        if nombre in NO_NORMALIZAR_IV600:
            # IV600 Pmax e Isc: sin normalizar (SR en valor absoluto %)
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
        if nombre in NO_NORMALIZAR_IV600:
            # IV600 Pmax/Isc: SR sin normalizar → U en pp, misma escala que el eje Y (valor absoluto %)
            if U_pp_por_metodologia is not None:
                U_pp = U_pp_por_metodologia(nombre, q25.values)
                datos_u_pp_orig[nombre] = pd.Series(np.where(np.isfinite(U_pp), U_pp, np.nan), index=q25.index)
            else:
                u_by_name = _cargar_incertidumbre_u_pp(project_root)
                u_const = u_by_name.get(nombre, 0.5)
                datos_u_pp_orig[nombre] = pd.Series(np.full(len(q25), u_const), index=q25.index)
            datos_u_pp_norm[nombre] = datos_u_pp_orig[nombre].copy()
        else:
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

    if not solo_sin_normalizar:
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

    # --- CSV gráfico incertidumbre (SIN normalizar): sr_q25 + U(SR) por semana e instrumento
    incert_rows_orig = []
    for nombre, (q25, _, _) in datos_con_std.items():
        u_pp_s = datos_u_pp_orig.get(nombre)
        for fecha in q25.index:
            sr_q25 = q25.loc[fecha]
            u_sr_pp = (
                u_pp_s.reindex([fecha]).fillna(np.nan).iloc[0]
                if u_pp_s is not None
                else np.nan
            )
            incert_rows_orig.append({
                "semana": fecha,
                "instrumento": nombre,
                "sr_q25": round(float(sr_q25), 4) if np.isfinite(sr_q25) else "",
                "U_SR_pp": round(float(u_sr_pp), 4) if np.isfinite(u_sr_pp) else "",
            })
    df_incert_orig = pd.DataFrame(incert_rows_orig)
    path_incert_orig = os.path.join(out_dir, "sr_semanal_q25_incertidumbre.csv")
    df_incert_orig.to_csv(path_incert_orig, index=False)
    logger.info("CSV gráfico incertidumbre (sin normalizar): %s", path_incert_orig)

    # --- CSV datos exactos de sr_semanal_q25_sombra*.png (Q25 sin normalizar ± std de días dentro de la semana)
    sombra_rows = []
    for nombre, (q25, std, n) in datos_con_std.items():
        for fecha in q25.index:
            qv = q25.loc[fecha]
            sv = (
                std.reindex([fecha]).iloc[0]
                if std is not None and len(std) > 0
                else np.nan
            )
            nv = (
                n.reindex([fecha]).iloc[0]
                if n is not None and len(n) > 0
                else np.nan
            )
            std_plot = 0.0 if pd.isna(sv) else float(sv)
            qf = float(qv) if np.isfinite(qv) else np.nan
            sombra_rows.append({
                "semana": fecha,
                "instrumento": nombre,
                "sr_q25_pct": round(qf, 4) if np.isfinite(qf) else "",
                "std_diarios_en_semana_pct": round(float(sv), 4) if np.isfinite(sv) else "",
                "n_dias_con_dato_en_semana": int(nv) if np.isfinite(nv) else "",
                "std_usada_en_grafico_pct": round(std_plot, 4),
                "banda_inferior_pct": round(qf - std_plot, 4) if np.isfinite(qf) else "",
                "banda_superior_pct": round(qf + std_plot, 4) if np.isfinite(qf) else "",
            })
    df_sombra = pd.DataFrame(sombra_rows)
    path_sombra = os.path.join(out_dir, "sr_semanal_q25_sombra_datos.csv")
    df_sombra.to_csv(path_sombra, index=False)
    logger.info("CSV datos gráfico sombra Q25 (sin norm.): %s", path_sombra)
    path_sombra_sin_pg = os.path.join(out_dir, "sr_semanal_q25_sombra_datos_sin_pv_glasses.csv")
    df_sombra[df_sombra["instrumento"] != INSTRUMENTO_PV_GLASSES].to_csv(
        path_sombra_sin_pg, index=False)
    logger.info("CSV datos gráfico sombra (sin PV Glasses): %s", path_sombra_sin_pg)

    # --- CSV dispersión: principal sin PV Glasses, _completo con todos
    df_disp = pd.DataFrame(disp_rows).round(4)
    df_disp_sin_pg = df_disp[df_disp["instrumento"] != INSTRUMENTO_PV_GLASSES]
    df_disp_sin_pg.to_csv(os.path.join(out_dir, "dispersion_semanal.csv"), index=False)
    logger.info("CSV dispersión (sin PV Glasses): %s", os.path.join(out_dir, "dispersion_semanal.csv"))
    df_disp.to_csv(os.path.join(out_dir, "dispersion_semanal_completo.csv"), index=False)
    logger.info("CSV dispersión completo: %s", os.path.join(out_dir, "dispersion_semanal_completo.csv"))

    # --- Gráficos (principal sin PV Glasses; _completo con todos los instrumentos)
    if MATPLOTLIB_AVAILABLE:
        datos_norm_sin_pg = {k: v for k, v in datos_norm.items() if k != INSTRUMENTO_PV_GLASSES}
        datos_u_pp_norm_sin_pg = {k: v for k, v in datos_u_pp_norm.items() if k != INSTRUMENTO_PV_GLASSES}
        df_largo_sin_pg = df_largo[df_largo["instrumento"] != INSTRUMENTO_PV_GLASSES]
        datos_q25_sin_pg = {k: (v[0], v[1]) for k, v in datos_con_std.items() if k != INSTRUMENTO_PV_GLASSES}
        datos_q25_all = {k: (v[0], v[1]) for k, v in datos_con_std.items()}

        grafico_series_semanales(df_ancho, os.path.join(out_dir, "sr_semanal_q25.png"))
        grafico_q25_superpuesto_sombra(
            datos_q25_sin_pg,
            os.path.join(out_dir, "sr_semanal_q25_sombra.png"),
        )
        grafico_q25_superpuesto_sombra(
            datos_q25_all,
            os.path.join(out_dir, "sr_semanal_q25_sombra_completo.png"),
        )
        grafico_boxplot_dispersion(df_largo_sin_pg, os.path.join(out_dir, "dispersion_semanal.png"))
        grafico_boxplot_dispersion(df_largo, os.path.join(out_dir, "dispersion_semanal_completo.png"))
        grafico_series_con_barras_error(datos_con_std,
                                        os.path.join(out_dir, "sr_semanal_barras_t.png"))
        if not solo_sin_normalizar:
            grafico_norm_superpuesto(datos_norm,
                                     os.path.join(out_dir, "sr_semanal_norm.png"))
            grafico_norm_superpuesto_sombra(datos_norm_sin_pg,
                                            os.path.join(out_dir, "sr_semanal_norm_sombra.png"))
            grafico_norm_superpuesto_sombra(datos_norm,
                                            os.path.join(out_dir, "sr_semanal_norm_sombra_completo.png"))
            grafico_norm_barras_t(datos_norm,
                                  os.path.join(out_dir, "sr_semanal_norm_barras_t.png"))
            # Incertidumbre: principal sin PV Glasses, _completo con todos
            grafico_norm_superpuesto_incertidumbre(
                datos_norm_sin_pg,
                os.path.join(out_dir, "sr_semanal_norm_incertidumbre.png"),
                datos_u_pp_norm_sin_pg,
            )
            grafico_norm_superpuesto_incertidumbre(
                datos_norm,
                os.path.join(out_dir, "sr_semanal_norm_incertidumbre_completo.png"),
                datos_u_pp_norm,
            )
            grafico_norm_superpuesto_barras_incertidumbre(
                datos_norm,
                os.path.join(out_dir, "sr_semanal_norm_incertidumbre_barras.png"),
                datos_u_pp_norm,
            )

        # Incertidumbre (SIN normalizar): principal sin PV Glasses; _completo con todos
        datos_u_pp_orig_sin_pg = {k: v for k, v in datos_u_pp_orig.items() if k != INSTRUMENTO_PV_GLASSES}

        grafico_q25_superpuesto_incertidumbre(
            datos_q25_sin_pg,
            os.path.join(out_dir, "sr_semanal_q25_incertidumbre.png"),
            datos_u_pp_orig_sin_pg,
        )
        grafico_q25_superpuesto_incertidumbre(
            datos_q25_all,
            os.path.join(out_dir, "sr_semanal_q25_incertidumbre_completo.png"),
            datos_u_pp_orig,
        )
        grafico_q25_superpuesto_barras_incertidumbre(
            datos_q25_all,
            os.path.join(out_dir, "sr_semanal_q25_incertidumbre_barras.png"),
            datos_u_pp_orig,
        )

    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sr_dir = os.path.join(project_root, "analysis", "sr")
    out_dir = os.path.join(project_root, "analysis", "stats")
    argv_pos = [a for a in sys.argv[1:] if not str(a).startswith("--")]
    solo_sin_normalizar = "--solo-sin-normalizar" in sys.argv[1:]
    if len(argv_pos) >= 1:
        sr_dir = os.path.abspath(argv_pos[0])
    if len(argv_pos) >= 2:
        out_dir = os.path.abspath(argv_pos[1])
    logger.info("SR dir: %s | Salida: %s | solo_sin_normalizar=%s", sr_dir, out_dir, solo_sin_normalizar)
    ok = run(sr_dir, out_dir, solo_sin_normalizar=solo_sin_normalizar)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
