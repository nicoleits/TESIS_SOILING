"""
Análisis de tendencias del SR semanal: regresión lineal por metodología.

Para cada metodología se ajusta SR semanal Q25 normalizado (t₀=100%) vs tiempo
(semana 0, 1, 2, ...). La pendiente indica la tasa de cambio promedio (% por semana):
  - Pendiente negativa: tendencia a la baja (soiling acumulado).
  - Pendiente ≈ 0: estable.
  - Pendiente positiva: recuperación o ganancia relativa.

Salidas en analysis/tendencias/:
  - tendencias_resumen.csv   : instrumento, pendiente_por_semana, pendiente_por_mes, R2, p_value, n_semanas
  - tendencias_grafico.png   : series observadas + rectas de tendencia
  - tendencias_pendientes.png: barras de pendiente por instrumento
  - tendencias_report.md     : resumen breve

Entrada: analysis/stats/sr_semanal_norm.csv (generado por agregacion_semanal).

Uso (desde si_test con PYTHONPATH=TESIS_SOILING):
  python -m analysis.tendencias.analisis_tendencias
  python -m analysis.tendencias.analisis_tendencias [ruta_sr_semanal_norm.csv] [carpeta_salida]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

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
    plt.rcParams["axes.formatter.use_locale"] = True
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


def run(norm_csv_path, out_dir):
    if not os.path.isfile(norm_csv_path):
        logger.error("No encontrado: %s", norm_csv_path)
        return False

    df = pd.read_csv(norm_csv_path)
    if "semana" not in df.columns:
        logger.error("Se espera columna 'semana' en el CSV.")
        return False
    df["semana"] = pd.to_datetime(df["semana"])
    df = df.set_index("semana").sort_index()

    instrumentos = [c for c in df.columns if df[c].dtype in (np.float64, np.int64, float)]
    if not instrumentos:
        logger.error("No hay columnas numéricas en el CSV.")
        return False

    os.makedirs(out_dir, exist_ok=True)
    semanas_num = np.arange(len(df))

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

    # CSV resumen
    df_res = pd.DataFrame(resultados)
    path_csv = os.path.join(out_dir, "tendencias_resumen.csv")
    df_res.to_csv(path_csv, index=False)
    logger.info("Resumen: %s", path_csv)

    # Gráfico: series + rectas de tendencia
    if MATPLOTLIB_AVAILABLE:
        fig, ax = plt.subplots(figsize=(14, 6))
        colors = ["#D32F2F", "#FF6F00", "#388E3C", "#1976D2", "#7B1FA2", "#C2185B", "#0097A7"]
        for i, inst in enumerate(instrumentos):
            if inst not in tendencias:
                continue
            fechas, y_obs, y_pred = tendencias[inst]
            color = colors[i % len(colors)]
            ax.plot(fechas, y_obs, "o-", color=color, alpha=0.7, linewidth=1, markersize=3, label=inst)
            ax.plot(fechas, y_pred, "--", color=color, alpha=0.9, linewidth=1.2)
        ax.axhline(100, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)
        ax.set_xlabel("Fecha", fontsize=12)
        ax.set_ylabel("SR (%)", fontsize=12)
        ax.set_title("SR semanal Q25 normalizado y tendencia lineal por metodología", fontsize=13, pad=10)
        ax.xaxis.set_major_formatter(FuncFormatter(_fmt_month_es))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.legend(loc="lower left", fontsize=9, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=85)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=15, ha="right")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "tendencias_grafico.png"), dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Gráfico: %s/tendencias_grafico.png", out_dir)

        # Barras de pendiente
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        insts = [r["instrumento"] for r in resultados]
        pendientes = [r["pendiente_por_semana"] for r in resultados]
        colores = [colors[i % len(colors)] for i in range(len(insts))]
        bars = ax2.bar(insts, pendientes, color=colores, alpha=0.8, edgecolor="gray")
        ax2.axhline(0, color="black", linewidth=0.8)
        ax2.set_ylabel("Pendiente (% por semana)", fontsize=12)
        ax2.set_title("Tendencia lineal del SR semanal normalizado por metodología", fontsize=13, pad=10)
        plt.xticks(rotation=25, ha="right")
        ax2.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "tendencias_pendientes.png"), dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Pendientes: %s/tendencias_pendientes.png", out_dir)

    # Reporte Markdown
    lineas = [
        "# Análisis de tendencias — SR semanal Q25 normalizado",
        "",
        "Regresión lineal **SR = a + b × (semana)** por metodología. La pendiente **b** es la tasa de cambio en % por semana.",
        "",
        "## Resumen",
        "",
        "| Instrumento | Pendiente (%/semana) | Pendiente (%/mes) | R² | p-value | n_semanas |",
        "|-------------|---------------------|-------------------|-----|---------|-----------|",
    ]
    for r in resultados:
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
    ])
    with open(os.path.join(out_dir, "tendencias_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    logger.info("Reporte: %s/tendencias_report.md", out_dir)

    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    norm_csv = os.path.join(project_root, "analysis", "stats", "sr_semanal_norm.csv")
    out_dir = os.path.join(project_root, "analysis", "tendencias")
    if len(sys.argv) > 1:
        norm_csv = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        out_dir = os.path.abspath(sys.argv[2])
    logger.info("Entrada: %s | Salida: %s", norm_csv, out_dir)
    ok = run(norm_csv, out_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
