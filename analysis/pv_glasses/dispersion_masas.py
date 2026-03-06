"""
Análisis de dispersión del módulo de masas (diferencias soiled − clean).

- Por fila: promedio (A+B+C)/3 (mg) y dispersión entre los tres vidrios (std A,B,C).
- Por periodo: count, media, std, CV(%), percentiles, rango P95−P05, y media de la std entre vidrios.

Salidas en analysis/pv_glasses/:
  - dispersion_promedio/: por_periodo.csv, report.md, boxplot.png, barras_error.png (con promedio A+B+C/3)
  - dispersion_sin_promedio/: misma estructura con un valor por vidrio por evento, sin promediar

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

# Área del vidrio (cm²): 4×3 cm. Densidad de masa superficial ρm = Δm / área (mg/cm²).
AREA_VIDRIO_CM2 = 12.0

PERIODO_ORDEN = [
    "semanal", "2 semanas", "Mensual", "Trimestral", "Cuatrimestral", "Semestral", "1 año",
]
PERIODO_LABEL = {
    "semanal": "Semanal", "2 semanas": "2 semanas", "Mensual": "Mensual",
    "Trimestral": "Trimestral", "Cuatrimestral": "Cuatrimestral",
    "Semestral": "Semestral", "1 año": "1 año",
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
    # Densidad de masa superficial ρm = Δm / área (mg/cm²)
    df["promedio_densidad_mg_cm2"] = df["promedio_mg"] / AREA_VIDRIO_CM2
    df["std_entre_vidrios_densidad"] = df["std_entre_vidrios_mg"] / AREA_VIDRIO_CM2
    return df


def cargar_y_preparar_sin_promedio(csv_path):
    """Formato largo: una fila por (evento, vidrio). No se promedian A, B, C."""
    df = pd.read_csv(csv_path)
    cols_masa = ["Diferencia_Masa_A_mg", "Diferencia_Masa_B_mg", "Diferencia_Masa_C_mg"]
    for col in cols_masa:
        if col not in df.columns:
            raise ValueError(f"Falta columna: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    rows = []
    for vidrio, col in zip(["A", "B", "C"], cols_masa):
        sub = df[["Periodo", col]].copy()
        sub = sub.rename(columns={col: "Diferencia_mg"})
        sub["Vidrio"] = vidrio
        sub = sub.dropna(subset=["Diferencia_mg"])
        sub = sub[sub["Diferencia_mg"] >= 0]  # excluir negativos; 0 puede ser ausente
        rows.append(sub)
    long = pd.concat(rows, ignore_index=True)
    long["densidad_mg_cm2"] = long["Diferencia_mg"] / AREA_VIDRIO_CM2
    return long


def dispersion_por_periodo_sin_promedio(df_long):
    """Estadísticos por periodo sobre valores individuales de cada vidrio (sin promediar A+B+C)."""
    filas = []
    for periodo, g in df_long.groupby("Periodo"):
        v = g["Diferencia_mg"].dropna()
        d = g["densidad_mg_cm2"].dropna()
        if len(v) == 0:
            continue
        std_v = v.std() if len(v) > 1 else 0.0
        std_d = d.std() if len(d) > 1 else 0.0
        cv = (100.0 * std_v / v.mean()) if v.mean() > 0 else np.nan
        filas.append({
            "Periodo": periodo,
            "N_puntos": len(v),
            "Media_mg": round(v.mean(), 4),
            "Std_mg": round(std_v, 4),
            "Media_densidad_mg_cm2": round(d.mean(), 4),
            "Std_densidad_mg_cm2": round(std_d, 4),
            "CV_pct": round(cv, 2) if not np.isnan(cv) else np.nan,
            "Min_mg": round(v.min(), 4),
            "P05_mg": round(v.quantile(0.05), 4),
            "P25_mg": round(v.quantile(0.25), 4),
            "P50_mg": round(v.median(), 4),
            "P75_mg": round(v.quantile(0.75), 4),
            "P95_mg": round(v.quantile(0.95), 4),
            "Max_mg": round(v.max(), 4),
            "Rango_P95_P05_mg": round(v.quantile(0.95) - v.quantile(0.05), 4),
        })
    res = pd.DataFrame(filas)
    orden = [p for p in PERIODO_ORDEN if p in res["Periodo"].values]
    res = res.set_index("Periodo").reindex(orden).reset_index()
    return res.dropna(subset=["N_puntos"])


def dispersion_por_periodo(df):
    """Estadísticos de dispersión por periodo (sobre promedio_mg y densidad ρm = Δm/área)."""
    filas = []
    for periodo, g in df.groupby("Periodo"):
        v = g["promedio_mg"].dropna()
        d = g["promedio_densidad_mg_cm2"].dropna()
        if len(v) == 0:
            continue
        std_v = v.std() if len(v) > 1 else 0.0
        std_d = d.std() if len(d) > 1 else 0.0
        cv = (100.0 * std_v / v.mean()) if v.mean() > 0 else np.nan
        std_entre = g["std_entre_vidrios_mg"].replace(0, np.nan).mean()
        if pd.isna(std_entre):
            std_entre = 0.0
        filas.append({
            "Periodo": periodo,
            "N_mediciones": len(v),
            "Media_mg": round(v.mean(), 4),
            "Std_mg": round(std_v, 4),
            "Media_densidad_mg_cm2": round(d.mean(), 4),
            "Std_densidad_mg_cm2": round(std_d, 4),
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
    return res.dropna(subset=["N_mediciones"])


def escribir_reporte_md(df_disp, out_path):
    """Escribe dispersion_masas_report.md con tabla y breve interpretación."""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Análisis de dispersión — Método gravimétrico (PV Glasses)\n\n")
        f.write("**Variable:** Diferencia de masa (soiled − clean) en mg. Por fila se usa el promedio (A+B+C)/3.  \n")
        f.write("**Gráficos:** en densidad de masa superficial ρm = Δm/12 (mg/cm²), área vidrio 4×3 cm.\n\n")
        f.write("## Estadísticos por periodo de exposición\n\n")
        # Tabla markdown
        cols = ["Periodo", "N_mediciones", "Media_mg", "Std_mg", "CV_pct", "Rango_P95_P05_mg", "Media_std_entre_vidrios_mg"]
        cols = [c for c in cols if c in df_disp.columns]
        sub = df_disp[cols]
        f.write("| " + " | ".join(str(c) for c in sub.columns) + " |\n")
        f.write("| " + " | ".join("---" for _ in sub.columns) + " |\n")
        for _, row in sub.iterrows():
            f.write("| " + " | ".join(str(row[c]) for c in sub.columns) + " |\n")
        f.write("\n**Notas:**\n")
        f.write("- **N_mediciones:** número de eventos de pesada (filas) en ese periodo; cada fila = una fecha de llegada y ya promedia los 3 vidrios (A+B+C)/3. No es el número de vidrios.\n")
        f.write("- **Media_mg:** media del promedio (A+B+C)/3 por medición.\n")
        f.write("- **Std_mg, CV_pct:** dispersión entre mediciones del mismo periodo.\n")
        f.write("- **Rango_P95_P05_mg:** diferencia entre percentil 95 y 5 (spread).\n")
        f.write("- **Media_std_entre_vidrios_mg:** promedio de la desviación estándar entre A, B y C en cada fila; indica variabilidad entre los tres vidrios en la misma medición.\n")


def escribir_reporte_md_sin_promedio(df_disp, out_path):
    """Reporte para el análisis sin promediar (un valor por vidrio por evento)."""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Análisis de dispersión — Método gravimétrico (PV Glasses) — Sin promediar vidrios\n\n")
        f.write("**Variable:** Diferencia de masa (soiled − clean) en mg, **por vidrio** (A, B, C). No se promedian los tres vidrios; cada medición aporta hasta 3 puntos (uno por vidrio).  \n")
        f.write("**Gráficos:** densidad ρm = Δm/12 (mg/cm²), área 4×3 cm.\n\n")
        f.write("## Estadísticos por periodo de exposición\n\n")
        cols = ["Periodo", "N_puntos", "Media_mg", "Std_mg", "Media_densidad_mg_cm2", "Std_densidad_mg_cm2", "CV_pct", "Rango_P95_P05_mg"]
        cols = [c for c in cols if c in df_disp.columns]
        sub = df_disp[cols]
        f.write("| " + " | ".join(str(c) for c in sub.columns) + " |\n")
        f.write("| " + " | ".join("---" for _ in sub.columns) + " |\n")
        for _, row in sub.iterrows():
            f.write("| " + " | ".join(str(row[c]) for c in sub.columns) + " |\n")
        f.write("\n**Notas:**\n")
        f.write("- **N_puntos:** número de valores (evento × vidrio); hasta 3 por evento si los tres vidrios están presentes.\n")
        f.write("- **Media_mg / Media_densidad_mg_cm2:** media sobre todos los valores individuales (A, B, C) en ese periodo.\n")


def grafico_boxplot(df_disp, out_path):
    """Boxplot de promedio_mg por periodo."""
    if plt is None or df_disp.empty:
        return
    labels = [PERIODO_LABEL.get(p, p) for p in df_disp["Periodo"]]
    # Necesitamos los datos crudos por periodo para el boxplot
    # df_disp solo tiene resúmenes; recargamos desde el CSV o pasamos df
    return  # boxplot requiere datos crudos; haremos bar con error en su lugar


def grafico_barras_error(df, df_disp, out_path):
    """Barras: densidad de masa superficial ρm = Δm/12 por periodo, ±1 std."""
    if plt is None or df_disp.empty:
        return
    orden = [p for p in PERIODO_ORDEN if p in df_disp["Periodo"].values]
    df_disp = df_disp.set_index("Periodo").reindex(orden).dropna(how="all").reset_index()
    labels = [PERIODO_LABEL.get(p, p) for p in df_disp["Periodo"]]
    medias = df_disp["Media_densidad_mg_cm2"].values
    stds = df_disp["Std_densidad_mg_cm2"].values
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    ax.bar(x, medias, yerr=stds, capsize=5, color="#B8A9C9", edgecolor="#5D4E6D", linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Densidad de masa superficial — Media ± 1 std (mg/cm²)")
    ax.set_xlabel("Periodo de exposición")
    ax.set_title("Dispersión del soiling por periodo (método gravimétrico)\nρm = Δm/12 (mg/cm²), media (A+B+C)/3 ± desv. estándar")
    ax.set_ylim(0, max(medias + stds) * 1.2 if len(medias) else 5)
    ax.grid(axis="y", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def grafico_boxplot_desde_df(df, out_path):
    """Boxplot con los datos crudos: densidad de masa superficial ρm = Δm/12 (mg/cm²) por periodo."""
    if plt is None or df.empty:
        return
    orden = [p for p in PERIODO_ORDEN if p in df["Periodo"].unique()]
    df_ord = df[df["Periodo"].isin(orden)].copy()
    df_ord["Periodo"] = pd.Categorical(df_ord["Periodo"], categories=orden, ordered=True)
    df_ord = df_ord.sort_values("Periodo")
    labels = [PERIODO_LABEL.get(p, p) for p in orden]
    data = [df_ord[df_ord["Periodo"] == p]["promedio_densidad_mg_cm2"].values for p in orden]
    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#B8A9C9")
        patch.set_edgecolor("#5D4E6D")
    ax.set_ylabel("Densidad de masa superficial ρm (mg/cm²)")
    ax.set_xlabel("Periodo de exposición")
    ax.set_title("Dispersión del soiling por periodo (método gravimétrico)\nρm = Δm/12")
    plt.xticks(rotation=15, ha="right")
    ax.grid(axis="y", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def grafico_barras_error_sin_promedio(df_disp, out_path):
    """Barras: media ± std de densidad por periodo (valores por vidrio, sin promediar)."""
    if plt is None or df_disp.empty:
        return
    orden = [p for p in PERIODO_ORDEN if p in df_disp["Periodo"].values]
    df_disp = df_disp.set_index("Periodo").reindex(orden).dropna(how="all").reset_index()
    labels = [PERIODO_LABEL.get(p, p) for p in df_disp["Periodo"]]
    medias = df_disp["Media_densidad_mg_cm2"].values
    stds = df_disp["Std_densidad_mg_cm2"].values
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(labels))
    ax.bar(x, medias, yerr=stds, capsize=5, color="#7EB8DA", edgecolor="#2E5F7A", linewidth=1.2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Densidad de masa superficial — Media ± 1 std (mg/cm²)")
    ax.set_xlabel("Periodo de exposición")
    ax.set_title("Dispersión del soiling por periodo (sin promediar vidrios)\nρm = Δm/12, un valor por vidrio por evento")
    ax.set_ylim(0, max(medias + stds) * 1.2 if len(medias) else 5)
    ax.grid(axis="y", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()


def grafico_boxplot_sin_promedio(df_long, out_path):
    """Boxplot: densidad por periodo con un punto por vidrio por evento (sin promediar)."""
    if plt is None or df_long.empty:
        return
    orden = [p for p in PERIODO_ORDEN if p in df_long["Periodo"].unique()]
    df_ord = df_long[df_long["Periodo"].isin(orden)].copy()
    df_ord["Periodo"] = pd.Categorical(df_ord["Periodo"], categories=orden, ordered=True)
    df_ord = df_ord.sort_values("Periodo")
    labels = [PERIODO_LABEL.get(p, p) for p in orden]
    data = [df_ord[df_ord["Periodo"] == p]["densidad_mg_cm2"].values for p in orden]
    fig, ax = plt.subplots(figsize=(8, 5))
    bp = ax.boxplot(data, tick_labels=labels, patch_artist=True)
    for patch in bp["boxes"]:
        patch.set_facecolor("#7EB8DA")
        patch.set_edgecolor("#2E5F7A")
    ax.set_ylabel("Densidad de masa superficial ρm (mg/cm²)")
    ax.set_xlabel("Periodo de exposición")
    ax.set_title("Dispersión del soiling por periodo (sin promediar vidrios)\nρm = Δm/12, un valor por vidrio")
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

    # Análisis con promedio (A+B+C)/3 → carpeta dispersion_promedio
    subdir_promedio = os.path.join(out_dir, "dispersion_promedio")
    os.makedirs(subdir_promedio, exist_ok=True)

    df = cargar_y_preparar(csv_path)
    df_disp = dispersion_por_periodo(df)

    csv_out = os.path.join(subdir_promedio, "dispersion_masas_por_periodo.csv")
    df_disp.to_csv(csv_out, index=False)
    print(f"CSV dispersión (promedio): {csv_out}")

    md_out = os.path.join(subdir_promedio, "dispersion_masas_report.md")
    escribir_reporte_md(df_disp, md_out)
    print(f"Reporte (promedio): {md_out}")

    if plt is not None:
        png_barras = os.path.join(subdir_promedio, "dispersion_masas_barras_error.png")
        grafico_barras_error(df, df_disp, png_barras)
        print(f"Gráfico barras (promedio): {png_barras}")
        png_box = os.path.join(subdir_promedio, "dispersion_masas_boxplot.png")
        grafico_boxplot_desde_df(df, png_box)
        print(f"Gráfico boxplot (promedio): {png_box}")

    # Mismo análisis sin promediar los vidrios → carpeta aparte
    subdir_sin_promedio = os.path.join(out_dir, "dispersion_sin_promedio")
    df_long = cargar_y_preparar_sin_promedio(csv_path)
    df_disp_sp = dispersion_por_periodo_sin_promedio(df_long)
    if not df_disp_sp.empty:
        os.makedirs(subdir_sin_promedio, exist_ok=True)
        csv_sp = os.path.join(subdir_sin_promedio, "dispersion_masas_por_periodo.csv")
        df_disp_sp.to_csv(csv_sp, index=False)
        print(f"CSV dispersión (sin promediar): {csv_sp}")
        md_sp = os.path.join(subdir_sin_promedio, "dispersion_masas_report.md")
        escribir_reporte_md_sin_promedio(df_disp_sp, md_sp)
        print(f"Reporte (sin promediar): {md_sp}")
        if plt is not None:
            grafico_barras_error_sin_promedio(df_disp_sp, os.path.join(subdir_sin_promedio, "dispersion_masas_barras_error.png"))
            grafico_boxplot_sin_promedio(df_long, os.path.join(subdir_sin_promedio, "dispersion_masas_boxplot.png"))
            print(f"Gráficos (sin promediar): {subdir_sin_promedio}")

    return df_disp


def main():
    parser = argparse.ArgumentParser(description="Análisis de dispersión del módulo de masas.")
    parser.add_argument("--csv", type=str, default=None, help="CSV de diferencias de masa.")
    parser.add_argument("--out", type=str, default=None, help="Directorio de salida.")
    args = parser.parse_args()
    run(csv_path=args.csv, out_dir=args.out)


if __name__ == "__main__":
    main()
