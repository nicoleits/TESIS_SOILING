"""
Análisis de dispersión del módulo de masas (diferencias soiled − clean).

- Por fila: promedio (A+B+C)/3 (mg) y dispersión entre los tres vidrios (std A,B,C).
- Por periodo: count, media, std, CV(%), percentiles, rango P95−P05, y media de la std entre vidrios.

Salidas en analysis/pv_glasses/:
  - dispersion_masas_por_periodo.csv
  - dispersion_masas_report.md
  - dispersion_masas_boxplot.png
  - dispersion_masas_barras_error.png (opcional)

Uso (desde pv_glasses o TESIS_SOILING):
  python -m analysis.pv_glasses.dispersion_masas
  python dispersion_masas.py [--csv ruta]
"""
import os
import sys
import argparse
import pandas as pd
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

PERIODO_ORDEN = [
    "semanal", "2 semanas", "Mensual", "Trimestral", "Cuatrimestral", "Semestral", "1 año",
]
PERIODO_LABEL = {
    "semanal": "Weekly", "2 semanas": "2 Weeks", "Mensual": "Monthly",
    "Trimestral": "Quarterly", "Cuatrimestral": "4-Monthly",
    "Semestral": "Semiannual", "1 año": "1 Year",
}


def cargar_y_preparar(csv_path):
    """Carga el CSV de diferencias y añade promedio_mg y std_entre_vidrios por fila."""
    df = pd.read_csv(csv_path)
    for col in ["Diferencia_Masa_A_mg", "Diferencia_Masa_B_mg", "Diferencia_Masa_C_mg"]:
        if col not in df.columns:
            raise ValueError(f"Falta columna: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["promedio_mg"] = (
        df["Diferencia_Masa_A_mg"] + df["Diferencia_Masa_B_mg"] + df["Diferencia_Masa_C_mg"]
    ) / 3.0
    # Dispersión entre los tres vidrios en cada fila (std de A, B, C)
    df["std_entre_vidrios_mg"] = df.apply(
        lambda r: np.nanstd([r["Diferencia_Masa_A_mg"], r["Diferencia_Masa_B_mg"], r["Diferencia_Masa_C_mg"]]),
        axis=1,
    )
    return df


def dispersion_por_periodo(df):
    """Estadísticos de dispersión por periodo (sobre promedio_mg y std_entre_vidrios)."""
    filas = []
    for periodo, g in df.groupby("Periodo"):
        v = g["promedio_mg"].dropna()
        if len(v) == 0:
            continue
        std_v = v.std() if len(v) > 1 else 0.0
        cv = (100.0 * std_v / v.mean()) if v.mean() > 0 else np.nan
        std_entre = g["std_entre_vidrios_mg"].replace(0, np.nan).mean()
        if pd.isna(std_entre):
            std_entre = 0.0
        filas.append({
            "Periodo": periodo,
            "N": len(v),
            "Media_mg": round(v.mean(), 4),
            "Std_mg": round(std_v, 4),
            "CV_pct": round(cv, 2) if not np.isnan(cv) else np.nan,
            "Min_mg": round(v.min(), 4),
            "P05_mg": round(v.quantile(0.05), 4),
            "P25_mg": round(v.quantile(0.25), 4),
            "P50_mg": round(v.median(), 4),
            "P75_mg": round(v.quantile(0.75), 4),
            "P95_mg": round(v.quantile(0.95), 4),
            "Max_mg": round(v.max(), 4),
            "Rango_P95_P05_mg": round(v.quantile(0.95) - v.quantile(0.05), 4),
            "Media_std_entre_vidrios_mg": round(std_entre, 4),
        })
    res = pd.DataFrame(filas)
    orden = [p for p in PERIODO_ORDEN if p in res["Periodo"].values]
    res = res.set_index("Periodo").reindex(orden).reset_index()
    return res.dropna(subset=["N"])


def escribir_reporte_md(df_disp, out_path):
    """Escribe dispersion_masas_report.md con tabla y breve interpretación."""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Análisis de dispersión — Método gravimétrico (PV Glasses)\n\n")
        f.write("**Variable:** Diferencia de masa (soiled − clean) en mg. Por fila se usa el promedio (A+B+C)/3.\n\n")
        f.write("## Estadísticos por periodo de exposición\n\n")
        # Tabla markdown
        cols = ["Periodo", "N", "Media_mg", "Std_mg", "CV_pct", "Rango_P95_P05_mg", "Media_std_entre_vidrios_mg"]
        cols = [c for c in cols if c in df_disp.columns]
        sub = df_disp[cols]
        f.write("| " + " | ".join(str(c) for c in sub.columns) + " |\n")
        f.write("| " + " | ".join("---" for _ in sub.columns) + " |\n")
        for _, row in sub.iterrows():
            f.write("| " + " | ".join(str(row[c]) for c in sub.columns) + " |\n")
        f.write("\n**Notas:**\n")
        f.write("- **N:** número de mediciones (filas Fija a RC soiled) en ese periodo.\n")
        f.write("- **Media_mg:** media del promedio (A+B+C)/3 por medición.\n")
        f.write("- **Std_mg, CV_pct:** dispersión entre mediciones del mismo periodo.\n")
        f.write("- **Rango_P95_P05_mg:** diferencia entre percentil 95 y 5 (spread).\n")
        f.write("- **Media_std_entre_vidrios_mg:** promedio de la desviación estándar entre A, B y C en cada fila; indica variabilidad entre los tres vidrios en la misma medición.\n")


