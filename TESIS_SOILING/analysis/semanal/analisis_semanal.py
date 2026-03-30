"""
Análisis de los resultados de agregación semanal SR (Q25).

Lee los CSV generados por agregacion_q25.py y produce:
  - Matriz de correlación entre metodologías (sobre semanas comunes)
  - Pares de correlación (instrumento_i, instrumento_j, r, p-value)
  - Reporte en Markdown con resumen descriptivo, correlaciones y dispersión

Salidas en analysis/semanal/:
  - correlacion_semanal.csv       : pares (instrumento_i, instrumento_j, r, p_value)
  - correlacion_semanal_matrix.csv : matriz de correlación (ancho)
  - analisis_semanal_report.md    : reporte de análisis

Uso (desde si_test con PYTHONPATH=TESIS_SOILING):
  python -m analysis.semanal.analisis_semanal
  python -m analysis.semanal.analisis_semanal [semanal_dir]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run(semanal_dir):
    semanal_dir = os.path.abspath(semanal_dir)
    path_ancho = os.path.join(semanal_dir, "sr_semanal_q25.csv")
    path_disp = os.path.join(semanal_dir, "dispersion_semanal.csv")

    if not os.path.isfile(path_ancho):
        logger.error("No encontrado: %s. Ejecute antes: python -m analysis.semanal.agregacion_q25", path_ancho)
        return False

    df = pd.read_csv(path_ancho)
    if "semana" in df.columns:
        df = df.set_index("semana")
    df.index = pd.to_datetime(df.index)
    # Solo columnas numéricas (metodologías)
    cols = [c for c in df.columns if df[c].dtype in (np.float64, np.int64, float)]
    if len(cols) < 2:
        logger.warning("Se necesitan al menos 2 metodologías para correlación.")
        return False

    df = df[cols].dropna(how="all")

    # --- Correlación entre pares (solo semanas con datos en ambos) ---
    pairs = []
    for i, a in enumerate(cols):
        for j, b in enumerate(cols):
            if i >= j:
                continue
            sub = df[[a, b]].dropna()
            if len(sub) < 5:
                continue
            r, p = stats.pearsonr(sub[a], sub[b])
            pairs.append({"instrumento_i": a, "instrumento_j": b, "r": round(r, 4), "p_value": round(p, 4)})

    df_pairs = pd.DataFrame(pairs)
    path_corr = os.path.join(semanal_dir, "correlacion_semanal.csv")
    df_pairs.to_csv(path_corr, index=False)
    logger.info("Correlación pares: %s", path_corr)

    # Matriz de correlación
    corr_matrix = df[cols].corr()
    path_matrix = os.path.join(semanal_dir, "correlacion_semanal_matrix.csv")
    corr_matrix.to_csv(path_matrix)
    logger.info("Matriz correlación: %s", path_matrix)

    # --- Reporte ---
    lineas = [
        "# Análisis de agregación semanal SR (Q25)",
        "",
        "Resultados del resample semanal (Q25) por metodología y su análisis estadístico.",
        "",
        "## 1. Resumen",
        "",
        f"- **Metodologías:** {len(cols)}",
        f"- **Semanas (máx.):** {len(df)}",
        "- **Periodo:** mismo que intercomparación SR (config: PERIODO_ANALISIS_INICIO/FIN, RefCells hasta REFCELLS_FECHA_MAX).",
        "",
        "## 2. Estadísticos descriptivos (SR Q25 semanal)",
        "",
    ]

    if os.path.isfile(path_disp):
        disp = pd.read_csv(path_disp)
        lineas.append("| Instrumento | n_semanas | media | std | CV (%) | min | p50 | max |")
        lineas.append("|------------|-----------|-------|-----|--------|-----|-----|-----|")
        for _, row in disp.iterrows():
            lineas.append(
                "| {} | {} | {:.2f} | {:.2f} | {:.2f} | {:.2f} | {:.2f} | {:.2f} |".format(
                    row["instrumento"], int(row["n_semanas"]), row["mean"], row["std"],
                    row["cv_pct"], row["min"], row["p50"], row["max"]
                )
            )
        lineas.extend(["", ""])
    else:
        lineas.append("*No se encontró dispersion_semanal.csv.*")
        lineas.extend(["", ""])

    lineas.extend([
        "## 3. Correlación entre metodologías (Pearson, semanas comunes)",
        "",
        "Pares con |r| ≥ 0,7:",
        "",
        "| Metodología i | Metodología j | r | p-value |",
        "|---------------|---------------|-----|---------|",
    ])

    if not df_pairs.empty:
        strong = df_pairs[df_pairs["r"].abs() >= 0.7].sort_values("r", key=abs, ascending=False)
        for _, row in strong.iterrows():
            lineas.append(f"| {row['instrumento_i']} | {row['instrumento_j']} | {row['r']:.3f} | {row['p_value']:.4f} |")
        if strong.empty:
            lineas.append("| — | — | Ningún par con |r| ≥ 0,7 | — |")
    lineas.extend(["", ""])

    lineas.extend([
        "## 4. Interpretación breve",
        "",
        "- **Dispersión (CV):** mayor CV indica más variabilidad del SR Q25 semanal entre semanas para esa metodología.",
        "- **Correlación:** valores de r próximos a 1 indican que dos metodologías evolucionan de forma similar en el tiempo (semanas comunes).",
        "- Los resultados semanales (Q25) permiten comparar tendencias de soiling entre instrumentos con menor ruido que la serie diaria.",
        "",
    ])

    path_report = os.path.join(semanal_dir, "analisis_semanal_report.md")
    with open(path_report, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    logger.info("Reporte: %s", path_report)

    return True


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    semanal_dir = os.path.join(project_root, "analysis", "semanal")
    if len(sys.argv) > 1:
        semanal_dir = os.path.abspath(sys.argv[1])
    ok = run(semanal_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
