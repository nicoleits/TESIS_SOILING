"""
Sesgo de cada metodología respecto a una única referencia: PVStand Isc (SR por Isc).

Usa SR semanal Q25 (sr_semanal_norm.csv; IV600 Pmax/Isc valor absoluto). Para cada método se calcula
el error con signo e_i = SR_m,i - SR_PVStand Isc,i solo en semanas comunes (sin rellenar NaN).
Métricas: MBE, mediana del error, P25, P75, SD del error, RMSE; opcional MBE%.

Salidas en analysis/sesgo/:
  sesgo_tabla.csv           : tabla por método (n, MBE pp, mediana, P25, P75, SD, RMSE, MBE%)
  sesgo_barras_mbe.png      : barras MBE (pp) por método, línea en 0
  sesgo_error_vs_semana.png : error e_i vs semana por método

Uso (desde TESIS_SOILING):
  python -m analysis.sesgo.sesgo_referencia
"""
import os
import sys
import logging

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import locale
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    try:
        locale.setlocale(locale.LC_NUMERIC, "es_ES.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_NUMERIC, "es_ES")
        except locale.Error:
            pass
    plt.rcParams["axes.formatter.use_locale"] = True

    def _formatter_coma(x, pos=None):
        return f"{x:.2f}".replace(".", ",")

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    FuncFormatter = None
    _formatter_coma = None

REFERENCIA = "PVStand Isc"


def cargar_semanal_norm(csv_path):
    """Carga tabla semanal: índice = semana, columnas = metodologías. Sin rellenar NaN."""
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    df.index.name = "semana"
    return df


def metodologias_a_evaluar(df):
    """Todas las columnas excepto la referencia (no comparamos referencia consigo misma)."""
    return [c for c in df.columns if c != REFERENCIA]


def sesgo_por_metodo(df, metodo):
    """
    Para un método: solo semanas comunes con PVStand Isc.
    e_i = SR_m,i - SR_PVStand Isc,i (error con signo).
    Retorna serie de errores y n.
    """
    sub = df[[REFERENCIA, metodo]].dropna(how="any")
    if len(sub) == 0:
        return pd.Series(dtype=float), 0
    e = sub[metodo] - sub[REFERENCIA]
    return e, len(sub)


def metricas_sesgo(e, sr_ref_media=None):
    """
    e: serie de errores con signo (en misma unidad que SR, ej. 0-100).
    Retorna dict con MBE, mediana, P25, P75, SD, RMSE; opcional MBE_pct.
    """
    if e is None or len(e) == 0:
        return None
    e = e.astype(float)
    n = len(e)
    mbe = float(e.mean())
    mediana = float(e.median())
    p25 = float(e.quantile(0.25))
    p75 = float(e.quantile(0.75))
    sd = float(e.std()) if n > 1 else 0.0
    rmse = float(np.sqrt((e ** 2).mean()))
    out = {
        "n": n,
        "MBE_pp": round(mbe, 4),
        "mediana_error_pp": round(mediana, 4),
        "P25_pp": round(p25, 4),
        "P75_pp": round(p75, 4),
        "SD_error_pp": round(sd, 4),
        "RMSE_pp": round(rmse, 4),
    }
    if sr_ref_media is not None and sr_ref_media != 0:
        mbe_pct = 100.0 * mbe / sr_ref_media
        out["MBE_pct"] = round(mbe_pct, 2)
    else:
        out["MBE_pct"] = None
    return out


def tabla_sesgo(df, out_path):
    """
    Tabla final: Método evaluado, Referencia, n, MBE (pp), Mediana error (pp), P25, P75, SD error, RMSE, MBE%.
    """
    ref_serie = df[REFERENCIA].dropna()
    sr_ref_media = float(ref_serie.mean()) if len(ref_serie) > 0 else None
    metodos = metodologias_a_evaluar(df)
    rows = []
    for metodo in metodos:
        e, n = sesgo_por_metodo(df, metodo)
        if n == 0:
            rows.append({
                "metodo_evaluado": metodo,
                "referencia": REFERENCIA,
                "n": 0,
                "MBE_pp": np.nan,
                "mediana_error_pp": np.nan,
                "P25_pp": np.nan,
                "P75_pp": np.nan,
                "SD_error_pp": np.nan,
                "RMSE_pp": np.nan,
                "MBE_pct": np.nan,
            })
            continue
        m = metricas_sesgo(e, sr_ref_media)
        rows.append({
            "metodo_evaluado": metodo,
            "referencia": REFERENCIA,
            "n": m["n"],
            "MBE_pp": m["MBE_pp"],
            "mediana_error_pp": m["mediana_error_pp"],
            "P25_pp": m["P25_pp"],
            "P75_pp": m["P75_pp"],
            "SD_error_pp": m["SD_error_pp"],
            "RMSE_pp": m["RMSE_pp"],
            "MBE_pct": m["MBE_pct"] if m["MBE_pct"] is not None else np.nan,
        })
    tabla = pd.DataFrame(rows)
    tabla.to_csv(out_path, index=False)
    logger.info("Tabla sesgo: %s", out_path)
    return tabla


def errores_por_semana_por_metodo(df):
    """
    Dict metodo -> DataFrame con index=semana, columnas [referencia, metodo, error_pp].
    Solo semanas comunes (sin NaN).
    """
    metodos = metodologias_a_evaluar(df)
    out = {}
    for metodo in metodos:
        sub = df[[REFERENCIA, metodo]].dropna(how="any")
        if len(sub) == 0:
            out[metodo] = pd.DataFrame(columns=["referencia", "metodo", "error_pp"])
            continue
        e = sub[metodo] - sub[REFERENCIA]
        out[metodo] = pd.DataFrame({
            "referencia": sub[REFERENCIA].values,
            "metodo": sub[metodo].values,
            "error_pp": e.values,
        }, index=sub.index)
    return out


def grafico_barras_mbe(tabla, out_path):
    """Barras: eje x = método, eje y = MBE (pp), línea horizontal en 0."""
    if not MATPLOTLIB_AVAILABLE or len(tabla) == 0:
        return
    tabla = tabla[tabla["n"] > 0].copy()
    if len(tabla) == 0:
        return
    fig, ax = plt.subplots(figsize=(max(8, len(tabla) * 0.9), 5))
    x = np.arange(len(tabla))
    colors = ["C1" if v > 0 else "C0" for v in tabla["MBE_pp"]]
    ax.bar(x, tabla["MBE_pp"], color=colors, edgecolor="gray")
    ax.axhline(0, color="black", linewidth=0.8, linestyle="-")
    ax.set_xticks(x)
    ax.set_xticklabels(tabla["metodo_evaluado"], rotation=35, ha="right", fontsize=9)
    ax.set_ylabel("MBE (pp)")
    if FuncFormatter is not None:
        # Eje Y sin decimales (quitar dos ceros)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x:.0f}"))
    ax.set_title(f"Sesgo medio respecto a {REFERENCIA}\n(SR semanal Q25; IV600 Pmax/Isc valor absoluto)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico barras MBE: %s", out_path)


def grafico_error_vs_semana(df, out_path):
    """Todas las series de error en un solo gráfico, con n en la leyenda."""
    dict_errores = errores_por_semana_por_metodo(df)
    metodos = [m for m in dict_errores if len(dict_errores[m]) > 0]
    if not MATPLOTLIB_AVAILABLE or len(metodos) == 0:
        return
    fig, ax = plt.subplots(figsize=(12, 5))
    for idx, metodo in enumerate(metodos):
        d = dict_errores[metodo]
        ax.plot(d.index, d["error_pp"], "o-", markersize=4,
                label=f"{metodo} (n={len(d)})", color=f"C{idx}")
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--")
    ax.set_ylabel("Error (pp)")
    ax.set_xlabel("Semana")
    if _formatter_coma is not None:
        ax.yaxis.set_major_formatter(FuncFormatter(_formatter_coma))
    ax.set_title(f"Error con signo (SR_m − SR_{{{REFERENCIA}}}) por semana",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="best")
    ax.tick_params(axis="x", rotation=25)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    logger.info("Gráfico error vs semana: %s", out_path)


def run(norm_csv, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df = cargar_semanal_norm(norm_csv)
    if REFERENCIA not in df.columns:
        logger.error("Referencia '%s' no encontrada en el CSV. Columnas: %s", REFERENCIA, list(df.columns))
        return False
    logger.info("Referencia: %s | Métodos: %s", REFERENCIA, metodologias_a_evaluar(df))
    tabla = tabla_sesgo(df, os.path.join(out_dir, "sesgo_tabla.csv"))
    if MATPLOTLIB_AVAILABLE:
        grafico_barras_mbe(tabla, os.path.join(out_dir, "sesgo_barras_mbe.png"))
        grafico_error_vs_semana(df, os.path.join(out_dir, "sesgo_error_vs_semana.png"))
    return True


def main():
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    norm_csv = os.path.join(project_root, "analysis", "stats", "sr_semanal_norm.csv")
    out_dir = os.path.join(project_root, "analysis", "sesgo")
    if len(sys.argv) > 1:
        norm_csv = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        out_dir = os.path.abspath(sys.argv[2])
    logger.info("Input: %s | Salida: %s", norm_csv, out_dir)
    ok = run(norm_csv, out_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
