"""
Figura 4.4b — Dispersión diaria por método.

Para cada método se calcula |ΔSR| día a día (diferencia absoluta entre días consecutivos)
y se resume con la mediana y el P95. Se grafica una barra por método (altura = mediana de |ΔSR|).

Interpretación: qué tan "saltón" es cada método día a día.

Entrada: analysis/sr/*.csv (mismo periodo que agregación semanal).
Salida:
  - dispersion_diaria_metodo.csv : mediana y P95 de |ΔSR| por método (datos del gráfico de barras)
  - dispersion_diaria_deltas_punto_a_punto.csv : cada tramo día a día (fechas, SR, |ΔSR|)
  - dispersion_diaria_metodo.png

Uso (desde si_test con PYTHONPATH=TESIS_SOILING):
  python -m analysis.stats.dispersion_diaria
  python -m analysis.stats.dispersion_diaria [SR_DIR] [OUT_DIR]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from analysis.plot_metodos import color_metodo, configure_matplotlib_for_thesis, ticklabels_mathtext

try:
    import locale
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
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

try:
    from analysis.config import PERIODO_ANALISIS_INICIO, PERIODO_ANALISIS_FIN, REFCELLS_FECHA_MAX
except ImportError:
    PERIODO_ANALISIS_INICIO = "2024-08-03"
    PERIODO_ANALISIS_FIN = "2025-08-04"
    REFCELLS_FECHA_MAX = "2025-05-20"

# Misma configuración que agregacion_semanal: (nombre, ruta_csv, col_sr, fecha_max_override)
def _build_config(sr_dir):
    return [
        ("Soiling Kit",   os.path.join(sr_dir, "soilingkit_sr.csv"),       "SR",                  None),
        ("DustIQ",        os.path.join(sr_dir, "dustiq_sr.csv"),            "SR",                  None),
        ("RefCells",      os.path.join(sr_dir, "refcells_sr.csv"),         "SR",                  REFCELLS_FECHA_MAX),
        ("PVStand Pmax",  os.path.join(sr_dir, "pvstand_sr_corr.csv"),     "SR_Pmax_corr",        None),
        ("PVStand Isc",   os.path.join(sr_dir, "pvstand_sr_corr.csv"),     "SR_Isc_corr",         None),
        ("IV600 Pmax",    os.path.join(sr_dir, "iv600_sr_corr.csv"),       "SR_Pmax_corr_434",    None),
        ("IV600 Isc",     os.path.join(sr_dir, "iv600_sr_corr.csv"),       "SR_Isc_corr_434",    None),
    ]


def _get_time_col(df):
    for c in df.columns:
        if any(t in c.lower() for t in ("time", "fecha", "timestamp", "date")):
            return c
    return None


def cargar_sr_diario(ruta, col_sr, fecha_min=None, fecha_max=None):
    """Serie de SR con un valor por día, índice = fecha."""
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
    if df.empty or len(df) < 2:
        return None
    serie = df.set_index("fecha")[col_sr].sort_index()
    return serie


def dispersion_dia_a_dia(serie):
    """
    |ΔSR| entre días consecutivos. Devuelve array de diferencias absolutas.
    """
    if serie is None or len(serie) < 2:
        return np.array([])
    sr = serie.values.astype(float)
    delta = np.abs(np.diff(sr))
    return delta


def run(sr_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    config = _build_config(sr_dir)
    resultados = []
    deltas_largo_rows = []

    for nombre, ruta, col_sr, fecha_max_override in config:
        fecha_max = fecha_max_override if fecha_max_override is not None else PERIODO_ANALISIS_FIN
        serie = cargar_sr_diario(ruta, col_sr, fecha_min=PERIODO_ANALISIS_INICIO, fecha_max=fecha_max)
        if serie is None or len(serie) < 2:
            logger.warning("Omite %s: pocos datos.", nombre)
            continue
        delta = dispersion_dia_a_dia(serie)
        if len(delta) == 0:
            continue
        mediana = float(np.median(delta))
        p95 = float(np.percentile(delta, 95))
        resultados.append({
            "metodo": nombre,
            "mediana_abs_delta_sr": round(mediana, 4),
            "p95_abs_delta_sr": round(p95, 4),
            "n_dias": len(serie),
            "n_deltas": len(delta),
        })
        logger.info("%s: mediana(|ΔSR|) = %.4f %%, P95 = %.4f %%", nombre, mediana, p95)

        idx = serie.index
        vals = serie.values.astype(float)
        for i in range(len(vals) - 1):
            dabs = abs(float(vals[i + 1]) - float(vals[i]))
            f0, f1 = idx[i], idx[i + 1]
            deltas_largo_rows.append({
                "metodo": nombre,
                "fecha": f0.isoformat() if hasattr(f0, "isoformat") else str(f0),
                "fecha_dia_siguiente": f1.isoformat() if hasattr(f1, "isoformat") else str(f1),
                "sr_dia": round(float(vals[i]), 4),
                "sr_dia_siguiente": round(float(vals[i + 1]), 4),
                "abs_delta_sr_pp": round(dabs, 4),
            })

    if not resultados:
        logger.error("No se pudo calcular dispersión diaria.")
        return False

    df = pd.DataFrame(resultados)
    path_csv = os.path.join(out_dir, "dispersion_diaria_metodo.csv")
    df.to_csv(path_csv, index=False)
    logger.info("CSV resumen (gráfico): %s", path_csv)

    path_delta_largo = os.path.join(out_dir, "dispersion_diaria_deltas_punto_a_punto.csv")
    pd.DataFrame(deltas_largo_rows).to_csv(path_delta_largo, index=False)
    logger.info("CSV deltas día a día: %s (%d filas)", path_delta_largo, len(deltas_largo_rows))

    if MATPLOTLIB_AVAILABLE:
        fig, ax = plt.subplots(figsize=(10, 5))
        metodos = [r["metodo"] for r in resultados]
        medianas = [r["mediana_abs_delta_sr"] for r in resultados]
        bar_colors = [color_metodo(m) for m in metodos]
        xpos = np.arange(len(metodos))
        ax.bar(xpos, medianas, color=bar_colors, alpha=0.85, edgecolor="gray")
        ax.set_xticks(xpos)
        ax.set_xticklabels(ticklabels_mathtext(metodos), rotation=25, ha="right", fontsize=13)
        ax.set_ylabel("Mediana de |ΔSR| (%)", fontsize=15)
        ax.set_xlabel("Método", fontsize=15)
        ax.set_title("Figura 4.4b — Dispersión diaria por método\nMediana de la diferencia absoluta de SR entre días consecutivos", fontsize=15, pad=12)
        ax.tick_params(axis="both", labelsize=13)
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        path_png = os.path.join(out_dir, "dispersion_diaria_metodo.png")
        plt.savefig(path_png, dpi=220, bbox_inches="tight")
        plt.close()
        logger.info("Figura: %s", path_png)

    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sr_dir = os.path.join(project_root, "analysis", "sr")
    out_dir = os.path.join(project_root, "analysis", "stats")
    if len(sys.argv) > 1:
        sr_dir = os.path.abspath(sys.argv[1])
    if len(sys.argv) > 2:
        out_dir = os.path.abspath(sys.argv[2])
    ok = run(sr_dir, out_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
