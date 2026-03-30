"""
Análisis de tendencias del SR semanal: regresión lineal por metodología.

Para cada metodología se ajusta SR semanal Q25 (t₀=100% norm.; IV600 Pmax/Isc valor absoluto) vs tiempo
(semana 0, 1, 2, ...). La pendiente indica la tasa de cambio promedio (% por semana):
  - Pendiente negativa: tendencia a la baja (soiling acumulado).
  - Pendiente ≈ 0: estable.
  - Pendiente positiva: recuperación o ganancia relativa.

Salidas en analysis/tendencias/:
  - tendencias_resumen.csv   : instrumento, pendiente_por_semana, pendiente_por_mes, R2, p_value, n_semanas
  - tendencias_grafico.png   : series observadas + rectas de tendencia
  - tendencias_pendientes.png: barras de pendiente por instrumento
  - tendencias_report.md     : resumen breve
  - tendencias_mensuales_resumen.csv : regresión sobre SR mensual; pendiente %/mes
  - sr_mensual_q25_desde_datos_diarios.csv : si se pasa SR_DIR con entrada sin normalizar: Q25 de SR diarios por mes
  - sr_mensual_promedio_q25_semanales.csv : si no hay SR_DIR o entrada normalizada: media de Q25 semanales del mes
  - tendencias_mensuales_grafico.png : series mensuales + rectas
  - tendencias_mensuales_pendientes.png : barras pendiente mensual
  - pendientes_entre_meses.csv : cambio mes a mes (misma serie mensual que la tendencia lineal mensual)
  - pendientes_entre_meses_tramo_1_mes_calendario.csv : solo saltos de exactamente 1 mes en calendario
  - pendientes_entre_meses_resumen_por_instrumento.csv : estadísticos por instrumento
  - pendientes_entre_semanas.csv : pendiente local (ΔSR pp), separación en calendario y pp/semana calendario
  - pendientes_entre_semanas_tramo_1_semana_calendario.csv : solo pares de semanas ISO consecutivas (7 días)
  - pendientes_entre_semanas_resumen_por_instrumento.csv : estadísticos de esas pendientes
  - pendientes_entre_semanas_boxplot.png : boxplot de pendiente_pp por instrumento (sin PV Glasses)
  - pendientes_entre_semanas_boxplot_completo.png : con todos los instrumentos
  - pendientes_entre_semanas_tramo_7d_boxplot.png : solo tramos de 7 días (sin PV Glasses)
  - delta_semanal_sr_q25_punto_a_punto.csv : alias retrocompatible (mismo tramo que pendientes_entre_semanas)

Entrada: analysis/stats/sr_semanal_norm.csv o sr_semanal_q25.csv (generado por agregacion_semanal).

Uso (desde si_test con PYTHONPATH=TESIS_SOILING):
  python -m analysis.tendencias.analisis_tendencias
  python -m analysis.tendencias.analisis_tendencias [csv_semanal] [carpeta_salida] [analysis/sr opcional]
  Con sr_semanal_q25.csv + tercer argumento = ruta a analysis/sr: el SR mensual es Q25 de los datos diarios por mes.
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

from analysis.plot_metodos import (
    color_metodo,
    configure_matplotlib_for_thesis,
    etiqueta_metodo_mathtext,
    orden_instrumentos,
    ticklabels_mathtext,
    titulo_reemplazar_iv600_pmax_isc,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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

INSTRUMENTO_PV_GLASSES = "PV Glasses"


def grafico_boxplot_pendientes_entre_semanas(
    df_pend: pd.DataFrame,
    out_path: str,
    *,
    modo_txt: str,
    excluir_pv_glasses: bool,
    subtitulo: str = "",
):
    """
    Boxplot de la columna pendiente_pp (SR semana_actual − semana_anterior) por instrumento.
    """
    if not MATPLOTLIB_AVAILABLE or df_pend is None or df_pend.empty:
        return
    d = df_pend.copy()
    d["pendiente_pp"] = pd.to_numeric(d["pendiente_pp"], errors="coerce")
    d = d.dropna(subset=["pendiente_pp", "instrumento"])
    if excluir_pv_glasses:
        d = d[d["instrumento"] != INSTRUMENTO_PV_GLASSES]
    if d.empty:
        logger.warning("Boxplot pendientes semanas: sin datos tras filtros.")
        return
    orden = orden_instrumentos(d["instrumento"].unique())
    data = [d.loc[d["instrumento"] == inst, "pendiente_pp"].values for inst in orden]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    bp = ax.boxplot(
        data,
        tick_labels=ticklabels_mathtext(orden),
        patch_artist=True,
        medianprops=dict(color="black", linewidth=1.5),
    )
    for patch, inst in zip(bp["boxes"], orden):
        patch.set_facecolor(color_metodo(inst))
        patch.set_alpha(0.72)
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.9, alpha=0.7)
    ax.set_ylabel("Cambio intersemanal de SR, ΔSR (pp/semana)", fontsize=14)
    ax.set_xlabel("Instrumento", fontsize=14)
    suf = " (sin PV Glasses)" if excluir_pv_glasses else ""
    st = f"\n{subtitulo}" if subtitulo else ""
    ax.set_title(
        f"Distribución de pendientes semana a semana{suf} — {modo_txt}{st}",
        fontsize=14,
        pad=10,
    )
    plt.xticks(rotation=22, ha="right")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close()
    logger.info("Boxplot pendientes entre semanas: %s", out_path)


def _fmt_month_es(x, pos=None):
    dt = mdates.num2date(x)
    mes_idx = dt.month - 1
    mes = SPANISH_MONTHS[mes_idx] if 0 <= mes_idx < len(SPANISH_MONTHS) else dt.strftime("%b")
    return f"{mes} {dt.year}"


def regresion_linear(x, y):
    """
    Regresión lineal y = a + b*x. x, y: arrays 1d sin NaN.
    Devuelve: pendiente (b), ordenada (a), R², p_value (del test de pendiente), stderr_slope.
    """
    if len(x) < 3 or len(y) < 3:
        return None, None, None, None, None
    res = scipy_stats.linregress(x, y)
    r2 = res.rvalue ** 2
    return res.slope, res.intercept, r2, res.pvalue, res.stderr


def _agregar_mensual_media_semanas(df: pd.DataFrame, instrumentos: list) -> pd.DataFrame:
    """
    Por cada mes natural: media de los valores Q25 semanales que caen en ese mes.
    Índice: fin de mes (ME). Solo columnas de instrumentos.
    """
    sub = df[instrumentos].sort_index()
    return sub.resample("ME").mean()


def _mensual_q25_desde_diario(sr_dir: str) -> pd.DataFrame:
    """
    Por cada mes natural: percentil 25 de los valores diarios de SR en ese mes.
    Mismos CSV, columnas y filtros (≥80 %) que agregacion_semanal / cargar_sr_diario.
    No incluye PV Glasses (no hay serie diaria homogénea en sr/).
    """
    from analysis.stats.agregacion_semanal import (
        _build_config,
        cargar_sr_diario,
        PERIODO_ANALISIS_INICIO,
        PERIODO_ANALISIS_FIN,
    )

    cols = {}
    for nombre, ruta, col_sr, fecha_max_override in _build_config(sr_dir):
        fecha_max = fecha_max_override if fecha_max_override is not None else PERIODO_ANALISIS_FIN
        serie = cargar_sr_diario(
            ruta, col_sr, fecha_min=PERIODO_ANALISIS_INICIO, fecha_max=fecha_max,
        )
        if serie is None or serie.empty:
            logger.debug("Mensual diario: sin datos %s", nombre)
            continue
        idx = pd.to_datetime(pd.Series(serie.index.astype(str)))
        s = pd.Series(serie.values, index=pd.DatetimeIndex(idx)).sort_index()
        cols[nombre] = s.resample("ME").quantile(0.25)
    if not cols:
        return pd.DataFrame()
    return pd.DataFrame(cols).sort_index()


def _tabla_pendientes_entre_semanas(df: pd.DataFrame, instrumentos: list) -> pd.DataFrame:
    """
    Para cada instrumento, recorre las semanas **con dato** en orden temporal.
    Entre cada par consecutivo en esa lista (no necesariamente 7 días en el calendario si faltan semanas):
      - pendiente_pp = SR_actual − SR_anterior (cambio total del tramo)
      - semanas_calendario = días entre fechas / 7
      - pendiente_pp_por_semana_calendario = pendiente_pp / semanas_calendario (tasa media en el tramo)
    """
    rows = []
    for inst in instrumentos:
        s = df[inst].dropna().sort_index()
        prev_idx = None
        prev_val = None
        for idx, val in s.items():
            if prev_val is not None and np.isfinite(val) and np.isfinite(prev_val):
                dpp = float(val) - float(prev_val)
                rel = (100.0 * dpp / float(prev_val)) if abs(float(prev_val)) > 1e-9 else np.nan
                t0 = pd.Timestamp(prev_idx)
                t1 = pd.Timestamp(idx)
                dias = (t1.normalize() - t0.normalize()).days
                sem_cal = dias / 7.0 if dias > 0 else np.nan
                pend_norm = (dpp / sem_cal) if sem_cal and np.isfinite(sem_cal) and sem_cal > 0 else np.nan
                rows.append({
                    "instrumento": inst,
                    "semana_anterior": t0.strftime("%Y-%m-%d"),
                    "semana_actual": t1.strftime("%Y-%m-%d"),
                    "sr_semana_anterior": round(float(prev_val), 4),
                    "sr_semana_actual": round(float(val), 4),
                    "pendiente_pp": round(dpp, 4),
                    "pendiente_pp_por_semana_calendario": round(float(pend_norm), 6) if np.isfinite(pend_norm) else "",
                    "dias_entre_semanas": int(dias),
                    "semanas_calendario": round(float(sem_cal), 4) if np.isfinite(sem_cal) else "",
                    "delta_relativa_pct": round(rel, 4) if np.isfinite(rel) else "",
                })
            prev_idx, prev_val = idx, val
    return pd.DataFrame(rows)


def _resumen_pendientes_por_instrumento(df_pend: pd.DataFrame) -> pd.DataFrame:
    """Media, std, n de pendiente_pp; mismo para tramos con exactamente 7 días en calendario."""
    if df_pend is None or df_pend.empty:
        return pd.DataFrame()
    df1 = df_pend[df_pend["dias_entre_semanas"] == 7]
    out_rows = []

    def _stat(series):
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) == 0:
            return "", "", 0
        m = float(s.mean())
        sd = float(s.std(ddof=1)) if len(s) > 1 else ""
        return round(m, 6), (round(sd, 6) if sd != "" else ""), int(len(s))

    for inst, sub in df_pend.groupby("instrumento"):
        sub1 = df1[df1["instrumento"] == inst]
        m_pp, sd_pp, n_pp = _stat(sub["pendiente_pp"])
        m_n, sd_n, n_n = _stat(sub1["pendiente_pp"])
        m_r, sd_r, n_r = _stat(sub1["pendiente_pp_por_semana_calendario"])
        out_rows.append({
            "instrumento": inst,
            "n_tramos_todos": int(len(sub)),
            "media_pendiente_pp": m_pp,
            "std_pendiente_pp": sd_pp,
            "n_tramos_1_semana_calendario": n_n,
            "media_pendiente_pp_solo_1sem": m_n,
            "std_pendiente_pp_solo_1sem": sd_n,
            "media_pp_por_semana_cal_solo_1sem": m_r,
        })
    return pd.DataFrame(out_rows)


def _meses_calendario_entre(t0, t1) -> int:
    """Meses de calendario entre dos fechas (ej. ago→sep = 1)."""
    a = pd.Timestamp(t0).normalize()
    b = pd.Timestamp(t1).normalize()
    return (b.year - a.year) * 12 + (b.month - a.month)


def _tabla_pendientes_entre_meses(df_mensual: pd.DataFrame, instrumentos: list) -> pd.DataFrame:
    """
    Entre cada par de meses consecutivos **con dato** en la serie mensual (orden temporal):
    pendiente_pp = SR_mes_actual − SR_mes_anterior; meses_calendario entre marcas; tasa / mes calendario.
    """
    rows = []
    for inst in instrumentos:
        if inst not in df_mensual.columns:
            continue
        s = df_mensual[inst].dropna().sort_index()
        prev_idx = None
        prev_val = None
        for idx, val in s.items():
            if prev_val is not None and np.isfinite(val) and np.isfinite(prev_val):
                dpp = float(val) - float(prev_val)
                rel = (100.0 * dpp / float(prev_val)) if abs(float(prev_val)) > 1e-9 else np.nan
                t0 = pd.Timestamp(prev_idx)
                t1 = pd.Timestamp(idx)
                nmes = _meses_calendario_entre(t0, t1)
                pend_norm = (dpp / nmes) if nmes and nmes > 0 else np.nan
                rows.append({
                    "instrumento": inst,
                    "mes_anterior": t0.strftime("%Y-%m-%d"),
                    "mes_actual": t1.strftime("%Y-%m-%d"),
                    "sr_mes_anterior": round(float(prev_val), 4),
                    "sr_mes_actual": round(float(val), 4),
                    "pendiente_pp": round(dpp, 4),
                    "meses_calendario_entre_puntos": int(nmes),
                    "pendiente_pp_por_mes_calendario": round(float(pend_norm), 6) if np.isfinite(pend_norm) else "",
                    "delta_relativa_pct": round(rel, 4) if np.isfinite(rel) else "",
                })
            prev_idx, prev_val = idx, val
    return pd.DataFrame(rows)


def _resumen_pendientes_entre_meses(df_pend: pd.DataFrame) -> pd.DataFrame:
    if df_pend is None or df_pend.empty:
        return pd.DataFrame()
    df1 = df_pend[df_pend["meses_calendario_entre_puntos"] == 1]

    def _stat(series):
        s = pd.to_numeric(series, errors="coerce").dropna()
        if len(s) == 0:
            return "", "", 0
        m = float(s.mean())
        sd = float(s.std(ddof=1)) if len(s) > 1 else ""
        return round(m, 6), (round(sd, 6) if sd != "" else ""), int(len(s))

    out_rows = []
    for inst, sub in df_pend.groupby("instrumento"):
        sub1 = df1[df1["instrumento"] == inst]
        m_pp, sd_pp, n_pp = _stat(sub["pendiente_pp"])
        m_n, sd_n, n_n = _stat(sub1["pendiente_pp"])
        m_r, sd_r, _n_r = _stat(sub1["pendiente_pp_por_mes_calendario"])
        out_rows.append({
            "instrumento": inst,
            "n_tramos_todos": int(len(sub)),
            "media_pendiente_pp": m_pp,
            "std_pendiente_pp": sd_pp,
            "n_tramos_1_mes_calendario": n_n,
            "media_pendiente_pp_solo_1mes": m_n,
            "std_pendiente_pp_solo_1mes": sd_n,
            "media_pp_por_mes_cal_solo_1mes": m_r,
        })
    return pd.DataFrame(out_rows)


def run(norm_csv_path, out_dir, sr_dir=None):
    if not os.path.isfile(norm_csv_path):
        logger.error("No encontrado: %s", norm_csv_path)
        return False

    df = pd.read_csv(norm_csv_path)
    if "semana" not in df.columns:
        logger.error("Se espera columna 'semana' en el CSV.")
        return False
    df["semana"] = pd.to_datetime(df["semana"])
    df = df.set_index("semana").sort_index()

    base_name = os.path.basename(norm_csv_path).lower()
    sin_normalizar = ("sr_semanal_q25" in base_name) and ("norm" not in base_name)
    modo_txt = "SIN normalizar" if sin_normalizar else "normalizado (t0=100%)"

    instrumentos = [c for c in df.columns if df[c].dtype in (np.float64, np.int64, float)]
    if not instrumentos:
        logger.error("No hay columnas numéricas en el CSV.")
        return False

    os.makedirs(out_dir, exist_ok=True)

    resultados = []
    tendencias = {}  # instrumento -> (x_weeks, y_obs, y_pred) para el gráfico

    for inst in instrumentos:
        y = df[inst].dropna().reindex(df.index)
        y = y.dropna()
        if len(y) < 3:
            logger.warning("Omite %s: menos de 3 puntos.", inst)
            continue
        # Índice de semana alineado: 0, 1, 2, ... para las filas con dato
        x = np.arange(len(y))
        y_vals = y.values
        pendiente, ordenada, r2, pval, stderr = regresion_linear(x, y_vals)
        if pendiente is None:
            continue
        # Pendiente está en % por "unidad de x"; x avanza 1 por semana → pendiente = %/semana
        pendiente_por_mes = pendiente * (365.25 / 7) / 12  # aprox % por mes (4.35 semanas/mes)
        resultados.append({
            "instrumento": inst,
            "pendiente_por_semana": round(pendiente, 6),
            "pendiente_por_mes": round(pendiente_por_mes, 4),
            "R2": round(r2, 4),
            "p_value": round(pval, 4),
            "n_semanas": len(y),
        })
        # Guardar para gráfico: usar índice temporal real (fechas) para las filas con dato
        x_full = np.arange(len(df))
        y_pred_full = ordenada + pendiente * x_full
        tendencias[inst] = (df.index.values, df[inst].values, y_pred_full)
        logger.info("%s: pendiente = %+.4f %%/semana, R² = %.4f, p = %.4f", inst, pendiente, r2, pval)

    if not resultados:
        logger.error("No se pudo calcular ninguna tendencia.")
        return False

    # CSV resumen: principal sin PV Glasses (pendiente no comparable); _completo con todos
    resultados_sin_pg = [r for r in resultados if r["instrumento"] != "PV Glasses"]
    df_res = pd.DataFrame(resultados_sin_pg)
    path_csv = os.path.join(out_dir, "tendencias_resumen.csv")
    df_res.to_csv(path_csv, index=False)
    logger.info("Resumen (sin PV Glasses): %s", path_csv)
    df_res_completo = pd.DataFrame(resultados)
    path_csv_completo = os.path.join(out_dir, "tendencias_resumen_completo.csv")
    df_res_completo.to_csv(path_csv_completo, index=False)
    logger.info("Resumen completo (con PV Glasses): %s", path_csv_completo)

    # --- Pendientes entre semanas (tramos entre observaciones consecutivas con dato)
    df_pend = _tabla_pendientes_entre_semanas(df, instrumentos)
    path_pend = os.path.join(out_dir, "pendientes_entre_semanas.csv")
    df_pend.to_csv(path_pend, index=False)
    logger.info("Pendientes entre semanas: %s (%d filas)", path_pend, len(df_pend))

    df_1sem = df_pend[df_pend["dias_entre_semanas"] == 7].copy()
    path_1 = os.path.join(out_dir, "pendientes_entre_semanas_tramo_1_semana_calendario.csv")
    df_1sem.to_csv(path_1, index=False)
    logger.info("Pendientes solo tramos 7 días: %s (%d filas)", path_1, len(df_1sem))

    df_pend_res = _resumen_pendientes_por_instrumento(df_pend)
    path_pres = os.path.join(out_dir, "pendientes_entre_semanas_resumen_por_instrumento.csv")
    df_pend_res.to_csv(path_pres, index=False)
    logger.info("Resumen pendientes por instrumento: %s", path_pres)

    # Retrocompatibilidad: mismo contenido que antes (delta_pp = pendiente_pp)
    path_delta = os.path.join(out_dir, "delta_semanal_sr_q25_punto_a_punto.csv")
    df_delta_legacy = df_pend.rename(columns={
        "semana_actual": "semana",
        "sr_semana_anterior": "sr_q25_semana_anterior",
        "sr_semana_actual": "sr_q25_semana",
    })
    if "pendiente_pp" in df_delta_legacy.columns:
        df_delta_legacy = df_delta_legacy.assign(delta_pp=df_delta_legacy["pendiente_pp"])
    cols_legacy = [
        c for c in [
            "instrumento", "semana_anterior", "semana",
            "sr_q25_semana_anterior", "sr_q25_semana",
            "delta_pp", "delta_relativa_pct",
        ] if c in df_delta_legacy.columns
    ]
    df_delta_legacy[cols_legacy].to_csv(path_delta, index=False)
    logger.info("Delta semanal (legacy): %s", path_delta)

    if MATPLOTLIB_AVAILABLE and not df_pend.empty:
        grafico_boxplot_pendientes_entre_semanas(
            df_pend,
            os.path.join(out_dir, "pendientes_entre_semanas_boxplot.png"),
            modo_txt=modo_txt,
            excluir_pv_glasses=True,
        )
        grafico_boxplot_pendientes_entre_semanas(
            df_pend,
            os.path.join(out_dir, "pendientes_entre_semanas_boxplot_completo.png"),
            modo_txt=modo_txt,
            excluir_pv_glasses=False,
        )
        if not df_1sem.empty:
            grafico_boxplot_pendientes_entre_semanas(
                df_1sem,
                os.path.join(out_dir, "pendientes_entre_semanas_tramo_7d_boxplot.png"),
                modo_txt=modo_txt,
                excluir_pv_glasses=True,
                subtitulo="Solo tramos con 7 días entre fechas (semanas ISO consecutivas)",
            )

    # --- Serie mensual + tendencia lineal (%/mes)
    df_m_weekly = _agregar_mensual_media_semanas(df, instrumentos)
    mensual_desde_diario = False
    txt_metodo_mensual = "media de Q25 semanales por mes"
    if sr_dir and os.path.isdir(sr_dir) and sin_normalizar:
        df_m_diario = _mensual_q25_desde_diario(sr_dir)
        if not df_m_diario.empty:
            df_mensual = df_m_weekly.copy()
            for c in df_m_diario.columns:
                if c in df_mensual.columns:
                    df_mensual[c] = df_m_diario[c]
            mensual_desde_diario = True
            txt_metodo_mensual = "Q25 de datos diarios por mes (PV Glasses: media de Q25 semanales)"
            logger.info(
                "SR mensual: Q25 desde datos diarios en %s (columnas: %s).",
                sr_dir, ", ".join(df_m_diario.columns),
            )
        else:
            df_mensual = df_m_weekly
            logger.warning(
                "sr_dir=%s no produjo series diarias; se usa media de Q25 semanales.", sr_dir,
            )
    elif sr_dir and os.path.isdir(sr_dir) and not sin_normalizar:
        df_mensual = df_m_weekly
        logger.info(
            "Entrada normalizada: SR mensual = media de Q25 semanales (no se aplican CSV diarios).",
        )
    else:
        df_mensual = df_m_weekly

    df_mensual.index.name = "mes"
    if mensual_desde_diario:
        path_mserie = os.path.join(out_dir, "sr_mensual_q25_desde_datos_diarios.csv")
    else:
        path_mserie = os.path.join(out_dir, "sr_mensual_promedio_q25_semanales.csv")
    df_mensual.to_csv(path_mserie)
    logger.info("Serie mensual (%s): %s", txt_metodo_mensual, path_mserie)

    # --- Pendientes entre meses (misma serie mensual que arriba)
    df_pend_m = _tabla_pendientes_entre_meses(df_mensual, instrumentos)
    path_pm = os.path.join(out_dir, "pendientes_entre_meses.csv")
    df_pend_m.to_csv(path_pm, index=False)
    logger.info("Pendientes entre meses: %s (%d filas)", path_pm, len(df_pend_m))

    df_1m = df_pend_m[df_pend_m["meses_calendario_entre_puntos"] == 1].copy()
    path_1m = os.path.join(out_dir, "pendientes_entre_meses_tramo_1_mes_calendario.csv")
    df_1m.to_csv(path_1m, index=False)
    logger.info("Pendientes mes a mes (1 mes calendario): %s (%d filas)", path_1m, len(df_1m))

    df_pend_m_res = _resumen_pendientes_entre_meses(df_pend_m)
    path_pm_res = os.path.join(out_dir, "pendientes_entre_meses_resumen_por_instrumento.csv")
    df_pend_m_res.to_csv(path_pm_res, index=False)
    logger.info("Resumen pendientes entre meses: %s", path_pm_res)

    resultados_m = []
    tendencias_m = {}
    for inst in instrumentos:
        y = df_mensual[inst].dropna()
        if len(y) < 3:
            logger.warning("Tendencia mensual: omite %s: menos de 3 meses con dato.", inst)
            continue
        x = np.arange(len(y))
        y_vals = y.values
        pendiente, ordenada, r2, pval, _stderr = regresion_linear(x, y_vals)
        if pendiente is None:
            continue
        resultados_m.append({
            "instrumento": inst,
            "pendiente_por_mes": round(pendiente, 6),
            "pendiente_por_semana_aprox": round(pendiente / (365.25 / 12 / 7), 6),
            "R2": round(r2, 4),
            "p_value": round(pval, 4),
            "n_meses": len(y),
        })
        # Recta alineada al índice temporal: x = 0,1,... solo en meses con dato (mismo ajuste que regresión)
        x_pos = pd.Series(np.nan, index=df_mensual.index, dtype=float)
        k = 0
        for t in df_mensual.index:
            if pd.notna(df_mensual.loc[t, inst]):
                x_pos.loc[t] = float(k)
                k += 1
        y_pred_full = ordenada + pendiente * x_pos.values
        tendencias_m[inst] = (df_mensual.index.values, df_mensual[inst].values, y_pred_full)
        logger.info(
            "%s (mensual): pendiente = %+.4f %%/mes, R² = %.4f, p = %.4f",
            inst, pendiente, r2, pval,
        )

    if resultados_m:
        res_m_sin_pg = [r for r in resultados_m if r["instrumento"] != "PV Glasses"]
        pd.DataFrame(res_m_sin_pg).to_csv(
            os.path.join(out_dir, "tendencias_mensuales_resumen.csv"), index=False)
        logger.info("Resumen tendencias mensuales (sin PV Glasses): %s", os.path.join(out_dir, "tendencias_mensuales_resumen.csv"))
        pd.DataFrame(resultados_m).to_csv(
            os.path.join(out_dir, "tendencias_mensuales_resumen_completo.csv"), index=False)
        logger.info("Resumen tendencias mensuales completo: %s", os.path.join(out_dir, "tendencias_mensuales_resumen_completo.csv"))

    # Gráfico: series + rectas de tendencia (sin PV Glasses para comparabilidad de pendientes)
    if MATPLOTLIB_AVAILABLE:
        fig, ax = plt.subplots(figsize=(14, 6))
        insts_grafico = [r["instrumento"] for r in resultados_sin_pg]
        for inst in insts_grafico:
            if inst not in tendencias:
                continue
            fechas, y_obs, y_pred = tendencias[inst]
            color = color_metodo(inst)
            ax.plot(fechas, y_obs, "o-", color=color, alpha=0.7, linewidth=1, markersize=3,
                    label=etiqueta_metodo_mathtext(inst))
            ax.plot(fechas, y_pred, "--", color=color, alpha=0.9, linewidth=1.2)
        ax.axhline(100, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
        ax.set_xlabel("Fecha", fontsize=15)
        ax.set_ylabel("SR (%)", fontsize=15)
        ax.set_title(
            titulo_reemplazar_iv600_pmax_isc(
                f"SR semanal Q25 ({modo_txt}) y tendencia lineal por metodología (IV600 Pmax/Isc valor absoluto)"
            ),
            fontsize=16, pad=12,
        )
        ax.xaxis.set_major_formatter(FuncFormatter(_fmt_month_es))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.legend(loc="lower left", fontsize=13, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=85)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "tendencias_grafico.png"), dpi=220, bbox_inches="tight")
        plt.close()
        logger.info("Gráfico: %s/tendencias_grafico.png", out_dir)

        # Barras de pendiente (sin PV Glasses)
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        insts = [r["instrumento"] for r in resultados_sin_pg]
        pendientes = [r["pendiente_por_semana"] for r in resultados_sin_pg]
        colores = [color_metodo(i) for i in insts]
        xb = np.arange(len(insts))
        ax2.bar(xb, pendientes, color=colores, alpha=0.8, edgecolor="gray")
        ax2.set_xticks(xb)
        ax2.set_xticklabels(ticklabels_mathtext(insts), rotation=25, ha="right")
        ax2.axhline(0, color="black", linewidth=0.8)
        ax2.set_ylabel("Pendiente (% por semana)", fontsize=15)
        ax2.set_title("Tendencia lineal del SR semanal por metodología", fontsize=16, pad=12)
        ax2.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "tendencias_pendientes.png"), dpi=220, bbox_inches="tight")
        plt.close()
        logger.info("Pendientes: %s/tendencias_pendientes.png", out_dir)

        # --- Gráficos tendencia MENSUAL (misma paleta; sin PV Glasses en principal)
        if resultados_m:
            res_m_sin_pg = [r for r in resultados_m if r["instrumento"] != "PV Glasses"]
            insts_m = [r["instrumento"] for r in res_m_sin_pg]
            fig_m, ax_m = plt.subplots(figsize=(14, 6))
            for inst in insts_m:
                if inst not in tendencias_m:
                    continue
                fechas, y_obs, y_pred = tendencias_m[inst]
                color = color_metodo(inst)
                ax_m.plot(fechas, y_obs, "o-", color=color, alpha=0.7, linewidth=1, markersize=4,
                          label=etiqueta_metodo_mathtext(inst))
                ax_m.plot(fechas, y_pred, "--", color=color, alpha=0.9, linewidth=1.2)
            ax_m.axhline(100, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
            ax_m.set_xlabel("Mes (fin de mes)", fontsize=15)
            ylab_m = (
                "SR (%) — Q25 diarios por mes"
                if mensual_desde_diario
                else "SR (%) — media Q25 semanales del mes"
            )
            ax_m.set_ylabel(ylab_m, fontsize=15)
            tit_m = (
                f"SR mensual ({txt_metodo_mensual}) ({modo_txt}) y tendencia lineal"
            )
            ax_m.set_title(tit_m, fontsize=16, pad=12)
            ax_m.xaxis.set_major_formatter(FuncFormatter(_fmt_month_es))
            ax_m.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
            ax_m.legend(loc="lower left", fontsize=13, ncol=2)
            ax_m.grid(True, alpha=0.3)
            ax_m.set_ylim(bottom=85)
            plt.setp(ax_m.xaxis.get_majorticklabels(), rotation=15, ha="right")
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, "tendencias_mensuales_grafico.png"), dpi=220, bbox_inches="tight")
            plt.close()
            logger.info("Gráfico mensual: %s/tendencias_mensuales_grafico.png", out_dir)

            fig_mb, ax_mb = plt.subplots(figsize=(10, 5))
            pend_m = [r["pendiente_por_mes"] for r in res_m_sin_pg]
            col_m = [color_metodo(j) for j in insts_m]
            xbm = np.arange(len(insts_m))
            ax_mb.bar(xbm, pend_m, color=col_m, alpha=0.8, edgecolor="gray")
            ax_mb.set_xticks(xbm)
            ax_mb.set_xticklabels(ticklabels_mathtext(insts_m), rotation=25, ha="right")
            ax_mb.axhline(0, color="black", linewidth=0.8)
            ax_mb.set_ylabel("Pendiente (% por mes)", fontsize=15)
            ax_mb.set_title("Tendencia lineal del SR mensual por metodología", fontsize=16, pad=12)
            ax_mb.grid(True, axis="y", alpha=0.3)
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, "tendencias_mensuales_pendientes.png"), dpi=220, bbox_inches="tight")
            plt.close()
            logger.info("Pendientes mensuales: %s/tendencias_mensuales_pendientes.png", out_dir)

    # Reporte Markdown
    lineas = [
        "# Análisis de tendencias — SR semanal Q25 ({}) ({})".format(
            modo_txt,
            titulo_reemplazar_iv600_pmax_isc("IV600 Pmax/Isc valor absoluto"),
        ),
        "",
        "Regresión lineal **SR = a + b × (semana)** por metodología. La pendiente **b** es la tasa de cambio en % por semana.",
        "",
        "## Resumen",
        "",
        "| Instrumento | Pendiente (%/semana) | Pendiente (%/mes) | R² | p-value | n_semanas |",
        "|-------------|---------------------|-------------------|-----|---------|-----------|",
    ]
    for r in resultados_sin_pg:
        lineas.append("| {} | {:+.4f} | {:+.4f} | {:.4f} | {:.4f} | {} |".format(
            r["instrumento"], r["pendiente_por_semana"], r["pendiente_por_mes"],
            r["R2"], r["p_value"], r["n_semanas"]))
    lineas.extend([
        "",
        "## Interpretación",
        "",
        "- **Pendiente negativa:** el SR tiende a bajar en el tiempo (acumulación de soiling o deriva).",
        "- **Pendiente ≈ 0:** el SR se mantiene estable en promedio.",
        "- **Pendiente positiva:** el SR tiende a subir (recuperación, lluvia, o efecto estacional).",
        "- **R²** mide cuánto de la variabilidad del SR se explica por la tendencia lineal.",
        "- **p-value < 0,05** sugiere que la pendiente es estadísticamente significativa.",
        "",
        "## Tendencias mensuales",
        "",
        f"**Método en esta ejecución:** {txt_metodo_mensual}.",
        "Regresión lineal **SR_mes = a + b × (índice de mes con dato)**; **b** = % SR por mes.",
        "",
        f"Serie numérica: `{os.path.basename(path_mserie)}` + `tendencias_mensuales_resumen.csv` + gráficos `tendencias_mensuales_*.png`.",
        "",
        "### Cambio mes a mes (punto a punto)",
        "",
        "- `pendientes_entre_meses.csv`: **pendiente_pp** entre meses consecutivos **en la serie observada**; **meses_calendario_entre_puntos**; **pendiente_pp_por_mes_calendario**.",
        "- `pendientes_entre_meses_tramo_1_mes_calendario.csv`: solo cuando entre fechas hay **1 mes** de calendario.",
        "- `pendientes_entre_meses_resumen_por_instrumento.csv`: medias / desviaciones.",
        "",
        "## Pendientes entre semanas",
        "",
        "- `pendientes_entre_semanas.csv`: entre cada par de semanas **consecutivas en la serie observada** (solo días con dato),",
        "  **pendiente_pp** = cambio de SR; **semanas_calendario** = días/7 entre fechas; **pendiente_pp_por_semana_calendario** = pendiente_pp / semanas_calendario.",
        "- `pendientes_entre_semanas_tramo_1_semana_calendario.csv`: solo tramos con **7 días** entre fechas (semanas ISO contiguas).",
        "- `pendientes_entre_semanas_resumen_por_instrumento.csv`: medias y desviaciones por instrumento.",
        "- `delta_semanal_sr_q25_punto_a_punto.csv`: columnas antiguas (delta_pp = pendiente_pp).",
        "",
    ])
    with open(os.path.join(out_dir, "tendencias_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    logger.info("Reporte: %s/tendencias_report.md", out_dir)

    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    norm_csv = os.path.join(project_root, "analysis", "stats", "sr_semanal_norm.csv")
    out_dir = os.path.join(project_root, "analysis", "tendencias")
    sr_dir = None
    argv_pos = [a for a in sys.argv[1:] if not str(a).startswith("--")]
    if len(argv_pos) >= 1:
        norm_csv = os.path.abspath(argv_pos[0])
    if len(argv_pos) >= 2:
        out_dir = os.path.abspath(argv_pos[1])
    if len(argv_pos) >= 3:
        sr_dir = os.path.abspath(argv_pos[2])
    logger.info("Entrada: %s | Salida: %s | sr_dir (diario mensual): %s", norm_csv, out_dir, sr_dir)
    ok = run(norm_csv, out_dir, sr_dir=sr_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