def grafico_boxplot(df_disp, out_path):
    """Boxplot de promedio_mg por periodo."""
    if plt is None or df_disp.empty:
        return
    labels = [PERIODO_LABEL.get(p, p) for p in df_disp["Periodo"]]
    # Necesitamos los datos crudos por periodo para el boxplot
    # df_disp solo tiene resúmenes; recargamos desde el CSV o pasamos df
    return  # boxplot requiere datos crudos; haremos bar con error en su lugar


def grafico_barras_error(df, df_disp, out_path):
    """Barras: media por periodo con barras de error ±1 std."""
    if plt is None or df_disp.empty:
        return
    orden = [p for p in PERIODO_ORDEN if p in df_disp["Periodo"].values]
    df_disp = df_disp.set_index("Periodo").reindex(orden).dropna(how="all").reset_index()
    labels = [PERIODO_LABEL.get(p, p) for p in df_disp["Periodo"]]
    medias = df_disp["Media_mg"].values
    stds = df_disp["Std_mg"].values
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    bars = ax.bar(x, medias, yerr=stds, capsize=5, color="#B8A9C9", edgecolor="#5D4E6D", linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Diferencia de masa — Media ± 1 std (mg)")
    ax.set_xlabel("Periodo de exposición")
    ax.set_title("Dispersión del soiling por periodo (método gravimétrico)\nMedia (A+B+C)/3 ± desv. estándar")
    ax.set_ylim(0, max(medias + stds) * 1.2 if len(medias) else 15)
    ax.grid(axis="y", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def grafico_boxplot_desde_df(df, out_path):
    """Boxplot con los datos crudos de df (promedio_mg por periodo)."""
    if plt is None or df.empty:
        return
    orden = [p for p in PERIODO_ORDEN if p in df["Periodo"].unique()]
    df_ord = df[df["Periodo"].isin(orden)].copy()
    df_ord["Periodo"] = pd.Categorical(df_ord["Periodo"], categories=orden, ordered=True)
    df_ord = df_ord.sort_values("Periodo")
    labels = [PERIODO_LABEL.get(p, p) for p in orden]
    data = [df_ord[df_ord["Periodo"] == p]["promedio_mg"].values for p in orden]
    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#B8A9C9")
        patch.set_edgecolor("#5D4E6D")
    ax.set_ylabel("Diferencia de masa (A+B+C)/3 (mg)")
    ax.set_xlabel("Periodo de exposición")
    ax.set_title("Dispersión del soiling por periodo (método gravimétrico)")
    plt.xticks(rotation=15, ha="right")
    ax.grid(axis="y", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def run(csv_path=None, out_dir=None):
    base = os.path.dirname(os.path.abspath(__file__))
    if csv_path is None:
        csv_path = os.path.join(base, "resultados_diferencias_masas.csv")
    if out_dir is None:
        out_dir = base
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"No se encontró: {csv_path}")

    df = cargar_y_preparar(csv_path)
    df_disp = dispersion_por_periodo(df)

    csv_out = os.path.join(out_dir, "dispersion_masas_por_periodo.csv")
    df_disp.to_csv(csv_out, index=False)
    print(f"CSV dispersión: {csv_out}")

    md_out = os.path.join(out_dir, "dispersion_masas_report.md")
    escribir_reporte_md(df_disp, md_out)
    print(f"Reporte: {md_out}")

    if plt is not None:
        png_barras = os.path.join(out_dir, "dispersion_masas_barras_error.png")
        grafico_barras_error(df, df_disp, png_barras)
        print(f"Gráfico barras: {png_barras}")
        png_box = os.path.join(out_dir, "dispersion_masas_boxplot.png")
        grafico_boxplot_desde_df(df, png_box)
        print(f"Gráfico boxplot: {png_box}")

    return df_disp


def main():
    parser = argparse.ArgumentParser(description="Análisis de dispersión del módulo de masas.")
    parser.add_argument("--csv", type=str, default=None, help="CSV de diferencias de masa.")
    parser.add_argument("--out", type=str, default=None, help="Directorio de salida.")
    args = parser.parse_args()
    run(csv_path=args.csv, out_dir=args.out)


if __name__ == "__main__":
    main()
