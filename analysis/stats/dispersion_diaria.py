"""
Figura 4.4b — Dispersión diaria por método.

Para cada método se calcula |ΔSR| día a día (diferencia absoluta entre días consecutivos)
y se resume con la mediana y el P95. Se grafica una barra por método (altura = mediana de |ΔSR|).

Interpretación: qué tan "saltón" es cada método día a día.

Entrada: analysis/sr/*.csv (mismo periodo que agregación semanal).
Salida: analysis/stats/dispersion_diaria_metodo.png, dispersion_diaria_metodo.csv

Uso (desde si_test con PYTHONPATH=TESIS_SOILING):
  python -m analysis.stats.dispersion_diaria
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

    if not resultados:
        logger.error("No se pudo calcular dispersión diaria.")
        return False

    df = pd.DataFrame(resultados)
    path_csv = os.path.join(out_dir, "dispersion_diaria_metodo.csv")
    df.to_csv(path_csv, index=False)
    logger.info("CSV: %s", path_csv)

    if MATPLOTLIB_AVAILABLE:
        fig, ax = plt.subplots(figsize=(10, 5))
        metodos = [r["metodo"] for r in resultados]
        medianas = [r["mediana_abs_delta_sr"] for r in resultados]
        colors = ["#D32F2F", "#FF6F00", "#388E3C", "#1976D2", "#7B1FA2", "#C2185B", "#0097A7"]
        bars = ax.bar(metodos, medianas, color=[colors[i % len(colors)] for i in range(len(metodos))],
                      alpha=0.85, edgecolor="gray")
        ax.set_ylabel("Mediana de |ΔSR| (%)", fontsize=12)
        ax.set_xlabel("Método", fontsize=12)
        ax.set_title("Figura 4.4b — Dispersión diaria por método\nMediana de la diferencia absoluta de SR entre días consecutivos", fontsize=12, pad=10)
        plt.xticks(rotation=25, ha="right")
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        path_png = os.path.join(out_dir, "dispersion_diaria_metodo.png")
        plt.savefig(path_png, dpi=150, bbox_inches="tight")
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
